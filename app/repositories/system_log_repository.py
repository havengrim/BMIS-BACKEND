import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system_logs.model import SystemLog
from app.repositories.base import BaseRepository


class SystemLogRepository(BaseRepository[SystemLog]):
    def __init__(self) -> None:
        super().__init__(SystemLog)

    async def list_filtered(
        self,
        db: AsyncSession,
        *,
        level: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[SystemLog]:
        filters = self._build_filters(level, action, user_id, ip_address, from_dt, to_dt)
        return await self.list(db, skip=skip, limit=limit, filters=filters or None)

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        level: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> int:
        filters = self._build_filters(level, action, user_id, ip_address, from_dt, to_dt)
        return await self.count(db, filters=filters or None)

    @staticmethod
    def _build_filters(
        level: Optional[str],
        action: Optional[str],
        user_id: Optional[uuid.UUID],
        ip_address: Optional[str],
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
    ) -> list:
        filters = []
        if level:
            filters.append(SystemLog.level == level.upper())
        if action:
            filters.append(SystemLog.action.ilike(f"{action}%"))
        if user_id:
            filters.append(SystemLog.user_id == user_id)
        if ip_address:
            filters.append(SystemLog.ip_address == ip_address)
        if from_dt:
            filters.append(SystemLog.created_at >= from_dt)
        if to_dt:
            filters.append(SystemLog.created_at <= to_dt)
        return filters


system_log_repo = SystemLogRepository()
