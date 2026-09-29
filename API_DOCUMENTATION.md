# SaleAPI - Technical API Documentation

## Overview

Welcome to the **SaleAPI** documentation. This service provides secure, production-grade endpoints for authentication and sales transaction recording.

- **Base URL**: `http://<host>:<port>` (Default: `http://localhost:5000`)
- **Content-Type**: `application/json`
- **Authentication**: HTTP `Authorization: Bearer <access_token>`

---

## Key Features & Security Policies

1. **Bearer Token Authentication**:
   - Access tokens are valid for **12 hours** (configurable via `JWT_ACCESS_TOKEN_EXPIRES_HOURS` in `.env`).
   - No refresh tokens are used.

2. **Single Active Session Policy**:
   - Each user can have only **one active JWT token at a time**.
   - Requesting a new token automatically invalidates/revokes any previously issued token for that user.

3. **Rate Limiting**:
   - Strictly enforced on authentication (`POST /api/v1/auth/token`).
   - Maximum **4 authentication attempts per hour** per username/IP combination.
   - Sales APIs are exempt from this limit.

4. **Standardized Response Envelope**:
   - All responses follow a unified JSON structure containing `code`, `message`, `data` (on success), and `error` (on failure).

---

## Standard Response Format

### Success Response (`200 OK` / `201 Created`)

```json
{
  "code": 200,
  "message": "Operation completed successfully.",
  "data": { ... }
}
```

### Error Response (`400`, `401`, `403`, `409`, `429`)

```json
{
  "code": 400,
  "message": "Detailed error message describing what went wrong.",
  "error": "Error Type Category"
}
```

---

## Authentication Endpoints

### 1. Generate Auth Token

Generates a 12-hour JWT Bearer token. Disables any active prior token for the user.

- **Endpoint**: `POST /api/v1/auth/token`
- **Auth Required**: No
- **Rate Limit**: Max 4 attempts per hour

#### Request Body
```json
{
  "username": "admin",
  "password": "your_secure_password"
}
```

#### Success Response (`200 OK`)
```json
{
  "code": 200,
  "message": "Authentication token generated successfully.",
  "data": {
    "token_type": "Bearer",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in_hours": 12,
    "user": {
      "id": "13492a1c-e9f1-4837-a49c-7098fdff1033",
      "username": "admin"
    }
  }
}
```

#### Error Responses

- **400 Bad Request** (Missing Credentials):
  ```json
  {
    "code": 400,
    "message": "Username and password are required.",
    "error": "Validation Error"
  }
  ```

- **401 Unauthorized** (Invalid Credentials):
  ```json
  {
    "code": 401,
    "message": "Invalid username or password.",
    "error": "Unauthorized"
  }
  ```

- **403 Forbidden** (Disabled User Account):
  ```json
  {
    "code": 403,
    "message": "User account is disabled. Please contact administrator.",
    "error": "Forbidden"
  }
  ```

- **429 Too Many Requests** (Rate Limit Exceeded):
  ```json
  {
    "code": 429,
    "message": "Maximum authentication attempts exceeded (4 attempts allowed per hour). Please try again later.",
    "error": "Rate Limit Exceeded"
  }
  ```

---

### 2. Get Current User Profile

Retrieves current authenticated user details.

- **Endpoint**: `GET /api/v1/auth/me`
- **Auth Required**: Yes (`Authorization: Bearer <token>`)

#### Success Response (`200 OK`)
```json
{
  "code": 200,
  "message": "User profile retrieved successfully.",
  "data": {
    "id": "13492a1c-e9f1-4837-a49c-7098fdff1033",
    "username": "admin",
    "is_active": true,
    "created_at": "2026-09-29T16:30:54+00:00"
  }
}
```

---

## Sales Endpoints

### 1. Create Sale Entry

Creates a new sale transaction record linked to the authenticated user.

- **Endpoint**: `POST /api/v1/sales`
- **Auth Required**: Yes (`Authorization: Bearer <token>`)

#### Request Body
```json
{
  "invoice_number": "INV-2026-001",
  "invoice_date": "2026-09-29",
  "total_amount": 2450.75,
  "customer_name": "Ramesh Kumar",
  "customer_phone": "9876543210",
  "created_updated_timestamp": "2026-09-29 17:15:00"
}
```

#### Field Validation Specifications

| Field | Required | Type | Validation Rules |
| :--- | :--- | :--- | :--- |
| `invoice_number` | **Yes** | String | Must be unique across all sales entries. |
| `invoice_date` | **Yes** | String | Format: `YYYY-MM-DD` |
| `total_amount` | **Yes** | Numeric | Greater than 0, rounded to 2 decimal places. |
| `customer_name` | **Yes** | String | Non-empty text string. |
| `customer_phone` | Optional | String | Must be **exactly 10 digits** (`^\d{10}$`). |
| `created_updated_timestamp` | Optional | String | Timestamp string e.g. `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS`. |

#### Success Response (`201 Created`)
```json
{
  "code": 201,
  "message": "Sale entry created successfully.",
  "data": {
    "id": "e9b5a8d4-53a8-4e89-9400-b6f123456789",
    "invoice_number": "INV-2026-001",
    "invoice_date": "2026-09-29",
    "total_amount": "2450.75",
    "customer_name": "Ramesh Kumar",
    "customer_phone": "9876543210",
    "created_updated_timestamp": "2026-09-29 17:15:00",
    "user_id": "13492a1c-e9f1-4837-a49c-7098fdff1033",
    "username": "admin",
    "created_at": "2026-09-29T17:15:05.123456+00:00",
    "updated_at": "2026-09-29T17:15:05.123456+00:00"
  }
}
```

#### Error Responses

- **409 Conflict** (Duplicate Invoice Number):
  ```json
  {
    "code": 409,
    "message": "Invoice number 'INV-2026-001' already exists.",
    "error": "Duplicate Entry"
  }
  ```

- **400 Bad Request** (Invalid Phone Number):
  ```json
  {
    "code": 400,
    "message": "customer_phone must be a valid 10-digit number.",
    "error": "Validation Error"
  }
  ```

- **400 Bad Request** (Invalid Date Format):
  ```json
  {
    "code": 400,
    "message": "invoice_date must be in YYYY-MM-DD format.",
    "error": "Validation Error"
  }
  ```

- **401 Unauthorized** (Missing or Revoked Token):
  ```json
  {
    "code": 401,
    "message": "This token has been revoked because a newer login occurred or the account was disabled.",
    "error": "Token Revoked"
  }
  ```

---

## Health Check Endpoint

### Service Health Status

- **Endpoint**: `GET /health`
- **Auth Required**: No

#### Success Response (`200 OK`)
```json
{
  "code": 200,
  "message": "SaleAPI service is operational.",
  "data": {
    "status": "up"
  }
}
```

---

## Administrative User Management CLI (`script.py`)

User account management (creation, viewing, enabling, disabling, and deletion) is managed via the CLI script:

```bash
python script.py
```

### Menu Options
1. **Create User**: Prompts for username and password; hashes password with `werkzeug.security`.
2. **View Users**: Lists user IDs (UUID), usernames, status (`Active`/`Disabled`), and creation timestamps.
3. **Disable User**: Disables user login access and immediately revokes active tokens.
4. **Enable User**: Re-enables a disabled user account.
5. **Delete User**: Deletes user record permanently.
6. **Exit**: Exits CLI interface.
