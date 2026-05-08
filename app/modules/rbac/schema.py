import re
from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

_CODE_RE = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+$')
_SLUG_RE = re.compile(r'^[a-z0-9_]+$')


class PermissionCreate(BaseModel):
    code: str
    module: str
    action: str
    name: str
    description: Optional[str] = None

    @field_validator('code')
    @classmethod
    def code_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not _CODE_RE.match(v):
            raise ValueError('Permission code must be lowercase module.action format (e.g. users.read)')
        return v

    @field_validator('module', 'action')
    @classmethod
    def slug_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError('Must be lowercase letters, numbers, or underscores only')
        return v

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('name must not be empty')
        return v


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
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError('Role code must be lowercase letters, numbers, or underscores only')
        return v

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('name must not be empty')
        return v


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
