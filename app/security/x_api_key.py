import os
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException, status
import logging

logger = logging.getLogger(__name__)

api_key_headers = os.getenv("API_KEY_HEADERS", "api")
x_api_key = APIKeyHeader(name="X-Telegram-Bot-Api-Secret-Token", auto_error=False)


async def verificar_api(api_recibida: str = Security(x_api_key)):

    if not api_recibida:
        logger.warning("Intento de acceso sin el header de Telegram.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de seguridad.",
        )

    if api_recibida == api_key_headers:
        return api_recibida

    logger.warning(f"Intento de acceso con token inválido: {api_recibida}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
    )
