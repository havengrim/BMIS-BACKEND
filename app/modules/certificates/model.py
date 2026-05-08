import enum
from sqlalchemy import Column, String, Integer, Text, Date, DateTime, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.db.base import Base


class CertificateType(str, enum.Enum):
    BARANGAY_CLEARANCE = "barangay_clearance"
    INDIGENCY = "indigency"
    RESIDENCY = "residency"
    BUSINESS_CLEARANCE = "business_clearance"
    GOOD_MORAL = "good_moral"


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    RELEASED = "released"
    REJECTED = "rejected"


class CertificateRequest(Base):
    __tablename__ = "certificate_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_number = Column(String(20), unique=True, nullable=False, index=True)
    certificate_type = Column(SAEnum(CertificateType), nullable=False)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    complete_address = Column(Text, nullable=False)
    house_num = Column(String(20), nullable=True)
    contact_number = Column(String(20), nullable=False)
    email_address = Column(String(254), nullable=False)
    purpose = Column(Text, nullable=False)
    business_name = Column(String(255), nullable=True)
    agree_terms = Column(Boolean, default=False, nullable=False)

    status = Column(SAEnum(RequestStatus), nullable=False, default=RequestStatus.PENDING)
    remarks = Column(Text, nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    requester = relationship("User", foreign_keys=[user_id])


class CertificateCounter(Base):
    __tablename__ = "certificate_counters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_type = Column(SAEnum(CertificateType), unique=True, nullable=False)
    last_number = Column(Integer, default=0, nullable=False)
    year = Column(Integer, nullable=False)
