from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date
import uuid
from app.modules.business_permits.model import PermitStatus


class BusinessPermitCreate(BaseModel):
    business_name: str
    business_type: str
    business_description: Optional[str] = None
    business_address: str
    owner_name: str
    owner_address: str
    house_num: Optional[str] = None
    contact_number: str
    is_renewal: bool = False


class BusinessPermitUpdate(BaseModel):
    status: Optional[PermitStatus] = None
    remarks: Optional[str] = None
    expiry_date: Optional[date] = None


class BusinessPermitResponse(BusinessPermitCreate):
    id: uuid.UUID
    permit_number: Optional[str] = None
    status: PermitStatus
    remarks: Optional[str] = None
    expiry_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)
