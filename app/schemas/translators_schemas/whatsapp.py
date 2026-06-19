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


# ==========================================
# NUEVO MODELO: Para manejar los acuses de recibo
# ==========================================
class WhatsAppStatus(BaseModel):
    id: str
    status: str  # Aquí vendrá "sent", "delivered" o "read"
    timestamp: str
    recipient_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessageDetail]] = None
    statuses: Optional[List[WhatsAppStatus]] = None  # <--- EL CAMPO FALTANTE AÑADIDO


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]
