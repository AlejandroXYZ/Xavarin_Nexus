import os
import httpx
from app.schemas.translators_schemas.whatsapp import WhatsAppPayload
from app.schemas.message import Message
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def whatsapp_translator(payload: dict) -> Optional[Message]:
    """Carga el Payload de WhatsApp Cloud API al JSON BASE"""

    whatsapp_data = WhatsAppPayload(**payload)

    if not whatsapp_data.entry or not whatsapp_data.entry[0].changes:
        logger.warning("Payload de WhatsApp con estructura desconocida.")
        return None

    value = whatsapp_data.entry[0].changes[0].value
    messages = value.messages
    if not messages:
        statuses = value.statuses
        if statuses:
            estado = statuses[0].status
            logger.info(
                f"Aviso de Meta recibido: Mensaje {estado}. Ignorando silenciosamente."
            )
        return None  # Salida elegante

    contacts = value.contacts

    msg = messages[0]
    contact = contacts[0] if contacts else None

    user_id = msg.from_user
    username = contact.profile.name if contact and contact.profile else "Usuario"

    tipo_mensaje = getattr(msg, "type", "text")

    if tipo_mensaje == "text" and getattr(msg, "text", None):
        text_content = msg.text.body
    else:
        text_content = "multimedia"

    created_at = int(msg.timestamp) if msg.timestamp else None

    return Message(
        platform="whatsapp",
        platform_user_id=user_id,
        user_name=username,
        content=text_content,
        created_at=created_at,
        type="message",
        role="user",
    )


async def send_message_whatsapp(
    destinatario: str, texto: str, token: str, phone_id=None
):
    """Traduce el texto al payload de WhatsApp y lo envía a través de Meta API."""

    phone_id = os.getenv("META_PHONE_ID")
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "messaging_product": "whatsapp",
        "to": destinatario.replace("+", ""),
        "type": "text",
        "text": {"body": texto},
    }

    async with httpx.AsyncClient() as client:
        respuesta = await client.post(url, headers=headers, json=payload)
        respuesta.raise_for_status()
