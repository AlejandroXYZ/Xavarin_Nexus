import httpx
import asyncio
import logging
from app.scripts.register_payloads.payload_admin_completed import (
    payload_admin_completed_dict,
)
from app.scripts.register_payloads.payload_form_data import payload_form_completed_dict
import os


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

base_url = os.getenv("URL_API_BASE", "http://localhost:8000")


async def registrar_inquilino():
    async with httpx.AsyncClient(timeout=30.0) as client:
        name = "xavarin"

        # Peticion para que Redis cree el enlace y el token de sesion
        logger.info("Creando Enlace inquilino")
        url_tenant_register = await client.post(
            f"{base_url}/api/v1/tenants/form/url_generate?name={name}",
        )
        llave_sesion_obtenida = url_tenant_register.json()
        llave_sesion_obtenida = llave_sesion_obtenida.split("/")[-1]

        payload_form_completed_var = payload_form_completed_dict
        logger.info("Inyectando Datos inquilino")
        url_admin = await client.post(
            f"{base_url}/api/v1/tenants/form/completed/{llave_sesion_obtenida.strip()}",
            json=payload_form_completed_var,
        )
        llave_admin = url_admin.json().split("/")[-1]

        payload_admin_completed_var = payload_admin_completed_dict
        logger.info("Inyectando datos admin")
        register = await client.post(
            f"{base_url}/api/v1/tenants/register/{llave_admin}",
            json=payload_admin_completed_var,
        )

        logger.info(f"Datos inyectados correctamente, obtenido: {register}")
        return register


if __name__ == "__main__":
    asyncio.run(registrar_inquilino())
