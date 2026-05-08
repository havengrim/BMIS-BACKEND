from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from app.modules.users.model import UserRole, UserStatus
import uuid


class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    role: UserRole = UserRole.RESIDENT


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None


class UserResponse(UserBase):
    id: uuid.UUID
    status: UserStatus
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)
