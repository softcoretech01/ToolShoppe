import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.item import Item
from app.models.customer_request import CustomerRequest

logger = logging.getLogger("app.seed_demo_workflow")


def seed_demo_workflow(db: Session) -> None:
    """
    Seed the standard 12-stage back-to-back demo order chain:
    - 01. Customer Request: 3 documents (CR1 Completed, CR2 Quoted/Comparison, CR3 Requested)
    - 02. Purchase Request: 3 documents (PR1, PR2, PR3)
    - 03. Vendor Quotation: 5 documents (3 for PR1, 2 for PR2)
    - 04. Comparison: 1 document (QC1)
    - 05. Customer Quotation: 1 document (CQ1)
    - 06. Customer PO: 1 document (SO1)
    - 07. Supplier PO: 1 document (PO1)
    - 08. GRN: 1 document (GRN1)
    - 09. Inward: 1 document (INW1)
    - 10. Outward: 1 document (DC1)
    - 11. Sales Invoice: 1 document (SI1)
    - 12. Purchase Invoice: 1 document (PI1)
    """
    if db.query(CustomerRequest).count() > 0:
        return

    logger.info("Seeding 12-stage back-to-back demo order workflow...")

    from app.main import app
    client = TestClient(app)

    # 1. Login to get token
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    if login_res.status_code != 200:
        logger.error(f"Failed to authenticate admin during workflow seeding: {login_res.text}")
        return
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch master IDs
    cus1 = db.query(Customer).filter(Customer.customer_code == "CUS-001").first()
    cus2 = db.query(Customer).filter(Customer.customer_code == "CUS-002").first()
    cus3 = db.query(Customer).filter(Customer.customer_code == "CUS-003").first()

    sup1 = db.query(Supplier).filter(Supplier.supplier_code == "SUP-001").first()
    sup2 = db.query(Supplier).filter(Supplier.supplier_code == "SUP-002").first()
    sup3 = db.query(Supplier).filter(Supplier.supplier_code == "SUP-003").first()

    itm1 = db.query(Item).filter(Item.item_code == "ITM-0001").first()
    itm4 = db.query(Item).filter(Item.item_code == "ITM-0004").first()
    itm5 = db.query(Item).filter(Item.item_code == "ITM-0005").first()
    itm6 = db.query(Item).filter(Item.item_code == "ITM-0006").first()
    itm7 = db.query(Item).filter(Item.item_code == "ITM-0007").first()
    itm9 = db.query(Item).filter(Item.item_code == "ITM-0009").first()
    itm10 = db.query(Item).filter(Item.item_code == "ITM-0010").first()

    if not (cus1 and cus2 and cus3 and sup1 and sup2 and sup3 and itm1 and itm7 and itm10):
        logger.warning("Required master records missing for demo seeding.")
        return

    today = date.today()

    # =========================================================================
    # CR-0001: Full Lifecycle (CR -> PR -> VQ -> QC -> CQ -> SO -> PO -> GRN -> INW -> OUT -> SI -> PI)
    # =========================================================================
    cr1_payload = {
        "customer_id": cus1.id,
        "required_date": str(today + timedelta(days=14)),
        "customer_reference": "BEW/ENQ/2026/084",
        "lines": [
            {"item_id": itm1.id, "description": itm1.name, "quantity": 10.0, "unit": itm1.unit},
            {"item_id": itm7.id, "description": itm7.name, "quantity": 5.0, "unit": itm7.unit},
            {"item_id": itm10.id, "description": itm10.name, "quantity": 20.0, "unit": itm10.unit},
        ]
    }
    r = client.post("/sales/customer-request", json=cr1_payload, headers=headers)
    cr1_id = r.json()["data"]["id"]

    prs_res = client.get("/purchase/request", headers=headers)
    pr1 = next(p for p in prs_res.json()["data"]["items"] if p["customer_request_id"] == cr1_id)
    pr1_id = pr1["id"]

    # Dispatch RFQ for PR1
    client.post("/purchase/rfq/send", json={
        "pr_id": pr1_id,
        "supplier_ids": [sup2.id, sup3.id, sup1.id],
        "subject": f"Request for Quotation - Ref {pr1['pr_no']}",
        "body": "Please provide your best competitive quotation."
    }, headers=headers)

    # 3 Vendor Quotes for PR1
    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr1_id,
        "supplier_id": sup2.id,
        "quote_reference": "GIS/Q/2026/771",
        "quote_date": str(today - timedelta(days=5)),
        "validity": str(today + timedelta(days=25)),
        "delivery_days": 6,
        "payment_terms": "30 days",
        "freight": 250.0,
        "lines": [
            {"item_id": itm1.id, "rate": 1180.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm7.id, "rate": 2380.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm10.id, "rate": 295.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr1_id,
        "supplier_id": sup3.id,
        "quote_reference": "PMA-QT-2261",
        "quote_date": str(today - timedelta(days=5)),
        "validity": str(today + timedelta(days=25)),
        "delivery_days": 9,
        "payment_terms": "15 days",
        "freight": 0.0,
        "lines": [
            {"item_id": itm1.id, "rate": 1240.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm7.id, "rate": 2210.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm10.id, "rate": 320.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr1_id,
        "supplier_id": sup1.id,
        "quote_reference": "SVT/2026/449",
        "quote_date": str(today - timedelta(days=5)),
        "validity": str(today + timedelta(days=25)),
        "delivery_days": 4,
        "payment_terms": "Advance",
        "freight": 180.0,
        "lines": [
            {"item_id": itm1.id, "rate": 1150.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm7.id, "rate": 0.0, "tax_percent": 0.0, "not_quoted": True},
            {"item_id": itm10.id, "rate": 290.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    # Approve comparison for Supplier 2 (Auto generates Customer Quotation CQ1)
    client.post(f"/purchase/compare/{pr1_id}/approve", json={
        "selected_supplier_id": sup2.id,
        "override_reason": None
    }, headers=headers)

    # Fetch generated Customer Quotation
    cqs = client.get(f"/sales/quotation?request_id={cr1_id}", headers=headers).json()["data"]["items"]
    cq1_id = cqs[0]["id"]

    # Send and Accept CQ
    client.post("/sales/quotation/send", json={
        "quotation_id": cq1_id,
        "subject": "Quotation BEW/ENQ/2026/084",
        "body": "Please find attached our quotation."
    }, headers=headers)
    client.patch(f"/sales/quotation/{cq1_id}/accept", headers=headers)

    # Customer PO (Sales Order SO1) -> Auto generates Supplier PO1 to Supplier 2
    so_res = client.post("/sales/customer-order", json={
        "quotation_id": cq1_id,
        "customer_po_number": "BEW/PO/2026/117",
        "po_date": str(today - timedelta(days=3)),
        "delivery_date": str(today + timedelta(days=10)),
        "items": [
            {"item_id": itm1.id, "quantity": 10.0, "selling_price": 1321.60},
            {"item_id": itm7.id, "quantity": 5.0, "selling_price": 2665.60},
            {"item_id": itm10.id, "quantity": 20.0, "selling_price": 330.40},
        ]
    }, headers=headers)
    so_data = so_res.json()["data"]
    so_id = so_data["id"]
    po_id = so_data["auto_purchase_order_id"]

    # Send Supplier PO
    client.post(f"/purchase/purchase-order/{po_id}/send", json={
        "recipient": sup2.email,
        "subject": f"Purchase Order Ref {po_id}",
        "body": "Please supply items as per order."
    }, headers=headers)

    # Record GRN1
    grn_res = client.post("/purchase/grn", json={
        "purchase_order_id": po_id,
        "challan_no": "GIS/DC/2026/1188",
        "received_date": str(today - timedelta(days=2)),
        "received_by": "Stores - Mani",
        "remarks": "All items received in good condition.",
        "items": [
            {"item_id": itm1.id, "received_qty": 10.0, "accepted_qty": 10.0, "rejected_qty": 0.0},
            {"item_id": itm7.id, "received_qty": 5.0, "accepted_qty": 5.0, "rejected_qty": 0.0},
            {"item_id": itm10.id, "received_qty": 20.0, "accepted_qty": 20.0, "rejected_qty": 0.0},
        ]
    }, headers=headers)
    grn_data = grn_res.json()["data"]
    grn_id = grn_data["id"]
    inw_id = grn_data["inward_id"]

    # Inward Stock
    client.post(f"/purchase/inward/{inw_id}/add", headers=headers)

    # Dispatch Outward DC1
    out_res = client.post("/sales/outward", json={
        "customer_order_id": so_id,
        "dc_number": "TS/DC/2026/0341",
        "dispatch_date": str(today - timedelta(days=1)),
        "dispatch_mode": "Road",
        "vehicle_or_courier": "TN 09 BX 4471",
        "remarks": "Delivered to Plant 2 stores.",
        "items": [
            {"item_id": itm1.id, "dispatch_qty": 10.0},
            {"item_id": itm7.id, "dispatch_qty": 5.0},
            {"item_id": itm10.id, "dispatch_qty": 20.0},
        ]
    }, headers=headers)
    out_data = out_res.json()["data"]
    out_id = out_data["id"]

    # Sales Invoice SI1
    client.post("/sales/sales-invoice", json={
        "outward_id": out_id,
        "invoice_date": str(today),
        "due_date": str(today + timedelta(days=30)),
        "payment_terms": cus1.payment_terms or "30 days",
        "notes": "Sales Invoice against Delivery Challan TS/DC/2026/0341"
    }, headers=headers)

    # Purchase Invoice PI1
    client.post("/purchase/purchase-invoice", json={
        "grn_id": grn_id,
        "supplier_invoice_no": "GIS/2026/3391",
        "supplier_invoice_date": str(today - timedelta(days=2)),
        "due_date": str(today + timedelta(days=28)),
        "remarks": "Supplier Invoice against GRN GIS/DC/2026/1188"
    }, headers=headers)

    # =========================================================================
    # CR-0002: In Progress at Comparison stage (CR -> PR -> RFQ -> 2 VQs)
    # =========================================================================
    cr2_payload = {
        "customer_id": cus2.id,
        "required_date": str(today + timedelta(days=12)),
        "customer_reference": "SAC/RFQ/5521",
        "lines": [
            {"item_id": itm4.id, "description": itm4.name, "quantity": 25.0, "unit": itm4.unit},
            {"item_id": itm5.id, "description": itm5.name, "quantity": 25.0, "unit": itm5.unit},
            {"item_id": itm6.id, "description": itm6.name, "quantity": 10.0, "unit": itm6.unit},
        ]
    }
    r2 = client.post("/sales/customer-request", json=cr2_payload, headers=headers)
    cr2_id = r2.json()["data"]["id"]

    prs_res2 = client.get("/purchase/request", headers=headers)
    pr2 = next(p for p in prs_res2.json()["data"]["items"] if p["customer_request_id"] == cr2_id)
    pr2_id = pr2["id"]

    client.post("/purchase/rfq/send", json={
        "pr_id": pr2_id,
        "supplier_ids": [sup1.id, sup3.id],
        "subject": f"Request for Quotation - Ref {pr2['pr_no']}",
        "body": "Please provide rates for hand tools."
    }, headers=headers)

    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr2_id,
        "supplier_id": sup1.id,
        "quote_reference": "SVT/2026/512",
        "quote_date": str(today - timedelta(days=2)),
        "validity": str(today + timedelta(days=20)),
        "delivery_days": 5,
        "payment_terms": "30 days",
        "freight": 150.0,
        "lines": [
            {"item_id": itm4.id, "rate": 640.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm5.id, "rate": 385.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm6.id, "rate": 745.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    client.post("/purchase/vendor-quotation", json={
        "purchase_request_id": pr2_id,
        "supplier_id": sup3.id,
        "quote_reference": "MHA/Q/2026/88",
        "quote_date": str(today - timedelta(days=2)),
        "validity": str(today + timedelta(days=15)),
        "delivery_days": 8,
        "payment_terms": "15 days",
        "freight": 0.0,
        "lines": [
            {"item_id": itm4.id, "rate": 615.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm5.id, "rate": 398.0, "tax_percent": 18.0, "not_quoted": False},
            {"item_id": itm6.id, "rate": 720.0, "tax_percent": 18.0, "not_quoted": False},
        ]
    }, headers=headers)

    # =========================================================================
    # CR-0003: New Request (Requested stage, PR Open, ready for RFQ dispatch)
    # =========================================================================
    cr3_payload = {
        "customer_id": cus3.id,
        "required_date": str(today + timedelta(days=20)),
        "customer_reference": "KF/2026/PUR/019",
        "lines": [
            {"item_id": itm9.id, "description": itm9.name, "quantity": 40.0, "unit": itm9.unit},
            {"item_id": itm10.id, "description": itm10.name, "quantity": 30.0, "unit": itm10.unit},
        ]
    }
    client.post("/sales/customer-request", json=cr3_payload, headers=headers)

    logger.info("Successfully seeded 12-document demo order workflow into database.")
