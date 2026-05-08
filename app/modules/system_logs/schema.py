import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SystemLogResponse(BaseModel):
    id: uuid.UUID
    level: str
    logger: str
    action: Optional[str] = None
    message: str
    user_id: Optional[uuid.UUID] = None
    request_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
