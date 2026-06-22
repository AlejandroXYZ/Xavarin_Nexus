from fastapi import APIRouter, Request, status, HTTPException
from app.schemas.catalog import ProductoOdoo
import logging
import time
import os

catalog_router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])
logger = logging.getLogger(__name__)


@catalog_router.post("/{tenant}", status_code=status.HTTP_202_ACCEPTED)
async def actualizar_inventario(
    payload: ProductoOdoo,
    tenant: str,
    token: str,
    request: Request,
):
    """Recibe peticiones POST de Odoo para actualizar el inventario"""

    llave_redis = f"sala_espera_vectores:{tenant}"
    redis = request.app.state.redis
    await redis.rpush(llave_redis, payload.model_dump_json())
    ventana_tiempo = int(time.time() // 10)
    job_id = f"lote_{tenant}_{ventana_tiempo}"

    token_real = os.getenv("FASTAPI_WEBHOOK_SECRET", "token123")
    if token_real != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticacion no fueron proporcionadas",
        )
    try:
        await request.app.state.arq_pool.enqueue_job(
            "actualizar_inventario_odoo",
            _job_id=job_id,
            _defer_by=10,
            tenant=tenant,
        )
    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se enviaban las peticiones de odoo a la cola de tareas: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
        )
    return {"status": "en_sala_de_espera"}
