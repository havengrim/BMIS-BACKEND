from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.validation.rbac_validators import (
    validate_non_empty_name,
    validate_permission_code,
    validate_slug,
)


class PermissionCreate(BaseModel):
    code: str
    module: str
    action: str
    name: str
    description: Optional[str] = None

    @field_validator('code')
    @classmethod
    def code_format(cls, v: str) -> str:
        return validate_permission_code(v)

    @field_validator('module', 'action')
    @classmethod
    def slug_format(cls, v: str) -> str:
        return validate_slug(
            v,
            error_message='Must be lowercase letters, numbers, or underscores only',
        )

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        return validate_non_empty_name(v)


class PermissionResponse(PermissionCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    # is_system is intentionally excluded — callers cannot set this

    @field_validator('code')
    @classmethod
    def code_slug(cls, v: str) -> str:
        return validate_slug(v, field_label='Role code')

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        return validate_non_empty_name(v)


class RoleResponse(RoleCreate):
    id: uuid.UUID
    is_system: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleDetailResponse(RoleResponse):
    permissions: list[PermissionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class RolePermissionAssignRequest(BaseModel):
    permission_id: uuid.UUID


class UserRoleAssignRequest(BaseModel):
    role_id: uuid.UUID


class UserRoleResponse(BaseModel):
    role: RoleResponse
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)
