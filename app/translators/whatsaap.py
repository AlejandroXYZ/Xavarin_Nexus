import os
import httpx
from app.schemas.translators_schemas.whatsapp import WhatsAppPayload
from app.schemas.message import Message


def whatsapp_translator(payload: dict) -> Message:
    """Carga el Payload de WhatsApp Cloud API al JSON BASE"""

    whatsapp_data = WhatsAppPayload(**payload)

    if not whatsapp_data.entry or not whatsapp_data.entry[0].changes:
        raise ValueError("Payload de WhatsApp incompleto o inválido")

    value = whatsapp_data.entry[0].changes[0].value

    messages = value.messages
    contacts = value.contacts

    msg = messages[0] if messages else None
    contact = contacts[0] if contacts else None

    user_id = msg.from_user if msg else None
    username = contact.profile.name if contact and contact.profile else None
    text_content = msg.text.body if msg and msg.text else None

    created_at = int(msg.timestamp) if msg and msg.timestamp else None
    msg_type = "message" if text_content else None

    return Message(
        platform="whatsapp",
        platform_user_id=user_id,
        user_name=username,
        content=text_content,
        created_at=created_at,
        type=msg_type,
        role="user",
    )


async def send_message_whatsapp(destinatario: str, texto: str):
    """Traduce el texto al payload de WhatsApp y lo envía a través de Meta API."""

    # Extraemos las variables de entorno de Meta
    token = os.getenv("META_BEARER_TOKEN")
    phone_id = os.getenv("META_PHONE_ID")

    # URL oficial de la Cloud API de WhatsApp (puedes ajustar la versión v18.0 si usas otra)
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "messaging_product": "whatsapp",
        # WhatsApp exige el número con código de país, pero SIN el símbolo '+'
        # (ej. 584141234567). Usualmente, 'destinatario' ya viene así desde el webhook de entrada.
        "to": destinatario.replace("+", ""),
        "type": "text",
        "text": {"body": texto},
    }

    async with httpx.AsyncClient() as client:
        respuesta = await client.post(url, headers=headers, json=payload)
        respuesta.raise_for_status()  # Lanza error si Meta rechaza el envío
