import os
from contextlib import asynccontextmanager
import asyncpg
import logging
from fastapi import FastAPI, Request
from app.clients.odoo_jsonrpc import obtener_catalogo

logger = logging.getLogger(__name__)

user = os.getenv("POSTGRES_USER", "user")
host = os.getenv("HOST", "db")
password = os.getenv("POSTGRES_PASSWORD", "123456")
database = os.getenv("POSTGRES_DB", "db")

new_user = os.getenv("FASTAPI_USER", "fastapi")
new_password = os.getenv("FASTAPI_PASSWORD", "123")
new_db = os.getenv("FASTAPI_DB", "db")


async def create_db():
    conn = None
    try:
        logger.info("Conectando como Admin para preparar entorno")
        conn = await asyncpg.connect(
            host=host, user=user, password=password, database=database
        )
        await conn.fetchval("SELECT 1")  # Ping a Docker

        user_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", new_user
        )
        if not user_exists:
            logger.info(f"Creando Usuario: {new_user}")
            await conn.execute(
                f"CREATE USER {new_user} WITH PASSWORD '{new_password}';"
            )

        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", new_db
        )
        if not db_exists:
            logger.info(f"Creando DB: {new_db}")
            await conn.execute(f"CREATE DATABASE {new_db} OWNER {new_user};")

        await conn.close()

        conn = await asyncpg.connect(
            host=host, user=user, password=password, database=new_db
        )
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.close()

        logger.info(f"Configurando esquema en {new_db}")
        conn = await asyncpg.connect(
            host=host, user=new_user, password=new_password, database=new_db
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS catalog (
                id INTEGER PRIMARY KEY, 
                nombre TEXT,
                descripcion TEXT,
                semantica TEXT,
                precio NUMERIC(12,2),
                cantidad_disponible NUMERIC(12,2),
                embedding VECTOR(384)
            );""")
        await conn.execute("""CREATE INDEX IF NOT EXISTS catalog_embedding_hnsw_idx 
        ON catalog 
        USING hnsw (embedding vector_cosine_ops);""")

        logger.info("Entorno de base de datos listo")
    except Exception as e:
        logger.error(f"Error en setup: {e}")
        raise e
    finally:
        if conn:
            await conn.close()


@asynccontextmanager
async def lifespan_db(app: FastAPI):
    """Abre un pool de conexiones y crea la db para FastAPI"""
    await create_db()

    logger.info("Creando pool de conexiones...")
    app.state.db = await asyncpg.create_pool(
        user=new_user,
        password=new_password,
        database=new_db,
        host=host,
        min_size=5,
        max_size=20,
    )

    try:
        async with app.state.db.acquire() as conn:
            await obtener_catalogo(conn)
            logger.info("Sincronización exitosa")
    except Exception as e:
        logger.error(f"Error critico al sincronizar con Odoo: {e}")
        raise e

    yield

    logger.info("Cerrando pool de conexiones...")
    await app.state.db.close()


async def get_db(request: Request):
    """Para usar el Pool en los endpoints como dependencia"""
    async with request.app.state.db.acquire() as connection:
        yield connection

