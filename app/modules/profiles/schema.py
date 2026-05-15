from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import date
import uuid

from app.validation.common_validators import validate_optional_safe_text, validate_phone_number


class ProfileBase(BaseModel):
    name: Optional[str] = None
    contact_number: Optional[str] = None
    house_num: Optional[str] = None
    address: Optional[str] = None
    civil_status: Optional[str] = None
    birthdate: Optional[date] = None
    image: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_profile_name(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Name", max_length=120)

    @field_validator("contact_number")
    @classmethod
    def validate_profile_contact(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)

    @field_validator("house_num")
    @classmethod
    def validate_house_num(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="House number", max_length=32)

    @field_validator("address")
    @classmethod
    def validate_profile_address(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Address", max_length=255)

    @field_validator("civil_status")
    @classmethod
    def validate_civil_status(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Civil status", max_length=50)

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Image", max_length=500)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
