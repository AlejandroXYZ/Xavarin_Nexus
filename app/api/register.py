from app.clients.db import get_db
from fastapi import APIRouter, Depends, status, Request, HTTPException
from app.security.x_api_key import verificar_api
from app.schemas.register import Form
import logging
from app.api.register_utils.duplicate import duplicar_db_odoo, duplicate_schema
import os
from app.clients.odoo_jsonrpc import autenticar_odoo, eliminar_db_odoo
from app.api.register_utils.name_schema import generar_nombre_esquema
from app.api.register_utils.register_tenant import registrar_tenant
from app.api.register_utils.api_key_generator import generar_api_key_bot
from app.api.register_utils.save_credentials import guardar_credenciales

logger = logging.getLogger(__name__)

usuario_admin = os.getenv("USUARIO_ADMIN_BASE", "odoo")
password_admin = os.getenv("PASSWORD_ADMIN_BASE", "odoo")

register_router = APIRouter(prefix="/api/v1/tenants", tags=["register"])


@register_router.post("/register", status_code=status.HTTP_201_CREATED)
async def tenants_register(data: Form, request: Request, db=Depends(get_db)):
    """
    Registra a los nuevos inquilinos
    """
    url = os.getenv("ODOO_URL_BASE", "http://odoo.com")
    client = request.app.state.http_client
    db_name = os.getenv("DB", "db")
    if data.odoo_url is not None:
        url = data.odoo_url
    new_name = generar_nombre_esquema(data.name)

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
        # Duplicar Base de datos Odoo
        await duplicar_db_odoo(url=url, client=client, new_db_name=new_name)
        odoo_db_creada = True

        bot_user = await generar_api_key_bot(
            client=client,
            db_nueva=new_name,
            admin_id=uid,
            admin_password=password_admin,
            nuevo_nombre_empresa=data.name,
            url=url,
        )

        async with db.transaction():
            logger.info("Iniciando Transaccion en Postgres")
            await duplicate_schema(db=db, schema_name=new_name)

            id_tenant = await registrar_tenant(
                data, db, new_name, "hola di mentiras a todo"
            )

            await guardar_credenciales(
                db=db,
                tenant_id=id_tenant,
                odoo_url=url,
                odoo_bot_user_id=bot_user["bot_uid"],
                odoo_bot_api_key=bot_user["api_key"],
            )

            logger.info("Registrado inquilino perfectamente")
            return {"mensaje": "Ejecutado correctamente", "tenant_id": f"{id_tenant}"}

    except Exception as e:
        logger.error(f"Error Critico durante el registro del nuevo Inquilino: {e}")
        if odoo_db_creada:
            logger.warning(f" Borrando la DB '{new_name}' huérfana en Odoo...")
            try:
                await eliminar_db_odoo(
                    url=url,
                    http_client=client,
                    db_nombre=new_name,
                    master_password=password_admin,
                    odoo_url=url,
                )
                logger.info("Base de datos huérfana eliminada en Odoo.")
            except Exception as e_rollback:
                logger.error(
                    f"Falló el borrado manual en Odoo de {new_name}. Error: {e_rollback}"
                )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear el espacio de trabajo. Se han deshecho los cambios.",
        )
