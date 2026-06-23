from app.schemas.register import Form, FormAdmin, RegisterData
import logging
from app.services.register_utils.duplicate import duplicar_db_odoo, duplicate_schema
import os
from app.clients.odoo_jsonrpc import autenticar_odoo, eliminar_db_odoo
from app.services.register_utils.name_schema import generar_nombre_esquema
from app.services.register_utils.register_tenant import registrar_tenant
from app.services.register_utils.api_key_generator import generar_api_key_bot
from app.services.register_utils.save_credentials import guardar_credenciales
from app.services.register_utils.payment_plans import CONFIGURACION_PLANES
import secrets
from app.services.register_utils.update_webhook_odoo import actualizar_webhook_odoo
import json
from unidecode import unidecode


logger = logging.getLogger(__name__)

usuario_admin = os.getenv("ODOO_USUARIO_ADMIN_BASE", "odoo")
master_password = os.getenv("MASTER_PASSWORD", "odoo")
password_admin = os.getenv("ODOO_PASSWORD_ADMIN_BASE", "odoo")


async def generate_tenant_link(redis, name: str, prefix_url: str):
    """Genera url única de formulario para el inquilino llene sus datos"""
    logger.info("Generando URL para Nuevo Inquilino")
    token = secrets.token_urlsafe(32)
    name = unidecode(name.replace(" ", "").strip().lower())
    llave_sesion = f"form:public:{name}"
    await redis.set(llave_sesion, token, ex=172800)
    url_base = os.getenv("URL_API_BASE", "http://localhost:8000")
    url = f"{url_base}{prefix_url}/form/public/{llave_sesion}"
    logger.info(f"Sesion y Url Generada bajo la llave: {llave_sesion}")
    return url


async def save_form_data(redis, llave_sesion: str, data: Form, prefix_url: str):
    """Guarda los datos que llenó el inquilinos en el formulario y genera el formulario del usuario admin"""

    if not await redis.exists(llave_sesion):
        logger.warning("Intento Fraudulento o Token Expirado")
        raise ValueError("Token Inválido")
    try:
        logger.info("Guardando datos en Redis")
        nombre = unidecode(data.name.replace(" ", "").strip())
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
        return url_admin

    except Exception as e:
        raise ValueError(f"Error al generar el Enlace para el formulario del admin {e}")


async def create_tenant(redis, db, llave_sesion: str, data: FormAdmin, client):
    """Registra y activa al nuevo inquilino"""
    if not await redis.exists(llave_sesion):
        logger.error("Intento de acceso con token expirado o invalido")
        raise ValueError("Error, enlace expirado")
    datos_recopilados_admin = json.loads(await redis.get(llave_sesion))
    datos_recopilados_inquilino = data.model_dump()
    datos_completos = datos_recopilados_inquilino | datos_recopilados_admin
    datos_registro = RegisterData(**datos_completos)
    logger.info("Eliminando Llave de Sesion en Redis")
    await redis.delete(llave_sesion)
    url = os.getenv("ODOO_URL_BASE", "http://odoo.com")
    logger.warning(f"INTENTO DE CONEXIÓN - URL de Odoo: '{url}'")
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

        await duplicar_db_odoo(new_db_name=new_name, db=db)
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

        async with db.acquire() as db_conn:
            async with db_conn.transaction():
                logger.info("Iniciando Transaccion en Postgres")
                await duplicate_schema(schema_name=new_name)
                plan = datos_registro.payment_plan.lower()
                features = json.dumps(
                    CONFIGURACION_PLANES.get(plan, CONFIGURACION_PLANES["basico"])
                )

                id_tenant = await registrar_tenant(
                    data=datos_registro,
                    db=db_conn,
                    schema_name=new_name,
                    features=features,
                    odoo=client,
                    odoo_url=url,
                    odoo_bot_user_id=bot_user["bot_uid"],
                    odoo_bot_api_key=bot_user["api_key"],
                )

                await guardar_credenciales(
                    db=db_conn,
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
                    secret=token_secret,
                )
                logger.info("Registrado inquilino perfectamente")
                return {
                    "mensaje": "Ejecutado correctamente",
                    "tenant_id": f"{id_tenant}",
                }

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

        raise ValueError(
            f"Error interno al crear el espacio de trabajo. Se han deshecho los cambios, error: {e}"
        )
