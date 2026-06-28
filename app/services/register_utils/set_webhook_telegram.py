from httpx import AsyncClient, HTTPStatusError, RequestError
import os
import logging

logger = logging.getLogger(__name__)


async def set_webhook_telegram_bot(tenant_db: str, token_telegram: str):
    """Configura el Bot de Telegram para que redirija el tráfico al endpoint de mensajes"""

    secret_token = os.getenv("API_KEY_HEADERS", "x-api-key")
    domain_name = os.getenv("DOMAIN_NAME", "mi_api.com")

    endpoint = f"https://api-nexus.{domain_name}/api/v1/message/{tenant_db}/telegram"
    telegram_url = f"https://api.telegram.org/bot{token_telegram}/setWebhook"

    params = {"url": endpoint, "secret_token": secret_token}

    async with AsyncClient() as client:
        try:
            response = await client.post(url=telegram_url, params=params)

            data = response.json()
            if not data.get("ok"):
                raise ValueError(
                    data.get("description", "Error desconocido de Telegram")
                )

            logger.info(f"Webhook de Telegram configurado con éxito: {response.text}")
            return {"status": "success", "info": "Webhook configurado correctamente"}

        except (HTTPStatusError, RequestError, ValueError) as err:
            logger.error(f"Error al configurar webhook de Telegram: {err}")
            logger.info("Requires configurar el webhook del bot manualmente")
            return {
                "status": "error",
                "info": f"No se pudo configurar el webhook de Telegram: {err}",
            }
