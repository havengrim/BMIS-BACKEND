import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum as SAEnum,
    Integer, Text
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"       # System-wide admin
    BARANGAY_ADMIN = "barangay_admin" # Manages one barangay
    STAFF = "staff"                   # Barangay staff / encoder
    RESIDENT = "resident"             # Regular barangay resident


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Personal info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    contact_number = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)

    # Barangay context
    barangay_id = Column(Integer, nullable=True, index=True)  # FK to Barangay table later

    # Auth
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.RESIDENT)
    status = Column(SAEnum(UserStatus), nullable=False, default=UserStatus.PENDING)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
