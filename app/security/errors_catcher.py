from app.schemas.message import Message
import json
import logging
import time
from app.clients.odoo_jsonrpc import ejecutar_odoo
from app.services.message_utils.cache import get_cache_data

logger = logging.getLogger(__name__)


async def message_pending_try(message: Message, tenant_db: str, redis, arq):
    """Guarda mensaje en Redis como pending_try para que el worker reintente el procesamiento del mensaje"""
    llave_pending_try = f"pending_try:{message.platform}:{message.platform_user_id}"
    content = {"message": message.model_dump(), "tenant_db": tenant_db}
    logger.info("Guardando mensaje pending_try en redis")
    ventana_tiempo = int(time.time() // 10)
    job_id = f"lote_{tenant_db}_{ventana_tiempo}"
    try:
        await redis.set(llave_pending_try, json.dumps(content, default=str), ex=86400)
        logger.info("Enviando Mensaje al Worker para ser Procesado")
        await arq.enqueue_job(
            "procesar_pending_try",
            _job_id=job_id,
            _defer_by=60,
            llave=llave_pending_try,
        )
        logger.info("Mensaje Enviado al Worker")
    except Exception as e:
        logger.error(
            f"Ha ocurrido un error Guardando el mensaje llave_pending_try en Redis: {e}"
        )
        raise e


async def manual_handling(message: Message, tenant_db: str, db, odoo, redis):
    """Procesa los mensajes que necesitan intervención manual debido a un error no procesable"""

    logger.info(
        "Mensaje no se pudo procesar, Guardando en la db para que reciba intervención manual"
    )
    metadata_json = json.dumps({"requiere_atencion_manual": True})
    await db.execute(
        f"""
    INSERT INTO "{tenant_db}".messages (created_at,platform,platform_user_id,role,content,metadata) VALUES ($1,$2,$3,$4,$5,$6);
    """,
        message.created_at,
        message.platform,
        message.platform_user_id,
        message.role,
        message.content,
        metadata_json,
    )

    # Backend Dispara una notificación al dueño
    logger.info("Avisando al Dueño sobre el mensaje que no pudo ser procesado")

    llave = f"cache:{tenant_db}"
    logger.info(f"Obteniendo datos del Inquilino {tenant_db}")
    datos_redis = await redis.get(llave)
    if not datos_redis:
        logger.info(f"Generando caché con los datos del inquilino {tenant_db}")
        await get_cache_data(tenant=tenant_db, db=db, redis=redis, redis_key=llave)
        datos_redis = json.loads(await redis.get(llave))
    datos = json.loads(datos_redis)
    transcripcion_html = (
        f"<b>Alerta del Sistema IA</b><br/>"
        f"Error al procesar el mensaje. Este cliente necesita atención manual:<br/>"
        f"<b>Usuario:</b> {message.user_name} ({message.platform})<br/>"
        f"<b>Mensaje Original:</b> <i>{message.content}</i>"
    )
    channel_id_odoo = getattr(message, "channel_id", None)

    if not channel_id_odoo:
        logger.warning(
            f"No se encontró channel_id para {message.user_name}. Creando Canal de Emergencia en Odoo..."
        )

        try:
            respuesta_odoo = await ejecutar_odoo(
                http_client=odoo,
                odoo_url=datos["odoo_url"],
                db=tenant_db,
                uid=datos["odoo_bot_user"],
                api_key=datos["odoo_bot_api_key"],
                modelo="discuss.channel",
                metodo="create",
                args=[
                    {
                        "name": f"{message.platform.capitalize()} - {message.user_name} (Emergencia)",
                    }
                ],
            )

            if isinstance(respuesta_odoo, list) and len(respuesta_odoo) > 0:
                channel_id_odoo = respuesta_odoo[0]
            else:
                channel_id_odoo = respuesta_odoo
            logger.info(f"Canal creado con ID: {channel_id_odoo}")

        except Exception as e:
            logger.critical(
                f"Fallo total al intentar crear canal de emergencia en Odoo: {e}"
            )
            return

    await ejecutar_odoo(
        http_client=odoo,
        odoo_url=datos["odoo_url"],
        db=tenant_db,
        uid=datos["odoo_bot_user"],
        api_key=datos["odoo_bot_api_key"],
        modelo="discuss.channel",
        metodo="message_post",
        args=[channel_id_odoo],
        kwargs={
            "body": transcripcion_html,
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
            "body_is_html": True,
        },
    )

    logger.info(f"Se ha enviado el mensaje al dueño de {tenant_db} correctamente")
