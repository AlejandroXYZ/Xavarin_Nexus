from pydantic import BaseModel
from typing import Optional, Union


class IA_answer(BaseModel):
    product: Optional[Union[str, bool]] = None
    intent: str
    text: Optional[Union[str, bool]] = None
    answer: Optional[str] = None


class Message(BaseModel):
    platform: str
    id_shop: int
    customer_id: int
    customer_name: str
    text: str
