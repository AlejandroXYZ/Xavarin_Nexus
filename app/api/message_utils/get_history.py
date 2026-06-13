from app.schemas.message import Message
import logging
import json

logger = logging.getLogger(__name__)


async def obtener_historial_cliente(
    redis, db, message: Message, schema_name: str, redis_key: str
):
    """
    Obtiene el chat de conversacion completo del cliente para que la IA tenga memoria
    """

    logger.info(
        f"Obteniendo Historial del Cliente {message.user_name} de ID: {message.platform_user_id} de {message.platform}"
    )
    historial = await db.fetch(
        f"""
    SELECT content,ia_is_active,role FROM "{schema_name}".messages WHERE platform_user_id = $1 AND platform = $2 ORDER BY created_at DESC LIMIT 6;
    """,
        str(message.platform_user_id),
        message.platform,
    )

    channel_id = await db.fetchval(
        f"""SELECT channel_id FROM "{schema_name}".clients WHERE platform_user_id = $1 AND platform = $2""",
        str(message.platform_user_id),
        message.platform,
    )
    logger.info(f"channel_id query: {channel_id}")

    if not historial:
        logger.info("NO se encontró historial para este cliente")
        logger.info("Guardando mensaje en caché")
        await redis.set(
            redis_key,
            json.dumps([]),
            ex=86400,
        )
        return False

    extraccion_historial = [dict(fila) for fila in historial]
    resultado_final = {"historial": extraccion_historial, "channel_id": channel_id}

    logger.info("Guardando historial del cliente en Caché")
    await redis.set(redis_key, json.dumps(resultado_final, default=str), ex=86400)
    logger.info("Datos guardados perfectamente")
    return True
