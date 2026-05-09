import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.blotter.model import BlotterReport
from app.modules.blotter.schema import BlotterReportCreate, BlotterReportResponse, BlotterReportUpdate
from app.repositories.blotter_repository import blotter_repo

router = APIRouter()
logger = logging.getLogger(__name__)


async def _generate_report_number(db: AsyncSession) -> str:
    year = datetime.now().year
    result = await db.execute(
        select(func.count()).select_from(BlotterReport).where(
            BlotterReport.report_number.like(f"BLT-{year}-%")
        )
    )
    count = result.scalar() or 0
    return f"BLT-{year}-{count + 1:04d}"


@router.get("/", response_model=list[BlotterReportResponse])
async def list_reports(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("blotter.read")),
):
    reports = await blotter_repo.list(db, skip=page.skip, limit=page.limit)
    logger.info("BLOTTER_LIST count=%d skip=%d by user=%s", len(reports), page.skip, current_user.get("sub"))
    return reports


@router.post("/", response_model=BlotterReportResponse, status_code=status.HTTP_201_CREATED)
async def file_report(
    body: BlotterReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("blotter.manage")),
):
    report = await blotter_repo.create(db, BlotterReport(
        **body.model_dump(),
        report_number=await _generate_report_number(db),
        filed_by_id=uuid.UUID(current_user["sub"]),
    ))
    await db.commit()
    logger.info(
        "BLOTTER_CREATE id=%s report_number=%s complainant=%r incident_type=%s by user=%s",
        report.id, report.report_number, report.complainant_name,
        report.incident_type, current_user.get("sub"),
    )
    return report


@router.get("/{id}", response_model=BlotterReportResponse)
async def get_report(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("blotter.read")),
):
    obj = await blotter_repo.get(db, id)
    if not obj:
        logger.warning("BLOTTER_GET_NOT_FOUND id=%s by user=%s", id, current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    logger.info("BLOTTER_GET id=%s report_number=%s by user=%s", obj.id, obj.report_number, current_user.get("sub"))
    return obj


@router.patch("/{id}", response_model=BlotterReportResponse)
async def update_report(
    id: uuid.UUID,
    body: BlotterReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("blotter.manage")),
):
    obj = await blotter_repo.get(db, id)
    if not obj:
        logger.warning("BLOTTER_UPDATE_NOT_FOUND id=%s by user=%s", id, current_user.get("sub"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    data = body.model_dump(exclude_unset=True)
    obj = await blotter_repo.update(db, obj, data)
    await db.commit()
    logger.info(
        "BLOTTER_UPDATE id=%s report_number=%s fields=%s status=%s by user=%s",
        obj.id, obj.report_number, list(data.keys()), obj.status, current_user.get("sub"),
    )
    return obj

