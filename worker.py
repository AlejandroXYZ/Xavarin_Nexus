from arq import Retry
from arq.connections import RedisSettings
import logging
import json
from app.ia.product_embedding import vector
import asyncpg
import os
import dotenv
import re
import httpx
from app.schemas.message import Message
from app.services.message_handler import message_handler_func
from app.security.errors_catcher import manual_handling

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)
dotenv.load_dotenv()

LIMITE_PETICIONES_A_EJECUTAR = 500

tiempos_de_intentos = {1: 60, 2: 300, 3: 600}


async def catch_pending_try_messages(
    ctx,
    llave: str,
    platform,
    tenant_db,
):
    """Se ejecuta cada minuto para procesar mensajes tipo pending_try (mensajes no procesados correctamente)"""
    intentos_actuales = ctx["job_try"]
    redis = ctx["redis"]
    logger.info(
        f"Worker procesando mensaje (Intento #{intentos_actuales}) para {tenant_db}"
    )

    message_redis = await redis.hget(llave, "message")
    if not message_redis:
        logger.error(
            "No se pudo obtener el mensaje en Redis, posiblemente fue eliminado"
        )
        return {"status": "error", "detail": "Mensaje no encontrado en Caché"}
    message = json.loads(message_redis.decode("utf-8"))
    message = Message(**message)

    try:
        await message_handler_func(
            message=message,
            tenant_db=tenant_db,
            platform=platform,
            db=ctx["db_pool"],
            redis=redis,
            odoo=ctx["http_client"],
            arq=ctx["redis"],
        )
        logger.info(f"Reintento exitoso para {tenant_db}")
    except Exception as e:
        if intentos_actuales >= 4:
            logger.critical(
                f"Limite de Reintentos alcanzados, llevando a intervencion manual: {e}"
            )
            await manual_handling(
                message=message,
                tenant_db=tenant_db,
                db=ctx["db_pool"],
                odoo=ctx["http_client"],
                redis=redis,
            )

        segundos_espera = tiempos_de_intentos.get(intentos_actuales, 60)
        logger.warning(
            f"Reencolando tarea en Redis. Se reintentará en {segundos_espera} segundos."
        )
        raise Retry(defer=segundos_espera)


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
        logger.info("Lote Vacío")
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
            INSERT INTO "{tenant}".catalog (id_odoo, name, description,stock,price, embedding)
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
    ctx["http_client"] = httpx.AsyncClient(
        timeout=15.0,
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
    )

    logger.info("Worker listo y conectado a la base de datos.")


async def shutdown(ctx):
    """Se ejecuta cuando se apaga el worker"""
    logger.info("Apagando Worker y cerrando conexiones de Postgres...")
    await ctx["db_pool"].close()
    await ctx["http_client"].aclose()


class WorkerSettings:
    redis_settings = RedisSettings(host="redis", port=6379)

    on_startup = startup
    on_shutdown = shutdown
    functions = [actualizar_inventario_odoo, catch_pending_try_messages]
    max_jobs = 10
    job_timeout = 60
