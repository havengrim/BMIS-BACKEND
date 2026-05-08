import enum
from sqlalchemy import Column, String, Text, Date, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from app.db.base import Base


class AnnouncementStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TargetAudience(str, enum.Enum):
    ALL = "all"
    RESIDENTS = "residents"
    SENIORS = "seniors"
    YOUTH = "youth"
    BUSINESSES = "businesses"


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(AnnouncementStatus), nullable=False, default=AnnouncementStatus.DRAFT)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    location = Column(String(255), nullable=True)
    target_audience = Column(SAEnum(TargetAudience), nullable=False, default=TargetAudience.ALL)
    image = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
