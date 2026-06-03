import logging
import os
from fastapi import HTTPException, status

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def duplicate_schema(db, schema_name: str):
    """Duplica el Schema Plantilla para el nuevo inquilino en Postgres"""

    safe_schema = f'"{schema_name}"'

    try:
        logger.info(f"Duplicando Schema de Postgres para: {schema_name}...")

        await db.execute(f"CREATE SCHEMA IF NOT EXISTS {safe_schema};")

        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {safe_schema}.catalog (
                id_odoo INTEGER PRIMARY KEY, 
                name TEXT NOT NULL,
                description TEXT,
                semantics TEXT,
                price NUMERIC(12,2) DEFAULT 0.00,
                stock NUMERIC(12,2) DEFAULT 0.00,
                embedding VECTOR(384),
                conversions JSONB DEFAULT '{{}}'::jsonb,
                metadata JSONB DEFAULT '{{}}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS catalog_embedding_idx 
            ON {safe_schema}.catalog 
            USING hnsw (embedding vector_cosine_ops);

            CREATE INDEX IF NOT EXISTS catalog_name_idx 
            ON {safe_schema}.catalog(name);
        """)

        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {safe_schema}.clients (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ,
                platform TEXT NOT NULL,
                platform_user TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','waiting_for_sale','waiting_for_support')),
                metadata JSONB DEFAULT '{{}}'::jsonb
            );

            CREATE INDEX IF NOT EXISTS clients_name_idx ON {safe_schema}.clients(name);
            CREATE INDEX IF NOT EXISTS clients_platform_idx ON {safe_schema}.clients(platform);
            CREATE INDEX IF NOT EXISTS clients_status_idx ON {safe_schema}.clients(status);
        """)

        logger.info(f"Esquema de Postgres clonado perfectamente: {schema_name}")

    except Exception as e:
        logger.error(
            f"Fallo Crítico al crear el esquema en Postgres [{schema_name}]: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
