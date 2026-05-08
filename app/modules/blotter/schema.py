from pydantic import BaseModel
from typing import Optional
from datetime import date, time
import uuid
from app.modules.blotter.model import BlotterStatus


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


class BlotterReportCreate(BlotterReportBase):
    pass


class BlotterReportUpdate(BaseModel):
    status: Optional[BlotterStatus] = None
    hearing_date: Optional[date] = None
    resolution_notes: Optional[str] = None


class BlotterReportResponse(BlotterReportBase):
    id: uuid.UUID
    report_number: str
    status: BlotterStatus
    hearing_date: Optional[date] = None
    resolution_notes: Optional[str] = None

    class Config:
        from_attributes = True
