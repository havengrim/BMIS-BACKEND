from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid
from datetime import datetime


class ChatMessageCreate(BaseModel):
    user_message: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    user_message: str
    bot_reply: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
