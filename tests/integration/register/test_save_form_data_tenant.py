import pytest
from faker import Faker
from tests.validators.url_validator import validar_url
import json


@pytest.mark.asyncio
async def test_save_form_data_tenant_received(testclient, redisfake):
    llave_sesion = "test:cache"

    await redisfake.set(
        llave_sesion,
        "1234567890",
    )
    endpoint = f"/api/v1/tenants/form/completed/{llave_sesion}"

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
    }
    payload_sanitizado = json.loads(json.dumps(payload, default=str))

    data = await testclient.post(endpoint, json=payload_sanitizado)
    url_obtenida_admin = data.json()

    assert validar_url(url_obtenida_admin)
    assert data.status_code == 202
