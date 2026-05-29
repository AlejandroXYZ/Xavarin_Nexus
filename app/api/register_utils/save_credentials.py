from fastapi import HTTPException, status
from app.security.encrypter import encriptar
import logging

logger = logging.getLogger(__name__)


async def guardar_credenciales(
    db,
    tenant_id: int,
    odoo_url: str,
    odoo_bot_user_id: int,
    odoo_bot_api_key: str,
    tokens_platforms: dict | None = {},
):
    try:
        logger.info("Guardando credenciales")
        odoo_url = encriptar(odoo_url)
        odoo_bot_api_key = encriptar(odoo_bot_api_key)

        db.execute(
            """
            INSERT INTO 'credentials' (
                   tenant_id,
                   odoo_url,
                   odoo_db,
                   odoo_bot_user,
                   odoo_bot_api_key,
                   tokens_platforms) 
                   VALUES ($1,$2,$3,$4,$5);"
                   """,
            tenant_id,
            odoo_url,
            odoo_bot_user_id,
            odoo_bot_api_key,
            tokens_platforms,
        )
        logger.info("Credenciales guardadas correctamente")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar credenciales {e}",
        )
