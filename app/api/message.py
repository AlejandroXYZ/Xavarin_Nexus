from fastapi import APIRouter, status, Depends, HTTPException
from app.security.x_api_key import verificar_api
import logging
from app.ia.groq_IA import groq
from app.schemas.message import IA_answer, Message
from app.clients.db import get_db

message_router = APIRouter(prefix="/api/v1/message/{tenant_id}", tags=["message"])


logger = logging.getLogger(__name__)
prompt = "Saluda"


@message_router.post(
    "/message/",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verificar_api)],
)
async def message_handler(message: Message, db=Depends(get_db)):
    try:
        response = await groq(prompt, message.text)
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
                return "ask"
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
