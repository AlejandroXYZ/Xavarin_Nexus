import os
import logging

logger = logging.getLogger(__name__)


async def actualizar_webhook_odoo(
    http_client,
    odoo_url: str,
    db: str,
    uid: int,
    password: str,
    secret: str,
):
    """
    Busca todas las acciones de Servidor (Webhooks) heredadas de la base de datos
    plantilla en Odoo y les inyecta el nombre real del nuevo inquilino.
    """
    base_url = os.getenv("URL_API_BASE_DOCKER", "http://localhost:8000")

    webhooks_a_actualizar = [
        {
            "nombre_accion": "Webhook IA FastAPI",
            "nueva_url": f"{base_url}/api/v1/catalog/{db}?token={secret}",
        },
        {
            "nombre_accion": "Webhook Salida Chat FastAPI",
            "nueva_url": f"{base_url}/api/v1/message/{db}/webhook?token={secret}",
        },
    ]

    for webhook in webhooks_a_actualizar:
        payload_search = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    db,
                    uid,
                    password,
                    "ir.actions.server",
                    "search",
                    [[["name", "=", webhook["nombre_accion"]]]],
                ],
            },
        }

        response = await http_client.post(f"{odoo_url}/jsonrpc", json=payload_search)

        data = response.json()
        action_ids = data.get("result")

        if action_ids:
            payload_write = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        db,
                        uid,
                        password,
                        "ir.actions.server",
                        "write",
                        [action_ids, {"webhook_url": webhook["nueva_url"]}],
                    ],
                },
            }
            await http_client.post(f"{odoo_url}/jsonrpc", json=payload_write)
            logger.info(
                f"Webhook '{webhook['nombre_accion']}' actualizado exitosamente para el inquilino '{db}'."
            )
        else:
            logger.warning(
                f"No se encontró la acción '{webhook['nombre_accion']}' en la base de datos '{db}'."
            )
