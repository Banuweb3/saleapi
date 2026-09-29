from flask import jsonify
from extensions import db
from models import User

def setup_jwt_callbacks(jwt):
    """
    Registers custom response handlers and single-active-session
    blocklist loader with JWTManager using standardized API responses.
    """

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        user_id = jwt_payload.get("sub")
        
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            return True  # Revoke if user doesn't exist or is disabled
        
        # Token is revoked if its JTI does not match the user's latest active_jti
        return user.active_jti != jti

    @jwt.revoked_token_loader
    def revoked_token_response(jwt_header, jwt_payload):
        return jsonify({
            "code": 401,
            "message": "This token has been revoked because a newer login occurred or the account was disabled.",
            "error": "Token Revoked"
        }), 401

    @jwt.unauthorized_loader
    def missing_token_response(error):
        return jsonify({
            "code": 401,
            "message": "Missing Authorization header with Bearer token.",
            "error": "Authorization Required"
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_response(error):
        return jsonify({
            "code": 401,
            "message": "The provided token is invalid or malformed.",
            "error": "Invalid Token"
        }), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        return jsonify({
            "code": 401,
            "message": "The token has expired. Please log in again to obtain a new token.",
            "error": "Token Expired"
        }), 401
