from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.modules.business_permits.model import BusinessPermit
from app.modules.business_permits.schema import BusinessPermitCreate, BusinessPermitUpdate, BusinessPermitResponse
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=list[BusinessPermitResponse])
async def list_permits(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(BusinessPermit).order_by(BusinessPermit.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=BusinessPermitResponse, status_code=status.HTTP_201_CREATED)
async def apply_permit(
    body: BusinessPermitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    permit = BusinessPermit(**body.model_dump(), user_id=uuid.UUID(current_user["sub"]))
    db.add(permit)
    await db.commit()
    await db.refresh(permit)
    return permit


@router.patch("/{id}", response_model=BusinessPermitResponse)
async def update_permit(
    id: uuid.UUID,
    body: BusinessPermitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(BusinessPermit).where(BusinessPermit.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permit not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj
