import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatMessage
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository[ChatMessage]):
    def __init__(self) -> None:
        super().__init__(ChatMessage)

    async def list_by_sender(
        self, db: AsyncSession, sender_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> Sequence[ChatMessage]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[ChatMessage.sender_id == sender_id],
        )

    async def list_room(
        self, db: AsyncSession, room_id: str, *, skip: int = 0, limit: int = 100
    ) -> Sequence[ChatMessage]:
        return await self.list(
            db,
            skip=skip,
            limit=limit,
            filters=[ChatMessage.room_id == room_id],
        )


chat_repo = ChatRepository()
