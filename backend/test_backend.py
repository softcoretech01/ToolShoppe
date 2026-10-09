"""
Comprehensive test script for ToolShoppe FastAPI Backend.
Uses FastAPI TestClient to test all endpoints end-to-end.
"""
import sys
from decimal import Decimal
from starlette.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.models.user import User
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.item import Item

client = TestClient(app)


def test_suite():
    print("\n" + "=" * 60)
    print("RUNNING TOOLSHOPPE BACKEND VERIFICATION SUITE")
    print("=" * 60)

    # 1. Database & Seed Verification
    print("\n[1/7] Testing database initialization & seed data...")
    db = SessionLocal()
    try:
        init_db(db)
        admin = db.query(User).filter(User.username == "admin").first()
        assert admin is not None, "Admin user must exist"
        assert admin.role == "Admin", "Admin role must be 'Admin'"

        cus_count = db.query(Customer).count()
        sup_count = db.query(Supplier).count()
        itm_count = db.query(Item).count()
        print(f"  -> Customers in DB: {cus_count} (>= 3 required)")
        print(f"  -> Suppliers in DB: {sup_count} (>= 3 required)")
        print(f"  -> Items in DB:     {itm_count} (>= 10 required)")
        assert cus_count >= 3, "At least 3 customers must be seeded"
        assert sup_count >= 3, "At least 3 suppliers must be seeded"
        assert itm_count >= 10, "At least 10 items must be seeded"
        print("  PASS: Seed data verified.")
    finally:
        db.close()

    # 2. Root & Documentation
    print("\n[2/7] Testing root & OpenAPI documentation...")
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["success"] is True

    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert "ToolShoppe ERP Backend" in schema["info"]["title"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/customers" in schema["paths"]
    assert "/api/v1/suppliers" in schema["paths"]
    assert "/api/v1/items" in schema["paths"]
    print("  PASS: OpenAPI specification and Swagger endpoints verified.")

    # 3. Authentication
    print("\n[3/7] Testing Authentication endpoints...")
    # Bad login
    bad_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert bad_login.status_code == 401
    assert bad_login.json()["success"] is False

    # Good login
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["success"] is True
    assert "access_token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "Admin"
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get /me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["username"] == "admin"
    print("  PASS: Authentication and JWT Bearer flow verified.")

    import time
    ts = int(time.time() * 1000)

    # 4. Customer Master CRUD
    print("\n[4/7] Testing Customer Master CRUD & Validation...")
    # Validation error: markup > 100
    invalid_cus = client.post("/api/v1/customers", json={
        "name": "Invalid Customer",
        "email": f"invalid_{ts}@test.com",
        "default_markup": 150.00
    }, headers=headers)
    assert invalid_cus.status_code == 422
    assert invalid_cus.json()["success"] is False

    # Create new customer
    test_email = f"apex_{ts}@apexprecision.in"
    new_cus_res = client.post("/api/v1/customers", json={
        "name": "Apex Precision Tools Pvt Ltd",
        "email": test_email,
        "phone": "+91 98401 99999",
        "gstin": "33AAAPA9999P1Z1",
        "billing_address": "SIDCO Industrial Estate, Guindy, Chennai",
        "shipping_address": "SIDCO Industrial Estate, Guindy, Chennai",
        "default_markup": 18.5,
        "payment_terms": "30 days"
    }, headers=headers)
    assert new_cus_res.status_code == 201
    cus_data = new_cus_res.json()["data"]
    cus_id = cus_data["id"]
    assert cus_data["customer_code"].startswith("CUS-")
    assert cus_data["name"] == "Apex Precision Tools Pvt Ltd"

    # Duplicate email check
    dup_res = client.post("/api/v1/customers", json={
        "name": "Apex Duplicate",
        "email": test_email,
    }, headers=headers)
    assert dup_res.status_code == 400

    # List customers with search
    search_res = client.get("/api/v1/customers?search=Apex", headers=headers)
    assert search_res.status_code == 200
    assert len(search_res.json()["data"]["items"]) >= 1

    # Update customer
    update_res = client.put(f"/api/v1/customers/{cus_id}", json={
        "name": "Apex Precision Engineering Ltd",
        "default_markup": 20.0
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Apex Precision Engineering Ltd"

    # Soft delete / toggle status
    deactivate_res = client.patch(f"/api/v1/customers/{cus_id}/status", json={"status": False}, headers=headers)
    assert deactivate_res.status_code == 200
    assert deactivate_res.json()["data"]["status"] is False

    # Check filter inactive
    inactive_res = client.get("/api/v1/customers?status=inactive", headers=headers)
    assert any(c["id"] == cus_id for c in inactive_res.json()["data"]["items"])

    # Reactivate
    activate_res = client.patch(f"/api/v1/customers/{cus_id}/status", json={"status": True}, headers=headers)
    assert activate_res.status_code == 200
    assert activate_res.json()["data"]["status"] is True
    print("  PASS: Customer CRUD, validation, and soft-delete verified.")

    # 5. Supplier Master CRUD
    print("\n[5/7] Testing Supplier Master CRUD & Validation...")
    # Validation error: negative lead time
    invalid_sup = client.post("/api/v1/suppliers", json={
        "name": "Bad Supplier",
        "email": f"bad_{ts}@sup.com",
        "lead_time_days": -5
    }, headers=headers)
    assert invalid_sup.status_code == 422
    assert invalid_sup.json()["success"] is False

    # Create new supplier
    sup_email = f"sales_{ts}@supertechtools.com"
    new_sup_res = client.post("/api/v1/suppliers", json={
        "name": f"SuperTech Tooling Solutions {ts}",
        "contact_person": "K. Ramanathan",
        "phone": "+91 97890 12345",
        "email": sup_email,
        "categories": "Cutting tools, Carbide Inserts",
        "lead_time_days": 6
    }, headers=headers)
    assert new_sup_res.status_code == 201
    sup_data = new_sup_res.json()["data"]
    sup_id = sup_data["id"]
    assert sup_data["supplier_code"].startswith("SUP-")

    # List suppliers with search
    sup_list = client.get(f"/api/v1/suppliers?search={ts}", headers=headers)
    assert sup_list.status_code == 200
    assert len(sup_list.json()["data"]["items"]) >= 1

    # Update supplier
    sup_update = client.put(f"/api/v1/suppliers/{sup_id}", json={
        "lead_time_days": 8
    }, headers=headers)
    assert sup_update.status_code == 200
    assert sup_update.json()["data"]["lead_time_days"] == 8

    # Soft delete
    sup_deact = client.patch(f"/api/v1/suppliers/{sup_id}/status", json={"status": False}, headers=headers)
    assert sup_deact.status_code == 200
    assert sup_deact.json()["data"]["status"] is False
    print("  PASS: Supplier CRUD, validation, and soft-delete verified.")

    # 6. Item Master CRUD
    print("\n[6/7] Testing Item Master CRUD & Validation...")
    # Validation error: tax > 100
    invalid_itm = client.post("/api/v1/items", json={
        "name": "Bad Item",
        "unit": "Nos",
        "tax_percent": 120.0
    }, headers=headers)
    assert invalid_itm.status_code == 422

    # Create new item
    item_name = f"Carbide Ball Nose End Mill R5 {ts}"
    new_itm_res = client.post("/api/v1/items", json={
        "name": item_name,
        "description": "2-Flute solid carbide ball nose, nano AlTiN coating",
        "category": "Cutting tools",
        "unit": "Nos",
        "hsn_code": "82075090",
        "tax_percent": 18.0,
        "last_purchase_rate": 1450.00
    }, headers=headers)
    assert new_itm_res.status_code == 201
    itm_data = new_itm_res.json()["data"]
    itm_id = itm_data["id"]
    assert itm_data["item_code"].startswith("ITM-")
    assert float(itm_data["last_purchase_rate"]) == 1450.00

    # Query with category filter
    cat_items = client.get("/api/v1/items?category=Cutting", headers=headers)
    assert cat_items.status_code == 200
    assert len(cat_items.json()["data"]["items"]) >= 1

    # Update item
    itm_update = client.put(f"/api/v1/items/{itm_id}", json={
        "last_purchase_rate": 1500.00
    }, headers=headers)
    assert itm_update.status_code == 200
    assert float(itm_update.json()["data"]["last_purchase_rate"]) == 1500.00

    # Soft delete item
    itm_deact = client.patch(f"/api/v1/items/{itm_id}/status", json={"status": False}, headers=headers)
    assert itm_deact.status_code == 200
    assert itm_deact.json()["data"]["status"] is False
    print("  PASS: Item CRUD, category filtering, and soft-delete verified.")

    # 7. Unauthenticated Access Protection
    print("\n[7/7] Testing endpoint protection without token...")
    unauth_cus = client.get("/api/v1/customers")
    assert unauth_cus.status_code == 401
    unauth_sup = client.get("/api/v1/suppliers")
    assert unauth_sup.status_code == 401
    unauth_itm = client.get("/api/v1/items")
    assert unauth_itm.status_code == 401
    print("  PASS: Protected routes reject unauthorized requests with 401.")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY! (100% DONE)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_suite()
