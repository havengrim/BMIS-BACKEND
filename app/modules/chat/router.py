import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import Pagination, get_current_user, require_permissions
from app.db.session import get_db
from app.modules.chat.model import ChatMessage
from app.modules.chat.schema import ChatMessageCreate, ChatMessageResponse
from app.repositories.chat_repository import chat_repo

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[ChatMessageResponse])
async def get_history(
    page: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("chat.read")),
):
    messages = await chat_repo.list_by_sender(
        db, uuid.UUID(current_user["sub"]), skip=page.skip, limit=page.limit
    )
    logger.info("CHAT_HISTORY_GET count=%d user_id=%s", len(messages), current_user.get("sub"))
    return messages


@router.post("/", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_permissions("chat.manage")),
):
    # Placeholder bot reply — replace with AI integration later
    bot_reply = "Thank you for your message. A barangay staff will respond shortly."

    msg = await chat_repo.create(db, ChatMessage(
        user_id=uuid.UUID(current_user["sub"]),
        user_message=body.user_message,
        bot_reply=bot_reply,
    ))
    await db.commit()
    logger.info("CHAT_MESSAGE_SENT id=%s user_id=%s", msg.id, current_user.get("sub"))
    return msg

