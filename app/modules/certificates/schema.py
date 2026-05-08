from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
from app.modules.certificates.model import CertificateType, RequestStatus


class CertificateRequestCreate(BaseModel):
    certificate_type: CertificateType
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    complete_address: str
    house_num: Optional[str] = None
    contact_number: str
    email_address: EmailStr
    purpose: str
    business_name: Optional[str] = None
    agree_terms: bool


class CertificateRequestUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    remarks: Optional[str] = None


class CertificateRequestResponse(CertificateRequestCreate):
    id: uuid.UUID
    request_number: str
    status: RequestStatus
    remarks: Optional[str] = None

    class Config:
        from_attributes = True
