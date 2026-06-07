from app.schemas.translators_schemas.telegram import TelegramUpdate
from app.schemas.message import Message


def telegram_translator(payload: dict):
    """Carga el Payload de Telegram al JSON BASE"""

    payload = TelegramUpdate(**payload)
    msg = payload.message
    user = msg.from_user if msg else None
    user_id = user.id if user else None
    username = user.username if user else None
    text_content = msg.text if msg else None
    created_at = msg.date if msg else None
    type = "text" if msg.text else None

    return Message(
        platform="telegram",
        platform_user_id=user_id,
        user_name=username,
        content=text_content,
        created_at=created_at,
        type=type,
    )
