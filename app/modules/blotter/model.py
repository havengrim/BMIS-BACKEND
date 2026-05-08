import enum
from sqlalchemy import Column, String, Text, Date, Time, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.db.base import Base


class BlotterStatus(str, enum.Enum):
    FILED = "filed"
    UNDER_INVESTIGATION = "under_investigation"
    MEDIATED = "mediated"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class BlotterReport(Base):
    __tablename__ = "blotter_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    report_number = Column(String(20), unique=True, nullable=False, index=True)
    filed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    complainant_name = Column(String(255), nullable=False)
    complainant_contact = Column(String(50), nullable=True)
    complainant_email = Column(String(254), nullable=True)
    complainant_address = Column(Text, nullable=True)

    respondent_name = Column(String(255), nullable=True)
    respondent_address = Column(Text, nullable=True)

    incident_type = Column(String(100), nullable=False)
    incident_date = Column(Date, nullable=False)
    incident_time = Column(Time, nullable=True)
    incident_location = Column(String(255), nullable=True)
    narrative = Column(Text, nullable=True)

    status = Column(SAEnum(BlotterStatus), nullable=False, default=BlotterStatus.FILED)
    hearing_date = Column(Date, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    filed_by = relationship("User", foreign_keys=[filed_by_id])
