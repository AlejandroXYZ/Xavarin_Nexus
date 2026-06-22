import fakeredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app
import fakeredis.aioredis as redis
from unittest.mock import AsyncMock
import os
import asyncpg
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta, datetime
import json

RAIZ = Path(__file__).parent.parent
RUTA_ENV = RAIZ / ".env"
load_dotenv(dotenv_path=RUTA_ENV, override=True)

from app.scripts.register_payloads.payload_admin_completed import (
    payload_admin_completed_dict,
)
from app.scripts.register_payloads.payload_form_data import payload_form_completed_dict


fecha_actual = datetime.now()
siguiente_mes = fecha_actual + timedelta(days=30)
baseurl = RAIZ / "app" / "sql"

user = os.getenv("NEW_USER_DB", "postgres")
host = "localhost"
password = os.getenv("NEW_PASSWORD_DB", "mi_db")
database = os.getenv("NEW_DB", "mi_db")

print("\n" + "=" * 50)
print(f"Buscando archivo .env en: {RUTA_ENV}")
print(f"¿El archivo .env existe físicamente?: {RUTA_ENV.exists()}")
print(f"Credenciales finales -> USER: {user} | PASS: {password}")
print("=" * 50 + "\n")


async def create_test_db(conn, owner: str):
    schema_name = "testing"
    await conn.execute(f"""CREATE DATABASE tests OWNER {owner};""")
    await conn.close()
    new_conn = await asyncpg.connect(
        user=user, host=host, database="tests", password=password
    )
    async with new_conn.transaction():
        archivo_sql = baseurl / "init_public.sql"
        query = archivo_sql.read_text(encoding="utf-8")
        await new_conn.execute(query)
        await new_conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        tenant_sql = baseurl / "init_tenant.sql"
        query_tenant = tenant_sql.read_text(encoding="utf-8")
        query_tenant = query_tenant.format(schema_name=schema_name)
        await new_conn.execute(query_tenant)
        data_tenant = payload_form_completed_dict
        data_admin = payload_admin_completed_dict
        await new_conn.fetchval(
            """INSERT INTO tenants (
        name,
        expiry_date,
        phone_number,
        email,
        schema_name,
        ai_system_prompt,
        status,
        country,
        social_networks,
        description,
        payment_plan,
        partner_id) 
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        RETURNING id""",
            data_tenant["name"],
            siguiente_mes,
            data_tenant["phone_number"],
            data_tenant["email"],
            data_tenant["name"],
            data_admin["ai_system_prompt"],
            "activo",
            data_tenant["country"],
            json.dumps(data_tenant["social_networks"]),
            data_tenant["description"],
            data_tenant["payment_plan"],
            2,
        )

    return new_conn


@pytest_asyncio.fixture(autouse=True)
def variables_entorno_prueba(monkeypatch):
    monkeypatch.setenv("BASEURL", "http://localhost:8000")


@pytest_asyncio.fixture
async def redisfake():
    fake_server = fakeredis.FakeServer()
    redis_mock = await redis.FakeRedis(server=fake_server)
    yield redis_mock
    await redis_mock.aclose()


@pytest_asyncio.fixture
async def db_connection_test():
    conn = await asyncpg.connect(
        user=user, password=password, host=host, database=database
    )
    db_exists = await conn.fetchval(
        """SELECT 1 FROM pg_database WHERE datname = 'tests' """
    )
    if not db_exists:
        test_db = await create_test_db(conn, user)
    else:
        await conn.close()
        test_db = await asyncpg.connect(
            user=user, host=host, database="tests", password=password
        )
    tr = test_db.transaction()

    await tr.start()
    try:
        yield test_db
    finally:
        await tr.rollback()
        await test_db.close()


@pytest_asyncio.fixture
async def testclient(redisfake, db_connection_test):
    app.state.db = db_connection_test
    app.state.redis = redisfake
    app.state.arq_pool = AsyncMock()
    app.state.http_client = AsyncMock()
    transport = ASGITransport(app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
        app.dependency_overrides.clear()
