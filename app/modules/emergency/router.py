from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.modules.emergency.model import EmergencyReport, EmergencyAlert
from app.modules.emergency.schema import EmergencyReportCreate, EmergencyReportResponse, EmergencyAlertCreate, EmergencyAlertResponse
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/reports", response_model=list[EmergencyReportResponse])
async def list_reports(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(EmergencyReport).order_by(EmergencyReport.submitted_at.desc()))
    return result.scalars().all()


@router.post("/reports", response_model=EmergencyReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(body: EmergencyReportCreate, db: AsyncSession = Depends(get_db)):
    report = EmergencyReport(**body.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/alerts", response_model=list[EmergencyAlertResponse])
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmergencyAlert))
    return result.scalars().all()


@router.post("/alerts", response_model=EmergencyAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: EmergencyAlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    alert = EmergencyAlert(**body.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert
