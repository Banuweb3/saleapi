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

    source_id_raw = data.get("source_id") if data.get("source_id") is not None else data.get("Source_id")
    invoice_number = str(data.get("invoice_number", "")).strip() if data.get("invoice_number") else None
    invoice_date_str = str(data.get("invoice_date", "")).strip() if data.get("invoice_date") else None
    total_amount_raw = data.get("total_amount")
    customer_name = str(data.get("customer_name", "")).strip() if data.get("customer_name") else None
    customer_phone = str(data.get("customer_phone", "")).strip() if data.get("customer_phone") else None
    timestamp_str = str(data.get("created_updated_timestamp", "")).strip() if data.get("created_updated_timestamp") else None

    # Parse and validate mandatory source_id
    if source_id_raw is None or str(source_id_raw).strip() == "":
        return jsonify({
            "code": 400,
            "message": "source_id is required.",
            "error": "Validation Error"
        }), 400

    try:
        parsed_source_id = int(source_id_raw)
    except (ValueError, TypeError):
        return jsonify({
            "code": 400,
            "message": "source_id must be a valid integer.",
            "error": "Validation Error"
        }), 400

    # Reject duplicates based on source_id
    existing_sale = Sale.query.filter_by(source_id=parsed_source_id).first()
    if existing_sale:
        return jsonify({
            "code": 409,
            "message": f"Sale with source_id '{parsed_source_id}' already exists.",
            "error": "Duplicate Entry",
            "data": {
                "existing_id": str(existing_sale.id),
                "source_id": existing_sale.source_id,
                "invoice_number": existing_sale.invoice_number
            }
        }), 409

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

    # 4. Use invoice_date string directly as provided by client (store whatever string comes)
    invoice_date_val = invoice_date_str

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
        source_id=parsed_source_id,
        invoice_number=invoice_number or f"INV-AUTO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        invoice_date=invoice_date_val,
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
            "source_id": new_sale.source_id,
            "invoice_number": new_sale.invoice_number,
            "invoice_date": new_sale.invoice_date,
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

    # 1. Pre-extract and validate mandatory source_ids
    valid_items_to_process = []
    skipped_items = []
    seen_batch_source_ids = set()

    for idx, item in enumerate(sales_data):
        if not isinstance(item, dict):
            return jsonify({
                "code": 400,
                "message": f"Item at index {idx} must be an object.",
                "error": "Validation Error"
            }), 400

        sid = item.get("source_id") if item.get("source_id") is not None else item.get("Source_id")
        if sid is None or str(sid).strip() == "":
            return jsonify({
                "code": 400,
                "message": f"source_id is required for item at index {idx}.",
                "error": "Validation Error"
            }), 400

        try:
            parsed_sid = int(sid)
        except (ValueError, TypeError):
            return jsonify({
                "code": 400,
                "message": f"source_id '{sid}' at index {idx} must be a valid integer.",
                "error": "Validation Error"
            }), 400

        # Check for duplicates within this request batch
        if parsed_sid in seen_batch_source_ids:
            skipped_items.append({
                "source_id": parsed_sid,
                "reason": "Duplicate source_id within current request batch."
            })
            continue

        seen_batch_source_ids.add(parsed_sid)
        valid_items_to_process.append((parsed_sid, item))

    # 2. Query database for existing source_ids in one batch
    candidate_sids = [sid for sid, _ in valid_items_to_process]
    existing_db_sids = set()
    if candidate_sids:
        existing_records = Sale.query.filter(Sale.source_id.in_(candidate_sids)).with_entities(Sale.source_id).all()
        existing_db_sids = {rec[0] for rec in existing_records}

    allowed_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]

    validated_sales = []

    for idx, (parsed_source_id, item) in enumerate(valid_items_to_process):
        # Skip if already exists in database
        if parsed_source_id in existing_db_sids:
            skipped_items.append({
                "source_id": parsed_source_id,
                "reason": f"Sale with source_id '{parsed_source_id}' already exists in database."
            })
            continue

        invoice_number = str(item.get("invoice_number", "")).strip() if item.get("invoice_number") else None
        invoice_date_str = str(item.get("invoice_date", "")).strip() if item.get("invoice_date") else None
        total_amount_raw = item.get("total_amount")
        customer_name = str(item.get("customer_name", "")).strip() if item.get("customer_name") else None
        customer_phone = str(item.get("customer_phone", "")).strip() if item.get("customer_phone") else None
        timestamp_str = str(item.get("created_updated_timestamp", "")).strip() if item.get("created_updated_timestamp") else None

        # Use invoice_date string directly as provided by client (store whatever string comes)
        invoice_date_val = invoice_date_str

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
            source_id=parsed_source_id,
            invoice_number=invoice_number or f"INV-AUTO-{idx}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            invoice_date=invoice_date_val,
            total_amount=parsed_total_amount,
            customer_name=customer_name or "N/A",
            customer_phone=customer_phone,
            created_updated_timestamp=parsed_client_timestamp,
            user_id=user.id,
            username=user.username
        ))

    # Bulk save non-duplicate sales to database
    if validated_sales:
        db.session.add_all(validated_sales)
        db.session.commit()

    return jsonify({
        "code": 201,
        "message": f"Processed bulk sales: {len(validated_sales)} created, {len(skipped_items)} skipped.",
        "data": {
            "created_count": len(validated_sales),
            "skipped_count": len(skipped_items),
            "skipped_items": skipped_items,
            "sales": [
                {
                    "id": str(sale.id),
                    "source_id": sale.source_id,
                    "invoice_number": sale.invoice_number,
                    "invoice_date": sale.invoice_date,
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


