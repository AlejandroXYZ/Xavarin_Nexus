from app.schemas.register import Form
from fastapi import HTTPException, status as status_code
import logging

logger = logging.getLogger(__name__)


async def registrar_tenant(
    data: Form,
    db,
    schema_name: str,
    ai_system_prompt: str,
    status: str | None = None,
    options: dict | None = None,
    features: dict | None = None,
    metadata: dict | None = None,
    timezone: str | None = None,
) -> int:
    """Registra al inquilino en la tabla tenants"""
    try:
        id_tenant = await db.fetchval(
            "INSERT INTO tenants (name,expiry_date,phone_number,email,schema_name,ai_system_prompt,status,timezone,social_networks,options,features,metadata) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING id",
            data.name,
            "2028-05-28 15:30:00-04",
            data.phone_number,
            data.email,
            schema_name,
            ai_system_prompt,
            status,
            timezone,
            data.social_networks,
            options,
            features,
            metadata,
        )
        logger.info(
            f"Registrado inquilino {data.name} correctamente en la tabla tenants"
        )

        return id_tenant

    except Exception as e:
        HTTPException(
            status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}"
        )
