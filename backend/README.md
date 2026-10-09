# ToolShoppe ERP — FastAPI Backend

Production-ready, layered REST backend for **ToolShoppe ERP** developed with FastAPI, SQLAlchemy 2.0, Pydantic v2, and MySQL with automated SQLite fallback.

---

## Architecture

```text
backend/
│
├── app/
│   ├── main.py                  # FastAPI app factory, CORS, exception handlers
│   ├── core/
│   │   ├── config.py            # Environment settings and CORS configuration
│   │   ├── security.py          # Password hashing (bcrypt / PBKDF2) & JWT tokens
│   │   └── auth.py              # OAuth2 Bearer token dependencies
│   ├── db/
│   │   ├── base.py              # SQLAlchemy 2.0 DeclarativeBase
│   │   ├── session.py           # Database engine with MySQL and SQLite fallback
│   │   └── init_db.py           # Table creation & sample data seeder
│   ├── models/                  # SQLAlchemy 2.0 ORM Models
│   │   ├── user.py              # users table
│   │   ├── customer.py          # customers table
│   │   ├── supplier.py          # suppliers table
│   │   └── item.py              # items table
│   ├── schemas/                 # Pydantic v2 validation models
│   │   ├── response.py          # Standard SuccessResponse and ErrorResponse envelopes
│   │   ├── user.py              # Login and UserOut schemas
│   │   ├── customer.py          # Customer CRUD schemas
│   │   ├── supplier.py          # Supplier CRUD schemas
│   │   └── item.py              # Item CRUD schemas
│   ├── crud/                    # Data access layer
│   │   ├── customer.py          # Customer queries, auto-numbering (CUS-001)
│   │   ├── supplier.py          # Supplier queries, auto-numbering (SUP-001)
│   │   └── item.py              # Item queries, auto-numbering (ITM-0001)
│   ├── api/
│   │   └── v1/                  # Version 1 API routers
│   │       ├── auth.py          # /api/v1/auth/login and /api/v1/auth/me
│   │       ├── customers.py     # /api/v1/customers CRUD and status toggle
│   │       ├── suppliers.py     # /api/v1/suppliers CRUD and status toggle
│   │       └── items.py         # /api/v1/items CRUD and status toggle
│   └── utils/
│
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (Tested with Python 3.14)
- MySQL Server (optional; falls back automatically to SQLite for immediate zero-config testing)

### 2. Configuration (`.env`)
Copy `.env.example` to `.env` or customize settings:

```env
PROJECT_NAME="ToolShoppe ERP Backend"
API_V1_STR="/api/v1"
SECRET_KEY="toolshoppe_super_secret_jwt_key_change_in_production"
DATABASE_URL="mysql+pymysql://root:root@localhost:3306/toolshoppe?charset=utf8mb4"
FALLBACK_TO_SQLITE=True
SQLITE_DB_PATH="./toolshoppe.db"
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
```

### 3. Run the Development Server
From the `backend/` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

On first startup, the database tables are automatically initialized and pre-seeded with:
- Default Admin account (`admin` / `admin123`)
- 3 Sample Customers
- 3 Sample Suppliers
- 10 Sample Items

---

## Interactive API Documentation

Once the server is running:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Default Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | `Admin` |

---

## API Endpoints Overview

### Authentication
- `POST /api/v1/auth/login` — Authenticate and receive a JWT Bearer token
- `GET /api/v1/auth/me` — Retrieve current authenticated user profile

### Customer Master
- `POST /api/v1/customers` — Create customer (auto-generates `CUS-001`, enforces unique email, markup 0–100%)
- `GET /api/v1/customers` — List customers with search, status filter (`active`, `inactive`, `all`), and pagination
- `GET /api/v1/customers/{id}` — Get single customer details
- `PUT /api/v1/customers/{id}` — Update customer details
- `PATCH /api/v1/customers/{id}/status` — Activate/deactivate customer (soft delete)

### Supplier Master
- `POST /api/v1/suppliers` — Create supplier (auto-generates `SUP-001`, non-negative lead time)
- `GET /api/v1/suppliers` — List suppliers with search, status filter, and pagination
- `GET /api/v1/suppliers/{id}` — Get single supplier details
- `PUT /api/v1/suppliers/{id}` — Update supplier details
- `PATCH /api/v1/suppliers/{id}/status` — Activate/deactivate supplier (soft delete)

### Item Master
- `POST /api/v1/items` — Create item (auto-generates `ITM-0001`, tax 0–100%, non-negative rate)
- `GET /api/v1/items` — List items with category filter, search, status filter, and pagination
- `GET /api/v1/items/{id}` — Get single item details
- `PUT /api/v1/items/{id}` — Update item details
- `PATCH /api/v1/items/{id}/status` — Activate/deactivate item (soft delete)

---

## Standardized Responses

### Success Response
```json
{
  "success": true,
  "message": "Customer created successfully",
  "data": {
    "id": 1,
    "customer_code": "CUS-001",
    "name": "Bharat Engineering Works",
    "email": "purchase@bharatengg.co.in",
    "status": true
  }
}
```

### Validation Error Response
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": [
    {
      "field": "default_markup",
      "message": "Input should be less than or equal to 100",
      "type": "less_than_equal"
    }
  ]
}
```
