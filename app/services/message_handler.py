import logging
from app.ia.groq_IA import groq
from app.schemas.message import IA_answer, Message, OdooMessageWebhook
from app.ia.product_embedding import product_embedding
from app.services.message_utils.cache import get_cache_data
from app.translators.translator import Translator
from app.services.message_utils.get_history import obtener_historial_cliente
from app.services.message_utils.update_context import save_messages_db
import json
from datetime import datetime
from app.clients.odoo_jsonrpc import ejecutar_odoo
from app.services.message_utils.register_client import register_client_db
from app.services.message_utils.cache_client import get_cache_client
from app.services.message_utils.html_format import format_html, limpiar_html
from app.security.errors_catcher import manual_handling, message_pending_try
from app.services.message_utils.commands.facturar import procesar_factura

logger = logging.getLogger(__name__)


async def response_to_client_handler(
    tenant_db: str, payload: OdooMessageWebhook, redis, db, odoo
):
    """Recibe mensaje de Odoo, lo procesa y responde al cliente"""

    llave = f"cache:{tenant_db}"
    datos_redis = await redis.get(llave)
    if not datos_redis:
        logger.info(f"Generando caché con los datos del inquilino {tenant_db}")
        await get_cache_data(tenant=tenant_db, db=db, redis=redis, redis_key=llave)
        datos_redis = await redis.get(llave)
        if not datos_redis:
            logger.error("Error obteniendo caché del inquilino")
            return
    datos = json.loads(datos_redis)
    if isinstance(datos, dict):
        datos["tokens_platforms"] = json.loads(datos["tokens_platforms"])

    logger.info(f"webhook recibido para el tenant: {tenant_db}")
    logger.info(f"payload recibido: {payload}")
    if payload.model != "discuss.channel":
        return {"status": "ignored", "reason": "Modelo no soportado"}

    author_id_entrante = payload.author_id
    odoo_bot_user_id = datos["odoo_bot_user"]

    if author_id_entrante == odoo_bot_user_id:
        logger.info(
            "Ignorando webhook de Odoo: El mensaje fue enviado por nuestro propio BOT."
        )
        return {"status": "ignored", "detail": "Mensaje del sistema"}

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
        raise ValueError("No se pudo obtener los datos del cliente")
    elif "Resumen de la IA:" in payload.body or "BOT IA:" in payload.body:
        return {"status": "ignored", "reason": "Eco del bot bloqueado"}

    payload.body = limpiar_html(payload.body)
    if payload.body.startswith("/"):
        if payload.body == "/facturar":
            logger.info("Procesando Lógica de Venta y Factura")
            factura = await procesar_factura(
                db=db,
                tenant_db=tenant_db,
                tenant_cache_data=datos,
                http_client=odoo,
                platform_user_id=client["platform_user_id"],
                platform=client["platform"],
            )
            logger.info(f"Ejecutado con éxito: {factura}")
            return
        logger.info(f"Comando no válido: {payload.body}")
        return {"status": "error", "info": "comando no válido"}

    try:
        logger.info(f"Mensaje: {payload.body}")
        logger.info(f"Enviando Mensaje a {client['name']} de {client['platform']}")
        await Translator.enviar(
            plataforma=client["platform"],
            destinatario=client["platform_user_id"],
            texto=payload.body,
            token=datos["tokens_platforms"][client["platform"]],
        )
        logger.info("Mensaje Enviado Correctamente")

        return {"status": "sucess"}
    except Exception as e:
        logger.error(f"Ha Ocurrido un error enviando el mensaje al cliente {e}")


async def message_handler_func(
    message: dict, tenant_db: str, platform: str, arq, odoo, db, redis
):
    """Función encargada de procesar el mensaje recibido en el endpoint"""

    llave = f"cache:{tenant_db}"
    datos_redis = await redis.get(llave)
    if not datos_redis:
        logger.info(f"Generando caché con los datos del inquilino {tenant_db}")
        await get_cache_data(tenant=tenant_db, db=db, redis=redis, redis_key=llave)
        datos_redis = await redis.get(llave)
        if not datos_redis:
            logger.error("Error obteniendo caché del inquilino")
            return
    datos: dict = json.loads(datos_redis)
    if isinstance(datos.get("tokens_platforms"), str):
        datos["tokens_platforms"] = json.loads(datos["tokens_platforms"])
    logger.info(datos)
    if platform not in datos["tokens_platforms"]:
        logger.info(
            "Plataforma no válida, inquilino no tiene esa plataforma disponible"
        )
        return {"status": "error", "info": "plataforma del inquilino no disponible"}

    prompt = datos["ai_system_prompt"]
    message: Message = Translator.traducir(plataforma=platform.strip(), payload=message)
    if message is None:
        return {"status": "ignored", "info": "Evento de sistema o estado"}

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
        respuesta_para_cliente = None

        if message.content == "multimedia":
            logger.info("Mensaje Multimedia enviando al dueño")
            validacion = IA_answer(
                intent="another",
                product="",
                text="Mensaje Multimedia",
            )
        else:
            try:
                if prompt == "" or not prompt:
                    logger.error("No se pudo obtener el system prompt del inquilino")
                    await manual_handling(
                        message=message,
                        tenant_db=tenant_db,
                        redis=redis,
                        db=db,
                        odoo=odoo,
                    )
                    return {"status": "pending", "info": "Mensaje enviado al dueño"}

                logger.info(
                    f"===================={historial_limpio}========================"
                )

                response = await groq(historial_limpio)
                logger.info(f"respuesta de IA {response}")
                validacion = IA_answer.model_validate(response)
            except Exception as e:
                logger.error(
                    f"Ha ocurrido un error mientras se enviaba el mensaje a la IA: {e}"
                )
                return {
                    "status": "error",
                    "info": "Error al procesar el mensaje con la IA",
                }
            ia_is_now_active = True
            respuesta_para_cliente = validacion.text
        try:
            match validacion.intent:
                case "catalog":
                    result = {
                        "status": "success",
                        "intent": "catalog",
                        "data": "Catálogo solicitado",
                    }

                case "answered":
                    respuesta = f"Respondido al Usuario {message.user_name}-ID:{message.platform_user_id} de {message.platform}: {validacion.text}"
                    logger.info(respuesta)
                    result = {
                        "status": "sucess",
                        "intent": "answered",
                        "data": respuesta,
                    }
                    respuesta_para_cliente = validacion.text

                case "ask":
                    respuesta_cruda = await product_embedding(
                        db, validacion.product, message.content, tenant_db
                    )

                    if isinstance(respuesta_cruda, dict):
                        texto_extraido = respuesta_cruda.get(
                            "text", str(respuesta_cruda)
                        )
                    elif isinstance(respuesta_cruda, str):
                        try:
                            texto_extraido = json.loads(respuesta_cruda).get(
                                "text", respuesta_cruda
                            )
                        except json.JSONDecodeError:
                            texto_extraido = respuesta_cruda
                    else:
                        texto_extraido = str(respuesta_cruda)

                    result = {
                        "status": "success",
                        "intent": "ask",
                        "data": texto_extraido,
                    }
                    respuesta_para_cliente = texto_extraido
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
                        message.channel_id = channel_id
                    else:
                        logger.info(f"Reutilizando canal existente: {channel_id}")

                    ia_is_now_active = False
                    message.ia_is_active = ia_is_now_active

                    status_client = (
                        "waiting_for_support"
                        if validacion.intent == "another"
                        else "waiting_for_sale"
                    )
                    await register_client_db(
                        db=db,
                        mensaje=message,
                        schema_name=tenant_db,
                        status=status_client,
                        channel_id=channel_id,
                        tenant_cache_data=datos,
                        http_client=odoo,
                    )

                    transcripcion_html = format_html(historial_limpio)
                    logger.info("Inyectando conversacion")

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
                            "body": transcripcion_html,
                            "message_type": "comment",
                            "subtype_xmlid": "mail.mt_comment",
                            "body_is_html": True,
                        },
                    )
                    logger.info("conversacion Inyectada")

                    result = {
                        "status": "sucess",
                        "intent": validacion.intent,
                        "data": "Mensaje enviado al dueño",
                    }

                    respuesta_para_cliente = validacion.text

                case _:
                    logger.error(
                        f"Mensaje no Válido, error extrayendo intent, mensaje: {message}, intent: {validacion} "
                    )
                    return {"status": "Error"}

            logger.info("Guardando conversacion en segundo plano")
            mensajes_a_guardar = [message]

            if respuesta_para_cliente:
                memoria_ia_json = json.dumps(
                    {
                        "intent": validacion.intent,
                        "product": validacion.product,
                        "text": respuesta_para_cliente,
                    },
                    ensure_ascii=False,
                )

                response_to_message = Message(
                    platform=message.platform,
                    platform_user_id=message.platform_user_id,
                    user_name=message.user_name,
                    content=memoria_ia_json,
                    created_at=datetime.now(),
                    type="message",
                    role="assistant",
                    ia_is_active=ia_is_now_active,
                    metadata="{}",
                )
                mensajes_a_guardar.append(response_to_message)

            await save_messages_db(
                mensajes=mensajes_a_guardar,
                db=db,
                redis=redis,
                schema_name=tenant_db,
                key_redis=llave_historial_cliente,
                channel_id=channel_id,
            )

            logger.info("Respondiendo mensaje al cliente")
            logger.info(f"Tokens_platforms: {datos['tokens_platforms']}")
            await Translator.enviar(
                plataforma=message.platform,
                destinatario=message.platform_user_id,
                texto=respuesta_para_cliente,
                token=datos["tokens_platforms"][message.platform],
            )

            return result

        except Exception as e:
            logger.error(f"Error durante el procesamiento del mensaje: {e}")
            await message_pending_try(
                message=message, tenant_db=tenant_db, redis=redis, arq=arq
            )
