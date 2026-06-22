from typing import Optional
from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


class TelegramChat(BaseModel):
    id: int
    type: str  # puede ser "private", "group", "supergroup" o "channel"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    title: Optional[str] = None


class TelegramMessage(BaseModel):
    message_id: int
    from_user: Optional[TelegramUser] = Field(..., alias="from")
    chat: TelegramChat
    date: int
    text: Optional[str] = None  #


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None
