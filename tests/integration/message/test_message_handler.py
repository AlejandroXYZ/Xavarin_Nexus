import pytest
from app.translators.whatsaap import whatsapp_translator
from tests.payloads.whatsapp.message import payload_whatsaap_message
from app.security.x_api_key import verificar_api
from main import app
from faker import Faker
import json
from unittest.mock import patch, AsyncMock


@patch("app.services.message_handler.groq", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_prueba_mensajes_entrantes_de_clientes(mock_groq, testclient, redisfake):
    tenant_db = "testing"
    endpoint = f"/api/v1/message/{tenant_db}/whatsapp"
    message_object = payload_whatsaap_message()
    payload_whatsaap = message_object.model_dump_json(by_alias=True)
    message_translated = whatsapp_translator(json.loads(payload_whatsaap))

    def verificar_apí_mock():
        return True

    app.dependency_overrides[verificar_api] = verificar_apí_mock

    mock_groq.return_value = {
        "intent": "answered",
        "product": "",
        "text": "Estamos ubicados en Venezuela",
    }
    fake = Faker(locale="es_ES")

    payload = {
        "name": fake.name(),
        "description": fake.text(),
        "email": fake.email(),
        "phone_number": fake.phone_number(),
        "website": fake.uri(),
        "exact_address": fake.address(),
        "social_networks": {"social1": "instagram"},
        "attention_tone": "formal",
        "payment_plan": "basico",
        "odoo_url": fake.uri(),
        "country": fake.country(),
        "tokens_platforms": {
            "telegram": fake.random_number(fix_len=True, digits=10),
            "whatsapp": fake.random_number(fix_len=True, digits=10),
        },
        "ai_system_prompt": "Hola",
    }
    payload_sanitizado = json.dumps(payload, default=str)
    llave = f"cache:{tenant_db}"
    await redisfake.set(llave, payload_sanitizado)
    llave_cache_client = (
        f"history:client:whatsapp:{message_translated.platform_user_id}"
    )
    cache_client_data = [{"ia_is_active": True}]
    await redisfake.set(llave_cache_client, json.dumps(cache_client_data))

    response = await testclient.post(endpoint, json=json.loads(payload_whatsaap))
    datos_obtenidos = response.json()

    assert response.status_code == 200
    assert datos_obtenidos["status"] == "sucess"
    assert isinstance(datos_obtenidos["answer"], dict)
    assert datos_obtenidos["answer"]["status"] == "sucess"
    assert datos_obtenidos["answer"]["intent"] == "answered"
