from fastapi import APIRouter, BackgroundTasks, Request, status, HTTPException
from app.schemas.catalog import ProductoOdoo
import logging

catalog_router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])
logger = logging.getLogger(__name__)


@catalog_router.post("/")
async def actualizar_inventario(
    payload: ProductoOdoo, background_tasks: BackgroundTasks, tenant: str, token: str
):
    """Recibe petición POST de Odoo para actualizar el inventario"""
    logger.info(f"payload recibido: {payload}")
    return "ok"
    # background_tasks.add_task(procesar_lista_productos, payload.productos)
    # return {"status": "ok", "message": f"{cantidad} productos encolados"}
