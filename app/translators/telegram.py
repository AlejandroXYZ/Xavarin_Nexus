from app.schemas.translators_schemas.telegram import TelegramUpdate
from app.schemas.message import Message
import os
import httpx


def telegram_translator(payload: dict):
    """Carga el Payload de Telegram al JSON BASE"""

    payload = TelegramUpdate(**payload)
    msg = payload.message
    user = msg.from_user if msg else None
    user_id = user.id if user else None
    username = user.username if user else None
    text_content = msg.text if msg else None
    created_at = msg.date if msg else None
    type = "message" if msg.text else None

    if user:
        username = user.username or user.first_name or "Cliente"
    else:
        username = "Cliente"

    return Message(
        platform="telegram",
        platform_user_id=user_id,
        user_name=username,
        content=text_content,
        created_at=created_at,
        type=type,
        role="user",
    )


async def send_message_telegram(destinatario: str, texto: str):
    """Traduce el texto al payload de Telegram y lo envía."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": destinatario, "text": texto}

    async with httpx.AsyncClient() as client:
        respuesta = await client.post(url, json=payload)
        respuesta.raise_for_status()
