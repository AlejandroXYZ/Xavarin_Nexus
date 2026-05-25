import dotenv
import logging
from contextlib import asynccontextmanager, AsyncExitStack
import os
from fastapi import FastAPI
import sys
from app.api.webhook.webhook import webhook_router
from app.clients.db import lifespan_db
from app.clients.odoo_jsonrpc import lifespan_http_odoo

dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_main(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(lifespan_db(app))
        await stack.enter_async_context(lifespan_http_odoo(app))

        yield


entorno = os.getenv("ENTORNO", "desarrollo")

if entorno == "produccion":
    app = FastAPI(
        title="Vendedor Automático",
        lifespan=lifespan_main,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

else:
    app = FastAPI(
        title="Vendedor Automático",
        description="API para manejar peticiones de clientes automáticamente",
        lifespan=lifespan_main,
    )

app.include_router(webhook_router)
