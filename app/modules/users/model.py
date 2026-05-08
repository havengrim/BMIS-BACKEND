import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.db.base import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    BARANGAY_ADMIN = "barangay_admin"
    STAFF = "staff"
    RESIDENT = "resident"


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
    hashed_password = Column(String(255), nullable=True)  # nullable for OAuth users

    # SSO / OAuth
    oauth_provider = Column(String(50), nullable=True)      # "email" | "google"
    oauth_provider_id = Column(String(255), nullable=True, unique=True, index=True)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    contact_number = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    barangay_id = Column(Integer, nullable=True, index=True)

    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.RESIDENT)
    status = Column(SAEnum(UserStatus), nullable=False, default=UserStatus.PENDING)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    profile = relationship("Profile", back_populates="user", uselist=False)
    role_assignments = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
