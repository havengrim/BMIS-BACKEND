import enum
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from app.db.base import Base


class EmergencyType(str, enum.Enum):
    FIRE = "fire"
    FLOOD = "flood"
    MEDICAL = "medical"
    CRIME = "crime"
    EARTHQUAKE = "earthquake"
    ACCIDENT = "accident"
    OTHER = "other"


class EmergencyStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    RESPONDING = "responding"
    RESOLVED = "resolved"


class EmergencyReport(Base):
    __tablename__ = "emergency_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    contact_number = Column(String(20), nullable=True)
    incident_type = Column(SAEnum(EmergencyType), nullable=False)
    description = Column(Text, nullable=False)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    location_text = Column(String(255), nullable=False)
    media_file = Column(String(255), nullable=True)
    alert_message = Column(Text, nullable=True)
    status = Column(SAEnum(EmergencyStatus), nullable=False, default=EmergencyStatus.SUBMITTED)

    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    type = Column(SAEnum(EmergencyType), unique=True, nullable=False)
    alert_message = Column(Text, nullable=False)
    status = Column(SAEnum(EmergencyStatus), nullable=False, default=EmergencyStatus.ACKNOWLEDGED)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
