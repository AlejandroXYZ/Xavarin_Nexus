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
