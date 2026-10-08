import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    active_jti = db.Column(db.String(36), nullable=True)  # Stores current single active JWT ID (UUID)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def set_password(self, plaintext_password: str) -> None:
        """Hashes and stores the user's password."""
        self.password = generate_password_hash(plaintext_password)

    def check_password(self, plaintext_password: str) -> bool:
        """Verifies plaintext password against stored password hash."""
        return check_password_hash(self.password, plaintext_password)

    def __repr__(self):
        return f"<User {self.username}>"


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = db.Column(db.String(50), nullable=False, index=True)
    invoice_date = db.Column(db.String(100), nullable=True)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=True)

    # Client-supplied timestamp sent via API
    created_updated_timestamp = db.Column(db.DateTime, nullable=True)

    # Store User ID and Username
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False)

    # System-generated timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return f"<Sale {self.invoice_number} - {self.total_amount}>"
