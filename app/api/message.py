from fastapi import APIRouter, status, Depends, HTTPException
from app.security.x_api_key import verificar_api
import logging
from app.ia.groq_IA import groq
from app.schemas.message import IA_answer, Message
from app.clients.db import get_db
from app.ia.product_embedding import product_embedding

message_router = APIRouter(prefix="/api/v1/message/{tenant_db}", tags=["message"])


logger = logging.getLogger(__name__)


@message_router.post(
    "/",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verificar_api)],
)
async def message_handler(message: Message, tenant_db: str, db=Depends(get_db)):
    try:
        prompt = await db.fetchval(
            """
    SELECT ai_system_prompt FROM tenants WHERE schema_name = $1;
    """,
            tenant_db,
        )
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
                return "error"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
