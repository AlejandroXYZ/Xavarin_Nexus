import httpx
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.catalog import get_catalog
import os

logger = logging.getLogger(__name__)
base_url = "http://odoo:8069"
id_usuario = os.getenv("USUARIO_ID", None)
db = os.getenv("DB", "db")
usuario = os.getenv("ODOO_USER", "odoo")
api_key = os.getenv("API_KEY_ODOO", "api")


async def conexion_odoo():
    client = httpx.AsyncClient(timeout=15.0, base_url=base_url)
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
    response = await client.post("/jsonrpc", json=payload)
    response.raise_for_status()
    json = response.json()
    uid = json.get("result")
    if not uid:
        raise RuntimeError("Credenciales de Odoo no válidas. No se pudo obtener el UID")

    return {"client": client, "uid": uid}


@asynccontextmanager
async def lifespan_odoo(app: FastAPI):
    """Pool de conexión JSON-RPC Odoo-FastAPI"""
    try:
        datos = await conexion_odoo()
        app.state.odoo_client = datos["client"]
        app.state.odoo_uid = datos["uid"]

    except Exception as e:
        raise e
    yield

    await app.state.odoo_client.aclose()
