from typing import Optional, List
from pydantic import BaseModel, Field


class WhatsAppProfile(BaseModel):
    name: str


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppText(BaseModel):
    body: str


class WhatsAppMessageDetail(BaseModel):
    from_user: str = Field(
        ..., alias="from"
    )  # Usamos alias porque "from" es palabra reservada
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppText] = None


class WhatsAppValue(BaseModel):
    messaging_product: str
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessageDetail]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]
