import logging
import json

logger = logging.getLogger(__name__)


async def get_cache_client(redis, redis_key: str, db, tenant_db: str, channel_id: int):
    """Obtiene los datos del cliente y los guarda en la llave de Redis"""

    logger.info("Obteniendo datos del cliente")
    client = await db.fetchrow(
        f"""
    SELECT * FROM "{tenant_db}".clients WHERE channel_id = $1;
    """,
        channel_id,
    )
    if not client:
        return False
    logger.info(f"datos del cliente {client['name']} obtenidos")
    logger.info("Guardando en Redis")
    await redis.set(redis_key, json.dumps(dict(client), default=str), ex=86400)
    logger.info("Datos Guardados")
