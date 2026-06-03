from fastapi import HTTPException, status
from app.security.encrypter import encriptar, preparar_tokens_para_db
import logging

logger = logging.getLogger(__name__)


async def guardar_credenciales(
    db,
    tenant_id: int,
    odoo_url: str,
    odoo_db: str,
    odoo_bot_user_id: int,
    odoo_bot_api_key: str,
    tokens_platforms: dict[str, str] = {},
):
    try:
        logger.info("Guardando credenciales")
        odoo_url = encriptar(odoo_url)
        odoo_bot_api_key = encriptar(odoo_bot_api_key)
        tokens_platforms = preparar_tokens_para_db(tokens_platforms)

        await db.execute(
            """
            INSERT INTO credentials (
                   tenant_id,
                   odoo_url,
                   odoo_db,
                   odoo_bot_user,
                   odoo_bot_api_key,
                   tokens_platforms
            ) 
            VALUES ($1, $2, $3, $4, $5, $6);
            """,
            tenant_id,
            odoo_url,
            odoo_db,  # $3
            odoo_bot_user_id,  # $4
            odoo_bot_api_key,  # $5
            tokens_platforms,  # $6
        )
        logger.info("Credenciales guardadas correctamente")

    except Exception as e:
        logger.exception("Fallo crítico en la inserción de credenciales")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar credenciales: {e}",
        )
