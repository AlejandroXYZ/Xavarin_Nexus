import os
from contextlib import asynccontextmanager
import asyncpg
import logging
from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

user = os.getenv("POSTGRES_USER", "user")
host = os.getenv("HOST", "db")
password = os.getenv("POSTGRES_PASSWORD", "123456")
database = "postgres"

new_user = os.getenv("NEW_USER_DB", "fastapi")
new_password = os.getenv("NEW_PASSWORD_DB", "123")
new_db = os.getenv("NEW_DB", "db")


async def init_db():
    """Función que crea las bases de datos base de todo el sistema al iniciar"""
    conn = None
    try:
        logger.info("Conectando como Admin en Postgres para preparar entorno")
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

        # Conectando como admin en la nueva DB para activar la extension de vectores
        #
        conn = await asyncpg.connect(
            host=host, user=user, password=password, database=new_db
        )
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.close()

        # Conectando como nuevo usuario creado en la nueva DB
        logger.info(f"Configurando esquema en {new_db}")
        conn = await asyncpg.connect(
            host=host, user=new_user, password=new_password, database=new_db
        )

        # Creando la tabla Tenants
        #
        await conn.execute("""CREATE TABLE IF NOT EXISTS tenants (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'esperando_agencia' CHECK (status IN ('activo','suspendido','prueba','esperando_agencia' )),
        expiry_date TIMESTAMPTZ NOT NULL, 
        phone_number TEXT UNIQUE NOT NULL, 
        email TEXT UNIQUE NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL ,
        updated_at TIMESTAMPTZ,
        country TEXT,
        social_networks JSONB DEFAULT '{}'::jsonb,
        options JSONB DEFAULT '{}'::jsonb,
        features JSONB DEFAULT '{}'::jsonb,
        schema_name TEXT UNIQUE NOT NULL,
        ai_system_prompt TEXT NOT NULL,
        metadata JSONB DEFAULT '{}'::jsonb 
        );

        -- INDICES DE RENDIMIENTO
        CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

        -- INDICES PARA JSON
        CREATE INDEX IF NOT EXISTS idx_tenants_features ON tenants USING GIN (features);
        CREATE INDEX IF NOT EXISTS idx_tenants_options ON tenants USING GIN (options);
        CREATE INDEX IF NOT EXISTS idx_tenants_metadata ON tenants USING GIN (metadata);
        """)

        # Creación de la Tabla Credentials
        #
        await conn.execute("""CREATE TABLE IF NOT EXISTS credentials (
        tenant_id UUID PRIMARY KEY,
        odoo_url TEXT UNIQUE,
        odoo_db TEXT UNIQUE,
        odoo_bot_user TEXT,
        odoo_bot_api_key TEXT UNIQUE,
        tokens_platforms JSONB DEFAULT '{}'::jsonb,
        metadata JSONB DEFAULT '{}'::jsonb,

        CONSTRAINT credentials_tenants 
            FOREIGN KEY (tenant_id) 
            REFERENCES tenants(id) 
            ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_credentials_tokens ON credentials USING GIN (tokens_platforms);
        CREATE INDEX IF NOT EXISTS idx_credentials_metadata ON credentials USING GIN (metadata);
        """)

        # Creacion de Schema_Plantilla para nuevos inquilinos

        await conn.execute("""CREATE SCHEMA IF NOT EXISTS tenant_schema_template""")

        # Creacion Tabla Catalog
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_schema_template.catalog (
                id_odoo INTEGER PRIMARY KEY, 
                name TEXT NOT NULL,
                description TEXT,
                semantics TEXT,
                price NUMERIC(12,2) DEFAULT 0.00,
                stock NUMERIC(12,2) DEFAULT 0.00,
                embedding VECTOR(384),
                conversions JSONB DEFAULT '{}'::jsonb,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
                -- Métrica del Coseno (vector_cosine_ops) para modelos de embeddings
                CREATE INDEX IF NOT EXISTS idx_catalog_embedding 
                ON tenant_schema_template.catalog 
                USING hnsw (embedding vector_cosine_ops);

                -- Índice para búsquedas rápidas por nombre
                CREATE INDEX IF NOT EXISTS idx_catalog_name ON tenant_schema_template.catalog(name);
            """)

        await conn.execute("""CREATE TABLE IF NOT EXISTS tenant_schema_template.clients (
        id UUID PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ,
        platform TEXT NOT NULL,
        platform_user TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','waiting_for_sale','waiting_for_support')),
        metadata JSONB DEFAULT '{}'::jsonb);

        CREATE INDEX IF NOT EXISTS idx_clients_name ON tenant_schema_template.clients(name);
        CREATE INDEX IF NOT EXISTS idx_clients_platform ON tenant_schema_template.clients(platform);
        CREATE INDEX IF NOT EXISTS idx_clients_status ON tenant_schema_template.clients(status);

        """)

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
