import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.certificates.model import CertificateRequest
from app.repositories.base import BaseRepository


class CertificateRepository(BaseRepository[CertificateRequest]):
    def __init__(self) -> None:
        super().__init__(CertificateRequest)

    async def list_by_resident(
        self, db: AsyncSession, user_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> Sequence[CertificateRequest]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[CertificateRequest.resident_id == user_id],
        )

    async def list_by_status(
        self, db: AsyncSession, status: str, *, skip: int = 0, limit: int = 50
    ) -> Sequence[CertificateRequest]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[CertificateRequest.status == status],
        )

    async def count_by_status(self, db: AsyncSession, status: str) -> int:
        return await self.count(db, filters=[CertificateRequest.status == status])


certificate_repo = CertificateRepository()
