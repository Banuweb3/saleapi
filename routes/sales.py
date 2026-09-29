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

    invoice_number = str(data.get("invoice_number", "")).strip()
    invoice_date_str = str(data.get("invoice_date", "")).strip()
    total_amount_raw = data.get("total_amount")
    customer_name = str(data.get("customer_name", "")).strip()
    customer_phone = str(data.get("customer_phone", "")).strip()
    timestamp_str = str(data.get("created_updated_timestamp", "")).strip()

    # 1. Validate required fields presence
    if not invoice_number:
        return jsonify({
            "code": 400,
            "message": "invoice_number is required.",
            "error": "Validation Error"
        }), 400

    if not invoice_date_str:
        return jsonify({
            "code": 400,
            "message": "invoice_date is required.",
            "error": "Validation Error"
        }), 400

    if total_amount_raw is None or total_amount_raw == "":
        return jsonify({
            "code": 400,
            "message": "total_amount is required.",
            "error": "Validation Error"
        }), 400

    if not customer_name:
        return jsonify({
            "code": 400,
            "message": "customer_name is required.",
            "error": "Validation Error"
        }), 400

    # 2. Check for duplicate invoice number
    existing_sale = Sale.query.filter_by(invoice_number=invoice_number).first()
    if existing_sale:
        return jsonify({
            "code": 409,
            "message": f"Invoice number '{invoice_number}' already exists.",
            "error": "Duplicate Entry"
        }), 409

    # 3. Validate customer phone number format (must be 10 digits)
    if customer_phone:
        if not re.match(r"^\d{10}$", customer_phone):
            return jsonify({
                "code": 400,
                "message": "customer_phone must be a valid 10-digit number.",
                "error": "Validation Error"
            }), 400
    else:
        customer_phone = None

    # 4. Validate invoice date format (YYYY-MM-DD)
    try:
        parsed_invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "code": 400,
            "message": "invoice_date must be in YYYY-MM-DD format.",
            "error": "Validation Error"
        }), 400

    # 5. Validate total_amount format (decimal floating point)
    try:
        total_amount = Decimal(str(total_amount_raw)).quantize(Decimal("0.01"))
        if total_amount <= Decimal("0"):
            return jsonify({
                "code": 400,
                "message": "total_amount must be greater than zero.",
                "error": "Validation Error"
            }), 400
    except (InvalidOperation, TypeError, ValueError):
        return jsonify({
            "code": 400,
            "message": "total_amount must be a valid numeric decimal value.",
            "error": "Validation Error"
        }), 400

    # 6. Validate client timestamp format (YYYY-MM-DD HH:MM:SS or ISO YYYY-MM-DDTHH:MM:SS)
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

        if not parsed_client_timestamp:
            return jsonify({
                "code": 400,
                "message": "created_updated_timestamp must be in a valid format (e.g. 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DDTHH:MM:SS').",
                "error": "Validation Error"
            }), 400

    # Create new Sale record
    new_sale = Sale(
        invoice_number=invoice_number,
        invoice_date=parsed_invoice_date,
        total_amount=total_amount,
        customer_name=customer_name,
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
            "invoice_date": new_sale.invoice_date.strftime("%Y-%m-%d"),
            "total_amount": str(new_sale.total_amount),
            "customer_name": new_sale.customer_name,
            "customer_phone": new_sale.customer_phone,
            "created_updated_timestamp": new_sale.created_updated_timestamp.strftime("%Y-%m-%d %H:%M:%S") if new_sale.created_updated_timestamp else None,
            "user_id": str(new_sale.user_id),
            "username": new_sale.username,
            "created_at": new_sale.created_at.isoformat(),
            "updated_at": new_sale.updated_at.isoformat()
        }
    }), 201
