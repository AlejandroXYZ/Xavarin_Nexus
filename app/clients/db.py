import os
from contextlib import asynccontextmanager
import asyncpg
import logging
from fastapi import FastAPI, Request
from typing import Annotated
from pathlib import Path

logger = logging.getLogger(__name__)

user = os.getenv("POSTGRES_USER", "user")
host = os.getenv("HOST", "db")
password = os.getenv("POSTGRES_PASSWORD", "123456")
database = "postgres"

new_user = os.getenv("NEW_USER_DB", "fastapi")
new_password = os.getenv("NEW_PASSWORD_DB", "123")
new_db = os.getenv("NEW_DB", "db")
base_dir = Path(__file__).parent.parent / "sql"
logger.info(f"Base dir : {base_dir}")


async def init_schema(
    first_time: Annotated[
        bool, "Indica si es necesario crear las tablas para el schema public"
    ],
    schema_name: Annotated[str, "Nombre para el schema"],
):
    """Crea las tablas para los schemas leyendo desde archivos .sql"""
    conn = None
    try:
        logger.info(f"Configurando esquema '{schema_name}' en {new_db}")
        conn = await asyncpg.connect(
            host=host, user=new_user, password=new_password, database=new_db
        )

        async with conn.transaction():
            if first_time:
                ruta_public = base_dir / "init_public.sql"
                sql_publico = ruta_public.read_text(encoding="utf-8")
                await conn.execute(sql_publico)

            ruta_tenant = base_dir / "init_tenant.sql"
            sql_tenant_template = ruta_tenant.read_text(encoding="utf-8")

            sql_tenant = sql_tenant_template.format(schema_name=schema_name)

            await conn.execute(sql_tenant)

        logger.info("Entorno de base de datos listo")

    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se creaban las tablas para la db: {e}"
        )
        raise e
    finally:
        if conn:
            await conn.close()


async def init_db():
    """Función que crea las bases de datos base de todo el sistema al iniciar"""
    conn = None
    logger.info("Conectando como Admin en Postgres para preparar entorno")
    conn = await asyncpg.connect(
        host=host, user=user, password=password, database=database
    )
    try:
        await conn.fetchval("SELECT 1")  # Ping a Docker

        user_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", new_user
        )
        if not user_exists:
            logger.info(f"Creando Usuario: {new_user}")
            await conn.execute(
                f"CREATE USER {new_user} WITH SUPERUSER PASSWORD '{new_password}';"
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
        await init_schema(first_time=True, schema_name="tenant_schema_template")

    except Exception as e:
        logger.error(f"Error en setup: {e}")
        raise e
    finally:
        if conn:
            await conn.close()


@asynccontextmanager
async def lifespan_db(app: FastAPI):
    """Abre un pool de conexiones y crea la db para FastAPI"""
    await init_db()

    logger.info("Creando pool de conexiones...")
    app.state.db = await asyncpg.create_pool(
        user=new_user,
        password=new_password,
        database=new_db,
        host=host,
        min_size=5,
        max_size=20,
    )

    yield

    logger.info("Cerrando pool de conexiones...")
    await app.state.db.close()


async def get_db(request: Request):
    """Para usar el Pool en los endpoints como dependencia"""
    async with request.app.state.db.acquire() as connection:
        async with connection.transaction():
            try:
                yield connection
            except Exception as e:
                logger.error(
                    f"Error en la transaccion de la DB aplicando Rollback, motivo: {e}"
                )
                raise e
