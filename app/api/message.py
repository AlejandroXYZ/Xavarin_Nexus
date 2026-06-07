from fastapi import APIRouter, Request, status, Depends, HTTPException
from app.security.x_api_key import verificar_api
import logging
from app.ia.groq_IA import groq
from app.schemas.message import IA_answer, Message
from app.ia.product_embedding import product_embedding
from app.api.catalog_utils.cache import save_cache_data
import json

message_router = APIRouter(prefix="/api/v1/message/{tenant_db}", tags=["message"])


logger = logging.getLogger(__name__)


@message_router.post(
    "/",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verificar_api)],
)
async def message_handler(message: Message, tenant_db: str, request: Request):
    db = request.app.state.db
    redis = request.app.state.redis
    llave = f"cache:{tenant_db}"
    if not await redis.exists(llave):
        logger.info(f"Generando caché con los datos del inquilino {tenant_db}")
        await save_cache_data(tenant=tenant_db, db=db, redis=redis, redis_key=llave)
    datos = json.loads(await redis.get(llave))
    prompt = datos["ai_system_prompt"]
    try:
        if prompt is None:
            logger.error("No se pudo obtener el system prompt del inquilino")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ha ocurrido un error interno",
            )
        response = await groq(prompt, message.text)
        logger.info(f"respuesta de IA {response}")
        validacion = IA_answer.model_validate(response)

        match validacion.intent:
            case "buy":
                return "buying"

            case "answered":
                logger.info(
                    f"Respondido al Usuario {message.customer_name}-ID:{message.customer_id} de {message.platform}: {validacion.text}"
                )
                return validacion

            case "ask":
                respuesta = await product_embedding(
                    db, validacion.product, message.text, tenant_db
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
