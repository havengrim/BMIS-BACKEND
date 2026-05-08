import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profiles.model import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self) -> None:
        super().__init__(Profile)

    async def get_by_user_id(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Optional[Profile]:
        result = await db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()


profile_repo = ProfileRepository()
