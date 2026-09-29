from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, get_jti, jwt_required, get_jwt_identity
from extensions import db
from models import User
from middleware.rate_limiter import auth_limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

@auth_bp.route("/token", methods=["POST"])
def generate_auth_token():
    """
    Industrial standard token generation endpoint.
    POST /api/v1/auth/token
    Body: {"username": "...", "password": "..."}

    Rate Limited: Maximum 4 authentication attempts per hour per username/IP.
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.remote_addr or "127.0.0.1"

    # Identify rate limit bucket key by username or IP address
    rate_limit_key = f"{username.lower()}:{client_ip}" if username else client_ip

    # 1. Check rate limit BEFORE processing authentication
    if auth_limiter.is_rate_limited(rate_limit_key):
        return jsonify({
            "code": 429,
            "message": "Maximum authentication attempts exceeded (4 attempts allowed per hour). Please try again later.",
            "error": "Rate Limit Exceeded"
        }), 429

    # Record the authentication attempt
    auth_limiter.record_attempt(rate_limit_key)

    if not username or not password:
        return jsonify({
            "code": 400,
            "message": "Username and password are required.",
            "error": "Validation Error"
        }), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({
            "code": 401,
            "message": "Invalid username or password.",
            "error": "Unauthorized"
        }), 401

    if not user.is_active:
        return jsonify({
            "code": 403,
            "message": "User account is disabled. Please contact administrator.",
            "error": "Forbidden"
        }), 403

    # Generate new JWT access token
    access_token = create_access_token(identity=str(user.id))

    # Single active session policy: update user's active_jti
    new_jti = get_jti(access_token)
    user.active_jti = new_jti
    db.session.commit()

    expires_hours = current_app.config.get("JWT_EXPIRES_HOURS", 12)

    return jsonify({
        "code": 200,
        "message": "Authentication token generated successfully.",
        "data": {
            "token_type": "Bearer",
            "access_token": access_token,
            "expires_in_hours": expires_hours,
            "user": {
                "id": str(user.id),
                "username": user.username
            }
        }
    }), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user_profile():
    """
    Protected user profile verification endpoint.
    GET /api/v1/auth/me
    """
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({
            "code": 404,
            "message": "User not found.",
            "error": "Not Found"
        }), 404

    return jsonify({
        "code": 200,
        "message": "User profile retrieved successfully.",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
    }), 200
