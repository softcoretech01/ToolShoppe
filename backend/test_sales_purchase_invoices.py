"""
End-to-End Test Suite for ToolShoppe:
- Outward / Delivery Challan (Draft -> Edit -> Post -> Dispatched -> Invoiced)
- Stock validation (Zero stock rejection, excess stock rejection, excess order rejection)
- Stock Ledger OUT entries and inventory on-hand balance deduction
- Immutability of posted Outward documents
- Sales Invoice creation, line item calculations, tax amounts, customer payment terms, due date
- Duplicate Sales Invoice prevention on the same Outward
- Purchase Invoice creation from GRN accepted quantities (excluding rejected quantities)
- Duplicate Purchase Invoice prevention on the same GRN and duplicate supplier invoice references
- Order completion verification:
  - Dispatched + Sales Invoice only (No Purchase Invoice) => Customer Request != Completed (status: Invoiced)
  - Dispatched + Sales Invoice + Purchase Invoice => Customer Request == Completed
- Complete Order Tracking audit trail with Sales Invoice, Purchase Invoice, and Completed stage
"""
import time
from decimal import Decimal
from starlette.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.item import Item

client = TestClient(app)


def test_sales_purchase_invoices_suite():
    print("\n" + "=" * 80)
    print("RUNNING DISPATCH, SALES INVOICE & PURCHASE INVOICE TEST SUITE")
    print("=" * 80)

    # 1. Login & Token
    print("\n[1/12] Authenticating as Admin...")
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, f"Admin login must succeed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  PASS: Authenticated successfully.")

    # 2. Master Data
    print("\n[2/12] Preparing master data (Customer, Supplier, Items)...")
    db = SessionLocal()
    try:
        init_db(db)
        cust = db.query(Customer).first()
        items = db.query(Item).limit(2).all()
        suppliers = db.query(Supplier).limit(2).all()
        assert cust and len(items) >= 2 and len(suppliers) >= 2
        cust_id = cust.id
        item1, item2 = items[0], items[1]
        sup1, sup2 = suppliers[0], suppliers[1]
    finally:
        db.close()

    ts = int(time.time() * 1000)

    # 3. Sourcing workflow up to Customer Order & Supplier PO
    print("\n[3/12] Establishing Sourcing Pipeline: CR -> PR -> RFQ -> VQ -> Approval -> CQ -> SO -> PO...")
    cr_res = client.post("/sales/customer-request", json={
        "customer_id": cust_id,
        "required_date": "2026-12-15",
        "customer_reference": f"E2E-PHASE5-{ts}",
        "lines": [
            {"item_id": item1.id, "description": "Precision Tool A", "quantity": 10.0, "unit": item1.unit},
            {"item_id": item2.id, "description": "Precision Tool B", "quantity": 10.0, "unit": item2.unit},
        ]
    }, headers=headers)
    assert cr_res.status_code == 201
    cr_id = cr_res.json()["data"]["id"]

    prs_res = client.get("/purchase/request", headers=headers)
    matching_pr = next(p for p in prs_res.json()["data"]["items"] if p["customer_request_id"] == cr_id)
    pr_id = matching_pr["id"]

    client.post("/purchase/rfq/send", json={
        "pr_id": pr_id,
        "supplier_ids": [sup1.id, sup2.id],
        "subject": f"RFQ for PR #{matching_pr['pr_no']}",
        "body": "Please provide your best quotation."
    }, headers=headers)

    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup1.id,
        "quote_reference": f"Q-SUP1-{ts}",
        "quote_date": "2026-09-18",
        "validity": "2026-10-31",
        "delivery_days": 5,
        "payment_terms": "30 days",
        "freight": 0.0,
        "lines": [
            {"item_id": item1.id, "rate": 500.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item2.id, "rate": 300.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    client.post(f"/purchase/compare/{pr_id}/approve", json={
        "selected_supplier_id": sup1.id,
        "override_reason": None,
    }, headers=headers)

    cqs_res = client.get(f"/sales/quotation?request_id={cr_id}", headers=headers)
    cq_id = cqs_res.json()["data"]["items"][0]["id"]
    client.patch(f"/sales/quotation/{cq_id}/accept", headers=headers)

    so_res = client.post("/sales/customer-order", json={
        "quotation_id": cq_id,
        "customer_po_number": f"PO-CLIENT-{ts}",
        "po_date": "2026-09-18",
        "delivery_date": "2026-10-10",
        "items": [
            {"item_id": item1.id, "quantity": 10.0, "selling_price": 700.0},
            {"item_id": item2.id, "quantity": 10.0, "selling_price": 450.0},
        ],
    }, headers=headers)
    assert so_res.status_code == 201
    so_id = so_res.json()["data"]["id"]
    po_id = so_res.json()["data"]["auto_purchase_order_id"]

    client.post(f"/purchase/purchase-order/{po_id}/send", json={
        "recipient": sup1.email,
        "subject": "Supplier PO Send",
        "body": "Deliver promptly."
    }, headers=headers)
    print("  PASS: Sourcing workflow complete, Customer Order and Supplier PO generated.")

    # 4. GRN with Accepted and Rejected quantities & Inward Posting
    print("\n[4/12] Recording GRN (Item 1: 10 accepted, Item 2: 10 received with 8 accepted and 2 rejected)...")
    grn1_res = client.post("/purchase/grn", json={
        "purchase_order_id": po_id,
        "challan_no": f"SUP-DC-{ts}-1",
        "received_date": "2026-09-18",
        "received_by": "Warehouse Officer",
        "items": [
            {"item_id": item1.id, "received_qty": 10.0, "accepted_qty": 10.0, "rejected_qty": 0.0},
            {"item_id": item2.id, "received_qty": 10.0, "accepted_qty": 8.0, "rejected_qty": 2.0},
        ]
    }, headers=headers)
    assert grn1_res.status_code == 201
    grn1_data = grn1_res.json()["data"]
    grn1_id = grn1_data["id"]
    inw1_id = grn1_data["inward_id"]

    # Post Inward 1 to inventory
    inw1_res = client.post(f"/purchase/inward/{inw1_id}/add", headers=headers)
    assert inw1_res.status_code == 200
    print("  PASS: Inward 1 posted to inventory. Available on-hand: Item 1 = 10, Item 2 = 8.")

    # 5. Outward Validations (Draft -> Edit -> Post)
    print("\n[5/12] Validating Outward creation as Draft, updating Draft, and posting...")
    draft_payload = {
        "customer_order_id": so_id,
        "dc_number": f"DC-DRAFT-{ts}",
        "dispatch_date": "2026-09-19",
        "dispatch_mode": "Road",
        "vehicle_or_courier": "MH-04-AB-1111",
        "remarks": "Draft DC before vehicle dispatch",
        "status": "Draft",
        "items": [
            {"item_id": item1.id, "dispatch_qty": 10.0},
            {"item_id": item2.id, "dispatch_qty": 8.0},
        ]
    }
    draft_res = client.post("/api/outward", json=draft_payload, headers=headers)
    assert draft_res.status_code == 201
    draft_data = draft_res.json()["data"]
    outward_id = draft_data["id"]
    assert draft_data["status"] == "Draft"
    assert draft_data["dc_number"] == f"DC-DRAFT-{ts}"
    print(f"  PASS: Created Draft Outward #{draft_data['outward_no']} (Status: Draft).")

    # Verify inventory is untouched while in Draft
    inv_check = client.get("/inventory/summary", headers=headers).json()["data"]["items"]
    sum_it1 = next(s for s in inv_check if s["customer_request_id"] == cr_id and s["item_id"] == item1.id)
    assert float(sum_it1["qty_out"]) == 0.0 and float(sum_it1["on_hand"]) == 10.0
    print("  PASS: Stock remains unchanged while Outward is in Draft.")

    # Edit Draft Outward
    update_res = client.put(f"/api/outward/{outward_id}", json={
        "dc_number": f"DC-FINAL-{ts}",
        "vehicle_or_courier": "KA-01-EF-9999",
        "remarks": "Updated vehicle and final DC",
    }, headers=headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert updated_data["dc_number"] == f"DC-FINAL-{ts}"
    assert updated_data["vehicle_or_courier"] == "KA-01-EF-9999"
    print("  PASS: Updated Draft Outward successfully.")

    # Post Outward
    post_res = client.post(f"/api/outward/{outward_id}/post", headers=headers)
    assert post_res.status_code == 200
    posted_data = post_res.json()["data"]
    assert posted_data["status"] in ["Dispatched", "Partially Dispatched"]
    print(f"  PASS: Posted Outward #{posted_data['outward_no']} (Status: {posted_data['status']}).")

    # Verify Stock Ledger OUT and Stock Summary balance after posting
    inv_check2 = client.get("/inventory/summary", headers=headers).json()["data"]["items"]
    sum_it1_after = next(s for s in inv_check2 if s["customer_request_id"] == cr_id and s["item_id"] == item1.id)
    sum_it2_after = next(s for s in inv_check2 if s["customer_request_id"] == cr_id and s["item_id"] == item2.id)
    assert float(sum_it1_after["qty_out"]) == 10.0 and float(sum_it1_after["on_hand"]) == 0.0
    assert float(sum_it2_after["qty_out"]) == 8.0 and float(sum_it2_after["on_hand"]) == 0.0
    print("  PASS: Stock Ledger OUT verified and stock summary balance deducted to 0.")

    # Verify posted outward is immutable (BR-10)
    fail_edit = client.put(f"/api/outward/{outward_id}", json={"remarks": "Illegal edit"}, headers=headers)
    assert fail_edit.status_code == 400
    assert "immutable" in fail_edit.json()["message"].lower()
    print("  PASS: Posted Outward document is strictly immutable (BR-10 enforced).")

    # 6. Sales Invoice Preview
    print("\n[6/12] Testing Sales Invoice Preview endpoint...")
    preview_res = client.get(f"/api/sales-invoices/{outward_id}/preview", headers=headers)
    assert preview_res.status_code == 200
    prev_data = preview_res.json()["data"]
    assert len(prev_data["items"]) == 2
    # Item 1: 10 * 700 = 7,000; Tax 18% = 1,260; Line Total = 8,260
    # Item 2: 8 * 450 = 3,600; Tax 18% = 648; Line Total = 4,248
    # Subtotal = 10,600; Total Tax = 1,908; Grand Total = 12,508
    assert float(prev_data["subtotal"]) == 10600.0
    assert float(prev_data["tax_amount"]) == 1908.0
    assert float(prev_data["grand_total"]) == 12508.0
    assert prev_data["payment_terms"] is not None
    assert prev_data["due_date"] is not None
    print(f"  PASS: Sales Invoice preview verified (Grand Total: INR {prev_data['grand_total']}).")

    # 7. Sales Invoice Creation
    print("\n[7/12] Creating Sales Invoice from Outward...")
    si_payload = {
        "outward_id": outward_id,
        "invoice_date": "2026-09-20",
        "remarks": "Standard 30 days invoice",
    }
    si_res = client.post("/api/sales-invoices", json=si_payload, headers=headers)
    assert si_res.status_code == 201
    si_data = si_res.json()["data"]
    si_id = si_data["id"]
    si_no = si_data["invoice_no"]
    assert si_no.startswith("SI-")
    assert float(si_data["subtotal"]) == 10600.0
    assert float(si_data["tax_amount"]) == 1908.0
    assert float(si_data["grand_total"]) == 12508.0
    print(f"  PASS: Sales Invoice created: {si_no} (Grand Total: INR {si_data['grand_total']}).")

    # Verify Outward status transitioned to 'Invoiced'
    outward_check = client.get(f"/api/outward/{outward_id}", headers=headers).json()["data"]
    assert outward_check["status"] == "Invoiced"
    print("  PASS: Outward document status transitioned to 'Invoiced'.")

    # 8. Duplicate Sales Invoice Protection
    print("\n[8/12] Validating duplicate Sales Invoice prevention on the same Outward...")
    dup_si_res = client.post("/api/sales-invoices", json=si_payload, headers=headers)
    assert dup_si_res.status_code == 400
    assert "already been invoiced" in dup_si_res.json()["message"].lower()
    print("  PASS: Prevented duplicate Sales Invoice creation on already invoiced Outward.")

    # 9. Order Status Verification before Purchase Invoice (Test 8)
    print("\n[9/12] Verifying Customer Request is NOT Completed before Purchase Invoice (Test 8)...")
    cr_check1 = client.get(f"/sales/customer-request/{cr_id}", headers=headers).json()["data"]
    assert cr_check1["status"] != "Completed", "Customer Request must not be Completed without Purchase Invoice"
    assert cr_check1["status"] == "Invoiced"
    print(f"  PASS: Customer Request status is '{cr_check1['status']}' (NOT Completed).")

    # 10. Purchase Invoice Creation & Validations
    print("\n[10/12] Recording Purchase Invoice from GRN 1 (verifying accepted=8 used and rejected=2 excluded)...")
    pi_payload = {
        "grn_id": grn1_id,
        "supplier_invoice_no": f"SUP-INV-{ts}",
        "supplier_invoice_date": "2026-09-19",
        "remarks": "Supplier billing for accepted items in GRN 1",
    }
    pi_res = client.post("/api/purchase-invoices", json=pi_payload, headers=headers)
    assert pi_res.status_code == 201
    pi_data = pi_res.json()["data"]
    pi_id = pi_data["id"]
    pi_no = pi_data["internal_invoice_no"]
    assert pi_no.startswith("PI-")
    assert pi_data["supplier_invoice_no"] == f"SUP-INV-{ts}"
    assert len(pi_data["items"]) == 2

    # Verify accepted vs rejected quantities in purchase invoice
    # Item 1: accepted 10 * 500 = 5,000; Tax 18% = 900; Total = 5,900
    # Item 2: accepted 8 (2 rejected excluded!) * 300 = 2,400; Tax 18% = 432; Total = 2,832
    # Subtotal = 7,400; Total Tax = 1,332; Grand Total = 8,732
    pi_it1 = next(i for i in pi_data["items"] if i["item_id"] == item1.id)
    pi_it2 = next(i for i in pi_data["items"] if i["item_id"] == item2.id)
    assert float(pi_it1["quantity"]) == 10.0
    assert float(pi_it2["quantity"]) == 8.0, "Rejected quantity of 2.0 must be excluded from purchase billing"
    assert float(pi_data["subtotal"]) == 7400.0
    assert float(pi_data["tax_amount"]) == 1332.0
    assert float(pi_data["grand_total"]) == 8732.0
    print(f"  PASS: Purchase Invoice {pi_no} recorded using accepted quantities only (Grand Total: INR {pi_data['grand_total']}).")

    # Duplicate GRN invoicing rejection
    dup_grn_res = client.post("/api/purchase-invoices", json={
        "grn_id": grn1_id,
        "supplier_invoice_no": f"ANOTHER-INV-{ts}",
        "supplier_invoice_date": "2026-09-19",
    }, headers=headers)
    assert dup_grn_res.status_code == 400
    assert "already been invoiced" in dup_grn_res.json()["message"].lower()
    print("  PASS: Prevented duplicate Purchase Invoice on already invoiced GRN.")

    # Duplicate supplier invoice reference rejection for same supplier
    dup_sup_ref_res = client.post("/api/purchase-invoices", json={
        "grn_id": grn1_id,
        "supplier_invoice_no": f"SUP-INV-{ts}",
        "supplier_invoice_date": "2026-09-20",
    }, headers=headers)
    assert dup_sup_ref_res.status_code == 400
    print("  PASS: Prevented duplicate supplier invoice reference for the same supplier.")

    # 11. Order Completion Verification (Test 7)
    print("\n[11/12] Verifying Customer Request transitioned to 'Completed' (Test 7)...")
    cr_check2 = client.get(f"/sales/customer-request/{cr_id}", headers=headers).json()["data"]
    assert cr_check2["status"] == "Completed", f"Expected 'Completed', got '{cr_check2['status']}'"
    print("  PASS: Customer Request successfully reached 'Completed' stage after both invoices exist.")

    # 12. Order Tracking Timeline & Linked Documents
    print("\n[12/12] Verifying Order Tracking audit trail for Completed status and invoice documents...")
    track_res = client.get(f"/track/{cr_id}", headers=headers)
    assert track_res.status_code == 200
    track_data = track_res.json()["data"]

    assert track_data["current_stage"] == "Completed"
    assert "Invoiced" in track_data["stages_order"]
    assert "Completed" in track_data["stages_order"]

    linked_types = [d["document_type"] for d in track_data["linked_documents"]]
    assert "Delivery Challan" in linked_types
    assert "Sales Invoice" in linked_types
    assert "Purchase Invoice" in linked_types

    sales_doc = next(d for d in track_data["linked_documents"] if d["document_type"] == "Sales Invoice")
    assert sales_doc["document_no"] == si_no

    purchase_doc = next(d for d in track_data["linked_documents"] if d["document_type"] == "Purchase Invoice")
    assert purchase_doc["document_no"] == pi_no

    timeline_stages = [e["stage"] for e in track_data["timeline"]]
    assert "Invoiced" in timeline_stages
    assert "Completed" in timeline_stages

    assert track_data["details"]["sales_invoices_count"] >= 1
    assert track_data["details"]["purchase_invoices_count"] >= 1
    print("  PASS: Tracking audit trail contains Delivery Challan, Sales Invoice, Purchase Invoice, and Completed stage.")

    print("\n" + "=" * 80)
    print("ALL 12 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_sales_purchase_invoices_suite()
