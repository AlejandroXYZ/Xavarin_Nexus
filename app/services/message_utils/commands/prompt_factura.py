prompt = {
    "role": "system",
    "content": """
Analiza la siguiente conversación entre un cliente y un vendedor. El vendedor acaba de ordenar facturar. 
Tu tarea es extraer EXCLUSIVAMENTE los productos que el cliente acordó comprar con su nombre exacto y su cantidad. Devuelve únicamente un JSON con esta estructura:
{"items": [{"nombre_producto": "...", "cantidad": X},{"nombre_producto":"...", "cantidad": X}]}. Si no hay acuerdo claro, devuelve la lista vacía, cantidad es un numero entero""",
}
