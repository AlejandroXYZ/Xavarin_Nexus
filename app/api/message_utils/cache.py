from app.security.encrypter import desencriptar, preparar_tokens_para_db
from fastapi import HTTPException, status
import logging
import json

logger = logging.getLogger(__name__)


async def get_cache_data(tenant: str, db, redis, redis_key: str):
    """
    Genera el Caché para que el inquilino y así responder los mensajes rapidamente
    """
    try:
        logger.info("Obteniendo Datos del Inquilino")
        data = await db.fetchrow(
            """SELECT id,name,status,ai_system_prompt,features,metadata,partner_id 
        FROM tenants 
        WHERE schema_name = $1""",
            tenant,
        )
        if data is not None:
            data = dict(data)
        else:
            logger.error("Enlace no válido, DB de inquilino no existe")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enlace no válido o Expirado",
            )

        tenant_id = data["id"]
        logger.info("Verificando estatus del Inquilino ")
        if data["status"] == "suspendido":
            logger.info("Inquilino suspendido")
            return {"status": "suspended", "message": "tenant is suspended"}

        logger.info("Obteniendo Credenciales del Inquilino")

        credentials = dict(
            await db.fetchrow(
                "SELECT * FROM credentials WHERE tenant_id = $1", tenant_id
            )
        )
        logger.info("Desencriptando credenciales")
        logger.info(f"Credenciales obtenidas: {credentials}")
        credentials["odoo_url"] = desencriptar(credentials["odoo_url"])
        credentials["odoo_bot_api_key"] = desencriptar(credentials["odoo_bot_api_key"])
        credentials["tokens_platforms"] = preparar_tokens_para_db(
            json.loads(credentials["tokens_platforms"]), accion="desencriptar"
        )

        all_data = credentials | data

        await redis.set(redis_key, json.dumps(dict(all_data), default=str), ex=86400)
        logger.info(f"Datos del inquilino {tenant} Cargados en memoria correctamente")

    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se solicitaban los datos para procesar los mensajes: {e}"
        )
        raise e
