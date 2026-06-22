import logging
import os
from app.clients.db import init_schema

logger = logging.getLogger(__name__)


async def duplicar_db_odoo(url: str, client, new_db_name: str) -> bool:
    """Duplica la DB Plantilla de Odoo para el nuevo inquilino"""
    try:
        url = f"{url}/web/database/duplicate"
        master_password = os.getenv("MASTER_PASSWORD", "passwd")
        odoo_db = os.getenv("DB", "db")

        form_data = {
            "master_pwd": master_password,
            "name": odoo_db,
            "new_name": new_db_name,
        }

        logger.info("Clonando DB de ODOO")
        response = await client.post(url, data=form_data, timeout=60.0)

        if response.status_code != 200 and response.status_code != 303:
            raise RuntimeError(
                f"Fallo al clonar Odoo. Código: {response.status_code}, código de respuesta no esperado"
            )

        logger.info("DB Clonada Perfectamente")
        return True

    except Exception as e:
        logger.error(f"Ha ocurrido un error mientras se duplicaba la db de Odoo: {e}")
        raise e


async def duplicate_schema(schema_name: str):
    """Duplica el Schema Plantilla para el nuevo inquilino en Postgres"""

    try:
        logger.info(f"Duplicando Schema de Postgres para: {schema_name}...")
        await init_schema(first_time=False, schema_name=schema_name)
        logger.info(f"Esquema de Postgres clonado perfectamente: {schema_name}")

    except Exception as e:
        logger.error(
            f"Fallo Crítico al crear el esquema en Postgres [{schema_name}]: {e}"
        )
        raise e
