"""
End-to-End Test Suite for Goods Receipt (GRN), Inward, and Inventory Management:
- PO status validation (Sent / Partially Received requirement).
- GRN creation with accepted/rejected split.
- Rule 1: Accepted Qty + Rejected Qty == Received Qty.
- Rule 2: Received Qty <= Outstanding PO Qty.
- Rule 3: Auto Inward creation with accepted quantities only.
- Inward posting to inventory: Stock Ledger, Stock Summary, and Item Last Purchase Rate.
- Irreversible posting prevention (cannot double-add).
- Order Tracking audit trail with 'Stock In' stage and linked documents.
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


def test_inventory_management_suite():
    print("\n" + "=" * 75)
    print("RUNNING GOODS RECEIPT (GRN), INWARD & INVENTORY MANAGEMENT TEST SUITE")
    print("=" * 75)

    # 1. Login & Token
    print("\n[1/11] Authenticating as Admin...")
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, "Admin login must succeed"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  PASS: Authenticated successfully.")

    # 2. Setup Prerequisites: Customer, Items, Supplier
    print("\n[2/11] Preparing test master data...")
    db = SessionLocal()
    try:
        init_db(db)
        cust = db.query(Customer).first()
        items = db.query(Item).limit(2).all()
        suppliers = db.query(Supplier).limit(2).all()
        assert cust and len(items) >= 2 and len(suppliers) >= 2
        cust_id = cust.id
        item1, item2 = items[0], items[1]
        sup1 = suppliers[0]
        sup2 = suppliers[1]
    finally:
        db.close()

    ts = int(time.time() * 1000)

    # 3. Create Sourcing Workflow up to Supplier Purchase Order
    print("\n[3/11] Creating Customer Request and progressing to Supplier PO...")
    cr_res = client.post("/sales/customer-request", json={
        "customer_id": cust_id,
        "required_date": "2026-12-01",
        "customer_reference": f"GRN-TEST-{ts}",
        "lines": [
            {"item_id": item1.id, "description": "Precision Tool A", "quantity": 10.0, "unit": item1.unit},
            {"item_id": item2.id, "description": "Precision Tool B", "quantity": 20.0, "unit": item2.unit},
        ]
    }, headers=headers)
    assert cr_res.status_code == 201
    cr_data = cr_res.json()["data"]
    cr_id = cr_data["id"]

    # Retrieve Auto PR
    prs_res = client.get("/purchase/request", headers=headers)
    matching_pr = next(p for p in prs_res.json()["data"]["items"] if p["customer_request_id"] == cr_id)
    pr_id = matching_pr["id"]

    # Send RFQ
    client.post("/purchase/rfq/send", json={
        "pr_id": pr_id,
        "supplier_ids": [sup1.id, sup2.id],
        "subject": f"RFQ for PR #{matching_pr['pr_no']}",
        "body": "Please provide your best quotation."
    }, headers=headers)

    # Submit Supplier Quotations
    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup1.id,
        "quote_reference": f"S1-Q-{ts}",
        "quote_date": "2026-09-18",
        "validity": "2026-10-31",
        "delivery_days": 5,
        "payment_terms": "30 days",
        "freight": 0.0,
        "lines": [
            {"item_id": item1.id, "rate": 500.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item2.id, "rate": 250.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup2.id,
        "quote_reference": f"S2-Q-{ts}",
        "quote_date": "2026-09-18",
        "validity": "2026-10-31",
        "delivery_days": 7,
        "payment_terms": "30 days",
        "freight": 0.0,
        "lines": [
            {"item_id": item1.id, "rate": 550.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item2.id, "rate": 280.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    # Approve comparison for Sup1
    appr_res = client.post(f"/purchase/compare/{pr_id}/approve", json={
        "selected_supplier_id": sup1.id,
        "override_reason": None,
    }, headers=headers)
    assert appr_res.status_code == 200

    # Auto Customer Quotation is created
    cqs_res = client.get(f"/sales/quotation?request_id={cr_id}", headers=headers)
    cq = cqs_res.json()["data"]["items"][0]
    cq_id = cq["id"]

    # Send Quotation and Record Acceptance
    client.post("/sales/quotation/send", json={
        "quotation_id": cq_id,
        "subject": "Customer Quotation",
        "body": "Please find attached quotation."
    }, headers=headers)

    accept_res = client.patch(f"/sales/quotation/{cq_id}/accept", headers=headers)
    assert accept_res.status_code == 200

    # Create Customer Order (Auto-creates Supplier PO)
    so_res = client.post("/sales/customer-order", json={
        "quotation_id": cq_id,
        "customer_po_number": f"CUST-PO-{ts}",
        "po_date": "2026-09-18",
        "delivery_date": "2026-10-10",
        "items": [
            {"item_id": item1.id, "quantity": 10.0, "selling_price": 600.0},
            {"item_id": item2.id, "quantity": 20.0, "selling_price": 300.0},
        ]
    }, headers=headers)
    assert so_res.status_code == 201
    so_data = so_res.json()["data"]
    po_id = so_data["auto_purchase_order_id"]
    po_no = so_data["auto_purchase_order_no"]
    print(f"  PASS: Sourcing workflow complete. PO created: {po_no} (ID: {po_id})")

    # 4. GRN Validation: Rejection when PO is in 'Created' status (not sent yet)
    print("\n[4/11] Validating GRN rejection when PO is not yet 'Sent'...")
    grn_payload_invalid_status = {
        "purchase_order_id": po_id,
        "challan_no": f"DC-{ts}-1",
        "received_date": "2026-09-18",
        "received_by": "Warehouse Supervisor",
        "items": [
            {"item_id": item1.id, "received_qty": 6.0, "accepted_qty": 5.0, "rejected_qty": 1.0},
            {"item_id": item2.id, "received_qty": 10.0, "accepted_qty": 10.0, "rejected_qty": 0.0},
        ]
    }
    grn_fail_res = client.post("/purchase/grn", json=grn_payload_invalid_status, headers=headers)
    assert grn_fail_res.status_code == 400, "Should reject GRN when PO is not Sent"
    print("  PASS: Rejected GRN creation for unsent PO.")

    # Send the Supplier PO
    print("\n[5/11] Dispatching Supplier PO...")
    po_send_res = client.post(f"/purchase/purchase-order/{po_id}/send", json={
        "recipient": sup1.email,
        "subject": f"PO {po_no}",
        "body": "Please deliver the goods as ordered."
    }, headers=headers)
    assert po_send_res.status_code == 200
    assert po_send_res.json()["data"]["status"] == "Sent"
    print("  PASS: Supplier PO status is now 'Sent'.")

    # 5. GRN Validation: Rule 1 (Accepted + Rejected == Received)
    print("\n[6/11] Validating Rule 1: Accepted + Rejected must equal Received...")
    bad_rule1_payload = {
        "purchase_order_id": po_id,
        "challan_no": f"DC-{ts}-1",
        "received_date": "2026-09-18",
        "received_by": "Warehouse Supervisor",
        "items": [
            {"item_id": item1.id, "received_qty": 6.0, "accepted_qty": 5.0, "rejected_qty": 0.0},  # 5 + 0 != 6
            {"item_id": item2.id, "received_qty": 10.0, "accepted_qty": 10.0, "rejected_qty": 0.0},
        ]
    }
    r1_fail_res = client.post("/purchase/grn", json=bad_rule1_payload, headers=headers)
    assert r1_fail_res.status_code == 400
    assert "accepted quantity" in r1_fail_res.json()["message"].lower()
    print("  PASS: Correctly rejected mismatched accepted + rejected quantities.")

    # 6. GRN Validation: Rule 2 (Received <= Outstanding)
    print("\n[7/11] Validating Rule 2: Received quantity exceeds Outstanding...")
    bad_rule2_payload = {
        "purchase_order_id": po_id,
        "challan_no": f"DC-{ts}-1",
        "received_date": "2026-09-18",
        "received_by": "Warehouse Supervisor",
        "items": [
            {"item_id": item1.id, "received_qty": 15.0, "accepted_qty": 15.0, "rejected_qty": 0.0},  # ordered 10
            {"item_id": item2.id, "received_qty": 10.0, "accepted_qty": 10.0, "rejected_qty": 0.0},
        ]
    }
    r2_fail_res = client.post("/purchase/grn", json=bad_rule2_payload, headers=headers)
    assert r2_fail_res.status_code == 400
    assert "exceeds outstanding quantity" in r2_fail_res.json()["message"].lower()
    print("  PASS: Correctly rejected delivery exceeding outstanding balance.")

    # 7. Partial Delivery 1: Create GRN-001 & Auto Inward INW-001
    print("\n[8/11] Creating Partial Delivery GRN 1 (Item 1: 6 rec / 5 acc / 1 rej; Item 2: 10 rec / 10 acc / 0 rej)...")
    valid_grn1_payload = {
        "purchase_order_id": po_id,
        "challan_no": f"DC-{ts}-1",
        "supplier_invoice_ref": f"INV-{ts}-A",
        "received_date": "2026-09-18",
        "received_by": "Warehouse Supervisor",
        "items": [
            {"item_id": item1.id, "received_qty": 6.0, "accepted_qty": 5.0, "rejected_qty": 1.0},
            {"item_id": item2.id, "received_qty": 10.0, "accepted_qty": 10.0, "rejected_qty": 0.0},
        ]
    }
    grn1_res = client.post("/purchase/grn", json=valid_grn1_payload, headers=headers)
    assert grn1_res.status_code == 201
    grn1_data = grn1_res.json()["data"]
    grn1_id = grn1_data["id"]
    inw1_id = grn1_data["inward_id"]
    assert grn1_data["status"] == "Received"
    assert inw1_id is not None
    print(f"  PASS: GRN 1 created ({grn1_data['grn_no']}). Auto Inward generated (ID: {inw1_id}).")

    # Check PO status updated to 'Partially Received'
    po_check = client.get(f"/purchase/purchase-order/{po_id}", headers=headers).json()["data"]
    assert po_check["status"] == "Partially Received"
    print("  PASS: Purchase Order status updated to 'Partially Received'.")

    # Verify Inward 1 contains ONLY accepted quantities
    inw1_res = client.get(f"/purchase/inward/{inw1_id}", headers=headers)
    assert inw1_res.status_code == 200
    inw1_data = inw1_res.json()["data"]
    assert inw1_data["status"] == "Pending"
    assert len(inw1_data["items"]) == 2
    item1_inw = next(i for i in inw1_data["items"] if i["item_id"] == item1.id)
    item2_inw = next(i for i in inw1_data["items"] if i["item_id"] == item2.id)
    assert Decimal(str(item1_inw["accepted_qty"])) == Decimal("5.00")
    assert Decimal(str(item2_inw["accepted_qty"])) == Decimal("10.00")
    print("  PASS: Inward document verified with accepted quantities only (rejected excluded).")

    # 8. Post Inward 1 to Inventory & Verify Ledger, Summary & Last Purchase Rate
    print("\n[9/11] Posting Inward 1 to Inventory...")
    add_res = client.post(f"/purchase/inward/{inw1_id}/add", headers=headers)
    assert add_res.status_code == 200
    assert add_res.json()["data"]["status"] == "Added"

    # Verify cannot double add
    readd_res = client.post(f"/purchase/inward/{inw1_id}/add", headers=headers)
    assert readd_res.status_code == 400
    print("  PASS: Post to inventory successful, double-posting prevented.")

    # Check Stock Ledger entries
    ledger_res = client.get(f"/inventory/ledger?customer_request_id={cr_id}", headers=headers)
    assert ledger_res.status_code == 200
    ledger_entries = ledger_res.json()["data"]["items"]
    assert len(ledger_entries) == 2
    assert all(e["movement_type"] == "IN" and e["reference_type"] == "GRN" for e in ledger_entries)
    print("  PASS: Stock Ledger entries recorded with movement_type='IN' and reference_type='GRN'.")

    # Check Stock Summary
    summary_res = client.get(f"/inventory/summary?customer_request_id={cr_id}", headers=headers)
    assert summary_res.status_code == 200
    summaries = summary_res.json()["data"]["items"]
    sum1 = next(s for s in summaries if s["item_id"] == item1.id)
    sum2 = next(s for s in summaries if s["item_id"] == item2.id)
    assert Decimal(str(sum1["on_hand"])) == Decimal("5.00")
    assert Decimal(str(sum2["on_hand"])) == Decimal("10.00")
    print("  PASS: Stock Summary balances verified (Item 1: 5 on hand, Item 2: 10 on hand).")

    # Check Item Last Purchase Rate
    item1_inv = client.get(f"/inventory/item/{item1.id}", headers=headers).json()["data"]
    assert Decimal(str(item1_inv["last_purchase_rate"])) == Decimal("500.00")
    print("  PASS: Item last purchase rate updated to 500.00.")

    # Check Customer Request status transitioned to 'Stock In'
    cr_check = client.get(f"/sales/customer-request/{cr_id}", headers=headers).json()["data"]
    assert cr_check["status"] == "Stock In"
    print("  PASS: Customer Request status transitioned to 'Stock In'.")

    # 9. Partial Delivery 2 (Fulfilling the remaining balance)
    print("\n[10/11] Completing remaining PO balance with Partial Delivery 2...")
    # Item 1: ordered 10, received 6 -> remaining outstanding 4
    # Item 2: ordered 20, received 10 -> remaining outstanding 10
    # Test over-delivery rejection on remaining balance
    over_res = client.post("/purchase/grn", json={
        "purchase_order_id": po_id,
        "challan_no": f"DC-{ts}-2",
        "received_date": "2026-09-19",
        "received_by": "Warehouse Supervisor",
        "items": [
            {"item_id": item1.id, "received_qty": 5.0, "accepted_qty": 5.0, "rejected_qty": 0.0},  # 5 > 4 outstanding
            {"item_id": item2.id, "received_qty": 10.0, "accepted_qty": 10.0, "rejected_qty": 0.0},
        ]
    }, headers=headers)
    assert over_res.status_code == 400
    print("  PASS: Over-delivery on remaining PO balance rejected.")

    # Valid completion GRN
    valid_grn2_payload = {
        "purchase_order_id": po_id,
        "challan_no": f"DC-{ts}-2",
        "supplier_invoice_ref": f"INV-{ts}-B",
        "received_date": "2026-09-19",
        "received_by": "Warehouse Supervisor",
        "items": [
            {"item_id": item1.id, "received_qty": 4.0, "accepted_qty": 4.0, "rejected_qty": 0.0},
            {"item_id": item2.id, "received_qty": 10.0, "accepted_qty": 9.0, "rejected_qty": 1.0},
        ]
    }
    grn2_res = client.post("/purchase/grn", json=valid_grn2_payload, headers=headers)
    assert grn2_res.status_code == 201
    grn2_data = grn2_res.json()["data"]
    inw2_id = grn2_data["inward_id"]

    # Verify PO status is now completely 'Received'
    po_check2 = client.get(f"/purchase/purchase-order/{po_id}", headers=headers).json()["data"]
    assert po_check2["status"] == "Received"
    print("  PASS: Purchase Order status transitioned to fully 'Received'.")

    # Post Inward 2 to inventory
    add2_res = client.post(f"/purchase/inward/{inw2_id}/add", headers=headers)
    assert add2_res.status_code == 200

    # Verify cumulative stock summary:
    # Item 1: 5 + 4 = 9 on hand
    # Item 2: 10 + 9 = 19 on hand
    summary2_res = client.get(f"/inventory/summary?customer_request_id={cr_id}", headers=headers)
    sums2 = summary2_res.json()["data"]["items"]
    sum1_final = next(s for s in sums2 if s["item_id"] == item1.id)
    sum2_final = next(s for s in sums2 if s["item_id"] == item2.id)
    assert Decimal(str(sum1_final["on_hand"])) == Decimal("9.00")
    assert Decimal(str(sum2_final["on_hand"])) == Decimal("19.00")
    print("  PASS: Final on-hand stock balances verified (Item 1: 9 on hand, Item 2: 19 on hand).")

    # 10. Order Tracking Audit Trail
    print("\n[11/11] Verifying Order Tracking audit trail & milestones...")
    track_res = client.get(f"/track/{cr_id}", headers=headers)
    assert track_res.status_code == 200
    track_data = track_res.json()["data"]

    assert track_data["current_stage"] == "Stock In"
    assert "Stock In" in track_data["stages_order"]
    assert track_data["details"]["grn_count"] == 2
    assert track_data["details"]["inward_count"] == 2

    # Check linked documents
    linked_types = [doc["document_type"] for doc in track_data["linked_documents"]]
    assert "Goods Receipt Note" in linked_types
    assert "Inward" in linked_types

    # Check timeline events
    timeline_titles = [e["title"] for e in track_data["timeline"]]
    assert any("Goods Receipt Recorded" in t for t in timeline_titles)
    assert any("Inward Created" in t for t in timeline_titles)
    assert any("Stock Inwarded to Inventory" in t for t in timeline_titles)
    print("  PASS: Tracking timeline and linked documents include all Goods Receipt & Inventory events.")

    print("\n" + "=" * 75)
    print("ALL GOODS RECEIPT, INWARD & INVENTORY MANAGEMENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    test_inventory_management_suite()
