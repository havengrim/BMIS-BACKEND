import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_permissions
from app.db.session import get_db
from app.modules.profiles.schema import ProfileCreate, ProfileResponse, ProfileUpdate
from app.repositories.profile_repository import profile_repo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("profiles.read")),
):
    profile = await profile_repo.get_by_user_id(db, uuid.UUID(current_user["sub"]))
    if not profile:
        logger.warning("PROFILES_GET_NOT_FOUND user_id=%s", current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    logger.info("PROFILES_GET user_id=%s profile_id=%s", current_user.get("sub"), profile.id)
    return profile


@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    body: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("profiles.manage")),
):
    from app.modules.profiles.model import Profile
    profile = await profile_repo.create(db, Profile(
        user_id=uuid.UUID(current_user["sub"]), **body.model_dump()
    ))
    await db.commit()
    logger.info("PROFILES_CREATE profile_id=%s user_id=%s", profile.id, current_user.get("sub"))
    return profile


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("profiles.manage")),
):
    profile = await profile_repo.get_by_user_id(db, uuid.UUID(current_user["sub"]))
    if not profile:
        logger.warning("PROFILES_UPDATE_NOT_FOUND user_id=%s", current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    data = body.model_dump(exclude_unset=True)
    profile = await profile_repo.update(db, profile, data)
    await db.commit()
    logger.info(
        "PROFILES_UPDATE profile_id=%s fields=%s user_id=%s",
        profile.id, list(data.keys()), current_user.get("sub"),
    )
    return profile

