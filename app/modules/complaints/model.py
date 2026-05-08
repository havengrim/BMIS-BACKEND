import enum
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.db.base import Base


class ComplaintStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ComplaintPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ComplaintType(str, enum.Enum):
    NOISE = "noise"
    GARBAGE = "garbage"
    PROPERTY = "property"
    PUBLIC_DISTURBANCE = "public_disturbance"
    ILLEGAL_STRUCTURE = "illegal_structure"
    OTHER = "other"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reference_number = Column(String(50), unique=True, nullable=False, index=True)

    fullname = Column(String(150), nullable=False)
    contact_number = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    email_address = Column(String(254), nullable=False)

    type = Column(SAEnum(ComplaintType), nullable=False)
    subject = Column(String(200), nullable=False)
    detailed_description = Column(Text, nullable=False)
    evidence = Column(String(255), nullable=True)

    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)

    respondent_name = Column(String(150), nullable=True)
    respondent_address = Column(Text, nullable=True)

    date_filed = Column(Date, nullable=False)
    status = Column(SAEnum(ComplaintStatus), nullable=False, default=ComplaintStatus.PENDING)
    priority = Column(SAEnum(ComplaintPriority), nullable=False, default=ComplaintPriority.MEDIUM)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    filed_by = relationship("User", foreign_keys=[user_id])
