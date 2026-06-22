from fastapi import (
    APIRouter,
    Request,
    status,
    Depends,
    HTTPException,
    BackgroundTasks,
)
from app.security.x_api_key import verificar_api
import logging
import os
from app.services.message_handler import (
    response_to_client_handler,
    message_handler_func,
)
from app.schemas.message import OdooMessageWebhook

message_router = APIRouter(prefix="/api/v1/message/{tenant_db}", tags=["message"])


logger = logging.getLogger(__name__)


@message_router.post(
    "/webhook",
    status_code=status.HTTP_202_ACCEPTED,
)
async def response_to_client(
    tenant_db: str,
    payload: OdooMessageWebhook,
    request: Request,
    token: str,
    background_tasks: BackgroundTasks,
):
    """Recibe Mensaje de Odoo, lo procesa y responde al cliente"""
    redis = request.app.state.redis
    db = request.app.state.db
    odoo = request.app.state.http_client
    true_token = os.getenv("FASTAPI_WEBHOOK_SECRET", "1234")
    if token != true_token:
        logger.error("Token no válido")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token no válido"
        )
    background_tasks.add_task(
        response_to_client_handler,
        tenant_db=tenant_db,
        payload=payload,
        redis=redis,
        db=db,
        odoo=odoo,
    )
    return {"status": "sucess", "status_code": "202_ACCEPTED"}


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
):
    """Endpoint encargado de toda la lógica de procesamiento del mensaje y respuesta"""

    db = request.app.state.db
    redis = request.app.state.redis
    http_client = request.app.state.http_client
    arq = request.app.state.arq_pool
    response = await message_handler_func(
        message=message,
        tenant_db=tenant_db,
        platform=platform,
        odoo=http_client,
        db=db,
        redis=redis,
        arq=arq,
    )

    return {"status": "sucess", "answer": response}
