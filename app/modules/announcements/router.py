import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.announcements.model import Announcement
from app.modules.announcements.schema import AnnouncementCreate, AnnouncementResponse, AnnouncementUpdate
from app.repositories.announcement_repository import announcement_repo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[AnnouncementResponse])
async def list_announcements(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    announcements = await announcement_repo.list(db, skip=page.skip, limit=page.limit)
    logger.info("ANNOUNCEMENTS_LIST count=%d skip=%d limit=%d", len(announcements), page.skip, page.limit)
    return announcements


@router.post("/", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    body: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("announcements.manage")),
):
    obj = await announcement_repo.create(db, Announcement(**body.model_dump()))
    await db.commit()
    logger.info(
        "ANNOUNCEMENTS_CREATE id=%s title=%r status=%s by user=%s",
        obj.id, obj.title, obj.status, current_user.get("sub"),
    )
    return obj


@router.get("/{id}", response_model=AnnouncementResponse)
async def get_announcement(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await announcement_repo.get(db, id)
    if not obj:
        logger.warning("ANNOUNCEMENTS_GET_NOT_FOUND id=%s", id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    logger.info("ANNOUNCEMENTS_GET id=%s title=%r", obj.id, obj.title)
    return obj


@router.patch("/{id}", response_model=AnnouncementResponse)
async def update_announcement(
    id: uuid.UUID,
    body: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("announcements.manage")),
):
    obj = await announcement_repo.get(db, id)
    if not obj:
        logger.warning("ANNOUNCEMENTS_UPDATE_NOT_FOUND id=%s by user=%s", id, current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    data = body.model_dump(exclude_unset=True)
    obj = await announcement_repo.update(db, obj, data)
    await db.commit()
    logger.info(
        "ANNOUNCEMENTS_UPDATE id=%s fields=%s by user=%s",
        obj.id, list(data.keys()), current_user.get("sub"),
    )
    return obj


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("announcements.manage")),
):
    obj = await announcement_repo.get(db, id)
    if not obj:
        logger.warning("ANNOUNCEMENTS_DELETE_NOT_FOUND id=%s by user=%s", id, current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    title = obj.title
    await announcement_repo.delete(db, obj)
    await db.commit()
    logger.info("ANNOUNCEMENTS_DELETE id=%s title=%r by user=%s", id, title, current_user.get("sub"))

