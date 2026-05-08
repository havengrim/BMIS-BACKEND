from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.modules.announcements.model import Announcement
from app.modules.announcements.schema import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=list[AnnouncementResponse])
async def list_announcements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Announcement).order_by(Announcement.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    body: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    announcement = Announcement(**body.model_dump())
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return announcement


@router.get("/{id}", response_model=AnnouncementResponse)
async def get_announcement(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Announcement).where(Announcement.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return obj


@router.patch("/{id}", response_model=AnnouncementResponse)
async def update_announcement(
    id: uuid.UUID,
    body: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Announcement).where(Announcement.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Announcement).where(Announcement.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    await db.delete(obj)
    await db.commit()
