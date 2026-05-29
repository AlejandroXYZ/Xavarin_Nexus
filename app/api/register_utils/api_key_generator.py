from app.clients.odoo_jsonrpc import ejecutar_odoo
import logging
import os
from fastapi import HTTPException, status
import datetime

logger = logging.getLogger(__name__)


async def generar_api_key_bot(
    client,
    db_nueva: str,
    admin_id: int,
    admin_password: str,
    nuevo_nombre_empresa: str,
    url: str,
) -> dict:
    """Genera una API KEY para el Usuario BOT y cambia el nombre de la empresa"""
    try:
        await ejecutar_odoo(
            http_client=client,
            db=db_nueva,
            uid=admin_id,
            api_key=admin_password,
            modelo="res.company",
            metodo="write",
            odoo_url=url,
            args=[[1], {"name": nuevo_nombre_empresa}],
        )
        logger.info(f"Nombre de la empresa cambiado a: {nuevo_nombre_empresa}")

        logger.info("Buscando BOT IA en Plantilla DB")
        correo_bot = os.getenv("EMAIL_BOT", "bot@bot.com")

        bots_encontrados = await ejecutar_odoo(
            http_client=client,
            odoo_url=url,
            db=db_nueva,
            uid=admin_id,
            api_key=admin_password,
            modelo="res.users",
            metodo="search",
            args=[[["login", "=", correo_bot]]],
        )

        if not bots_encontrados:
            raise RuntimeError("No se encontró el Usuario Bot en la plantilla clonada.")

        bot_uid = bots_encontrados[0]

        model_ids = await ejecutar_odoo(
            http_client=client,
            odoo_url=url,
            db=db_nueva,
            uid=admin_id,
            api_key=admin_password,
            modelo="ir.model",
            metodo="search",
            args=[[["model", "=", "res.users"]]],
        )

        codigo_python_interno = f"""
bot = env['res.users'].browse({bot_uid})
fecha_objeto = datetime.datetime.now() + datetime.timedelta(days=90)
texto_llave = env['res.users.apikeys'].with_user(bot)._generate('rpc', 'Llave_FastAPI_SaaS',fecha_objeto)
action = {{"key": texto_llave}}
""".strip()

        # Crear acción en el servidor
        action_id = await ejecutar_odoo(
            http_client=client,
            odoo_url=url,
            db=db_nueva,
            uid=admin_id,
            api_key=admin_password,
            modelo="ir.actions.server",
            metodo="create",
            args=[
                {
                    "name": "Generador Temporal de API Key",
                    "model_id": model_ids[0],
                    "state": "code",
                    "code": codigo_python_interno,
                }
            ],
        )

        # Ejecutar Accion creada
        resultado_accion = await ejecutar_odoo(
            http_client=client,
            odoo_url=url,
            db=db_nueva,
            uid=admin_id,
            api_key=admin_password,
            modelo="ir.actions.server",
            metodo="run",
            args=[[action_id]],
        )

        api_key_generada = resultado_accion.get("key")

        # Se borra la accion del servidor
        await ejecutar_odoo(
            http_client=client,
            odoo_url=url,
            db=db_nueva,
            uid=admin_id,
            api_key=admin_password,
            modelo="ir.actions.server",
            metodo="unlink",
            args=[[action_id]],
        )
        logger.info("API-Key del Bot generada y script destruido.")

        return {"bot_uid": bot_uid, "api_key": api_key_generada}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error Generando API-KEY para el BOT: {e}",
        )
