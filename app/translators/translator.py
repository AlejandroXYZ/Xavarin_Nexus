from app.translators.telegram import telegram_translator
from app.translators.whatsaap import whatsapp_translator
import logging

logger = logging.getLogger(__name__)

REGISTRO_TRADUCTORES = {
    "TELEGRAM": telegram_translator,
    "WHATSAPP": whatsapp_translator,
}


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
