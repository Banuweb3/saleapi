import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Sale, User

sales_bp = Blueprint("sales", __name__, url_prefix="/api/v1/sales")

@sales_bp.route("", methods=["POST"])
@jwt_required()
def create_sale():
    """
    POST /api/v1/sales
    Requires Bearer Token authentication.
    
    Expected JSON Body:
    {
        "invoice_number": "INV-1001",
        "invoice_date": "2026-09-29",
        "total_amount": 1500.50,
        "customer_name": "John Doe",
        "customer_phone": "9876543210",
        "created_updated_timestamp": "2026-09-29 17:10:00"  (optional or ISO format YYYY-MM-DD HH:MM:SS / YYYY-MM-DDTHH:MM:SS)
    }
    """
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)

    if not user or not user.is_active:
        return jsonify({
            "code": 401,
            "message": "User account is invalid or disabled.",
            "error": "Unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    invoice_number = str(data.get("invoice_number", "")).strip() if data.get("invoice_number") else None
    invoice_date_str = str(data.get("invoice_date", "")).strip() if data.get("invoice_date") else None
    total_amount_raw = data.get("total_amount")
    customer_name = str(data.get("customer_name", "")).strip() if data.get("customer_name") else None
    customer_phone = str(data.get("customer_phone", "")).strip() if data.get("customer_phone") else None
    timestamp_str = str(data.get("created_updated_timestamp", "")).strip() if data.get("created_updated_timestamp") else None

    # --- VALIDATIONS COMMENTED OUT TO ACCEPT WHATEVER DATA COMES ---
    # # 1. Validate required fields presence
    # if not invoice_number:
    #     return jsonify({"code": 400, "message": "invoice_number is required.", "error": "Validation Error"}), 400
    # if not invoice_date_str:
    #     return jsonify({"code": 400, "message": "invoice_date is required.", "error": "Validation Error"}), 400
    # if total_amount_raw is None or total_amount_raw == "":
    #     return jsonify({"code": 400, "message": "total_amount is required.", "error": "Validation Error"}), 400
    # if not customer_name:
    #     return jsonify({"code": 400, "message": "customer_name is required.", "error": "Validation Error"}), 400

    # # 2. Check for duplicate invoice number
    # existing_sale = Sale.query.filter_by(invoice_number=invoice_number).first()
    # if existing_sale:
    #     return jsonify({"code": 409, "message": f"Invoice number '{invoice_number}' already exists.", "error": "Duplicate Entry"}), 409

    # # 3. Validate mandatory customer phone number format (must be 10 digits)
    # if not customer_phone:
    #     return jsonify({"code": 400, "message": "customer_phone is required.", "error": "Validation Error"}), 400
    # if not re.match(r"^\d{10}$", customer_phone):
    #     return jsonify({"code": 400, "message": "customer_phone must be a valid 10-digit number.", "error": "Validation Error"}), 400

    # 4. Parse invoice date (fallback to today if invalid/missing)
    parsed_invoice_date = None
    if invoice_date_str:
        try:
            parsed_invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if not parsed_invoice_date:
        parsed_invoice_date = datetime.now().date()

    # 5. Parse total_amount (fallback to 0.00 if invalid/missing)
    parsed_total_amount = Decimal("0.00")
    if total_amount_raw is not None and total_amount_raw != "":
        try:
            parsed_total_amount = Decimal(str(total_amount_raw)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            pass

    # 6. Parse client timestamp
    parsed_client_timestamp = None
    if timestamp_str:
        allowed_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f"
        ]
        for fmt in allowed_formats:
            try:
                parsed_client_timestamp = datetime.strptime(timestamp_str, fmt)
                break
            except ValueError:
                continue

    # Create new Sale record
    new_sale = Sale(
        invoice_number=invoice_number or f"INV-AUTO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        invoice_date=parsed_invoice_date,
        total_amount=parsed_total_amount,
        customer_name=customer_name or "N/A",
        customer_phone=customer_phone,
        created_updated_timestamp=parsed_client_timestamp,
        user_id=user.id,
        username=user.username
    )

    db.session.add(new_sale)
    db.session.commit()

    return jsonify({
        "code": 201,
        "message": "Sale entry created successfully.",
        "data": {
            "id": str(new_sale.id),
            "invoice_number": new_sale.invoice_number,
            "invoice_date": new_sale.invoice_date.strftime("%Y-%m-%d") if new_sale.invoice_date else None,
            "total_amount": str(new_sale.total_amount),
            "customer_name": new_sale.customer_name,
            "customer_phone": new_sale.customer_phone,
            "created_updated_timestamp": new_sale.created_updated_timestamp.strftime("%Y-%m-%d %H:%M:%S") if new_sale.created_updated_timestamp else None,
            "user_id": str(new_sale.user_id),
            "username": new_sale.username
        }
    }), 201


@sales_bp.route("/bulk", methods=["POST"])
@jwt_required()
def create_sales_bulk():
    """
    POST /api/v1/sales/bulk
    Requires Bearer Token authentication.
    Accepts up to 500 sales records per request.
    Validations commented out to accept whatever data comes.
    """
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)

    if not user or not user.is_active:
        return jsonify({
            "code": 401,
            "message": "User account is invalid or disabled.",
            "error": "Unauthorized"
        }), 401

    payload = request.get_json(silent=True) or {}
    sales_data = payload.get("sales")

    if sales_data is None or not isinstance(sales_data, list):
        return jsonify({
            "code": 400,
            "message": "'sales' field is required and must be a list.",
            "error": "Validation Error"
        }), 400

    if len(sales_data) == 0:
        return jsonify({
            "code": 400,
            "message": "The 'sales' list cannot be empty.",
            "error": "Validation Error"
        }), 400

    # Limit maximum batch size to 500 records
    if len(sales_data) > 500:
        return jsonify({
            "code": 400,
            "message": f"Bulk creation limit exceeded. Maximum 500 records allowed per request (received {len(sales_data)}).",
            "error": "Validation Error"
        }), 400

    validated_sales = []

    allowed_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]

    for idx, item in enumerate(sales_data):
        if not isinstance(item, dict):
            continue

        invoice_number = str(item.get("invoice_number", "")).strip() if item.get("invoice_number") else None
        invoice_date_str = str(item.get("invoice_date", "")).strip() if item.get("invoice_date") else None
        total_amount_raw = item.get("total_amount")
        customer_name = str(item.get("customer_name", "")).strip() if item.get("customer_name") else None
        customer_phone = str(item.get("customer_phone", "")).strip() if item.get("customer_phone") else None
        timestamp_str = str(item.get("created_updated_timestamp", "")).strip() if item.get("created_updated_timestamp") else None

        # --- VALIDATIONS COMMENTED OUT TO ACCEPT WHATEVER DATA COMES ---
        # # 1. Mandatory field checks
        # if not invoice_number:
        #     item_errors.append("invoice_number is required.")
        # if not invoice_date_str:
        #     item_errors.append("invoice_date is required.")
        # if total_amount_raw is None or total_amount_raw == "":
        #     item_errors.append("total_amount is required.")
        # if not customer_name:
        #     item_errors.append("customer_name is required.")
        # if not customer_phone:
        #     item_errors.append("customer_phone is required.")

        # # 2. Check mobile number format (must be 10 digits)
        # if customer_phone and not re.match(r"^\d{10}$", customer_phone):
        #     item_errors.append("customer_phone must be a valid 10-digit number.")

        # # 3. Duplicate checks
        # if invoice_number:
        #     if invoice_number in payload_invoices:
        #         item_errors.append(f"Duplicate invoice_number '{invoice_number}' within this request batch.")
        #     if invoice_number in existing_db_invoices:
        #         item_errors.append(f"Invoice number '{invoice_number}' already exists in database.")

        # Parse invoice date (fallback to today if invalid/missing)
        parsed_invoice_date = None
        if invoice_date_str:
            try:
                parsed_invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        if not parsed_invoice_date:
            parsed_invoice_date = datetime.now().date()

        # Parse total_amount (fallback to 0.00 if invalid/missing)
        parsed_total_amount = Decimal("0.00")
        if total_amount_raw is not None and total_amount_raw != "":
            try:
                parsed_total_amount = Decimal(str(total_amount_raw)).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError, ValueError):
                pass

        # Parse client timestamp
        parsed_client_timestamp = None
        if timestamp_str:
            for fmt in allowed_formats:
                try:
                    parsed_client_timestamp = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue

        validated_sales.append(Sale(
            invoice_number=invoice_number or f"INV-AUTO-{idx}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            invoice_date=parsed_invoice_date,
            total_amount=parsed_total_amount,
            customer_name=customer_name or "N/A",
            customer_phone=customer_phone,
            created_updated_timestamp=parsed_client_timestamp,
            user_id=user.id,
            username=user.username
        ))

    # Bulk save to database
    if validated_sales:
        db.session.add_all(validated_sales)
        db.session.commit()

    return jsonify({
        "code": 201,
        "message": f"Successfully created {len(validated_sales)} sales entries in bulk.",
        "data": {
            "created_count": len(validated_sales),
            "sales": [
                {
                    "id": str(sale.id),
                    "invoice_number": sale.invoice_number,
                    "invoice_date": sale.invoice_date.strftime("%Y-%m-%d") if sale.invoice_date else None,
                    "total_amount": str(sale.total_amount),
                    "customer_name": sale.customer_name,
                    "customer_phone": sale.customer_phone,
                    "created_updated_timestamp": sale.created_updated_timestamp.strftime("%Y-%m-%d %H:%M:%S") if sale.created_updated_timestamp else None,
                    "user_id": str(sale.user_id),
                    "username": sale.username
                }
                for sale in validated_sales
            ]
        }
    }), 201


