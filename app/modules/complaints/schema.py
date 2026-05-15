from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
from datetime import date
import uuid
from app.modules.complaints.model import ComplaintType, ComplaintStatus, ComplaintPriority

from app.validation.common_validators import (
    validate_optional_safe_text,
    validate_phone_number,
    validate_safe_text,
)


class ComplaintCreate(BaseModel):
    fullname: str
    contact_number: str
    address: str
    email_address: EmailStr
    type: ComplaintType
    subject: str
    detailed_description: str
    respondent_name: Optional[str] = None
    respondent_address: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    evidence: Optional[str] = None
    date_filed: date

    @field_validator("fullname", "address", "subject")
    @classmethod
    def validate_required_text_fields(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Field", min_length=1, max_length=255)

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, v: str) -> str:
        return validate_phone_number(v) or ""

    @field_validator("detailed_description")
    @classmethod
    def validate_detailed_description(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Detailed description", min_length=1, max_length=5000)

    @field_validator("respondent_name", "respondent_address", "latitude", "longitude", "evidence")
    @classmethod
    def validate_optional_fields(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Field", max_length=255)


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    priority: Optional[ComplaintPriority] = None
    resolution_notes: Optional[str] = None

    @field_validator("resolution_notes")
    @classmethod
    def validate_resolution_notes(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Resolution notes", max_length=5000)


class ComplaintResponse(ComplaintCreate):
    id: uuid.UUID
    reference_number: str
    status: ComplaintStatus
    priority: ComplaintPriority
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
