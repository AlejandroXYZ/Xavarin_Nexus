from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Union


class IA_answer(BaseModel):
    product: str
    intent: str
    text: Optional[Union[str, bool]] = None
    answer: Optional[str] = None


class Message(BaseModel):
    platform: str
    platform_user_id: str | int
    user_name: str
    content: str
    created_at: datetime
    type: Optional[str]
