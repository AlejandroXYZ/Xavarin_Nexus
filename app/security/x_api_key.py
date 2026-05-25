import os
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException, status


api_key_headers = os.getenv("API_KEY_HEADERS", "api")
x_api_key = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def verificar_api(api_recibida: str = Security(x_api_key)):
    if api_recibida == api_key_headers:
        return api_recibida
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
