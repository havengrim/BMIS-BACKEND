import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.business_permits.model import BusinessPermit
from app.repositories.base import BaseRepository


class BusinessPermitRepository(BaseRepository[BusinessPermit]):
    def __init__(self) -> None:
        super().__init__(BusinessPermit)

    async def list_by_owner(
        self, db: AsyncSession, owner_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> Sequence[BusinessPermit]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[BusinessPermit.owner_id == owner_id],
        )

    async def list_by_status(
        self, db: AsyncSession, status: str, *, skip: int = 0, limit: int = 50
    ) -> Sequence[BusinessPermit]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[BusinessPermit.status == status],
        )

    async def count_by_status(self, db: AsyncSession, status: str) -> int:
        return await self.count(db, filters=[BusinessPermit.status == status])


business_permit_repo = BusinessPermitRepository()
