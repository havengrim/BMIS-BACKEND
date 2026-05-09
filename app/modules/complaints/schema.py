from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import date
import uuid
from app.modules.complaints.model import ComplaintType, ComplaintStatus, ComplaintPriority


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


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    priority: Optional[ComplaintPriority] = None
    resolution_notes: Optional[str] = None


class ComplaintResponse(ComplaintCreate):
    id: uuid.UUID
    reference_number: str
    status: ComplaintStatus
    priority: ComplaintPriority
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
