from fastapi import FastAPI
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_worker(app: FastAPI):
    """Lifespan que inicia el worker para actualizar inventario de productos"""
    logger.info("Iniciando worker")
    app.state.arq_pool = await create_pool(RedisSettings(host="redis", port=6379))
    logger.info("Worker Iniciado")
    yield
    await app.state.arq_pool.close()
