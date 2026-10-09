import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.suppliers import router as suppliers_router
from app.api.v1.items import router as items_router
from app.api.v1.customer_requests import router as customer_requests_router
from app.api.v1.purchase_requests import router as purchase_requests_router
from app.api.v1.vendor_quotations import router as vendor_quotations_router
from app.api.v1.comparisons import router as comparisons_router
from app.api.v1.tracking import router as tracking_router
from app.api.v1.email_logs import router as email_logs_router, api_alias_router as email_logs_api_router
from app.api.v1.customer_quotations import router as customer_quotations_router
from app.api.v1.customer_orders import router as customer_orders_router
from app.api.v1.purchase_orders import router as purchase_orders_router
from app.api.v1.grn import router as grn_router
from app.api.v1.inward import router as inward_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.outwards import router as outwards_router, api_alias_router as outwards_api_router
from app.api.v1.sales_invoices import router as sales_invoices_router, api_alias_router as sales_invoices_api_router
from app.api.v1.purchase_invoices import router as purchase_invoices_router, api_alias_router as purchase_invoices_api_router
from app.api.v1.dashboard import router as dashboard_router, api_alias_router as dashboard_api_router, root_alias_router as dashboard_root_router
from app.api.v1.reports import router as reports_router, api_alias_router as reports_api_router

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: initialize database tables and seed sample data on startup."""
    logger.info("Initializing database and checking seed records...")
    db = SessionLocal()
    try:
        init_db(db)
    except Exception as exc:
        logger.error(f"Error during startup database initialization: {exc}")
    finally:
        db.close()
    yield
    logger.info("Application shutdown complete.")


tags_metadata = [
    {
        "name": "0. Dashboard & Analytics",
        "description": "Executive KPI cards, actionable bottleneck alerts, workflow summary, and analytics charts.",
    },
    {
        "name": "1. Masters - Customers",
        "description": "Customer master records, payment terms, and contact details.",
    },
    {
        "name": "1. Masters - Suppliers",
        "description": "Supplier master directory, credit terms, and catalog mappings.",
    },
    {
        "name": "1. Masters - Items",
        "description": "Product catalog, SKU codes, pricing, units of measurement, and tax rates.",
    },
    {
        "name": "2. Sales - Customer Request",
        "description": "Customer sourcing requests and item requirements.",
    },
    {
        "name": "2. Sales - Quotation",
        "description": "Customer sales quotations, margins, and acceptance workflows.",
    },
    {
        "name": "2. Sales - Customer Order",
        "description": "Confirmed customer orders and dispatch readiness tracking.",
    },
    {
        "name": "2. Sales - Outward (Dispatch)",
        "description": "Delivery Challans (Outward) with strict inventory availability enforcement.",
    },
    {
        "name": "2. Sales - Invoice",
        "description": "Customer Sales Invoices generated from Delivery Challans.",
    },
    {
        "name": "3. Purchase - Request (PR & RFQ)",
        "description": "Purchase Requests (PR) and multi-supplier RFQ email dispatches.",
    },
    {
        "name": "3. Purchase - Vendor Quotation",
        "description": "Supplier quotation recording, landed rates, and payment terms.",
    },
    {
        "name": "3. Purchase - Quotation Comparison",
        "description": "Automated 4-tier vendor comparison matrix and approval decisions.",
    },
    {
        "name": "3. Purchase - Purchase Order (PO)",
        "description": "Supplier Purchase Orders with formal delivery dates and approval statuses.",
    },
    {
        "name": "3. Purchase - Goods Receipt Note (GRN)",
        "description": "Physical goods receipt with accepted/rejected quantity verification.",
    },
    {
        "name": "3. Purchase - Inward",
        "description": "Stock inwarding into warehouse inventory.",
    },
    {
        "name": "3. Purchase - Invoice",
        "description": "Supplier Purchase Invoices recorded against accepted GRN items.",
    },
    {
        "name": "4. Inventory",
        "description": "Real-time on-hand stock balances and full chronological stock ledger audit trail.",
    },
    {
        "name": "5. Reports & Analytics",
        "description": "Item-wise Sales, Purchase, Inventory, and Margin reports with RFC 4180 CSV export.",
    },
    {
        "name": "5. Order Tracking & Audit",
        "description": "14-stage end-to-end sourcing and order tracking timeline.",
    },
    {
        "name": "5. Email Communications",
        "description": "Outbound email dispatch audit logs (RFQs, quotations, etc.).",
    },
    {
        "name": "6. Authentication",
        "description": "JWT OAuth2 authentication and user management.",
    },
]

# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-grade FastAPI REST backend for **ToolShoppe ERP**.\n\n"
        "### Enterprise Modular Organization\n"
        "1. **0. Dashboard & Analytics**: Executive overview, KPIs, and charts.\n"
        "2. **1. Masters**: Customers, Suppliers, and Items.\n"
        "3. **2. Sales**: Customer Requests, Quotations, Orders, Outward/Dispatch, and Invoices.\n"
        "4. **3. Purchase**: PR & RFQ, Vendor Quotes, Comparison, PO, GRN, Inward, and Invoices.\n"
        "5. **4. Inventory**: Real-time stock summary and Stock Ledger.\n"
        "6. **5. Reports & Tracking**: Analytics reports with CSV export, audit trail, and email logs.\n"
    ),
    version="2.0.0",
    docs_url=None,
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Standardized Error Handling
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format request validation errors to match standard Error response."""
    errors = []
    for err in exc.errors():
        field_loc = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        errors.append({
            "field": field_loc or "body",
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
        content={
            "success": False,
            "message": "Validation failed",
            "errors": errors,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Format HTTP exceptions to match standard Error response."""
    detail = exc.detail
    errors = [detail] if isinstance(detail, str) else detail

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": detail if isinstance(detail, str) else "Request error occurred",
            "errors": errors if isinstance(errors, list) else [errors],
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all unexpected error handler."""
    logger.exception(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error occurred",
            "errors": [str(exc)],
        },
    )


# ============================================================================
# Mount API Routers
# ============================================================================

api_v1_prefix = settings.API_V1_STR

# 1. Mount under standard /api/v1 prefix
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(customers_router, prefix=api_v1_prefix)
app.include_router(suppliers_router, prefix=api_v1_prefix)
app.include_router(items_router, prefix=api_v1_prefix)
app.include_router(customer_requests_router, prefix=api_v1_prefix)
app.include_router(purchase_requests_router, prefix=api_v1_prefix)
app.include_router(vendor_quotations_router, prefix=api_v1_prefix)
app.include_router(comparisons_router, prefix=api_v1_prefix)
app.include_router(tracking_router, prefix=api_v1_prefix)
app.include_router(email_logs_router, prefix=api_v1_prefix)
app.include_router(customer_quotations_router, prefix=api_v1_prefix)
app.include_router(customer_orders_router, prefix=api_v1_prefix)
app.include_router(purchase_orders_router, prefix=api_v1_prefix)
app.include_router(grn_router, prefix=api_v1_prefix)
app.include_router(inward_router, prefix=api_v1_prefix)
app.include_router(inventory_router, prefix=api_v1_prefix)
app.include_router(outwards_router, prefix=api_v1_prefix)
app.include_router(sales_invoices_router, prefix=api_v1_prefix)
app.include_router(purchase_invoices_router, prefix=api_v1_prefix)
app.include_router(dashboard_router, prefix=api_v1_prefix)
app.include_router(reports_router, prefix=api_v1_prefix)

# 2. Mount root-level aliases matching API paths exactly
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(suppliers_router)
app.include_router(items_router)
app.include_router(customer_requests_router)
app.include_router(purchase_requests_router)
app.include_router(vendor_quotations_router)
app.include_router(comparisons_router)
app.include_router(tracking_router)
app.include_router(email_logs_router)
app.include_router(customer_quotations_router)
app.include_router(customer_orders_router)
app.include_router(purchase_orders_router)
app.include_router(grn_router)
app.include_router(inward_router)
app.include_router(inventory_router)
app.include_router(outwards_router)
app.include_router(sales_invoices_router)
app.include_router(purchase_invoices_router)
app.include_router(dashboard_router)
app.include_router(dashboard_root_router)
app.include_router(reports_router)

# 3. Mount /api/ prefixed aliases
app.include_router(auth_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(suppliers_router, prefix="/api")
app.include_router(items_router, prefix="/api")
app.include_router(outwards_api_router)
app.include_router(sales_invoices_api_router)
app.include_router(purchase_invoices_api_router)
app.include_router(dashboard_api_router)
app.include_router(reports_api_router)
app.include_router(email_logs_api_router)



@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={"persistAuthorization": True},
    )

    custom_injection = """
    <style>
      /* Transform button to 'Authorized' with solid green background when authenticated */
      .swagger-ui .btn.authorize.locked {
        background-color: #059669 !important;
        border-color: #047857 !important;
        color: #ffffff !important;
      }
      .swagger-ui .btn.authorize.locked span {
        display: none !important;
      }
      .swagger-ui .btn.authorize.locked::before {
        content: "Authorized " !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        margin-right: 6px !important;
      }
      .swagger-ui .btn.authorize.locked svg {
        fill: #ffffff !important;
      }
    </style>
    <script>
      document.addEventListener("DOMContentLoaded", function() {
        const updateAuthBtn = () => {
          const lockedBtn = document.querySelector('.btn.authorize.locked');
          if (lockedBtn) {
            const span = lockedBtn.querySelector('span');
            if (span && span.textContent !== 'Authorized') {
              span.textContent = 'Authorized';
            }
          }
        };
        const observer = new MutationObserver(updateAuthBtn);
        observer.observe(document.body, { childList: true, subtree: true });
        setInterval(updateAuthBtn, 1000);
      });
    </script>
    """
    html_content = response.body.decode("utf-8").replace("</head>", f"{custom_injection}\n</head>")
    return HTMLResponse(content=html_content)


@app.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get(
    "/",
    summary="Backend Health & Welcome",
    tags=["Root"],
)
@app.get(
    "/health",
    summary="Health Check",
    tags=["Root"],
)
@app.get(
    "/api/v1/health",
    summary="API v1 Health Check",
    tags=["Root"],
)
def root():
    return {
        "status": "healthy",
        "success": True,
        "message": f"Welcome to {settings.PROJECT_NAME} v1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }

