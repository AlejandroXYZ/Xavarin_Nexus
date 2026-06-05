from arq.connections import RedisSettings
import logging
import json
from app.ia.product_embedding import vector
import asyncpg
import os
import dotenv
import re

logger = logging.getLogger(__name__)
dotenv.load_dotenv()

LIMITE_PETICIONES_A_EJECUTAR = 500


def limpiar_html(texto_bruto: str) -> str:
    """Elimina las etiquetas HTML de un texto proveniente de Odoo"""
    if not texto_bruto:
        return ""
    texto_limpio = re.sub(r"<[^>]+>", " ", texto_bruto)
    return " ".join(texto_limpio.split())


async def actualizar_inventario_odoo(ctx, tenant: str):
    """Actualiza la tabla Catalog del schema del inquilino cuando el inquilino añade o actualiza un producto en su inventario de Odoo"""
    cliente_redis = ctx["redis"]
    db = ctx["db_pool"]

    llave_sala = f"sala_espera_vectores:{tenant}"

    productos_crudos = await cliente_redis.lrange(llave_sala, 0, -1)

    if not productos_crudos:
        return "lote vacio"

    await cliente_redis.delete(llave_sala)

    lote_productos = [json.loads(p) for p in productos_crudos]
    total_productos = len(lote_productos)
    logger.info(f"Lote de Productos pasados: {lote_productos[:10]}")

    logger.info(
        f"Lote Listo, Generando vectores para {len(lote_productos)} para {tenant}"
    )

    for p in lote_productos:
        p["description"] = limpiar_html(p.get("description", ""))

    for i in range(0, total_productos, LIMITE_PETICIONES_A_EJECUTAR):
        bloque_actual = lote_productos[i : i + LIMITE_PETICIONES_A_EJECUTAR]

        textos_a_vectorizar = [
            f"{p['name']} - {p['description']}" for p in bloque_actual
        ]
        vectores = vector(textos_a_vectorizar)
        datos_para_postgres = []

        for producto, embedding in zip(bloque_actual, vectores):
            embedding = str(embedding.tolist())
            fila = (
                producto["id"],
                producto["name"],
                producto.get("description", ""),
                producto.get("qty_available", 0.0),
                producto.get("list_price", 0.0),
                embedding,
            )
            datos_para_postgres.append(fila)

        query = f"""
            INSERT INTO {tenant}.catalog (id_odoo, name, description,stock,price, embedding)
            VALUES ($1, $2, $3, $4, $5, $6)
            
            ON CONFLICT (id_odoo) 
            DO UPDATE SET 
                name = EXCLUDED.name,
                price = EXCLUDED.price,
                embedding = EXCLUDED.embedding;
        """

        await db.executemany(query, datos_para_postgres)

    return f"Guardados/Actualizados {len(lote_productos)} productos en Postgres"


async def startup(ctx):
    """Se ejecuta 1 sola vez cuando el Worker arranca"""
    logger.info("Iniciando Worker y conectando a Postgres...")

    db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/mi_db")
    ctx["db_pool"] = await asyncpg.create_pool(db_url, min_size=5, max_size=20)

    logger.info("Worker listo y conectado a la base de datos.")


async def shutdown(ctx):
    """Se ejecuta cuando se apaga el worker"""
    logger.info("Apagando Worker y cerrando conexiones de Postgres...")
    await ctx["db_pool"].close()


class WorkerSettings:
    redis_settings = RedisSettings(host="redis", port=6379)

    on_startup = startup
    on_shutdown = shutdown
    functions = [actualizar_inventario_odoo]
    max_jobs = 10
    job_timeout = 60
