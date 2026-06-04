import os


async def actualizar_webhook_odoo(
    http_client,
    odoo_url: str,
    db: str,
    uid: int,
    password: str,
    tenant_id: str,
    secret: str,
):
    """Busca la acción de Automatización del Inventario del Webhook en Odoo y le inyecta el nombre real del inquilino"""

    base_url = os.getenv("URL_API_BASE_DOCKER", "http://localhost:8000")
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
                [[["name", "=", "Webhook IA FastAPI"]]],
            ],
        },
    }

    response = await http_client.post(f"{odoo_url}/jsonrpc", json=payload_search)
    action_ids = response.json().get("result")

    if action_ids:
        nueva_url = f"{base_url}/api/v1/catalog/?tenant={tenant_id}&token={secret}"

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
                    [action_ids, {"webhook_url": nueva_url}],
                ],
            },
        }
        await http_client.post(f"{odoo_url}/jsonrpc", json=payload_write)
