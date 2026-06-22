from pydantic import BaseModel, Field, HttpUrl, EmailStr
from enum import Enum
from typing import Annotated
from pydantic_extra_types.phone_numbers import PhoneNumberValidator


class Planes(str, Enum):
    BASICO = "basico"
    PROFESIONAL = "profesional"
    ENTERPRISE = "enterprise"


class Tonos_IA(str, Enum):
    ENTUSIASTA = "entusiasta"
    FORMAL = "formal"
    AMABLE = "amable"


class Form(BaseModel):
    """
    Datos para nuevos inquilinos, se usa para el llenado del formulario y registro en Postgres
    """

    name: str = Field(title="Nombre Comercial Exacto")
    description: str = Field(title="Descripcion")
    email: EmailStr = Field(title="Correo Electronico")
    phone_number: Annotated[str, PhoneNumberValidator(number_format="E164")] = Field(
        title="Numero Telefónico"
    )
    website: HttpUrl | None = Field(default=None, title="Sitio Web del Inquilino")
    exact_address: str | None = Field(
        default=None, title="Ubicación Física de la Empresa Inquilina"
    )
    social_networks: dict[str, str] | None = Field(title="Redes Sociales", default=None)
    schedule: str | None = Field(title="Horarios de Atención", default=None)
    attention_tone: Tonos_IA = Field(
        title="Tonos de Atencion IA", default=Tonos_IA.ENTUSIASTA
    )
    shipping_policies: str | None = Field(title="Politicas de envío", default=None)
    warranty_policies: str | None = Field(
        title="Politicas de Garantías y Devoluciones", default=None
    )
    bank_details: str | None = Field(title="Datos Bancarios", default=None)
    payment_plan: Planes = Field(title="Plan de Pago", default=Planes.BASICO)
    odoo_url: HttpUrl | None = Field(
        title="URL de odoo de la empresa",
        description="Se crea la URL automáticamente su la empresa no posee su propia URL",
        default=None,
    )
    country: str = Field(title="Pais de la Empresa")


class FormAdmin(BaseModel):
    """Esquema para Formulario de Admin"""

    ai_system_prompt: str = Field(
        title="Prompt Maestro para la INteligencia Artificial"
    )
    tokens_platforms: dict[str, str] = Field(title="Tokens para plataformas")


class RegisterData(BaseModel):
    """Datos Completos de los formularios"""

    name: str = Field(title="Nombre Comercial Exacto")
    description: str = Field(title="Descripcion")
    email: EmailStr = Field(title="Correo Electronico")
    phone_number: Annotated[str, PhoneNumberValidator(number_format="E164")] = Field(
        title="Numero Telefónico"
    )
    website: HttpUrl | None = Field(default=None, title="Sitio Web del Inquilino")
    exact_address: str | None = Field(
        default=None, title="Ubicación Física de la Empresa Inquilina"
    )
    social_networks: dict[str, str] | None = Field(title="Redes Sociales", default=None)
    schedule: str | None = Field(title="Horarios de Atención", default=None)
    attention_tone: Tonos_IA = Field(
        title="Tonos de Atencion IA", default=Tonos_IA.ENTUSIASTA
    )
    shipping_policies: str | None = Field(title="Politicas de envío", default=None)
    warranty_policies: str | None = Field(
        title="Politicas de Garantías y Devoluciones", default=None
    )
    bank_details: str | None = Field(title="Datos Bancarios", default=None)
    payment_plan: Planes = Field(title="Plan de Pago", default=Planes.BASICO)
    odoo_url: HttpUrl | None = Field(
        title="URL de odoo de la empresa",
        description="Se crea la URL automáticamente su la empresa no posee su propia URL",
        default=None,
    )
    country: str = Field(title="Pais de la Empresa")
    ai_system_prompt: str = Field(
        title="Prompt Maestro para la INteligencia Artificial"
    )
    tokens_platforms: dict[str, str] = Field(title="Tokens para plataformas")
