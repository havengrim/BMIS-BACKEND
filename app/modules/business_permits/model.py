import enum
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.db.base import Base


class PermitStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BusinessPermit(Base):
    __tablename__ = "business_permits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    permit_number = Column(String(20), unique=True, nullable=True)

    business_name = Column(String(255), nullable=False)
    business_type = Column(String(100), nullable=False)
    business_description = Column(Text, nullable=True)
    business_address = Column(Text, nullable=False)

    owner_name = Column(String(255), nullable=False)
    owner_address = Column(Text, nullable=False)
    house_num = Column(String(20), nullable=True)
    contact_number = Column(String(20), nullable=False)

    is_renewal = Column(Boolean, default=False, nullable=False)
    status = Column(SAEnum(PermitStatus), nullable=False, default=PermitStatus.PENDING)
    remarks = Column(Text, nullable=True)
    expiry_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    applicant = relationship("User", foreign_keys=[user_id])
