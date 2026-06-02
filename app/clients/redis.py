from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi import FastAPI
import logging


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_redis(app: FastAPI):
    logger.info("Iniciando conexion con Redis")
    url = "redis://redis:6379/0"
    pool = redis.ConnectionPool.from_url(
        url=url, decode_responses=True, max_connections=50
    )

    app.state.redis = redis.Redis(connection_pool=pool)

    yield

    logger.info("Cerrando Conexiones Redis")
    await app.state.redis.close()
