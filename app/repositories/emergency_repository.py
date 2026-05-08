import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.emergency.model import EmergencyAlert, EmergencyReport
from app.repositories.base import BaseRepository


class EmergencyReportRepository(BaseRepository[EmergencyReport]):
    def __init__(self) -> None:
        super().__init__(EmergencyReport)

    async def list_by_reporter(
        self, db: AsyncSession, user_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> Sequence[EmergencyReport]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[EmergencyReport.reporter_id == user_id],
        )

    async def list_by_status(
        self, db: AsyncSession, status: str, *, skip: int = 0, limit: int = 50
    ) -> Sequence[EmergencyReport]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[EmergencyReport.status == status],
        )


class EmergencyAlertRepository(BaseRepository[EmergencyAlert]):
    def __init__(self) -> None:
        super().__init__(EmergencyAlert)

    async def list_active(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 50
    ) -> Sequence[EmergencyAlert]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[EmergencyAlert.is_active == True],  # noqa: E712
        )


emergency_report_repo = EmergencyReportRepository()
emergency_alert_repo = EmergencyAlertRepository()
