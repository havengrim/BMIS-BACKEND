from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import date, time
import uuid
from app.modules.blotter.model import BlotterStatus

from app.validation.common_validators import (
    validate_optional_safe_text,
    validate_phone_number,
    validate_safe_text,
)


class BlotterReportBase(BaseModel):
    complainant_name: str
    complainant_contact: Optional[str] = None
    complainant_email: Optional[str] = None
    complainant_address: Optional[str] = None
    respondent_name: Optional[str] = None
    respondent_address: Optional[str] = None
    incident_type: str
    incident_date: date
    incident_time: Optional[time] = None
    incident_location: Optional[str] = None
    narrative: Optional[str] = None

    @field_validator("complainant_name", "incident_type")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Field", min_length=1, max_length=255)

    @field_validator("complainant_contact")
    @classmethod
    def validate_complainant_contact(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)

    @field_validator("complainant_email", "complainant_address", "respondent_name", "respondent_address", "incident_location")
    @classmethod
    def validate_optional_fields(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Field", max_length=255)

    @field_validator("narrative")
    @classmethod
    def validate_narrative(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Narrative", max_length=5000)


class BlotterReportCreate(BlotterReportBase):
    pass


class BlotterReportUpdate(BaseModel):
    status: Optional[BlotterStatus] = None
    hearing_date: Optional[date] = None
    resolution_notes: Optional[str] = None

    @field_validator("resolution_notes")
    @classmethod
    def validate_resolution_notes(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Resolution notes", max_length=5000)


class BlotterReportResponse(BlotterReportBase):
    id: uuid.UUID
    report_number: str
    status: BlotterStatus
    hearing_date: Optional[date] = None
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
