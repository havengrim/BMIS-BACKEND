from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.modules.chat.model import ChatMessage
from app.modules.chat.schema import ChatMessageCreate, ChatMessageResponse
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=list[ChatMessageResponse])
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user["sub"])
        .order_by(ChatMessage.timestamp.asc())
    )
    return result.scalars().all()


@router.post("/", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Placeholder bot reply — replace with AI integration later
    bot_reply = "Thank you for your message. A barangay staff will respond shortly."

    msg = ChatMessage(
        user_id=uuid.UUID(current_user["sub"]),
        user_message=body.user_message,
        bot_reply=bot_reply,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
