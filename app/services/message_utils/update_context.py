from app.schemas.message import Message
import logging
import json

logger = logging.getLogger(__name__)


async def save_messages_db(
    mensajes: list[Message],
    db,
    redis,
    schema_name: str,
    key_redis: str,
    channel_id: int | None,
):
    """Guarda una lista de mensajes entrantes en la tabla messages y actualiza ttl de redis"""
    logger.info(
        f"Guardando mensaje de usuario: {mensajes[0].user_name} de ID: {mensajes[0].platform_user_id} de {mensajes[0].platform}"
    )
    query = f"""
    INSERT INTO "{schema_name}".messages (created_at,platform,platform_user_id,role,content,ia_is_active,metadata) VALUES ($1,$2,$3,$4,$5,$6,$7);
    """

    for msg in mensajes:
        await db.execute(
            query,
            msg.created_at,
            msg.platform,
            str(msg.platform_user_id),
            msg.role,
            msg.content,
            msg.ia_is_active,
            json.dumps(getattr(msg, "metadata", {})),
        )
    historial_cache = await redis.get(key_redis)

    if historial_cache:
        historial_lista = json.loads(historial_cache)
        for msg in mensajes:
            historial_lista.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                    "ia_is_active": getattr(msg, "ia_is_active", True),
                }
            )
        historial_lista = historial_lista[-6:]
        if channel_id:
            historial_lista.append({"channel_id": channel_id})
        await redis.set(key_redis, json.dumps(historial_lista), ex=86400)
        logger.info(
            f"Caché actualizado exitosamente. Memoria actual: {len(historial_lista)} mensajes."
        )
        return {
            "message": f"Guardado mensaje de usuario: {mensajes[0].user_name} de ID: {mensajes[0].platform_user_id} de {mensajes[0].platform}"
        }
