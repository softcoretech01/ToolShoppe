"""
Comprehensive End-to-End Test Suite for Sales Confirmation & Supplier PO:
Customer Quotation, Pricing Engine, Customer PO, Auto Supplier PO, Email Logs & Order Tracking.
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


def test_sales_confirmation_suite():
    print("\n" + "=" * 70)
    print("RUNNING SALES CONFIRMATION & SUPPLIER PO VERIFICATION SUITE")
    print("=" * 70)

    # 1. Login & Token
    print("\n[1/10] Authenticating as Admin...")
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, "Login must succeed"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  PASS: Authenticated with Bearer token.")

    # Fetch reference IDs from DB
    db = SessionLocal()
    try:
        init_db(db)
        cust = db.query(Customer).first()
        items = db.query(Item).limit(3).all()
        suppliers = db.query(Supplier).limit(3).all()
        assert cust and len(items) >= 3 and len(suppliers) >= 3
        cust_id = cust.id
        item1, item2, item3 = items[0], items[1], items[2]
        sup1, sup2, sup3 = suppliers[0], suppliers[1], suppliers[2]
    finally:
        db.close()

    ts = int(time.time() * 1000)

    # 2. Setup Prerequisites: Customer Request, Auto PR, RFQs, Vendor Quotes, and Comparison Approval
    print("\n[2/10] Setting up Sourcing workflow up to Comparison Approval...")
    cr_payload = {
        "customer_id": cust_id,
        "required_date": "2026-11-01",
        "customer_reference": f"CR-REF-{ts}",
        "lines": [
            {"item_id": item1.id, "description": "Carbide Endmill 10mm", "quantity": 10.0, "unit": item1.unit},
            {"item_id": item2.id, "description": "HSS Drill Bit 8mm", "quantity": 5.0, "unit": item2.unit},
            {"item_id": item3.id, "description": "Thread Tap M12", "quantity": 2.0, "unit": item3.unit},
        ]
    }
    cr_res = client.post("/sales/customer-request", json=cr_payload, headers=headers)
    assert cr_res.status_code == 201
    cr_data = cr_res.json()["data"]
    cr_id = cr_data["id"]

    prs_res = client.get("/purchase/request", headers=headers)
    matching_pr = next(p for p in prs_res.json()["data"]["items"] if p["customer_request_id"] == cr_id)
    pr_id = matching_pr["id"]

    client.post("/purchase/rfq/send", json={
        "pr_id": pr_id,
        "supplier_ids": [sup1.id, sup2.id, sup3.id],
        "subject": f"RFQ for PR #{matching_pr['pr_no']}",
        "body": "Please provide rates."
    }, headers=headers)

    # Quote 1 (Supplier 1)
    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup1.id,
        "quote_reference": f"S1-Q-{ts}",
        "quote_date": "2026-09-18",
        "validity": "2026-10-31",
        "delivery_days": 5,
        "payment_terms": "30 days",
        "freight": 200.0,
        "lines": [
            {"item_id": item1.id, "rate": 1000.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item2.id, "rate": 800.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item3.id, "rate": 2000.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    # Quote 2 (Supplier 2 - Best complete offer: 950, 750, 1900)
    vq2_res = client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup2.id,
        "quote_reference": f"S2-Q-{ts}",
        "quote_date": "2026-09-18",
        "validity": "2026-10-31",
        "delivery_days": 4,
        "payment_terms": "15 days",
        "freight": 150.0,
        "lines": [
            {"item_id": item1.id, "rate": 950.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item2.id, "rate": 750.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item3.id, "rate": 1900.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)
    assert vq2_res.status_code == 201

    # Approve Supplier 2
    approve_res = client.post(f"/purchase/compare/{pr_id}/approve", json={
        "selected_supplier_id": sup2.id,
        "override_reason": None
    }, headers=headers)
    assert approve_res.status_code == 200
    print("  PASS: Sourcing workflow setup complete. Comparison approved for Supplier 2.")

    # 3. Customer Quotation Auto Creation from Approved Comparison
    print("\n[3/10] Verifying Auto-Creation of Customer Quotation...")
    cq_list_res = client.get(f"/sales/quotation?request_id={cr_id}", headers=headers)
    assert cq_list_res.status_code == 200
    cqs = cq_list_res.json()["data"]["items"]
    assert len(cqs) >= 1, "Customer Quotation must be auto-generated upon comparison approval"
    cq_data = cqs[0]
    cq_id = cq_data["id"]
    cq_no = cq_data["quotation_no"]
    assert cq_data["status"] == "Draft"
    assert cq_data["customer_id"] == cust_id
    assert cq_data["supplier_id"] == sup2.id
    print(f"  -> Auto Customer Quotation: {cq_no} (ID: {cq_id}) in Draft status.")

    # 4. Pricing Engine & Margin Formula Validation
    print("\n[4/10] Verifying Pricing Engine and Margin Calculations...")
    # Customer markup was e.g. 12% for CUS-001 (or 15%)
    # Let's verify line calculations:
    # Item 1: supplier_rate = 950.0. With 12% markup -> customer_price = 950 * 1.12 = 1064.00
    # Margin % = ((1064 - 950) / 1064) * 100 = 10.71%
    line1 = next(line for line in cq_data["items"] if line["item_id"] == item1.id)
    assert float(line1["supplier_rate"]) == 950.0
    expected_price = round(950.0 * (1 + float(cust.default_markup or 15.0) / 100.0), 2)
    assert abs(float(line1["customer_price"]) - expected_price) < 0.05
    expected_margin = round(((expected_price - 950.0) / expected_price) * 100.0, 2)
    assert abs(float(line1["margin_percent"]) - expected_margin) < 0.1
    print(f"  -> Item 1: Cost = INR {line1['supplier_rate']}, Selling Price = INR {line1['customer_price']}, Margin = {line1['margin_percent']}%")
    print("  PASS: Pricing engine formula and initial margin percentages verified.")

    # 5. Edit Customer Selling Price & Live Margin Recalculation
    print("\n[5/10] Testing Customer Selling Price Edit and Instant Margin Recalculation...")
    new_sp_1 = 1200.0
    new_sp_2 = 900.0
    update_res = client.put(f"/sales/quotation/{cq_id}", json={
        "items": [
            {"item_id": item1.id, "customer_price": new_sp_1},
            {"item_id": item2.id, "customer_price": new_sp_2},
        ]
    }, headers=headers)
    assert update_res.status_code == 200
    updated_cq = update_res.json()["data"]
    u_line1 = next(l for l in updated_cq["items"] if l["item_id"] == item1.id)
    u_line2 = next(l for l in updated_cq["items"] if l["item_id"] == item2.id)
    assert float(u_line1["customer_price"]) == 1200.0
    assert float(u_line1["supplier_rate"]) == 950.0, "Supplier rate must remain read-only"
    # Margin % = ((1200 - 950) / 1200) * 100 = 250 / 1200 * 100 = 20.83%
    assert abs(float(u_line1["margin_percent"]) - 20.83) < 0.05
    # Item 2: ((900 - 750) / 900) * 100 = 150 / 900 * 100 = 16.67%
    assert abs(float(u_line2["margin_percent"]) - 16.67) < 0.05
    print(f"  -> Updated Item 1 Margin to {u_line1['margin_percent']}% (Cost: {u_line1['supplier_rate']}, SP: {u_line1['customer_price']})")
    print("  PASS: Editable selling price and instant margin recalculation verified.")

    # 6. Send Customer Quotation & Email Log
    print("\n[6/10] Testing Send Customer Quotation & Email Logging...")
    send_res = client.post("/sales/quotation/send", json={
        "quotation_id": cq_id,
        "subject": f"ToolShoppe Quotation {cq_no}",
        "body": "Dear Customer, Please find our official quotation attached."
    }, headers=headers)
    assert send_res.status_code == 200
    sent_cq = send_res.json()["data"]
    assert sent_cq["status"] == "Sent"
    assert sent_cq["sent_at"] is not None

    # Check Email Log
    eml_res = client.get(f"/email-logs?document_id={cq_id}", headers=headers)
    assert eml_res.status_code == 200
    logs = [l for l in eml_res.json()["data"] if l["document_type"] == "Customer Quotation"]
    assert len(logs) >= 1
    print(f"  -> Dispatched Customer Quotation {cq_no}. Email logged for {logs[0]['recipient']}.")

    # Resend test
    resend_res = client.post(f"/sales/quotation/{cq_id}/resend", json={
        "subject": f"Reminder: Quotation {cq_no}",
        "body": "Gentle reminder regarding quotation."
    }, headers=headers)
    assert resend_res.status_code == 200
    logs2 = [l for l in client.get(f"/email-logs?document_id={cq_id}", headers=headers).json()["data"] if l["document_type"] == "Customer Quotation"]
    assert len(logs2) >= 2
    print("  PASS: Send quotation and resend email logging verified.")

    # 7. Customer Decision: Rejection and Acceptance Rules
    print("\n[7/10] Testing Customer Acceptance & Rejection Rules...")
    # Attempting to create PO before acceptance should fail
    bad_po = client.post("/sales/customer-order", json={
        "quotation_id": cq_id,
        "customer_po_number": f"PO-FAIL-{ts}",
        "po_date": "2026-09-18",
    }, headers=headers)
    assert bad_po.status_code == 400, "Cannot create Customer PO when quotation status is Sent"

    # Test Mark Rejected
    reject_res = client.patch(f"/sales/quotation/{cq_id}/reject", headers=headers)
    assert reject_res.status_code == 200
    assert reject_res.json()["data"]["status"] == "Rejected"

    # Cannot create Customer PO from rejected quotation
    rejected_po = client.post("/sales/customer-order", json={
        "quotation_id": cq_id,
        "customer_po_number": f"PO-FAIL-REJ-{ts}",
        "po_date": "2026-09-18",
    }, headers=headers)
    assert rejected_po.status_code == 400, "Rejected quotation cannot create Customer PO"

    # Now create a fresh second customer quotation or accept a quotation
    # Let's create a new CR + CQ to test clean acceptance -> PO flow
    print("  -> Verified rejected quotation blocks PO creation.")

    # Create dedicated CR for Acceptance & Supplier PO test
    cr2_res = client.post("/sales/customer-request", json={
        "customer_id": cust_id,
        "required_date": "2026-11-15",
        "customer_reference": f"ORDER-REF-{ts}",
        "lines": [
            {"item_id": item1.id, "description": "High precision drill", "quantity": 8.0, "unit": item1.unit},
            {"item_id": item2.id, "description": "Carbide end mill", "quantity": 4.0, "unit": item2.unit},
        ]
    }, headers=headers)
    cr2_id = cr2_res.json()["data"]["id"]
    pr2 = next(p for p in client.get("/purchase/request", headers=headers).json()["data"]["items"] if p["customer_request_id"] == cr2_id)
    pr2_id = pr2["id"]

    client.post("/purchase/rfq/send", json={"pr_id": pr2_id, "supplier_ids": [sup2.id], "subject": "RFQ", "body": "RFQ"}, headers=headers)
    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr2_id,
        "supplier_id": sup2.id,
        "quote_reference": f"S2-Q2-{ts}",
        "quote_date": "2026-09-18",
        "validity": "2026-10-31",
        "delivery_days": 3,
        "payment_terms": "Immediate",
        "freight": 100.0,
        "lines": [
            {"item_id": item1.id, "rate": 615.0, "tax_percent": 18.0, "not_quoted": False},  # Example rate 615
            {"item_id": item2.id, "rate": 500.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)
    client.post(f"/purchase/compare/{pr2_id}/approve", json={"selected_supplier_id": sup2.id}, headers=headers)

    cq2_list = client.get(f"/sales/quotation?request_id={cr2_id}", headers=headers).json()["data"]["items"]
    cq2 = cq2_list[0]
    cq2_id = cq2["id"]

    # Send CQ2
    client.post("/sales/quotation/send", json={
        "quotation_id": cq2_id,
        "subject": "Quotation 2",
        "body": "Attached."
    }, headers=headers)

    # Customer Accepts
    accept_res = client.patch(f"/sales/quotation/{cq2_id}/accept", headers=headers)
    assert accept_res.status_code == 200
    assert accept_res.json()["data"]["status"] == "Accepted"
    print(f"  -> Quotation {cq2['quotation_no']} successfully accepted by customer.")
    print("  PASS: Customer acceptance workflow validated.")

    # 8. Customer Purchase Order (Customer Order) Creation
    print("\n[8/10] Testing Customer PO Creation & Auto Supplier PO Generation...")
    co_payload = {
        "quotation_id": cq2_id,
        "customer_po_number": f"CUST-PO-{ts}",
        "po_date": "2026-09-18",
        "delivery_date": "2026-10-10",
        "items": [
            {"item_id": item1.id, "quantity": 8.0, "selling_price": 750.0},  # Custom selling price
            {"item_id": item2.id, "quantity": 4.0, "selling_price": 620.0},
        ]
    }
    co_res = client.post("/sales/customer-order", json=co_payload, headers=headers)
    assert co_res.status_code == 201
    co_data = co_res.json()["data"]
    co_id = co_data["id"]
    co_no = co_data["order_no"]
    assert co_data["status"] == "Open"
    assert co_data["customer_po_number"] == f"CUST-PO-{ts}"
    assert co_data["auto_purchase_order_id"] is not None
    auto_po_id = co_data["auto_purchase_order_id"]
    auto_po_no = co_data["auto_purchase_order_no"]
    print(f"  -> Created Customer PO: {co_no} (ID: {co_id})")
    print(f"  -> Automatically Created Supplier PO: {auto_po_no} (ID: {auto_po_id})")

    # 9. Verify Supplier PO Strictly Preserves Supplier Quotation Rates
    print("\n[9/10] Verifying Supplier PO Rates Invariance and Status Updates...")
    po_res = client.get(f"/purchase/purchase-order/{auto_po_id}", headers=headers)
    assert po_res.status_code == 200
    po_data = po_res.json()["data"]
    assert po_data["status"] == "Draft"
    assert po_data["supplier_id"] == sup2.id
    assert po_data["customer_order_id"] == co_id

    # CRITICAL TEST: Item 1 purchase rate MUST BE INR 615.00 (from supplier quote), NOT INR 750 (customer selling price)
    po_item1 = next(it for it in po_data["items"] if it["item_id"] == item1.id)
    assert float(po_item1["purchase_rate"]) == 615.0, f"Purchase rate must be INR 615.00, got {po_item1['purchase_rate']}"
    assert float(po_item1["quantity"]) == 8.0
    assert float(po_item1["line_total"]) == round(8.0 * 615.0, 2)
    print(f"  -> Verified Item 1 Purchase Rate: INR {po_item1['purchase_rate']} (unchanged despite customer selling price INR 750.00).")

    # Verify Customer Request stage transitioned to 'PO Created'
    cr2_check = client.get(f"/sales/customer-request/{cr2_id}", headers=headers).json()["data"]
    assert cr2_check["status"] == "PO Created", f"Expected Customer Request status 'PO Created', got {cr2_check['status']}"
    print(f"  -> Customer Request status successfully updated to '{cr2_check['status']}'.")

    # Send Supplier PO
    send_po_res = client.post(f"/purchase/purchase-order/{auto_po_id}/send", json={
        "subject": f"Purchase Order {auto_po_no}",
        "body": "Please execute this purchase order."
    }, headers=headers)
    assert send_po_res.status_code == 200
    sent_po_data = send_po_res.json()["data"]
    assert sent_po_data["status"] == "Sent"
    assert sent_po_data["sent_at"] is not None

    # Verify Email Log for Supplier PO
    po_logs = client.get(f"/email-logs?document_id={auto_po_id}", headers=headers).json()["data"]
    po_log_entries = [l for l in po_logs if l["document_type"] == "Purchase Order"]
    assert len(po_log_entries) >= 1
    print(f"  -> Dispatched Supplier PO {auto_po_no}. Email logged for {po_log_entries[0]['recipient']}.")
    print("  PASS: Auto Supplier PO generation, rate invariance, and send email verified.")

    # 10. Order Tracking Timeline Audit
    print("\n[10/10] Verifying Complete Order Tracking Timeline...")
    track_res = client.get(f"/track/{cr2_id}", headers=headers)
    assert track_res.status_code == 200
    track_data = track_res.json()["data"]
    assert track_data["current_stage"] == "PO Created"
    assert track_data["stage_index"] == 4  # Requested (0) -> RFQ Sent (1) -> Quoted (2) -> Approved (3) -> PO Created (4)
    assert track_data["stages_order"] == ["Requested", "RFQ Sent", "Quoted", "Approved", "PO Created", "Stock In", "Dispatched", "Invoiced", "Completed"]

    # Verify linked documents contain Customer Quotation, Customer Order, and Purchase Order
    doc_types = {d["document_type"] for d in track_data["linked_documents"]}
    assert "Customer Request" in doc_types
    assert "Purchase Request" in doc_types
    assert "Vendor Quotation" in doc_types
    assert "Comparison" in doc_types
    assert "Customer Quotation" in doc_types
    assert "Customer Order" in doc_types
    assert "Purchase Order" in doc_types

    print(f"  -> Final Stage: {track_data['current_stage']} (Index: {track_data['stage_index']})")
    print(f"  -> Linked Document Types: {', '.join(doc_types)}")
    print(f"  -> Timeline Events: {len(track_data['timeline'])} milestones tracked.")
    for ev in track_data["timeline"]:
        print(f"     - [{ev['stage']}] {ev['title']} ({ev['status']})")

    print("\n" + "=" * 70)
    print("ALL SALES CONFIRMATION & SUPPLIER PO TESTS PASSED! (100% DONE)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    test_sales_confirmation_suite()
