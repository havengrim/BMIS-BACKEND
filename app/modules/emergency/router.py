import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.emergency.model import EmergencyAlert, EmergencyReport
from app.modules.emergency.schema import (
    EmergencyAlertCreate,
    EmergencyAlertResponse,
    EmergencyReportCreate,
    EmergencyReportResponse,
)
from app.repositories.emergency_repository import emergency_alert_repo, emergency_report_repo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/reports", response_model=list[EmergencyReportResponse])
async def list_reports(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("emergency.read")),
):
    reports = await emergency_report_repo.list(db, skip=page.skip, limit=page.limit)
    logger.info("EMERGENCY_REPORTS_LIST count=%d skip=%d by user=%s", len(reports), page.skip, current_user.get("sub"))
    return reports


@router.post("/reports", response_model=EmergencyReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(body: EmergencyReportCreate, db: AsyncSession = Depends(get_db)):
    """Public endpoint — no auth required for emergency reports."""
    report = await emergency_report_repo.create(db, EmergencyReport(**body.model_dump()))
    await db.commit()
    logger.warning(
        "EMERGENCY_REPORT_SUBMITTED id=%s incident_type=%s location=%r name=%r",
        report.id, report.incident_type, report.location_text, report.name,
    )
    return report


@router.get("/alerts", response_model=list[EmergencyAlertResponse])
async def list_alerts(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    alerts = await emergency_alert_repo.list(db, skip=page.skip, limit=page.limit)
    logger.info("EMERGENCY_ALERTS_LIST count=%d", len(alerts))
    return alerts


@router.post("/alerts", response_model=EmergencyAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: EmergencyAlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("emergency.manage")),
):
    alert = await emergency_alert_repo.create(db, EmergencyAlert(**body.model_dump()))
    await db.commit()
    logger.warning(
        "EMERGENCY_ALERT_CREATED id=%s type=%s status=%s by user=%s",
        alert.id, alert.type, alert.status, current_user.get("sub"),
    )
    return alert

