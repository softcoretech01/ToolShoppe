"""
Comprehensive End-to-End Test Suite for Sourcing Workflow:
Customer Request, Purchase Request, RFQ, Vendor Quotations, Comparison & Order Tracking.
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


def test_sourcing_workflow_suite():
    print("\n" + "=" * 65)
    print("RUNNING SOURCING WORKFLOW VERIFICATION SUITE")
    print("=" * 65)

    # 1. Login & Token
    print("\n[1/7] Authenticating as Admin...")
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

    # 2. Customer Request & Auto PR Generation
    print("\n[2/7] Testing Customer Request & Automated PR Generation...")
    cr_payload = {
        "customer_id": cust_id,
        "required_date": "2026-10-15",
        "customer_reference": f"RFQ-SRC-{ts}",
        "lines": [
            {"item_id": item1.id, "description": "High precision drill", "quantity": 10.0, "unit": item1.unit},
            {"item_id": item2.id, "description": "Carbide end mill", "quantity": 5.0, "unit": item2.unit},
            {"item_id": item3.id, "description": "Tap and die set", "quantity": 2.0, "unit": item3.unit},
        ]
    }
    create_cr_res = client.post("/sales/customer-request", json=cr_payload, headers=headers)
    assert create_cr_res.status_code == 201, f"Expected 201, got {create_cr_res.status_code}: {create_cr_res.text}"
    cr_data = create_cr_res.json()["data"]
    cr_id = cr_data["id"]
    cr_no = cr_data["request_no"]
    assert cr_data["status"] == "Requested"
    assert len(cr_data["lines"]) == 3
    print(f"  -> Created Customer Request: {cr_no} (ID: {cr_id})")

    # Verify auto PR creation
    prs_res = client.get("/purchase/request", headers=headers)
    assert prs_res.status_code == 200
    pr_list = prs_res.json()["data"]["items"]
    matching_pr = next((p for p in pr_list if p["customer_request_id"] == cr_id), None)
    assert matching_pr is not None, "A matching Purchase Request must be automatically generated"
    pr_id = matching_pr["id"]
    pr_no = matching_pr["pr_no"]
    assert matching_pr["status"] == "Open"
    assert len(matching_pr["items"]) == 3
    print(f"  -> Auto-generated Purchase Request: {pr_no} (ID: {pr_id}) with {len(matching_pr['items'])} lines.")
    print("  PASS: Customer Request and Auto PR creation verified.")

    # 3. Test Editing CR before RFQ
    print("\n[3/7] Testing Customer Request Edit before RFQ...")
    edit_res = client.put(f"/sales/customer-request/{cr_id}", json={
        "customer_reference": f"RFQ-UPDATED-{ts}"
    }, headers=headers)
    assert edit_res.status_code == 200
    assert edit_res.json()["data"]["customer_reference"] == f"RFQ-UPDATED-{ts}"
    print("  PASS: Editing CR while in 'Requested' status is allowed.")

    # 4. Dispatch RFQ to Multiple Suppliers
    print("\n[4/7] Testing RFQ Dispatch & Email Logging...")
    rfq_payload = {
        "pr_id": pr_id,
        "supplier_ids": [sup1.id, sup2.id, sup3.id],
        "subject": f"Request for Quotation - Ref {pr_no}",
        "body": "Dear Supplier, Please provide your best competitive quotation for the attached items."
    }
    rfq_res = client.post("/purchase/rfq/send", json=rfq_payload, headers=headers)
    assert rfq_res.status_code == 200, f"Expected 200, got {rfq_res.status_code}: {rfq_res.text}"
    updated_pr = rfq_res.json()["data"]
    assert updated_pr["status"] == "RFQ Sent"
    assert updated_pr["suppliers_asked_count"] == 3

    # Verify CR status updated to 'RFQ Sent'
    cr_check = client.get(f"/sales/customer-request/{cr_id}", headers=headers).json()["data"]
    assert cr_check["status"] == "RFQ Sent"

    # Verify CR edit is now locked
    locked_edit = client.put(f"/sales/customer-request/{cr_id}", json={"customer_reference": "illegal"}, headers=headers)
    assert locked_edit.status_code == 400, "CR must be locked against edits after RFQ is sent"

    # Verify Email Logs
    email_logs_res = client.get(f"/email-logs?document_id={pr_id}", headers=headers)
    assert email_logs_res.status_code == 200
    logs = email_logs_res.json()["data"]
    assert len(logs) == 3, "3 email logs should be created"
    print(f"  -> Dispatched RFQ to {len(logs)} suppliers. Status: {updated_pr['status']}.")
    print("  PASS: RFQ dispatch, status transition, and email logs verified.")

    # 5. Vendor Quotation Entry & Calculations
    print("\n[5/7] Testing Vendor Quotation Entry & Calculations...")
    # Quotation 1: Supplier 1 (Complete, Moderate rate)
    vq1_res = client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup1.id,
        "quote_reference": f"S1-QUOTE-{ts}",
        "quote_date": "2026-09-17",
        "validity": "2026-10-30",
        "delivery_days": 6,
        "payment_terms": "30 days",
        "freight": 200.0,
        "lines": [
            {"item_id": item1.id, "rate": 1000.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item2.id, "rate": 800.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item3.id, "rate": 2000.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)
    assert vq1_res.status_code == 201
    vq1_data = vq1_res.json()["data"]
    # line 1: 10 * 1000 = 10000; line 2: 5 * 800 = 4000; line 3: 2 * 2000 = 4000 -> subtotal = 18000
    # tax: 18000 * 0.18 = 3240; freight = 200 -> grand_total = 21440
    assert float(vq1_data["subtotal"]) == 18000.0
    assert float(vq1_data["tax"]) == 3240.0
    assert float(vq1_data["grand_total"]) == 21440.0
    assert vq1_data["is_complete"] is True
    print(f"  -> Supplier 1 Quoted Grand Total: INR {float(vq1_data['grand_total']):,.2f} (Complete)")

    # Quotation 2: Supplier 2 (Complete, Lower total, Cheaper rates)
    vq2_res = client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup2.id,
        "quote_reference": f"S2-QUOTE-{ts}",
        "quote_date": "2026-09-17",
        "validity": "2026-10-30",
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
    vq2_data = vq2_res.json()["data"]
    # line 1: 10 * 950 = 9500; line 2: 5 * 750 = 3750; line 3: 2 * 1900 = 3800 -> subtotal = 17050
    # tax: 17050 * 0.18 = 3069; freight = 150 -> grand_total = 20269
    assert float(vq2_data["subtotal"]) == 17050.0
    assert float(vq2_data["tax"]) == 3069.0
    assert float(vq2_data["grand_total"]) == 20269.0
    assert vq2_data["is_complete"] is True
    print(f"  -> Supplier 2 Quoted Grand Total: INR {float(vq2_data['grand_total']):,.2f} (Complete, Lowest)")

    # Quotation 3: Supplier 3 (Incomplete - item 3 not quoted)
    vq3_res = client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup3.id,
        "quote_reference": f"S3-QUOTE-{ts}",
        "quote_date": "2026-09-17",
        "validity": "2026-10-30",
        "delivery_days": 2,
        "payment_terms": "Advance",
        "freight": 0.0,
        "lines": [
            {"item_id": item1.id, "rate": 800.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item2.id, "rate": 600.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": item3.id, "rate": 0.0, "tax_percent": 0.0, "not_quoted": True},  # NOT QUOTED
        ]
    }, headers=headers)
    assert vq3_res.status_code == 201
    vq3_data = vq3_res.json()["data"]
    assert vq3_data["is_complete"] is False
    print(f"  -> Supplier 3 Quoted Grand Total: INR {float(vq3_data['grand_total']):,.2f} (Incomplete - Item 3 missing)")

    # Duplicate quote prevention test
    dup_quote = client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr_id,
        "supplier_id": sup1.id,
        "lines": [{"item_id": item1.id, "rate": 500.0, "tax_percent": 18.0, "not_quoted": False}]
    }, headers=headers)
    assert dup_quote.status_code == 400, "Duplicate quote by same supplier must be rejected"
    print("  PASS: Vendor Quotation calculation, completeness detection, and duplicate rejection verified.")

    # 6. Quotation Comparison & Recommendation Logic
    print("\n[6/7] Testing Quotation Comparison & Recommendation Decision Tree...")
    compare_res = client.get(f"/purchase/compare/{pr_id}", headers=headers)
    assert compare_res.status_code == 200
    matrix = compare_res.json()["data"]
    assert matrix["status"] == "Draft"
    assert len(matrix["suppliers"]) == 3
    assert len(matrix["items"]) == 3

    # Verify Supplier 3 is flagged as incomplete
    s3_entry = next((s for s in matrix["suppliers"] if s["supplier_id"] == sup3.id), None)
    assert s3_entry and s3_entry["is_complete"] is False

    # Verify Supplier 2 is the recommended supplier (Lowest complete grand total: 20269 < 21440)
    assert matrix["recommended_supplier_id"] == sup2.id
    print(f"  -> Recommendation Engine selected Supplier 2 ({matrix['recommended_supplier_name']}) as best offer.")

    # Attempt to override without mandatory reason -> should fail with 400
    bad_override = client.post(f"/purchase/compare/{pr_id}/approve", json={
        "selected_supplier_id": sup1.id,
        "override_reason": ""  # Missing mandatory reason
    }, headers=headers)
    assert bad_override.status_code == 400, "Override reason must be mandatory when overriding recommendation"

    # Approve recommended supplier
    approve_res = client.post(f"/purchase/compare/{pr_id}/approve", json={
        "selected_supplier_id": sup2.id,
        "override_reason": None
    }, headers=headers)
    assert approve_res.status_code == 200
    approved_matrix = approve_res.json()["data"]
    assert approved_matrix["status"] == "Approved"
    assert approved_matrix["approved_supplier_id"] == sup2.id

    # Verify VQ statuses: Supplier 2 is 'Selected', Supplier 1 & 3 are 'Rejected'
    vq2_check = client.get(f"/purchase/vendor-quotation/{vq2_data['id']}", headers=headers).json()["data"]
    vq1_check = client.get(f"/purchase/vendor-quotation/{vq1_data['id']}", headers=headers).json()["data"]
    assert vq2_check["status"] == "Selected"
    assert vq1_check["status"] == "Rejected"

    # Verify PR status = 'Quoted', CR status = 'Approved' per Sourcing Rule 8
    pr_after = client.get(f"/purchase/request/{pr_id}", headers=headers).json()["data"]
    cr_after = client.get(f"/sales/customer-request/{cr_id}", headers=headers).json()["data"]
    assert pr_after["status"] == "Quoted"
    assert cr_after["status"] == "Approved"
    print(f"  -> Comparison Approved! PR status: {pr_after['status']}, CR status: {cr_after['status']}.")
    print("  PASS: 4-tier recommendation logic, override validation, and approval transitions verified.")

    # 7. Order Tracking Timeline
    print("\n[7/7] Testing Order Tracking Timeline...")
    track_res = client.get(f"/track/{cr_id}", headers=headers)
    assert track_res.status_code == 200
    track_data = track_res.json()["data"]
    assert track_data["customer_request_id"] == cr_id
    assert track_data["current_stage"] == "Approved"
    assert track_data["stage_index"] == 3  # Requested (0) -> RFQ Sent (1) -> Quoted (2) -> Approved (3)
    assert len(track_data["timeline"]) >= 5
    assert len(track_data["linked_documents"]) >= 4

    print(f"  -> Current Stage: {track_data['current_stage']} (Index: {track_data['stage_index']})")
    print(f"  -> Timeline Events: {len(track_data['timeline'])} events logged.")
    for ev in track_data["timeline"]:
        print(f"     • [{ev['stage']}] {ev['title']} ({ev['status']})")
    print("  PASS: Sourcing order tracking timeline verified.")

    print("\n" + "=" * 65)
    print("ALL SOURCING WORKFLOW TESTS PASSED! (100% DONE)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    test_sourcing_workflow_suite()
