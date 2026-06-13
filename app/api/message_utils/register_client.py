import logging
from app.schemas.message import Message

logger = logging.getLogger(__name__)


async def register_client_db(
    db, mensaje: Message, schema_name: str, status: str, channel_id: int
):
    """Guarda cliente en la DB"""

    logger.info(f"Guardando cliente {mensaje.user_name} en la tabla Clientes")
    try:
        await db.execute(
            f"""
        INSERT INTO "{schema_name}".clients (name,platform,platform_user_id,status,channel_id)
        VALUES ($1,$2,$3,$4,$5) 
        ON CONFLICT (platform,platform_user_id)
        DO NOTHING;""",
            mensaje.user_name,
            mensaje.platform,
            str(mensaje.platform_user_id),
            status,
            channel_id,
        )
        logger.info("Cliente {mensaje.user_name} registrado")

    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se registraba al cliente en la db: {e}"
        )
        raise e
