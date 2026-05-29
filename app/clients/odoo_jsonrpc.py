import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
import os

logger = logging.getLogger(__name__)


async def autenticar_odoo(
    http_client: httpx.AsyncClient, odoo_url: str, db: str, usuario: str, api_key: str
) -> int:
    """
    Autentica al bot de Odoo usando el cliente HTTP global y las credenciales específicas del inquilino
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

    logger.info(f"Autenticando Usuario {usuario}")
    response = await http_client.post(f"{odoo_url}/jsonrpc", json=payload)
    response.raise_for_status()
    json_data = response.json()
    logger.info(json_data)
    uid = json_data.get("result")

    if not uid:
        raise RuntimeError(
            f"Credenciales de Odoo no válidas para la DB {db}. Asegúrate de crear una API Válida."
        )
    return uid


async def ejecutar_odoo(
    http_client: httpx.AsyncClient,
    odoo_url: str,
    db: str,
    uid: int,
    api_key: str,
    modelo: str,
    metodo: str,
    args: list = None,
    kwargs: dict = None,
):
    """
    Función universal para hacer CUALQUIER operación en Odoo (Create, Read, Update, Delete).
    """

    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [db, uid, api_key, modelo, metodo, args, kwargs],
        },
        "id": 1,
    }

    response = await http_client.post(f"{odoo_url}/jsonrpc", json=payload)
    response.raise_for_status()

    json_data = response.json()

    if "error" in json_data:
        raise RuntimeError(f"Error interno de Odoo: {json_data['error']}")

    return json_data.get("result")


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
