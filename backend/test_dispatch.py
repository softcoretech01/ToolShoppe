"""
End-to-End Test Suite for Outward & Dispatch Management:
- Customer Order pending quantity validation.
- Inventory on-hand stock availability validation.
- Over-dispatch rejection (exceeding stock and exceeding order).
- Partial Delivery Challan (Outward) dispatch.
- Stock Ledger OUT entries and Stock Summary on-hand balance deduction.
- Customer Order status transition (Partially Dispatched -> Dispatched).
- Customer Request status transition to Dispatched upon full fulfillment.
- Order Tracking audit trail with 'Dispatched' stage and Delivery Challan documents.
"""
import time
from starlette.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.item import Item

client = TestClient(app)


def test_dispatch_management_suite():
    print("\n" + "=" * 75)
    print("RUNNING OUTWARD & DISPATCH MANAGEMENT TEST SUITE")
    print("=" * 75)

    # 1. Login & Token
    print("\n[1/10] Authenticating as Admin...")
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, "Admin login must succeed"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  PASS: Authenticated successfully.")

    # 2. Setup Prerequisites: Customer, Items, Supplier
    print("\n[2/10] Preparing test master data...")
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

    # 3. Create Sourcing Workflow up to Stock In Inventory
    print("\n[3/10] Progressing order through Sourcing -> PO -> GRN -> Inward -> Stock In...")
    # 3a. Customer Request
    cr_res = client.post("/sales/customer-request", json={
        "customer_id": cust_id,
        "required_date": "2026-12-01",
        "customer_reference": f"DISPATCH-TEST-{ts}",
        "lines": [
            {"item_id": item1.id, "description": "Precision Tool A", "quantity": 10.0, "unit": item1.unit},
            {"item_id": item2.id, "description": "Precision Tool B", "quantity": 20.0, "unit": item2.unit},
        ]
    }, headers=headers)
    assert cr_res.status_code == 201
    cr_data = cr_res.json()["data"]
    cr_id = cr_data["id"]

    # 3b. Retrieve Auto PR
    prs_res = client.get("/purchase/request", headers=headers)
    matching_pr = next(p for p in prs_res.json()["data"]["items"] if p["customer_request_id"] == cr_id)
    pr_id = matching_pr["id"]

    # 3c. Send RFQ
    client.post("/purchase/rfq/send", json={
        "pr_id": pr_id,
        "supplier_ids": [sup1.id, sup2.id],
        "subject": f"RFQ for PR #{matching_pr['pr_no']}",
        "body": "Please quote best rates."
    }, headers=headers)

    # 3d. Submit Supplier Quotations
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

    # 3e. Comparison & Approval
    appr_res = client.post(f"/purchase/compare/{pr_id}/approve", json={
        "selected_supplier_id": sup1.id,
        "override_reason": None,
    }, headers=headers)
    assert appr_res.status_code == 200

    # 3f. Auto Customer Quotation is created, accept it
    cqs_res = client.get(f"/sales/quotation?request_id={cr_id}", headers=headers)
    cq = cqs_res.json()["data"]["items"][0]
    cq_id = cq["id"]

    accept_res = client.patch(f"/sales/quotation/{cq_id}/accept", headers=headers)
    assert accept_res.status_code == 200

    # 3g. Create Customer PO (Sales Order)
    so_res = client.post("/sales/customer-order", json={
        "quotation_id": cq_id,
        "customer_po_number": f"CUST-PO-{ts}",
        "po_date": "2026-09-18",
        "delivery_date": "2026-10-10",
        "items": [
            {"item_id": item1.id, "quantity": 10.0, "selling_price": 600.0},
            {"item_id": item2.id, "quantity": 20.0, "selling_price": 300.0},
        ],
    }, headers=headers)
    assert so_res.status_code == 201
    so_data = so_res.json()["data"]
    so_id = so_data["id"]
    po_id = so_data["auto_purchase_order_id"]

    # 3h. Send Supplier PO
    client.post(f"/purchase/purchase-order/{po_id}/send", json={
        "recipient": sup1.email,
        "subject": "PO Send",
        "body": "Deliver promptly."
    }, headers=headers)

    # 3i. Create Partial GRN (5 of item1 out of 10, and 20 of item2 fully received)
    grn_res = client.post("/purchase/grn", json={
        "purchase_order_id": po_id,
        "challan_no": f"SUP-DC-{ts}-1",
        "received_date": "2026-09-18",
        "received_by": "Receiving Agent",
        "items": [
            {"item_id": item1.id, "received_qty": 5.0, "accepted_qty": 5.0, "rejected_qty": 0.0},
            {"item_id": item2.id, "received_qty": 20.0, "accepted_qty": 20.0, "rejected_qty": 0.0},
        ]
    }, headers=headers)
    assert grn_res.status_code == 201
    inw_id = grn_res.json()["data"]["inward_id"]

    # 3j. Post Inward to Inventory (Item 1 on-hand: 5.0, Item 2 on-hand: 20.0)
    post_res = client.post(f"/purchase/inward/{inw_id}/add", headers=headers)
    assert post_res.status_code == 200
    print("  PASS: Initial partial goods inwarded. Item 1 on-hand: 5.0, Item 2 on-hand: 20.0.")

    # Verify partial stock summary
    inv_res = client.get("/inventory/summary", headers=headers)
    summaries = inv_res.json()["data"]["items"]
    sum1 = next(s for s in summaries if s["customer_request_id"] == cr_id and s["item_id"] == item1.id)
    assert float(sum1["on_hand"]) == 5.0 and float(sum1["qty_out"]) == 0.0

    # 4. Over-Dispatch Validation: Exceeding Available On-Hand Stock
    print("\n[4/10] Validating rejection when dispatch quantity exceeds on-hand stock (ordered 10, stock 5, try 8)...")
    excess_stock_payload = {
        "customer_order_id": so_id,
        "dc_no": f"DC-EXCESS-{ts}",
        "dispatch_date": "2026-09-18",
        "dispatch_mode": "Road",
        "vehicle_no": "MH-12-AB-1234",
        "items": [
            {"item_id": item1.id, "dispatched_qty": 8.0}, # Pending order is 10, but only 5 in stock!
            {"item_id": item2.id, "dispatched_qty": 5.0},
        ]
    }
    fail_res1 = client.post("/sales/outward", json=excess_stock_payload, headers=headers)
    assert fail_res1.status_code == 400
    assert "exceeds available on-hand stock" in fail_res1.json()["message"].lower()
    print("  PASS: Successfully prevented dispatch exceeding available inventory.")

    # 3k. Receive remaining 5 of item 1 and inward to inventory
    grn2_res = client.post("/purchase/grn", json={
        "purchase_order_id": po_id,
        "challan_no": f"SUP-DC-{ts}-2",
        "received_date": "2026-09-18",
        "received_by": "Receiving Agent",
        "items": [
            {"item_id": item1.id, "received_qty": 5.0, "accepted_qty": 5.0, "rejected_qty": 0.0},
        ]
    }, headers=headers)
    assert grn2_res.status_code == 201
    inw2_id = grn2_res.json()["data"]["inward_id"]
    client.post(f"/purchase/inward/{inw2_id}/add", headers=headers)

    # Now stock is fully 10 of item 1 and 20 of item 2
    inv_res = client.get("/inventory/summary", headers=headers)
    summaries = inv_res.json()["data"]["items"]
    sum1 = next(s for s in summaries if s["customer_request_id"] == cr_id and s["item_id"] == item1.id)
    assert float(sum1["on_hand"]) == 10.0
    print("  PASS: Received second GRN batch. Stock now fully available (Item 1: 10.0, Item 2: 20.0).")

    # 5. Over-Dispatch Validation: Exceeding Order Quantity
    print("\n[5/10] Validating rejection when dispatch quantity exceeds Customer Order balance (ordered 10, try 15)...")
    excess_order_payload = {
        "customer_order_id": so_id,
        "dc_no": f"DC-EXCESS2-{ts}",
        "dispatch_date": "2026-09-18",
        "dispatch_mode": "Road",
        "vehicle_no": "MH-12-AB-1234",
        "items": [
            {"item_id": item1.id, "dispatched_qty": 15.0}, # Ordered only 10
            {"item_id": item2.id, "dispatched_qty": 5.0},
        ]
    }
    fail_res2 = client.post("/sales/outward", json=excess_order_payload, headers=headers)
    assert fail_res2.status_code == 400
    assert "exceeds pending customer order quantity" in fail_res2.json()["message"].lower()
    print("  PASS: Successfully prevented dispatch exceeding Customer Order balance.")

    # 6. Partial Dispatch #1 (Item 1: 4/10, Item 2: 8/20)
    print("\n[6/10] Creating Partial Delivery Challan #1 (Item 1: 4, Item 2: 8)...")
    partial_payload_1 = {
        "customer_order_id": so_id,
        "dc_no": f"DC-{ts}-01",
        "dispatch_date": "2026-09-18",
        "dispatch_mode": "Road",
        "vehicle_no": "DL-01-XY-5678",
        "remarks": "Partial shipment lot 1",
        "items": [
            {"item_id": item1.id, "dispatched_qty": 4.0},
            {"item_id": item2.id, "dispatched_qty": 8.0},
        ]
    }
    dc1_res = client.post("/sales/outward", json=partial_payload_1, headers=headers)
    assert dc1_res.status_code == 201
    dc1_data = dc1_res.json()["data"]
    dc1_id = dc1_data["id"]
    dc1_no = dc1_data["outward_no"]
    assert dc1_data["status"] == "Partially Dispatched"
    print(f"  PASS: Delivery Challan 1 created: {dc1_no} (Status: {dc1_data['status']}).")

    # Verify Customer Order updated after partial dispatch
    so_check1 = client.get(f"/sales/customer-order/{so_id}", headers=headers).json()["data"]
    assert so_check1["status"] == "Partially Dispatched"
    dc1_line1 = next(l for l in dc1_data["items"] if l["item_id"] == item1.id)
    dc1_line2 = next(l for l in dc1_data["items"] if l["item_id"] == item2.id)
    assert float(dc1_line1["dispatched_qty"]) == 4.0
    assert float(dc1_line2["dispatched_qty"]) == 8.0
    print("  PASS: Customer Order status updated to 'Partially Dispatched'.")

    # Verify Stock Summary after partial dispatch
    inv_res = client.get("/inventory/summary", headers=headers)
    summaries = inv_res.json()["data"]["items"]
    sum1 = next(s for s in summaries if s["customer_request_id"] == cr_id and s["item_id"] == item1.id)
    sum2 = next(s for s in summaries if s["customer_request_id"] == cr_id and s["item_id"] == item2.id)
    assert float(sum1["qty_out"]) == 4.0 and float(sum1["on_hand"]) == 6.0
    assert float(sum2["qty_out"]) == 8.0 and float(sum2["on_hand"]) == 12.0
    print("  PASS: Stock Summary deducted correctly (Item 1 on-hand: 6.0, Item 2 on-hand: 12.0).")

    # Verify Stock Ledger OUT entries
    ledger_res = client.get(f"/inventory/ledger?customer_request_id={cr_id}", headers=headers)
    ledger_items = ledger_res.json()["data"]["items"]
    out_entries = [e for e in ledger_items if e["movement_type"] == "OUT" and e["reference_type"] == "Outward"]
    assert len(out_entries) >= 2
    dc1_entry_1 = next(e for e in out_entries if e["item_id"] == item1.id and e["reference_id"] == dc1_id)
    dc1_entry_2 = next(e for e in out_entries if e["item_id"] == item2.id and e["reference_id"] == dc1_id)
    assert float(dc1_entry_1["quantity"]) == 4.0
    assert float(dc1_entry_2["quantity"]) == 8.0
    print("  PASS: Stock Ledger recorded movement_type='OUT' for Delivery Challan 1.")

    # 7. Second Partial Validation: Cannot exceed remaining balance
    print("\n[7/10] Validating rejection if subsequent dispatch exceeds remaining pending balance...")
    excess_subsequent_payload = {
        "customer_order_id": so_id,
        "dc_no": f"DC-SUBSEQ-{ts}",
        "dispatch_date": "2026-09-18",
        "dispatch_mode": "Road",
        "items": [
            {"item_id": item1.id, "dispatched_qty": 7.0}, # only 6 pending!
            {"item_id": item2.id, "dispatched_qty": 12.0},
        ]
    }
    fail_res3 = client.post("/sales/outward", json=excess_subsequent_payload, headers=headers)
    assert fail_res3.status_code == 400
    assert "exceeds pending customer order quantity" in fail_res3.json()["message"].lower()
    print("  PASS: Correctly rejected dispatch exceeding remaining order balance.")

    # 8. Final Dispatch #2 (Remaining 6 of Item 1 and 12 of Item 2)
    print("\n[8/10] Creating Final Delivery Challan #2 (Item 1: 6, Item 2: 12)...")
    final_payload_2 = {
        "customer_order_id": so_id,
        "dc_no": f"DC-{ts}-02",
        "dispatch_date": "2026-09-19",
        "dispatch_mode": "Road",
        "vehicle_no": "KA-04-MN-9999",
        "remarks": "Final delivery complete shipment",
        "items": [
            {"item_id": item1.id, "dispatched_qty": 6.0},
            {"item_id": item2.id, "dispatched_qty": 12.0},
        ]
    }
    dc2_res = client.post("/sales/outward", json=final_payload_2, headers=headers)
    assert dc2_res.status_code == 201
    dc2_data = dc2_res.json()["data"]
    dc2_id = dc2_data["id"]
    dc2_no = dc2_data["outward_no"]
    assert dc2_data["status"] == "Dispatched"
    print(f"  PASS: Delivery Challan 2 created: {dc2_no} (Status: {dc2_data['status']}).")

    # Verify Customer Order updated to 'Dispatched'
    so_check2 = client.get(f"/sales/customer-order/{so_id}", headers=headers).json()["data"]
    assert so_check2["status"] == "Dispatched"
    dc2_line1 = next(l for l in dc2_data["items"] if l["item_id"] == item1.id)
    dc2_line2 = next(l for l in dc2_data["items"] if l["item_id"] == item2.id)
    assert float(dc2_line1["dispatched_qty"]) == 6.0
    assert float(dc2_line2["dispatched_qty"]) == 12.0
    print("  PASS: Customer Order fully dispatched (Status: 'Dispatched').")

    # Verify Customer Request updated to 'Dispatched'
    cr_check = client.get(f"/sales/customer-request/{cr_id}", headers=headers).json()["data"]
    assert cr_check["status"] == "Dispatched"
    print("  PASS: Customer Request status transitioned to 'Dispatched'.")

    # Verify Stock Summary on-hand is now 0
    inv_res2 = client.get("/inventory/summary", headers=headers)
    summaries2 = inv_res2.json()["data"]["items"]
    sum1_final = next(s for s in summaries2 if s["customer_request_id"] == cr_id and s["item_id"] == item1.id)
    sum2_final = next(s for s in summaries2 if s["customer_request_id"] == cr_id and s["item_id"] == item2.id)
    assert float(sum1_final["qty_out"]) == 10.0 and float(sum1_final["on_hand"]) == 0.0
    assert float(sum2_final["qty_out"]) == 20.0 and float(sum2_final["on_hand"]) == 0.0
    print("  PASS: Stock Summary on-hand balance is now 0 for both items.")

    # 9. Outward Retrieval & Filters
    print("\n[9/10] Verifying Outward document listing and details endpoints...")
    outward_list_res = client.get(f"/sales/outward?customer_order_id={so_id}", headers=headers)
    assert outward_list_res.status_code == 200
    outward_list = outward_list_res.json()["data"]
    assert outward_list["total"] == 2
    print(f"  PASS: Retrieved {outward_list['total']} Delivery Challans for Customer Order.")

    outward_single_res = client.get(f"/sales/outward/{dc1_id}", headers=headers)
    assert outward_single_res.status_code == 200
    outward_single = outward_single_res.json()["data"]
    assert outward_single["outward_no"] == dc1_no
    assert outward_single["dc_no"] == f"DC-{ts}-01"
    assert outward_single["vehicle_no"] == "DL-01-XY-5678"
    assert len(outward_single["items"]) == 2
    print("  PASS: Retrieved single Outward document details with line items.")

    # 10. Order Tracking Audit Trail
    print("\n[10/10] Verifying Order Tracking audit trail for Dispatched status...")
    track_res = client.get(f"/track/{cr_id}", headers=headers)
    assert track_res.status_code == 200
    track_data = track_res.json()["data"]
    assert track_data["current_stage"] == "Dispatched"
    assert "Dispatched" in track_data["stages_order"]
    assert "Stock In" in track_data["stages_order"]
    
    timeline_stages = [ev["stage"] for ev in track_data["timeline"]]
    assert "Stock In" in timeline_stages
    assert "Dispatched" in timeline_stages
    print("  PASS: Tracking stages and timeline verified (Stock In & Dispatched recorded).")

    linked_docs = track_data["linked_documents"]
    dc_docs = [d for d in linked_docs if d["document_type"] == "Delivery Challan"]
    assert len(dc_docs) == 2
    dc_nums = [d["document_no"] for d in dc_docs]
    assert dc1_no in dc_nums and dc2_no in dc_nums
    print(f"  PASS: Tracking linked documents contains Delivery Challans: {dc_nums}")

    print("\n" + "=" * 75)
    print("ALL 10 OUTWARD & DISPATCH MANAGEMENT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    test_dispatch_management_suite()
