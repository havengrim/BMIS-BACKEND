from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import date
import uuid
from app.modules.announcements.model import AnnouncementStatus, TargetAudience

from app.validation.common_validators import validate_optional_safe_text, validate_safe_text


class AnnouncementBase(BaseModel):
    title: str
    description: str
    status: AnnouncementStatus = AnnouncementStatus.DRAFT
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    target_audience: TargetAudience = TargetAudience.ALL
    image: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Title", min_length=1, max_length=160)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Description", min_length=1, max_length=5000)

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Location", max_length=255)

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Image", max_length=500)


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(AnnouncementBase):
    title: Optional[str] = None
    description: Optional[str] = None


class AnnouncementResponse(AnnouncementBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
