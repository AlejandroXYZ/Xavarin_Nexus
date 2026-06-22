from app.translators.telegram import telegram_translator, send_message_telegram
from app.translators.whatsaap import whatsapp_translator, send_message_whatsapp
import logging

logger = logging.getLogger(__name__)

REGISTRO_TRADUCTORES = {
    "TELEGRAM": telegram_translator,
    "WHATSAPP": whatsapp_translator,
}

REGISTRO_SALIDA = {"TELEGRAM": send_message_telegram, "WHATSAPP": send_message_whatsapp}


class Translator:
    @classmethod
    def traducir(cls, plataforma: str, payload: dict):
        """Busca la plataforma y ejecuta su función."""

        plataforma_upper = plataforma.upper()
        traductor_func = REGISTRO_TRADUCTORES.get(plataforma_upper)

        if not traductor_func:
            logger.error(f"Plataforma no soportada pasada: {plataforma}")
            raise ValueError(f"La plataforma {plataforma} no está soportada.")
        return traductor_func(payload)

    @classmethod
    async def enviar(cls, plataforma: str, destinatario: str, texto: str):
        """Busca la plataforma y ejecuta su función de envío (SALIDA)."""
        plataforma_upper = plataforma.upper()
        enviar_func = REGISTRO_SALIDA.get(plataforma_upper)

        if not enviar_func:
            logger.error(f"Plataforma de salida no soportada: {plataforma}")
            raise ValueError(
                f"La plataforma {plataforma} no está soportada para envío."
            )

        logger.info(f"Enviando mensaje vía {plataforma_upper} a {destinatario}")
        await enviar_func(destinatario, texto)
