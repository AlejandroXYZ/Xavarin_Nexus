from pydantic import BaseModel, field_validator
from typing import Optional


class ProductoOdoo(BaseModel):
    id: int
    name: str
    list_price: float
    qty_available: float
    description: Optional[str] = None

    _action: Optional[str] = None
    _id: Optional[int] = None
    _model: Optional[str] = None

    @field_validator("description", mode="before")
    @classmethod
    def limpiar_falsos_de_odoo(cls, value):
        if value is False:
            return ""
        return value
