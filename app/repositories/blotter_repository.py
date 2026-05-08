import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blotter.model import BlotterReport
from app.repositories.base import BaseRepository


class BlotterRepository(BaseRepository[BlotterReport]):
    def __init__(self) -> None:
        super().__init__(BlotterReport)

    async def list_by_complainant(
        self, db: AsyncSession, user_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> Sequence[BlotterReport]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[BlotterReport.complainant_id == user_id],
        )

    async def list_by_status(
        self, db: AsyncSession, status: str, *, skip: int = 0, limit: int = 50
    ) -> Sequence[BlotterReport]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[BlotterReport.status == status],
        )

    async def count_by_status(self, db: AsyncSession, status: str) -> int:
        return await self.count(db, filters=[BlotterReport.status == status])


blotter_repo = BlotterRepository()
