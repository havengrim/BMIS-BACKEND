import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.system_logs.model import SystemLog
from app.modules.system_logs.schema import SystemLogResponse
from app.repositories.system_log_repository import system_log_repo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[SystemLogResponse])
async def list_system_logs(
    level: Optional[str] = Query(None, description="Filter by log level: DEBUG|INFO|WARNING|ERROR|CRITICAL"),
    action: Optional[str] = Query(None, description="Filter by action prefix (case-insensitive)"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user UUID"),
    from_dt: Optional[datetime] = Query(None, description="Start of date range (ISO-8601)"),
    to_dt: Optional[datetime] = Query(None, description="End of date range (ISO-8601)"),
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permissions("system_logs.read")),
):
    """Admin-only: Query persisted application logs stored in system_logs table."""
    logs = await system_log_repo.list_filtered(
        db,
        level=level,
        action=action,
        user_id=user_id,
        from_dt=from_dt,
        to_dt=to_dt,
        skip=page.skip,
        limit=page.limit,
    )
    logger.info(
        "SYSTEM_LOGS_LIST count=%d by user=%s",
        len(logs),
        current_user.get("sub"),
    )
    return logs


@router.get("/count")
async def count_system_logs(
    level: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    from_dt: Optional[datetime] = Query(None),
    to_dt: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permissions("system_logs.read")),
):
    """Return total count for a given filter — useful for pagination UI."""
    total = await system_log_repo.count_filtered(
        db,
        level=level,
        action=action,
        user_id=user_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    return {"total": total}
