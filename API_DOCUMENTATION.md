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
  "source_id": 1001,
  "invoice_number": "INV-2026-001",
  "invoice_date": "2026-09-29",
  "total_amount": 2450.75,
  "customer_name": "Ramesh Kumar",
  "customer_phone": "9876543210",
  "created_updated_timestamp": "2026-09-29 17:15:00"
}
```

#### Field Specifications

| Field | Required | Type | Validation / Behavior |
| :--- | :--- | :--- | :--- |
| `source_id` / `Source_id` | **Yes** | Integer | Mandatory source system record ID. **Must be unique**: duplicates are rejected (`409 Conflict`). Missing value returns `400 Bad Request`. |
| `invoice_number` | Optional | String | Invoice identifier. Falls back to auto-generated string if omitted. |
| `invoice_date` | Optional | String | Stored directly as supplied (raw string, up to 100 characters; does not fallback to current date). |
| `total_amount` | Optional | Numeric | Decimal amount. Falls back to `0.00` if missing or invalid. |
| `customer_name` | Optional | String | Customer name string. Falls back to `"N/A"` if omitted. |
| `customer_phone` | Optional | String | Phone number string. |
| `created_updated_timestamp` | Optional | String | Client timestamp string e.g. `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS`. |

#### Success Response (`201 Created`)
```json
{
  "code": 201,
  "message": "Sale entry created successfully.",
  "data": {
    "id": "e9b5a8d4-53a8-4e89-9400-b6f123456789",
    "source_id": 1001,
    "invoice_number": "INV-2026-001",
    "invoice_date": "2026-09-29",
    "total_amount": "2450.75",
    "customer_name": "Ramesh Kumar",
    "customer_phone": "9876543210",
    "created_updated_timestamp": "2026-09-29 17:15:00",
    "user_id": "13492a1c-e9f1-4837-a49c-7098fdff1033",
    "username": "admin"
  }
}
```

#### Error Responses

- **400 Bad Request** (Missing `source_id`):
  ```json
  {
    "code": 400,
    "message": "source_id is required.",
    "error": "Validation Error"
  }
  ```

- **409 Conflict** (Duplicate `source_id`):
  ```json
  {
    "code": 409,
    "message": "Sale with source_id '1001' already exists.",
    "error": "Duplicate Entry",
    "data": {
      "existing_id": "e9b5a8d4-53a8-4e89-9400-b6f123456789",
      "source_id": 1001,
      "invoice_number": "INV-2026-001"
    }
  }
  ```

- **400 Bad Request** (Invalid `source_id`):
  ```json
  {
    "code": 400,
    "message": "source_id must be a valid integer.",
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

### 2. Create Bulk Sales Entries (Max 500 Records)

Batch inserts up to **500 sales entries** in a single transaction.

- **Endpoint**: `POST /api/v1/sales/bulk`
- **Auth Required**: Yes (`Authorization: Bearer <token>`)

#### Request Body
```json
{
  "sales": [
    {
      "source_id": 2001,
      "invoice_number": "INV-2026-010",
      "invoice_date": "2026-09-29",
      "total_amount": 1500.50,
      "customer_name": "John Doe",
      "customer_phone": "9876543210",
      "created_updated_timestamp": "2026-09-29 17:10:00"
    },
    {
      "source_id": 2002,
      "invoice_number": "INV-2026-011",
      "invoice_date": "2026-09-29",
      "total_amount": 2200.00,
      "customer_name": "Jane Smith",
      "customer_phone": "9123456789"
    }
  ]
}
```

#### Batch Constraints & Limits
- **Maximum Records**: 500 items in `sales` array.
- **Item-Level Fault Isolation**: If an individual item fails validation (e.g. missing `source_id`, non-integer `source_id`, non-object item) or is a duplicate, **only that item is skipped**. The remaining valid items in the batch are processed and saved normally.
- **Flexible Fields**: If `invoice_number` is missing on a valid item, an auto-generated invoice number is assigned. `invoice_date` is stored as provided without modification.

#### Success Response (`201 Created`)
```json
{
  "code": 201,
  "message": "Processed bulk sales: 2 created, 1 skipped.",
  "data": {
    "created_count": 2,
    "skipped_count": 1,
    "skipped_items": [
      {
        "index": 0,
        "source_id": null,
        "reason": "source_id is required for item at index 0."
      }
    ],
    "sales": [
      {
        "id": "e9b5a8d4-53a8-4e89-9400-b6f123456789",
        "source_id": 2002,
        "invoice_number": "INV-2026-010",
        "invoice_date": "2026-09-29",
        "total_amount": "1500.50",
        "customer_name": "John Doe",
        "customer_phone": "9876543210",
        "created_updated_timestamp": "2026-09-29 17:10:00",
        "user_id": "13492a1c-e9f1-4837-a49c-7098fdff1033",
        "username": "admin"
      },
      {
        "id": "f8a4b7c3-42b7-4d78-8399-a5e012345678",
        "source_id": 2003,
        "invoice_number": "INV-2026-011",
        "invoice_date": "2026-09-29",
        "total_amount": "2200.00",
        "customer_name": "Jane Smith",
        "customer_phone": "9123456789",
        "created_updated_timestamp": null,
        "user_id": "13492a1c-e9f1-4837-a49c-7098fdff1033",
        "username": "admin"
      }
    ]
  }
}
```

#### Error Responses

- **400 Bad Request** (Empty `sales` list):
  ```json
  {
    "code": 400,
    "message": "The 'sales' list cannot be empty.",
    "error": "Validation Error"
  }
  ```

- **400 Bad Request** (Limit Exceeded > 500 records):
  ```json
  {
    "code": 400,
    "message": "Bulk creation limit exceeded. Maximum 500 records allowed per request (received 501).",
    "error": "Validation Error"
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
