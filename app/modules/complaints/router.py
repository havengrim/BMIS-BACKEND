from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from datetime import datetime

from app.db.session import get_db
from app.modules.complaints.model import Complaint
from app.modules.complaints.schema import ComplaintCreate, ComplaintUpdate, ComplaintResponse
from app.core.dependencies import get_current_user

router = APIRouter()


async def _generate_reference(db: AsyncSession) -> str:
    year = datetime.now().year
    result = await db.execute(select(func.count()).where(Complaint.reference_number.like(f"CMP-{year}-%")))
    count = result.scalar() or 0
    return f"CMP-{year}-{count + 1:04d}"


@router.get("/", response_model=list[ComplaintResponse])
async def list_complaints(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Complaint).order_by(Complaint.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def file_complaint(
    body: ComplaintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    complaint = Complaint(
        **body.model_dump(),
        user_id=uuid.UUID(current_user["sub"]),
        reference_number=await _generate_reference(db),
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)
    return complaint


@router.patch("/{id}", response_model=ComplaintResponse)
async def update_complaint(
    id: uuid.UUID,
    body: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Complaint).where(Complaint.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj
