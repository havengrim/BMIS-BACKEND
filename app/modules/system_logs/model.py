import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SystemLog(Base):
    """Persisted application log record written by AsyncDBHandler."""

    __tablename__ = "system_logs"
    __table_args__ = (
        Index("ix_system_logs_level", "level"),
        Index("ix_system_logs_action", "action"),
        Index("ix_system_logs_user_id", "user_id"),
        Index("ix_system_logs_ip_address", "ip_address"),
        Index("ix_system_logs_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(20), nullable=False)
    logger = Column(String(200), nullable=False)
    action = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    request_id = Column(String(100), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
