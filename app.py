from flask import Flask, jsonify
from config import Config
from extensions import db, migrate, jwt
from jwt_callbacks import setup_jwt_callbacks
from middleware import setup_request_logger
from routes import auth_bp, sales_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    setup_jwt_callbacks(jwt)

    # Initialize Production Request Logging Middleware
    setup_request_logger(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(sales_bp)

    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "code": 200,
            "message": "SaleAPI service is operational.",
            "data": {
                "status": "up"
            }
        }), 200

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
