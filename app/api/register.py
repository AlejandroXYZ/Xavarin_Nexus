from fastapi import APIRouter, Depends, status
from app.security.x_api_key import verificar_api
from app.schemas.register import Form
import logging

logger = logging.getLogger(__name__)

register_router = APIRouter(
    prefix="/api/v1/tenants", tags=["register"], dependencies=Depends(verificar_api)
)


@register_router.post("/register", status_code=status.HTTP_201_CREATED)
async def tenants_register(data: Form):
    """
    Registra a los nuevos inquilinos
    """
    try:
        
    except Exception as e:
        raise e
