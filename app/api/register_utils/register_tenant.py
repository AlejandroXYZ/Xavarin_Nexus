from fastapi import HTTPException, status as status_code
import logging
from app.schemas.register import RegisterData
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

fecha_actual = datetime.now()
siguiente_mes = fecha_actual + timedelta(days=30)


async def registrar_tenant(
    data: RegisterData,
    db,
    schema_name: str,
    options: dict | None = None,
    features: str | None = None,
    metadata: dict | None = None,
) -> int:
    """Registra al inquilino en la tabla tenants"""
    try:
        id_tenant = await db.fetchval(
            "INSERT INTO tenants (name,expiry_date,phone_number,email,schema_name,ai_system_prompt,status,country,social_networks,options,features,metadata,description,payment_plan) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) RETURNING id",
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
        )
        logger.info(
            f"Registrado inquilino {data.name} correctamente en la tabla tenants"
        )

        return id_tenant

    except Exception as e:
        logger.error(f"Error insertando tenant en base de datos: {e}")
        raise HTTPException(
            status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
        )
