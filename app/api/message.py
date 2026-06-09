from fastapi import APIRouter, Request, status, Depends, HTTPException, BackgroundTasks
from app.security.x_api_key import verificar_api
import logging
from app.ia.groq_IA import groq
from app.schemas.message import IA_answer, Message
from app.ia.product_embedding import product_embedding
from app.api.message_utils.cache import save_cache_data
from app.translators.translator import Translator
from app.api.message_utils.get_history import obtener_historial_cliente
from app.api.message_utils.update_context import save_messages_db
import json
from datetime import datetime

message_router = APIRouter(prefix="/api/v1/message/{tenant_db}", tags=["message"])


logger = logging.getLogger(__name__)


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
    llave = f"cache:{tenant_db}"
    if not await redis.exists(llave):
        logger.info(f"Generando caché con los datos del inquilino {tenant_db}")
        await save_cache_data(tenant=tenant_db, db=db, redis=redis, redis_key=llave)
    datos = json.loads(await redis.get(llave))
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

        if not ia_is_active:
            logger.info("IA desactivada, mensaje directo al dueño")
            return  # Mensaje directo a Dueño

        historial_limpio = [
            {clave: valor for clave, valor in fila.items() if clave != "ia_is_active"}
            for fila in historial
        ]
        historial_limpio = historial_limpio[::-1]
        historial_limpio.append({"role": "user", "content": message.content})
        historial_limpio.insert(0, {"role": "system", "content": prompt})

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
                content=f"{{'intent':{validacion.intent},'answer':{validacion.text},'product':{validacion.product} }}",
                created_at=datetime.now(),
                type="message",
                role="assistant",
                ia_is_active=True,
                metadata="{}",
            )
            logger.info("Guardando conversacion en segundo plano")
            background_tasks.add_task(
                save_messages_db,
                mensajes=[message, response_to_message],
                db=db,
                redis=redis,
                schema_name=tenant_db,
                key_redis=llave_historial_cliente,
            )

            match validacion.intent:
                case "buy":
                    return "buying"

                case "answered":
                    respuesta = f"Respondido al Usuario {message.user_name}-ID:{message.platform_user_id} de {message.platform}: {validacion.text}"
                    logger.info(respuesta)
                    return {"status": "sucess", "intent": "answered", "data": respuesta}

                case "ask":
                    respuesta = await product_embedding(
                        db, validacion.product, message.content, tenant_db
                    )
                    return {"status": "sucess", "intent": "ask", "data": respuesta}
                case "catalog":
                    return {"catalog"}
                case "another":
                    return "another"
                case _:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Mensaje no válido",
                    )
        except Exception as e:
            logger.error(f"Error durante el procesamiento del mensaje: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="error procesando el mensaje",
            )
