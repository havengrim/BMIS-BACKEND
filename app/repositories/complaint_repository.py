import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.complaints.model import Complaint
from app.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository[Complaint]):
    def __init__(self) -> None:
        super().__init__(Complaint)

    async def list_by_complainant(
        self, db: AsyncSession, user_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> Sequence[Complaint]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[Complaint.complainant_id == user_id],
        )

    async def list_by_status(
        self, db: AsyncSession, status: str, *, skip: int = 0, limit: int = 50
    ) -> Sequence[Complaint]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[Complaint.status == status],
        )

    async def count_by_status(self, db: AsyncSession, status: str) -> int:
        return await self.count(db, filters=[Complaint.status == status])


complaint_repo = ComplaintRepository()
