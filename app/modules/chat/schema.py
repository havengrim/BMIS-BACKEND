from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
import uuid
from datetime import datetime

from app.validation.common_validators import validate_safe_text


class ChatMessageCreate(BaseModel):
    user_message: str

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, v: str) -> str:
        return validate_safe_text(v, field_label="Message", min_length=1, max_length=3000)


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    user_message: str
    bot_reply: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
