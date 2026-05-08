from pydantic import BaseModel
from typing import Optional
import uuid
from app.modules.emergency.model import EmergencyType, EmergencyStatus


class EmergencyReportCreate(BaseModel):
    name: str
    contact_number: Optional[str] = None
    incident_type: EmergencyType
    description: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    location_text: str
    media_file: Optional[str] = None


class EmergencyReportResponse(EmergencyReportCreate):
    id: uuid.UUID
    status: EmergencyStatus
    alert_message: Optional[str] = None

    class Config:
        from_attributes = True


class EmergencyAlertCreate(BaseModel):
    type: EmergencyType
    alert_message: str


class EmergencyAlertResponse(EmergencyAlertCreate):
    id: uuid.UUID
    status: EmergencyStatus

    class Config:
        from_attributes = True
