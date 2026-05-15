from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
from app.modules.users.model import UserRole, UserStatus
import uuid

from app.validation.common_validators import (
    validate_optional_safe_text,
    validate_password_input,
    validate_phone_number,
    validate_safe_text,
    validate_username,
)


class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    role: UserRole = UserRole.RESIDENT

    @field_validator("username")
    @classmethod
    def validate_user_username(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Name", min_length=1, max_length=100)

    @field_validator("middle_name")
    @classmethod
    def validate_user_middle_name(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Middle name", max_length=100)

    @field_validator("contact_number")
    @classmethod
    def validate_user_contact(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)

    @field_validator("address")
    @classmethod
    def validate_user_address(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Address", max_length=255)


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_user_password(cls, v: str) -> str:
        return validate_password_input(v)


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_update_names(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_safe_text(v, field_label="Name", min_length=1, max_length=100)

    @field_validator("middle_name")
    @classmethod
    def validate_update_middle_name(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Middle name", max_length=100)

    @field_validator("contact_number")
    @classmethod
    def validate_update_contact(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)

    @field_validator("address")
    @classmethod
    def validate_update_address(cls, v: Optional[str]) -> Optional[str]:
        return validate_optional_safe_text(v, field_label="Address", max_length=255)


class UserResponse(UserBase):
    id: uuid.UUID
    status: UserStatus
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)
