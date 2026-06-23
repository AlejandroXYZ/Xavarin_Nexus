import logging
import os
from app.clients.db import init_schema

logger = logging.getLogger(__name__)


async def duplicar_db_odoo(new_db_name: str, db) -> bool:
    """
    Duplica la DB Plantilla de Odoo directamente en PostgreSQL
    para saltarse el bloqueo de seguridad web (list_db = False).
    """
    try:
        db_plantilla = os.getenv("DB", "db_plantilla_prod")

        logger.info(
            f"Clonando DB de ODOO vía Postgres: {db_plantilla} -> {new_db_name}"
        )

        await db.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_plantilla}'
            AND pid <> pg_backend_pid();
        """)

        await db.execute(
            f'CREATE DATABASE "{new_db_name}" WITH TEMPLATE "{db_plantilla}"'
        )

        logger.info(f"DB de Odoo '{new_db_name}' clonada perfectamente en Postgres.")
        return True

    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se duplicaba la db de Odoo en Postgres: {e}"
        )
        raise e


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

