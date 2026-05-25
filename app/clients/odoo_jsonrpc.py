import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI


logger = logging.getLogger(__name__)


async def autenticar_odoo_dinamico(
    http_client: httpx.AsyncClient, odoo_url: str, db: str, usuario: str, api_key: str
):
    """
    Autentica al bot de Odoo  usando el cliente HTTP global y las credenciales específicas del inquilino
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "authenticate",
            "args": [db, usuario, api_key, {}],
        },
        "id": 1,
    }

    response = await http_client.post(f"{odoo_url}/jsonrpc", json=payload)
    response.raise_for_status()

    json_data = response.json()
    uid = json_data.get("result")

    if not uid:
        raise RuntimeError(
            f"Credenciales de Odoo no válidas para la DB {db}. Asegúrate de crear una API Válida."
        )
    return uid


@asynccontextmanager
async def lifespan_http_odoo(app: FastAPI):
    """Pool de conexión HTTP para el SaaS"""
    logger.info("Inicializando pool de conexiones...")

    try:
        app.state.http_client = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
        )

        yield
    except Exception as e:
        logger.error(f" Error en el arranque: {e}")
        raise e

    finally:
        logger.info(" Apagando el servidor. Cerrando conexiones...")
        await app.state.http_client.aclose()
        logger.info("Conexiones cerradas.")
