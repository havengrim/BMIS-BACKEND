from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.model import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_oauth_id(self, db: AsyncSession, provider_id: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.oauth_provider_id == provider_id)
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 50
    ) -> Sequence[User]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[User.deleted_at.is_(None)],
        )

    async def count_active(self, db: AsyncSession) -> int:
        return await self.count(db, filters=[User.deleted_at.is_(None)])


user_repo = UserRepository()
