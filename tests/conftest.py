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

RAIZ = Path(__file__).parent.parent
RUTA_ENV = RAIZ / ".env"

load_dotenv(dotenv_path=RUTA_ENV, override=True)


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
    baseurl = Path(__file__).parent
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
        tenant_sql = baseurl / "init_tenant.sql"
        query_tenant = tenant_sql.read_text(encoding="utf-8")
        query_tenant = query_tenant.format(schema_name=schema_name)
        await new_conn.execute(query_tenant)
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
    app.state.arq = AsyncMock()
    app.state.odoo = AsyncMock()
    transport = ASGITransport(app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
