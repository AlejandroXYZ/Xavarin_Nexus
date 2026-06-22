import logging
from app.schemas.message import Message
from app.clients.odoo_jsonrpc import ejecutar_odoo

logger = logging.getLogger(__name__)


async def register_client_db(
    db,
    mensaje: Message,
    schema_name: str,
    status: str,
    channel_id: int,
    tenant_cache_data: dict,
    http_client,
):
    """Guarda cliente en la DB"""

    logger.info(f"Guardando cliente {mensaje.user_name} en la tabla Clientes")
    try:
        partner_id = await get_partner_id_client(
            tenant_cache_data=tenant_cache_data,
            name_client=mensaje.user_name,
            platform_user_id=mensaje.platform_user_id,
            http_client=http_client,
            tenant_db=schema_name,
        )

        await db.execute(
            f"""
        INSERT INTO "{schema_name}".clients (name,platform,platform_user_id,status,channel_id,partner_id)
        VALUES ($1,$2,$3,$4,$5,$6) 
        ON CONFLICT (platform,platform_user_id)
        DO NOTHING;""",
            mensaje.user_name,
            mensaje.platform,
            str(mensaje.platform_user_id),
            status,
            channel_id,
            partner_id,
        )
        logger.info("Cliente {mensaje.user_name} registrado")

    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se registraba al cliente en la db: {e}"
        )
        raise e


async def get_partner_id_client(
    tenant_cache_data: dict,
    name_client: str,
    platform_user_id: str,
    http_client,
    tenant_db: str,
):
    """
    Busca si el cliente ya existe en Odoo por su teléfono. Si no existe, lo crea.
    """
    busqueda = await ejecutar_odoo(
        http_client=http_client,
        odoo_url=tenant_cache_data["odoo_url"],
        db=tenant_db,
        uid=tenant_cache_data["odoo_bot_user"],
        api_key=tenant_cache_data["odoo_bot_api_key"],
        modelo="res.partner",
        metodo="search",
        args=[[("phone", "=", platform_user_id)]],
    )

    if busqueda and len(busqueda) > 0:
        return busqueda[0]

    nuevo_partner_id = await ejecutar_odoo(
        http_client=http_client,
        odoo_url=tenant_cache_data["odoo_url"],
        db=tenant_db,
        uid=tenant_cache_data["odoo_bot_user"],
        api_key=tenant_cache_data["odoo_bot_api_key"],
        modelo="res.partner",
        metodo="create",
        args=[
            {
                "name": name_client,
                "phone": platform_user_id,
                "customer_rank": 1,
            }
        ],
    )
    return (
        nuevo_partner_id[0] if isinstance(nuevo_partner_id, list) else nuevo_partner_id
    )
