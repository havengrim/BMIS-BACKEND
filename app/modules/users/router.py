import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.users.schema import UserResponse
from app.repositories.user_repository import user_repo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[UserResponse])
async def list_users(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permissions("users.read")),
):
    users = await user_repo.list_active(db, skip=page.skip, limit=page.limit)
    logger.info("USERS_LIST count=%d skip=%d by user=%s", len(users), page.skip, current_user.get("sub"))
    return users


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await user_repo.get(db, current_user["sub"])
    if not user:
        logger.warning("USERS_GET_ME_NOT_FOUND sub=%s", current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info("USERS_GET_ME user_id=%s email=%s", user.id, user.email)
    return user
