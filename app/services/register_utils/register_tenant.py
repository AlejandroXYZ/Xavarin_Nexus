import logging
from app.schemas.register import RegisterData
from datetime import datetime, timedelta
import json
from app.clients.odoo_jsonrpc import ejecutar_odoo

logger = logging.getLogger(__name__)

fecha_actual = datetime.now()
siguiente_mes = fecha_actual + timedelta(days=30)


async def registrar_tenant(
    data: RegisterData,
    db,
    schema_name: str,
    odoo,
    odoo_url,
    odoo_bot_user_id,
    odoo_bot_api_key,
    options: dict | None = None,
    features: str | None = None,
    metadata: dict | None = None,
) -> int:
    """Registra al inquilino en la tabla tenants"""
    try:
        logger.info("Obteniendo partner_id")
        partner_id = await ejecutar_odoo(
            http_client=odoo,
            odoo_url=odoo_url,
            db=schema_name,
            uid=odoo_bot_user_id,
            api_key=odoo_bot_api_key,
            modelo="res.users",
            metodo="read",
            args=[2],
            kwargs={"fields": ["partner_id"]},
        )

        id_tenant = await db.fetchval(
            "INSERT INTO tenants (name,expiry_date,phone_number,email,schema_name,ai_system_prompt,status,country,social_networks,options,features,metadata,description,payment_plan,partner_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15) RETURNING id",
            data.name,
            siguiente_mes,
            data.phone_number,
            data.email,
            schema_name,
            data.ai_system_prompt,
            "activo",
            data.country,
            json.dumps(data.social_networks),
            options,
            features,
            metadata,
            data.description,
            data.payment_plan,
            partner_id[0]["partner_id"][0],
        )
        logger.info(
            f"Registrado inquilino {data.name} correctamente en la tabla tenants"
        )

        return id_tenant

    except Exception as e:
        logger.error(f"Error insertando tenant en base de datos: {e}")
        raise e
