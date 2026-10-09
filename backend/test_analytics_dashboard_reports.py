"""
End-to-End Verification Test Suite:
SRS 6.0 — Dashboard + Reports + Margin Analysis + Email Log + Order Tracking
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
from app.models.customer_request import CustomerRequest
from app.models.email_log import EmailLog

client = TestClient(app)


def test_analytics_dashboard_reports_suite():
    print("\n" + "=" * 80)
    print("RUNNING SRS 6.0: DASHBOARD, REPORTS, MARGIN & TRACKING TEST SUITE")
    print("=" * 80)

    # 1. Login & Token
    print("\n[1/9] Authenticating as Admin...")
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200, f"Admin login must succeed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  PASS: Authenticated successfully.")

    # 2. Baseline Data Verification
    print("\n[2/9] Checking database and baseline records...")
    db = SessionLocal()
    try:
        init_db(db)
        customer_count = db.query(Customer).count()
        supplier_count = db.query(Supplier).count()
        item_count = db.query(Item).count()
        req_count = db.query(CustomerRequest).count()
        print(f"  Info: Customers={customer_count}, Suppliers={supplier_count}, Items={item_count}, Requests={req_count}")
        assert customer_count > 0 and supplier_count > 0 and item_count > 0
    finally:
        db.close()
    print("  PASS: Baseline data verified.")

    # 3. Full Dashboard Endpoint (Dual-route verification)
    print("\n[3/9] Testing Full Dashboard Overview (Dual routes)...")
    res_sales_dash = client.get("/sales/dashboard", headers=headers)
    assert res_sales_dash.status_code == 200, f"GET /sales/dashboard failed: {res_sales_dash.text}"
    data_sales_dash = res_sales_dash.json()["data"]

    res_api_dash = client.get("/api/dashboard", headers=headers)
    assert res_api_dash.status_code == 200, f"GET /api/dashboard failed: {res_api_dash.text}"
    data_api_dash = res_api_dash.json()["data"]

    res_root_dash = client.get("/dashboard", headers=headers)
    assert res_root_dash.status_code == 200, f"GET /dashboard failed: {res_root_dash.text}"

    # Verify structure
    assert "kpis" in data_sales_dash
    assert "needs_attention" in data_sales_dash
    assert "workflow_summary" in data_sales_dash
    assert "charts" in data_sales_dash

    kpis = data_sales_dash["kpis"]
    assert "total_customer_requests" in kpis
    assert "open_orders" in kpis
    assert "rfq_pending" in kpis
    assert "purchase_orders_draft" in kpis
    assert "stock_available" in kpis
    assert "goods_ready_for_dispatch" in kpis
    assert "sales_value" in kpis
    assert "purchase_value" in kpis
    assert "total_margin" in kpis
    assert "margin_percent" in kpis

    # Validate Margin Math: margin = sales_value - purchase_value
    sales_v = Decimal(str(kpis["sales_value"]))
    pur_v = Decimal(str(kpis["purchase_value"]))
    margin_v = Decimal(str(kpis["total_margin"]))
    assert margin_v == sales_v - pur_v, f"KPI margin mismatch: {margin_v} != {sales_v} - {pur_v}"

    wf = data_sales_dash["workflow_summary"]
    assert "customer_requests" in wf
    assert "rfqs" in wf
    assert "vendor_quotations" in wf
    assert "comparisons" in wf
    assert "customer_orders" in wf
    assert "purchase_orders" in wf
    assert "grns" in wf
    assert "inventory_inwards" in wf
    assert "outwards" in wf
    assert "sales_invoices" in wf
    assert "purchase_invoices" in wf

    charts = data_sales_dash["charts"]
    assert "sales_vs_purchase" in charts
    assert "work_waiting_by_stage" in charts
    assert "best_selling_items" in charts
    assert "margin_trend" in charts
    print("  PASS: Full dashboard returned all components with accurate KPI margin calculations.")

    # 4. Granular Dashboard Endpoints
    print("\n[4/9] Testing Granular Dashboard Sub-Endpoints...")
    # KPI cards
    res_kpi = client.get("/dashboard/kpi", headers=headers)
    assert res_kpi.status_code == 200
    res_api_kpi = client.get("/api/dashboard/kpi", headers=headers)
    assert res_api_kpi.status_code == 200

    # Charts
    res_charts = client.get("/dashboard/charts", headers=headers)
    assert res_charts.status_code == 200
    res_api_charts = client.get("/api/dashboard/charts", headers=headers)
    assert res_api_charts.status_code == 200

    # Needs Attention
    res_attn = client.get("/dashboard/needs-attention", headers=headers)
    assert res_attn.status_code == 200
    assert isinstance(res_attn.json()["data"], list)

    # Workflow summary
    res_summary = client.get("/dashboard/workflow-summary", headers=headers)
    assert res_summary.status_code == 200
    print("  PASS: Granular dashboard sub-endpoints operational.")

    # 5. Sales Report & CSV Export
    print("\n[5/9] Testing Sales Report (JSON & CSV)...")
    res_sales_rep = client.get("/reports/sales", headers=headers)
    assert res_sales_rep.status_code == 200
    sales_data = res_sales_rep.json()["data"]
    assert "total_sales_value" in sales_data
    assert "total_tax" in sales_data
    assert "total_grand_total" in sales_data
    assert "rows" in sales_data

    # Dual alias route
    res_api_sales_rep = client.get("/api/reports/sales", headers=headers)
    assert res_api_sales_rep.status_code == 200

    # CSV export
    res_sales_csv = client.get("/reports/sales?export=csv", headers=headers)
    assert res_sales_csv.status_code == 200
    assert res_sales_csv.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=sales_report.csv" in res_sales_csv.headers.get("content-disposition", "")
    csv_text = res_sales_csv.text
    assert "invoice_no,invoice_date,customer_name,item_code" in csv_text
    print("  PASS: Sales report JSON and CSV export verified.")

    # 6. Purchase Report & CSV Export
    print("\n[6/9] Testing Purchase Report (JSON & CSV)...")
    res_pur_rep = client.get("/reports/purchase", headers=headers)
    assert res_pur_rep.status_code == 200
    pur_data = res_pur_rep.json()["data"]
    assert "total_purchase_value" in pur_data
    assert "total_tax" in pur_data
    assert "total_grand_total" in pur_data
    assert "rows" in pur_data

    # Dual alias route
    res_api_pur_rep = client.get("/api/reports/purchase", headers=headers)
    assert res_api_pur_rep.status_code == 200

    # CSV export
    res_pur_csv = client.get("/reports/purchase?export=csv", headers=headers)
    assert res_pur_csv.status_code == 200
    assert res_pur_csv.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=purchase_report.csv" in res_pur_csv.headers.get("content-disposition", "")
    assert "internal_invoice_no,supplier_invoice_no" in res_pur_csv.text
    print("  PASS: Purchase report JSON and CSV export verified.")

    # 7. Inventory Stock Summary & Ledger Report & CSV Export
    print("\n[7/9] Testing Inventory Report (JSON & CSV)...")
    res_inv_rep = client.get("/reports/inventory", headers=headers)
    assert res_inv_rep.status_code == 200
    inv_data = res_inv_rep.json()["data"]
    assert "summary" in inv_data
    assert "ledger" in inv_data

    # Dual alias route
    res_api_inv_rep = client.get("/api/reports/inventory", headers=headers)
    assert res_api_inv_rep.status_code == 200

    # CSV export
    res_inv_csv = client.get("/reports/inventory?export=csv", headers=headers)
    assert res_inv_csv.status_code == 200
    assert res_inv_csv.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=inventory_report.csv" in res_inv_csv.headers.get("content-disposition", "")
    assert "item_id,item_code,item_name" in res_inv_csv.text
    print("  PASS: Inventory report JSON and CSV export verified.")

    # 8. Margin Analysis Report & Mathematical Integrity
    print("\n[8/9] Testing Margin Analysis Report & Formula Verification...")
    res_margin = client.get("/reports/margin", headers=headers)
    assert res_margin.status_code == 200
    m_data = res_margin.json()["data"]
    assert "overall_sales_value" in m_data
    assert "overall_purchase_value" in m_data
    assert "overall_margin" in m_data
    assert "overall_margin_percent" in m_data
    assert "requests" in m_data

    ov_sales = Decimal(str(m_data["overall_sales_value"]))
    ov_pur = Decimal(str(m_data["overall_purchase_value"]))
    ov_margin = Decimal(str(m_data["overall_margin"]))
    assert ov_margin == ov_sales - ov_pur, f"Overall margin calculation error: {ov_margin} != {ov_sales} - {ov_pur}"

    # Verify per-request margin formula
    for row in m_data["requests"]:
        s_val = Decimal(str(row["sales_value"]))
        p_val = Decimal(str(row["purchase_value"]))
        m_val = Decimal(str(row["margin"]))
        assert m_val == s_val - p_val, f"Request {row['request_no']} margin mismatch: {m_val} != {s_val} - {p_val}"
        if s_val > 0:
            expected_pct = ((m_val / s_val) * Decimal("100.00")).quantize(Decimal("0.01"))
            actual_pct = Decimal(str(row["margin_percent"])).quantize(Decimal("0.01"))
            assert actual_pct == expected_pct, f"Request {row['request_no']} margin % mismatch: {actual_pct} != {expected_pct}"

    # Dual alias route
    res_api_margin = client.get("/api/reports/margin", headers=headers)
    assert res_api_margin.status_code == 200

    # CSV export
    res_m_csv = client.get("/reports/margin?export=csv", headers=headers)
    assert res_m_csv.status_code == 200
    assert res_m_csv.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=margin_report.csv" in res_m_csv.headers.get("content-disposition", "")
    assert "customer_request_id,request_no,customer_name,purchase_value,sales_value,margin,margin_percent,status" in res_m_csv.text
    print("  PASS: Margin report mathematical integrity and CSV export verified.")

    # 9. Email Logs & Order Tracking with Margin Metrics
    print("\n[9/9] Testing Email Logs & Order Tracking with Margin Metrics...")
    # Email logs list
    res_logs = client.get("/email-logs", headers=headers)
    assert res_logs.status_code == 200
    res_api_logs = client.get("/api/email-logs", headers=headers)
    assert res_api_logs.status_code == 200

    # Check if any email log exists
    logs_list = res_logs.json()["data"]
    if logs_list:
        sample_log_id = logs_list[0]["id"]
        res_single_log = client.get(f"/email-logs/{sample_log_id}", headers=headers)
        assert res_single_log.status_code == 200
        assert res_single_log.json()["data"]["id"] == sample_log_id

        res_api_single = client.get(f"/api/email-logs/{sample_log_id}", headers=headers)
        assert res_api_single.status_code == 200

    # Test 404 on invalid email log ID
    res_404_log = client.get("/email-logs/9999999", headers=headers)
    assert res_404_log.status_code == 404

    # Tracking endpoints
    db = SessionLocal()
    try:
        sample_cr = db.query(CustomerRequest).first()
        sample_cr_id = sample_cr.id if sample_cr else None
    finally:
        db.close()

    if sample_cr_id:
        # Test all tracking routes: /track/{id}, /tracking/{id}, /api/tracking/{id}
        res_t1 = client.get(f"/track/{sample_cr_id}", headers=headers)
        assert res_t1.status_code == 200
        t1_data = res_t1.json()["data"]

        res_t2 = client.get(f"/tracking/{sample_cr_id}", headers=headers)
        assert res_t2.status_code == 200

        res_t3 = client.get(f"/api/tracking/{sample_cr_id}", headers=headers)
        assert res_t3.status_code == 200

        # Verify margin metrics embedded in tracking details
        details = t1_data.get("details", {})
        assert "purchase_value" in details
        assert "sales_value" in details
        assert "margin" in details
        assert "margin_percent" in details

        # Verify timeline stages
        assert "timeline" in t1_data
        assert isinstance(t1_data["timeline"], list)
        print(f"  Info: Customer Request #{sample_cr_id} timeline has {len(t1_data['timeline'])} audit events.")

    # 404 on non-existent tracking request
    res_track_404 = client.get("/tracking/9999999", headers=headers)
    assert res_track_404.status_code == 404

    print("  PASS: Email logs and Order Tracking with Margin verified.")

    print("\n" + "=" * 80)
    print("ALL SRS 6.0 TESTS PASSED SUCCESSFULLY (100% PASS RATE)!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_analytics_dashboard_reports_suite()
