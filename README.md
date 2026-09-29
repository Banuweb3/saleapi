# SaleAPI - Developer Guide & Project Documentation

## Project Overview

**SaleAPI** is a modular, production-grade Flask RESTful API designed for managing sales transactions with PostgreSQL database storage, JWT authentication, single active session enforcement, rate limiting, and request logging.

---

## Tech Stack

- **Framework**: Flask 3.1
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.1 / Flask-SQLAlchemy 3.1
- **Migrations**: Alembic / Flask-Migrate 4.1
- **Authentication**: Flask-JWT-Extended 4.7 (PyJWT)
- **Database Driver**: `psycopg2-binary`
- **Environment Management**: `python-dotenv`

---

## Folder Architecture

```text
saleapi/
├── app.py                   # Application Factory entry point
├── config.py                # Environment configuration & DB URI resolution
├── extensions.py            # Global extension instances (db, migrate, jwt)
├── jwt_callbacks.py         # JWT error handlers & blocklist callbacks
├── models.py                # SQLAlchemy ORM database models (User, Sale)
├── script.py                # CLI interactive tool for User Management
├── test_auth.py             # Integration test suite for Auth & Rate Limiting
├── test_sales.py            # Integration test suite for Sales API & Validations
├── requirements.txt         # Python package dependencies
├── .env                     # Production/Local environment variables (Git ignored)
├── .env.example             # Environment template
├── API_DOCUMENTATION.md     # Team API documentation reference
├── middleware/
│   ├── __init__.py
│   ├── logger.py            # Rotating file & console request logger middleware
│   └── rate_limiter.py      # Thread-safe in-memory auth attempt rate limiter
├── routes/
│   ├── __init__.py
│   ├── auth.py              # Authentication blueprint (/api/v1/auth)
│   └── sales.py             # Sales blueprint (/api/v1/sales)
├── migrations/              # Alembic database migration scripts
└── logs/                    # Rotating production log files (Git ignored)
```

---

## Setup & Local Development

### 1. Environment Activation

The application uses the virtual environment at `~/.venvs/saleapi`:

```bash
source ~/.venvs/saleapi/bin/activate
```

### 2. Environment Variables (`.env`)

Copy `.env.example` to `.env` and fill in your PostgreSQL database credentials:

```ini
# PostgreSQL Database Credentials
DB_HOST=localhost
DB_PORT=5432
DB_NAME=saleapi_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# JWT Configuration
JWT_SECRET_KEY=super-secret-jwt-key
JWT_ACCESS_TOKEN_EXPIRES_HOURS=12
```

### 3. Database Migrations

When making changes to models in `models.py`, generate and apply Alembic migration scripts:

```bash
# Generate a new migration script
flask db migrate -m "Describe your schema changes"

# Apply pending migrations to PostgreSQL
flask db upgrade
```

### 4. Running the Application

To start the Flask development server:

```bash
python app.py
```

Server runs on: `http://localhost:5000`

---

## CLI User Management Tool (`script.py`)

To manage user accounts (Create, View, Disable, Enable, Delete):

```bash
python script.py
```

---

## Running Test Suites

Run automated unit and integration tests:

```bash
# Run Authentication & Rate Limiting tests
python test_auth.py

# Run Sales API & Validation tests
python test_sales.py
```

---

## Developer Guidelines for Future Updates

### 1. Adding New Database Models

1. Open `models.py` and define your new `db.Model` class using `UUID(as_uuid=True)` for primary keys where applicable.
2. Run database migration commands:
   ```bash
   flask db migrate -m "Add NewModel table"
   flask db upgrade
   ```

### 2. Adding New API Routes

1. Create a new file in `routes/` (e.g. `routes/inventory.py`) and instantiate a Flask `Blueprint`:
   ```python
   from flask import Blueprint, jsonify
   
   inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/v1/inventory")
   ```
2. Export the blueprint in `routes/__init__.py`.
3. Register the blueprint in `app.py`:
   ```python
   app.register_blueprint(inventory_bp)
   ```

### 3. API Response Consistency Rules

Always use the standardized JSON envelope format:

- **Success (`200 OK` / `201 Created`)**:
  ```json
  {
    "code": 200,
    "message": "Descriptive success message.",
    "data": { ... }
  }
  ```

- **Error (`400`, `401`, `403`, `404`, `409`, `429`)**:
  ```json
  {
    "code": 400,
    "message": "Descriptive error message.",
    "error": "Error Category Name"
  }
  ```

### 4. Protecting Endpoints with JWT

To protect any route with Bearer token authentication:

```python
from flask_jwt_extended import jwt_required, get_jwt_identity

@my_bp.route("/protected-route", methods=["GET"])
@jwt_required()
def protected_handler():
    current_user_id = get_jwt_identity()
    ...
```

---

## Production Deployment Checklist

- [ ] Ensure `JWT_SECRET_KEY` and `SECRET_KEY` in `.env` are set to strong random values.
- [ ] Set `debug=False` in `app.py` or run via WSGI server like `gunicorn` / `uWSGI`:
  ```bash
  gunicorn -w 4 -b 0.0.0.0:5000 app:app
  ```
- [ ] Ensure PostgreSQL database indexes and constraints are verified.
