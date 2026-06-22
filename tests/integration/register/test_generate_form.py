import pytest
from tests.validators.url_validator import validar_url


@pytest.mark.asyncio
async def test_generar_enlace_formulario_inquilino(testclient):
    tenant = "ferreteria_Carlos"

    response = await testclient.post(f"/api/v1/tenants/form/url_generate?name={tenant}")
    tenant_url = response.json()
    assert response.status_code == 201
    assert validar_url(tenant_url)
