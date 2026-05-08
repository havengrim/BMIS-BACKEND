from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.announcements.model import Announcement
from app.repositories.base import BaseRepository


class AnnouncementRepository(BaseRepository[Announcement]):
    def __init__(self) -> None:
        super().__init__(Announcement)

    async def list_published(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 50
    ) -> Sequence[Announcement]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[Announcement.status == "published"],
        )

    async def count_published(self, db: AsyncSession) -> int:
        return await self.count(db, filters=[Announcement.status == "published"])


announcement_repo = AnnouncementRepository()
