import logging
import os
from app.clients.db import init_schema
import asyncpg

logger = logging.getLogger(__name__)


async def duplicar_db_odoo(new_db_name: str) -> bool:
    conn = None  # Cambié 'db' a 'conn' para no confundir con el nombre de la base
    try:
        user = os.getenv("POSTGRES_USER", "odoo")
        password = os.getenv("POSTGRES_PASSWORD", "123")
        host = os.getenv("HOST", "db")

        # 1. Conectarse a la base de datos 'postgres' (la base maestra que siempre existe)
        conn = await asyncpg.connect(
            user=user, password=password, host=host, database="postgres"
        )

        db_plantilla = os.getenv("DB", "db_plantilla_prod")

        logger.info(
            f"Clonando DB de ODOO vía Postgres: {db_plantilla} -> {new_db_name}"
        )

        # 2. Terminar conexiones activas de la plantilla
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_plantilla}'
            AND pid <> pg_backend_pid();
        """)

        # 3. Crear la nueva base de datos
        await conn.execute(
            f'CREATE DATABASE "{new_db_name}" WITH TEMPLATE "{db_plantilla}"'
        )

        # 4. Asignar el dueño correcto (IMPORTANTE para Odoo)
        await conn.execute(f'ALTER DATABASE "{new_db_name}" OWNER TO "{user}"')

        logger.info(f"DB de Odoo '{new_db_name}' clonada perfectamente.")
        return True

    except Exception as e:
        logger.error(f"Error al duplicar la DB en Postgres: {e}")
        raise e
    finally:
        # Solo cerramos si la conexión llegó a abrirse
        if conn:
            await conn.close()


async def duplicate_schema(schema_name: str):
    """Duplica el Schema Plantilla para el nuevo inquilino en Postgres (Para tu app FastAPI)"""
    try:
        logger.info(f"Duplicando Schema de Postgres para: {schema_name}...")
        await init_schema(first_time=False, schema_name=schema_name)
        logger.info(f"Esquema de Postgres clonado perfectamente: {schema_name}")

    except Exception as e:
        logger.error(
            f"Fallo Crítico al crear el esquema en Postgres [{schema_name}]: {e}"
        )
        raise e
