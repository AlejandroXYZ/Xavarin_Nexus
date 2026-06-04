from app.clients.db import get_db
from fastapi import APIRouter, Depends, status, Request, HTTPException, Response
from app.security.x_api_key import verificar_api
from app.schemas.register import Form, FormAdmin, RegisterData
import logging
from app.api.register_utils.duplicate import duplicar_db_odoo, duplicate_schema
import os
from app.clients.odoo_jsonrpc import autenticar_odoo, eliminar_db_odoo
from app.api.register_utils.name_schema import generar_nombre_esquema
from app.api.register_utils.register_tenant import registrar_tenant
from app.api.register_utils.api_key_generator import generar_api_key_bot
from app.api.register_utils.save_credentials import guardar_credenciales
from fastapi.responses import FileResponse
from app.api.register_utils.payment_plans import CONFIGURACION_PLANES
import secrets
from app.api.register_utils.update_webhook_odoo import actualizar_webhook_odoo
import json

logger = logging.getLogger(__name__)

prefix_url = "/api/v1/tenants"

usuario_admin = os.getenv("ODOO_USUARIO_ADMIN_BASE", "odoo")
master_password = os.getenv("MASTER_PASSWORD", "odoo")
password_admin = os.getenv("ODOO_PASSWORD_ADMIN_BASE", "odoo")
register_router = APIRouter(prefix=prefix_url, tags=["register"])


@register_router.post("/form/url_generate")
async def generar_enlace_inquilino(request: Request, name: str):
    """Genera la URL Única de formulario para que el inquilino llene sus datos"""
    logger.info("Generando URL para Nuevo Inquilino")
    redis = request.app.state.redis
    token = secrets.token_urlsafe(32)
    name = name.replace(" ", "").strip().lower()
    llave_sesion = f"form:public:{name}"
    await redis.set(llave_sesion, token, ex=172800)
    url_base = os.getenv("URL_API_BASE", "http://localhost:8000")
    url = f"{url_base}{prefix_url}/form/public/{llave_sesion}"
    logger.info(f"Sesion y Url Generada bajo la llave: {llave_sesion}")
    return url


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
):
    """Guarda los datos entrantes que envio el inquilino por el formulario y genera enlace para el formulario del usuario admin"""
    redis = request.app.state.redis
    logger.info(f"Datos Recibidos: {data}")
    if not await redis.exists(llave_sesion):
        logger.warning("Intento Fraudulento o Token Expirado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enlace inválido o ha expirado",
        )
    try:
        logger.info("Guardando datos en Redis")
        nombre = data.name.replace(" ", "").strip()
        llave_datos = f"tenant:admin:{nombre.lower()}"
        datos = data.model_dump_json()
        await redis.set(llave_datos, datos, ex=86400)
        logger.info(f"Datos Guardados en Redis bajo la llave: {llave_datos}")
        logger.info("Borrando Token Usado")
        await redis.delete(llave_sesion)
        logger.info("Llave de sesion usada y eliminada")

        logger.info("Generando URL Administrador")
        url_base = os.getenv("URL_API_BASE", "http://localhost:8000")
        url_admin = f"{url_base}{prefix_url}/form/admin/{llave_datos}"
        logger.info(f"URL de Admin generada: {url_admin}")
        return {"url": url_admin}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
        )


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
    if not redis.exists(llave_sesion):
        logger.error("Intento de sesion con enlace expirado")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Enlace Expirado"
        )

    return FileResponse(path="app/frontend/forms/admin/index.html")


@register_router.post("/register/{llave_sesion}", status_code=status.HTTP_201_CREATED)
async def tenants_register(
    data: FormAdmin, request: Request, llave_sesion: str, db=Depends(get_db)
):
    """
    Registra a los nuevos inquilinos con los datos del formulario
    """
    redis = request.app.state.redis
    if not await redis.exists(llave_sesion):
        logger.error("Intento de acceso con token expirado o invalido")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error Enlace Expirado",
        )
    datos_recopilados_admin = json.loads(await redis.get(llave_sesion))
    datos_recopilados_inquilino = data.model_dump()
    datos_completos = datos_recopilados_inquilino | datos_recopilados_admin
    datos_registro = RegisterData(**datos_completos)
    logger.info("Eliminando Llave de Sesion en Redis")
    await redis.delete(llave_sesion)
    url = os.getenv("ODOO_URL_BASE", "http://odoo.com")
    logger.warning(f"INTENTO DE CONEXIÓN - URL de Odoo: '{url}'")
    client = request.app.state.http_client
    db_name = os.getenv("DB", "db")

    if datos_registro.odoo_url is not None:
        url = datos_registro.odoo_url
    new_name = generar_nombre_esquema(datos_registro.name)
    odoo_db_creada = False

    try:
        uid = await autenticar_odoo(
            http_client=client,
            odoo_url=url,
            db=db_name,
            usuario=usuario_admin,
            api_key=password_admin,
        )
        logger.info(f"ID de usuario {usuario_admin} es {uid}")
        logger.info(f"Duplicando plantilla hacia: {new_name}")
        await duplicar_db_odoo(url=url, client=client, new_db_name=new_name)
        odoo_db_creada = True

        bot_user = await generar_api_key_bot(
            client=client,
            db_nueva=new_name,
            admin_id=uid,
            admin_password=password_admin,
            nuevo_nombre_empresa=datos_registro.name,
            url=url,
        )
        logger.info(f"Obtenido del Bot User: {bot_user}")

        async with db.transaction():
            logger.info("Iniciando Transaccion en Postgres")
            await duplicate_schema(db=db, schema_name=new_name)
            features = json.dumps(
                CONFIGURACION_PLANES.get("plan_elegido", CONFIGURACION_PLANES["basico"])
            )

            id_tenant = await registrar_tenant(
                data=datos_registro, db=db, schema_name=new_name, features=features
            )

            await guardar_credenciales(
                db=db,
                tenant_id=id_tenant,
                odoo_url=url,
                odoo_bot_user_id=bot_user["bot_uid"],
                odoo_bot_api_key=bot_user["api_key"],
                odoo_db=new_name,
                tokens_platforms=datos_registro.tokens_platforms,
            )

            logger.info("Actualizando Acciones automatizadas")
            token_secret = os.getenv(
                "FASTAPI_WEBHOOK_SECRET", "Token_para_webhook_odoo"
            )
            await actualizar_webhook_odoo(
                http_client=client,
                odoo_url=url,
                db=new_name,
                uid=uid,
                password=password_admin,
                tenant_id=id_tenant,
                secret=token_secret,
            )
            logger.info("Registrado inquilino perfectamente")
            return {"mensaje": "Ejecutado correctamente", "tenant_id": f"{id_tenant}"}

    except Exception as e:
        logger.error(f"Error Critico durante el registro del nuevo Inquilino: {e}")
        if odoo_db_creada:
            logger.warning(f" Borrando la DB '{new_name}' huérfana en Odoo...")
            try:
                await eliminar_db_odoo(
                    http_client=client,
                    db_nombre=new_name,
                    master_password=master_password,
                    odoo_url=url,
                )
                logger.info("Base de datos huérfana eliminada en Odoo.")
            except Exception as e_rollback:
                logger.error(
                    f"Falló el borrado manual en Odoo de {new_name}. Error: {e_rollback}"
                )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al crear el espacio de trabajo. Se han deshecho los cambios, error: {e}",
        )
