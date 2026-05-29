from pydantic import BaseModel, Field, HttpUrl
# from pydantic_extra_types.phone_numbers import PhoneNumber


class Form(BaseModel):
    """
    Datos para nuevos inquilinos, se usa para el llenado del formulario y registro en Postgres
    """

    name: str = Field(title="Nombre Comercial Exacto")
    description: str = Field(title="Descripcion")
    email: str = Field(title="Correo Electronico")
    phone_number: str = Field(title="Numero Telefónico")
    website: HttpUrl | None = Field(default=None, title="Sitio Web del Inquilino")
    location: str | None = Field(
        default=None, title="Ubicación Física de la Empresa Inquilina"
    )
    social_networks: dict[str, str] | None = Field(title="Redes Sociales", default=None)
    schedule: str | None = Field(title="Horarios de Atención", default=None)
    attention_tone: str = Field(title="Tonos de Atencion IA")
    shipping_policies: str | None = Field(title="Politicas de envío", default=None)
    warranty_policies: str | None = Field(
        title="Politicas de Garantías y Devoluciones", default=None
    )
    bank_details: str | None = Field(title="Datos Bancarios", default=None)
    payment_plan: str = Field(title="Plan de Pago")
    odoo_url: HttpUrl | None = Field(
        title="URL de odoo de la empresa",
        description="Se crea la URL automáticamente su la empresa no posee su propia URL",
        default=None,
    )
