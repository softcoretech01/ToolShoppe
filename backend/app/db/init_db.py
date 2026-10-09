import logging
from decimal import Decimal
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.item import Item

logger = logging.getLogger("app.init_db")


def init_db(db: Session) -> None:
    """Initialize tables and populate default admin and sample seed data."""
    # Ensure all tables are created
    Base.metadata.create_all(bind=engine)

    # Migrate columns if tables pre-exist without new columns
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        if "outwards" in table_names:
            outward_cols = [c["name"] for c in inspector.get_columns("outwards")]
            with engine.begin() as conn:
                if "created_by" not in outward_cols:
                    conn.execute(text("ALTER TABLE outwards ADD COLUMN created_by INTEGER NULL"))
                if "updated_at" not in outward_cols:
                    conn.execute(text("ALTER TABLE outwards ADD COLUMN updated_at DATETIME NULL"))
        if "outward_items" in table_names:
            item_cols = [c["name"] for c in inspector.get_columns("outward_items")]
            with engine.begin() as conn:
                if "available_qty" not in item_cols:
                    conn.execute(text("ALTER TABLE outward_items ADD COLUMN available_qty NUMERIC(12, 2) DEFAULT 0.00"))
                if "unit" not in item_cols:
                    conn.execute(text("ALTER TABLE outward_items ADD COLUMN unit VARCHAR(50) DEFAULT 'Nos'"))
        if "email_logs" in table_names:
            email_cols = [c["name"] for c in inspector.get_columns("email_logs")]
            with engine.begin() as conn:
                if "status" not in email_cols:
                    conn.execute(text("ALTER TABLE email_logs ADD COLUMN status VARCHAR(50) DEFAULT 'Sent'"))
                if "error_message" not in email_cols:
                    conn.execute(text("ALTER TABLE email_logs ADD COLUMN error_message VARCHAR(500) NULL"))
    except Exception as exc:
        logger.warning(f"Column migration warning (safe to ignore): {exc}")

    # 1. Default Admin User
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        logger.info("Seeding default admin user (admin / admin123)...")
        admin_user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="Admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()

    # 2. Sample Customers
    if db.query(Customer).count() == 0:
        logger.info("Seeding sample customers...")
        sample_customers = [
            Customer(
                customer_code="CUS-001",
                name="Bharat Engineering Works",
                email="purchase@bharatengg.co.in",
                phone="+91 98400 11223",
                gstin="33AABCB1234K1Z5",
                billing_address="14, Ambattur Industrial Estate, Chennai 600058",
                shipping_address="Plant 2, Ambattur Industrial Estate, Chennai 600058",
                default_markup=Decimal("12.00"),
                payment_terms="30 days from invoice",
                status=True,
            ),
            Customer(
                customer_code="CUS-002",
                name="Sundaram Auto Components",
                email="stores@sundaramauto.com",
                phone="+91 98410 44556",
                gstin="33AACCS7788M1ZP",
                billing_address="92, Sipcot Industrial Park, Irungattukottai 602117",
                shipping_address="92, Sipcot Industrial Park, Irungattukottai 602117",
                default_markup=Decimal("15.00"),
                payment_terms="45 days from invoice",
                status=True,
            ),
            Customer(
                customer_code="CUS-003",
                name="Kaveri Fabrication Pvt Ltd",
                email="arun@kaverifab.in",
                phone="+91 99620 77889",
                gstin="33AAECK5566L1ZQ",
                billing_address="7/3, Thirumudivakkam Industrial Estate, Chennai 600044",
                shipping_address="7/3, Thirumudivakkam Industrial Estate, Chennai 600044",
                default_markup=Decimal("20.00"),
                payment_terms="Advance 50%, balance on delivery",
                status=True,
            ),
        ]
        db.add_all(sample_customers)
        db.commit()

    # 3. Sample Suppliers
    if db.query(Supplier).count() == 0:
        logger.info("Seeding sample suppliers...")
        sample_suppliers = [
            Supplier(
                supplier_code="SUP-001",
                name="Sri Venkateswara Tools",
                contact_person="V. Rajesh",
                phone="+91 94440 12345",
                email="sales@svtools.in",
                categories="Cutting tools, Hand tools",
                lead_time_days=5,
                status=True,
            ),
            Supplier(
                supplier_code="SUP-002",
                name="Ganesh Industrial Supplies",
                contact_person="M. Ganesan",
                phone="+91 93810 55667",
                email="orders@ganeshindustrial.com",
                categories="Cutting tools, Measuring, Abrasives",
                lead_time_days=7,
                status=True,
            ),
            Supplier(
                supplier_code="SUP-003",
                name="Metro Hardware & Abrasives",
                contact_person="D. Nirmala",
                phone="+91 90030 33445",
                email="metro.hardware@gmail.com",
                categories="Hand tools, Abrasives",
                lead_time_days=4,
                status=True,
            ),
        ]
        db.add_all(sample_suppliers)
        db.commit()

    # 4. Sample Items
    if db.query(Item).count() == 0:
        logger.info("Seeding sample items...")
        sample_items = [
            Item(
                item_code="ITM-0001",
                name="HSS Drill Bit Set 1-13mm",
                description="Jobber length, 25 pieces, ground finish",
                category="Cutting tools",
                unit="Set",
                hsn_code="82075010",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("1150.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0002",
                name="Carbide End Mill 10mm 4-Flute",
                description="Solid carbide, TiAlN coated",
                category="Cutting tools",
                unit="Nos",
                hsn_code="82075090",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("980.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0003",
                name="Tap & Die Set M3-M12",
                description="32 piece set in steel case",
                category="Cutting tools",
                unit="Set",
                hsn_code="82076010",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("2250.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0004",
                name="Adjustable Wrench 300mm",
                description="Chrome vanadium, 12 inch",
                category="Hand tools",
                unit="Nos",
                hsn_code="82040000",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("615.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0005",
                name="Combination Plier 200mm",
                description="Insulated 1000V, 8 inch",
                category="Hand tools",
                unit="Nos",
                hsn_code="82032000",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("385.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0006",
                name="Screwdriver Set 12pc",
                description="Slotted and Phillips, magnetic tip",
                category="Hand tools",
                unit="Set",
                hsn_code="82054000",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("720.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0007",
                name="Digital Vernier Caliper 150mm",
                description="Resolution 0.01mm, IP54",
                category="Measuring",
                unit="Nos",
                hsn_code="90172000",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("2380.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0008",
                name="Outside Micrometer 0-25mm",
                description="Ratchet stop, carbide anvil",
                category="Measuring",
                unit="Nos",
                hsn_code="90172000",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("1850.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0009",
                name="Steel Rule 300mm",
                description="Stainless, dual marking mm/inch",
                category="Measuring",
                unit="Nos",
                hsn_code="90178000",
                tax_percent=Decimal("12.00"),
                last_purchase_rate=Decimal("145.00"),
                status=True,
            ),
            Item(
                item_code="ITM-0010",
                name="Flap Disc 100mm A60",
                description="Zirconia, pack of 10",
                category="Abrasives",
                unit="Box",
                hsn_code="68042210",
                tax_percent=Decimal("18.00"),
                last_purchase_rate=Decimal("295.00"),
                status=True,
            ),
        ]
        db.add_all(sample_items)
        db.commit()

    # 5. Sample 12-Document Order Workflow
    try:
        from app.db.seed_demo_workflow import seed_demo_workflow
        seed_demo_workflow(db)
    except Exception as exc:
        logger.warning(f"Demo workflow seeding notice: {exc}")

    logger.info("Database initialization and seeding completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
