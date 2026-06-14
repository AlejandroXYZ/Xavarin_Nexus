import re
from fastapi import (
    APIRouter,
    status,
    Request,
    HTTPException,
    Response,
    BackgroundTasks,
)
import logging
import os
from fastapi.responses import FileResponse
from app.services.register_handler import (
    generate_tenant_link,
    save_form_data,
    create_tenant,
)
from app.schemas.register import Form, FormAdmin

logger = logging.getLogger(__name__)

prefix_url = "/api/v1/tenants"

usuario_admin = os.getenv("ODOO_USUARIO_ADMIN_BASE", "odoo")
master_password = os.getenv("MASTER_PASSWORD", "odoo")
password_admin = os.getenv("ODOO_PASSWORD_ADMIN_BASE", "odoo")
register_router = APIRouter(prefix=prefix_url, tags=["register"])


@register_router.post("/form/url_generate")
async def generar_enlace_inquilino(request: Request, name: str) -> str:
    """Genera la URL Única de formulario para que el inquilino llene sus datos"""
    redis = request.app.state.redis
    enlace = await generate_tenant_link(redis=redis, name=name, prefix_url=prefix_url)
    return enlace


@register_router.get("/form/public/{llave_sesion}", status_code=status.HTTP_200_OK)
async def formulario_inquilino(request: Request, llave_sesion: str):
    """Verifica Token y sirve la página de formulario al cliente"""
    logger.info("Abriendo Formulario")

    redis = request.app.state.redis
    verificacion = await redis.exists(llave_sesion)
    if not verificacion:
        logger.warning(f"Intento de acceso fallido. Llave inválida: {llave_sesion}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El enlace es invalido o ha expirado",
        )
    else:
        return FileResponse(
            path="app/frontend/forms/public/formulario.html",
        )


@register_router.post(
    "/form/completed/{llave_sesion}", status_code=status.HTTP_202_ACCEPTED
)
async def guardar_datos_formulario_inquilino(
    data: Form, request: Request, llave_sesion: str
) -> str:
    """Guarda los datos entrantes que envio el inquilino por el formulario y genera enlace para el formulario del usuario admin"""
    redis = request.app.state.redis
    logger.info(f"Datos Recibidos: {data}")
    enlace_admin = await save_form_data(
        redis=redis, llave_sesion=llave_sesion, data=data, prefix_url=prefix_url
    )
    return enlace_admin


@register_router.post("/form/admin/{llave_sesion}/inyection")
async def inyeccion_datos_formulario_admin(request: Request, llave_sesion: str):
    """Envia los datos del cliente para ser inyectados en el HTML del formulario Admin"""
    redis = request.app.state.redis
    if not await redis.exists(llave_sesion):
        logger.warning("Intento Fraudulento o token expirado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enlace Invalido o ha expirado",
        )
    try:
        datos = await redis.get(llave_sesion)
        logger.info(f"datos: {datos}")
        logger.info("Datos Enviados")
        return Response(content=datos, media_type="application/json")
    except Exception as e:
        logger.error(f"Error durante la inyeccion de datos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error Interno"
        )


@register_router.get("/form/admin/{llave_sesion}", status_code=status.HTTP_200_OK)
async def generar_formulario_admin(request: Request, llave_sesion: str):
    """Sirve Formulario HTML al admin para completar registro del inquilino"""
    redis = request.app.state.redis
    if not await redis.exists(llave_sesion):
        logger.error("Intento de sesion con enlace expirado")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Enlace Expirado"
        )

    return FileResponse(path="app/frontend/forms/admin/index.html")


@register_router.post("/register/{llave_sesion}", status_code=status.HTTP_201_CREATED)
async def tenants_register(
    data: FormAdmin,
    request: Request,
    llave_sesion: str,
    background_tasks: BackgroundTasks,
):
    """
    Registra a los nuevos inquilinos con los datos del formulario
    """
    redis = request.app.state.redis
    client = request.app.state.http_client
    db = request.app.state.db
    background_tasks.add_task(
        create_tenant,
        redis=redis,
        db=db,
        llave_sesion=llave_sesion,
        data=data,
        client=client,
    )
