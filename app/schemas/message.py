from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Union, Any
from enum import Enum


class Roles(str, Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    OWNER = "owner"


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
    role: Roles
    ia_is_active: bool = Field(default=True)
    metadata: Optional[str] = Field(default="{}")
