"""Shared internal helpers used across auth services."""
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Security
from app.modules.auth.schema import TokenResponse
from app.modules.rbac.model import Role, UserRoleAssignment
from app.modules.users.model import User, UserRole, UserStatus

logger = logging.getLogger(__name__)


def make_tokens(user: User) -> TokenResponse:
    """Build a TokenResponse from a User object."""
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=Security.create_access_token(token_data),
        refresh_token=Security.create_refresh_token(token_data),
    )


async def get_user_or_404(db: AsyncSession, user_id: str) -> User:
    """Fetch a user by ID or raise 404."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def ensure_dynamic_role_assignment(db: AsyncSession, user: User, role_code: str) -> None:
    """Assign a dynamic RBAC role to a user if not already assigned."""
    if user.id is None:
        await db.flush()

    role = (await db.execute(select(Role).where(Role.code == role_code))).scalar_one_or_none()
    if role is None:
        return

    existing = (await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == role.id,
        )
    )).scalar_one_or_none()

    if existing is None:
        db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
