from fastapi import APIRouter, Request, status, Depends, HTTPException
from app.security.x_api_key import verificar_api
import logging
from app.ia.groq_IA import groq
from app.schemas.message import IA_answer, Message
from app.ia.product_embedding import product_embedding
from app.api.message_utils.cache import save_cache_data
from app.translators.translator import Translator
import json

message_router = APIRouter(prefix="/api/v1/message/{tenant_db}", tags=["message"])


logger = logging.getLogger(__name__)


@message_router.post(
    "/{platform}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verificar_api)],
)
async def message_handler(
    message: dict, tenant_db: str, request: Request, platform: str
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

    historial = obtener_historial_cliente(user_id=message.platform_user_id, db=db)

    try:
        if prompt == "" or not prompt:
            logger.error("No se pudo obtener el system prompt del inquilino")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error interno",
            )
        response = await groq(prompt, message.content)
        logger.info(f"respuesta de IA {response}")
        validacion = IA_answer.model_validate(response)

        match validacion.intent:
            case "buy":
                return "buying"

            case "answered":
                logger.info(
                    f"Respondido al Usuario {message.user_name}-ID:{message.platform_user_id} de {message.platform}: {validacion.text}"
                )
                return validacion

            case "ask":
                respuesta = await product_embedding(
                    db, validacion.product, message.content, tenant_db
                )
                return respuesta
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
