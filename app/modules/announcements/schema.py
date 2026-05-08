from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date
import uuid
from app.modules.announcements.model import AnnouncementStatus, TargetAudience


class AnnouncementBase(BaseModel):
    title: str
    description: str
    status: AnnouncementStatus = AnnouncementStatus.DRAFT
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    target_audience: TargetAudience = TargetAudience.ALL
    image: Optional[str] = None


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(AnnouncementBase):
    title: Optional[str] = None
    description: Optional[str] = None


class AnnouncementResponse(AnnouncementBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
