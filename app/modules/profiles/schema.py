from pydantic import BaseModel
from typing import Optional
from datetime import date
import uuid


class ProfileBase(BaseModel):
    name: Optional[str] = None
    contact_number: Optional[str] = None
    house_num: Optional[str] = None
    address: Optional[str] = None
    civil_status: Optional[str] = None
    birthdate: Optional[date] = None
    image: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID

    class Config:
        from_attributes = True
