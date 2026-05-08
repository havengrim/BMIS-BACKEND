from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from datetime import datetime

from app.db.session import get_db
from app.modules.blotter.model import BlotterReport
from app.modules.blotter.schema import BlotterReportCreate, BlotterReportUpdate, BlotterReportResponse
from app.core.dependencies import get_current_user

router = APIRouter()


async def _generate_report_number(db: AsyncSession) -> str:
    year = datetime.now().year
    result = await db.execute(
        select(func.count()).where(
            BlotterReport.report_number.like(f"BLT-{year}-%")
        )
    )
    count = result.scalar() or 0
    return f"BLT-{year}-{count + 1:04d}"


@router.get("/", response_model=list[BlotterReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(BlotterReport).order_by(BlotterReport.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=BlotterReportResponse, status_code=status.HTTP_201_CREATED)
async def file_report(
    body: BlotterReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    report = BlotterReport(
        **body.model_dump(),
        report_number=await _generate_report_number(db),
        filed_by_id=uuid.UUID(current_user["sub"]),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/{id}", response_model=BlotterReportResponse)
async def get_report(id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(BlotterReport).where(BlotterReport.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return obj


@router.patch("/{id}", response_model=BlotterReportResponse)
async def update_report(
    id: uuid.UUID,
    body: BlotterReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(BlotterReport).where(BlotterReport.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj
