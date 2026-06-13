from fastapi import APIRouter, Request, status, Depends, HTTPException, BackgroundTasks
from app.security.x_api_key import verificar_api
import logging
from app.ia.groq_IA import groq
from app.schemas.message import IA_answer, Message, OdooMessageWebhook
from app.ia.product_embedding import product_embedding
from app.api.message_utils.cache import get_cache_data
from app.translators.translator import Translator
from app.api.message_utils.get_history import obtener_historial_cliente
from app.api.message_utils.update_context import save_messages_db
import json
from datetime import datetime
from app.clients.odoo_jsonrpc import ejecutar_odoo
from app.api.message_utils.register_client import register_client_db
from app.api.message_utils.cache_client import get_cache_client
from app.api.message_utils.html_format import format_html
import os

message_router = APIRouter(prefix="/api/v1/message/{tenant_db}", tags=["message"])


logger = logging.getLogger(__name__)


@message_router.post(
    "/webhook",
    status_code=status.HTTP_202_ACCEPTED,
)
async def response_to_client(
    tenant_db: str, payload: OdooMessageWebhook, request: Request, token: str
):
    """Recibe Mensaje de Odoo, lo procesa y responde al cliente"""
    logger.info(f"webhook recibido para el tenant: {tenant_db}")
    logger.info(f"payload recibido: {payload}")
    true_token = os.getenv("FASTAPI_WEBHOOK_SECRET", "1234")
    if token != true_token:
        logger.error("Token no válido")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token no válido"
        )
    db = request.app.state.db
    redis = request.app.state.redis
    if payload.model != "discuss.channel":
        return {"status": "ignored", "reason": "Modelo no soportado"}

    llave_sesion = f"client:{tenant_db}:{payload.res_id}"

    datos_redis = await redis.get(llave_sesion)

    if not datos_redis:
        await get_cache_client(
            redis_key=llave_sesion,
            db=db,
            tenant_db=tenant_db,
            channel_id=payload.res_id,
            redis=redis,
        )
        datos_redis = await redis.get(llave_sesion)
    if not datos_redis:
        return {"status": "ignored", "reason": "Cliente no encontrado en caché"}
    client = json.loads(datos_redis)
    if not client:
        logger.error("Error, no se pudo obtener los datos del cliente")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener datos",
        )
    elif "Resumen de la IA:" in payload.body or "BOT IA:" in payload.body:
        return {"status": "ignored", "reason": "Eco del bot bloqueado"}

    try:
        logger.info(f"Mensaje: {payload.body}")
        logger.info(f"Enviando Mensaje a {client['name']} de {client['platform']}")
        await Translator.enviar(
            plataforma=client["platform"],
            destinatario=client["platform_user_id"],
            texto=payload.body,
        )
        logger.info("Mensaje Enviado Correctamente")

        return {"status": "sucess"}
    except Exception as e:
        logger.error(f"Ha Ocurrido un error enviando el mensaje al cliente {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ha ocurrido un error enviando el mensaje",
        )


@message_router.post(
    "/{platform}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verificar_api)],
)
async def message_handler(
    message: dict,
    tenant_db: str,
    request: Request,
    platform: str,
    background_tasks: BackgroundTasks,
):
    """Endpoint encargado de toda la lógica de procesamiento del mensaje y respuesta"""
    db = request.app.state.db
    redis = request.app.state.redis
    odoo = request.app.state.http_client
    llave = f"cache:{tenant_db}"
    datos_redis = await redis.get(llave)
    if not datos_redis:
        logger.info(f"Generando caché con los datos del inquilino {tenant_db}")
        await get_cache_data(tenant=tenant_db, db=db, redis=redis, redis_key=llave)
        datos_redis = json.loads(await redis.get(llave))
    datos = json.loads(datos_redis)
    logger.info(datos)
    if platform not in datos["tokens_platforms"]:
        logger.info(
            "Plataforma no válida, inquilino no tiene esa plataforma disponible"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Enlace no válido"
        )
    prompt = datos["ai_system_prompt"]
    message = Translator.traducir(plataforma=platform.strip(), payload=message)

    if message.type == "message":
        llave_historial_cliente = (
            f"history:client:{platform}:{message.platform_user_id}"
        )
        if not await redis.exists(llave_historial_cliente):
            await obtener_historial_cliente(
                message=message,
                db=db,
                redis=redis,
                schema_name=tenant_db,
                redis_key=llave_historial_cliente,
            )
        logger.info("Obteniendo datos desde caché")
        historial_cache = await redis.get(llave_historial_cliente)
        logger.info(f"historial_cache: {historial_cache}")
        if not historial_cache:
            logger.error("Los datos de caché del cliente están vacíos")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno",
            )
        historial = json.loads(historial_cache)
        ia_is_active = True
        if len(historial) > 0:
            ia_is_active = historial[0].get("ia_is_active", True)

        if not ia_is_active and historial[-1].get("channel_id", False):
            logger.info("IA desactivada, mensaje directo al dueño")
            channel_id = historial[-1].get("channel_id", False)
            await ejecutar_odoo(
                http_client=odoo,
                odoo_url=datos["odoo_url"],
                db=tenant_db,
                uid=datos["odoo_bot_user"],
                api_key=datos["odoo_bot_api_key"],
                modelo="discuss.channel",
                metodo="message_post",
                args=[channel_id],
                kwargs={
                    "body": message.content,
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_comment",
                    "body_is_html": True,
                },
            )
            return {"status": "success", "info": "Mensaje enviado a humano, IA pausada"}

        logger.info(f"Contenido de historial: {historial}")
        historial_limpio = []
        if len(historial) > 0:
            historial_reciente = historial[-10:]
            historial_limpio = [
                {"role": fila["role"], "content": fila["content"]}
                for fila in historial_reciente
                if "role" in fila and "content" in fila
            ]
        historial_limpio.append({"role": "user", "content": message.content})
        historial_limpio.insert(0, {"role": "system", "content": prompt})
        channel_id = None

        try:
            if prompt == "" or not prompt:
                logger.error("No se pudo obtener el system prompt del inquilino")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ha ocurrido un error interno",
                )

            logger.info(
                f"===================={historial_limpio}========================"
            )
            response = await groq(historial_limpio)
            logger.info(f"respuesta de IA {response}")
            validacion = IA_answer.model_validate(response)
            response_to_message = Message(
                platform=message.platform,
                platform_user_id=message.platform_user_id,
                user_name=message.user_name,
                content=validacion.model_dump_json(),
                created_at=datetime.now(),
                type="message",
                role="assistant",
                ia_is_active=True,
                metadata="{}",
            )

            match validacion.intent:
                case "catalog":
                    result = "catalog"

                case "answered":
                    respuesta = f"Respondido al Usuario {message.user_name}-ID:{message.platform_user_id} de {message.platform}: {validacion.text}"
                    logger.info(respuesta)
                    result = {
                        "status": "sucess",
                        "intent": "answered",
                        "data": respuesta,
                    }

                case "ask":
                    respuesta = await product_embedding(
                        db, validacion.product, message.content, tenant_db
                    )
                    result = {"status": "sucess", "intent": "ask", "data": respuesta}

                case "buy" | "another":
                    channel_id = historial[-1].get("channel_id") if historial else None
                    if not channel_id:
                        logger.info("Creando Canal de Venta en Odoo")
                        channel_id = await ejecutar_odoo(
                            http_client=odoo,
                            odoo_url=datos["odoo_url"],
                            db=tenant_db,
                            uid=datos["odoo_bot_user"],
                            api_key=datos["odoo_bot_api_key"],
                            modelo="discuss.channel",
                            metodo="create",
                            args=[
                                {
                                    "name": f"{message.platform}: {message.user_name}{message.platform_user_id}",
                                    "channel_type": "group",
                                    "channel_member_ids": [
                                        (0, 0, {"partner_id": datos["partner_id"]})
                                    ],
                                }
                            ],
                        )
                    else:
                        logger.info(f"Reutilizando canal existente: {channel_id}")

                    message.ia_is_active = False

                    status_client = (
                        "waiting_for_support"
                        if validacion.intent == "another"
                        else "waiting_for_sale"
                    )
                    background_tasks.add_task(
                        register_client_db,
                        db=db,
                        mensaje=message,
                        schema_name=tenant_db,
                        status=status_client,
                        channel_id=channel_id,
                    )

                    transcripcion_html = format_html(historial_limpio, validacion.text)
                    logger.info("Inyectando conversacion")
                    background_tasks.add_task(
                        ejecutar_odoo,
                        http_client=odoo,
                        odoo_url=datos["odoo_url"],
                        db=tenant_db,
                        uid=datos["odoo_bot_user"],
                        api_key=datos["odoo_bot_api_key"],
                        modelo="discuss.channel",
                        metodo="message_post",
                        args=[channel_id],
                        kwargs={
                            "body": transcripcion_html,
                            "message_type": "comment",
                            "subtype_xmlid": "mail.mt_comment",
                            "body_is_html": True,
                        },
                    )
                    logger.info("conversacion Inyectada")

                    result = {
                        "status": "sucess",
                        "intent": "answered",
                        "data": "respuesta",
                    }
                case _:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Mensaje no válido",
                    )

            logger.info("Guardando conversacion en segundo plano")
            background_tasks.add_task(
                save_messages_db,
                mensajes=[message, response_to_message],
                db=db,
                redis=redis,
                schema_name=tenant_db,
                key_redis=llave_historial_cliente,
                channel_id=channel_id,
            )

            return result
        except Exception as e:
            logger.error(f"Error durante el procesamiento del mensaje: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="error procesando el mensaje",
            )
