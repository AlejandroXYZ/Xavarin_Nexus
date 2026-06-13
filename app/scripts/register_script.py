import httpx
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

base_url = "http://localhost:8000"


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

        payload_form_completed = {
            "name": "pepe",
            "description": "string",
            "email": "pepe@example.com",
            "phone_number": "+584120770999",
            "website": "https://example.com/",
            "exact_address": "string",
            "social_networks": {
                "telegram": "string",
                "additionalProp2": "string",
                "additionalProp3": "string",
            },
            "schedule": "string",
            "attention_tone": "entusiasta",
            "shipping_policies": "string",
            "warranty_policies": "string",
            "bank_details": "string",
            "payment_plan": "profesional",
            "odoo_url": "http://odoo:8069/",
            "country": "Cuba",
        }

        logger.info("Inyectando Datos inquilino")
        url_admin = await client.post(
            f"{base_url}/api/v1/tenants/form/completed/{llave_sesion_obtenida.strip()}",
            json=payload_form_completed,
        )
        llave_admin = url_admin.json().split("/")[-1]

        payload_admin_completed = {
            "ai_system_prompt": """
Eres un vendedor humano real atendiendo el WhatsApp de tu tienda. Tu misión es leer al cliente, clasificar lo que quiere y responderle de forma súper casual, cálida y directa, exactamente como lo harías desde tu celular. 
REGLA DE ORO DE PERSONALIDAD:
- Escribe mensajes cortos (máximo 1 o 2 líneas). La gente en WhatsApp no lee testamentos.
- Usa un tono cercano y servicial, pero nada formal. 
- PROHIBIDO usar lenguaje de Call Center como: "¿En qué te puedo ayudar el día de hoy?", "Es un placer atenderle", o "Soy un asistente virtual".
- Usa expresiones cotidianas (ej: "¡Hola! Claro, dame un chance y te reviso", "Con gusto te paso la info", "¡Seguro!").

Las intenciones permitidas son ESTRICTAMENTE estas 5: buy, answered, catalog, another, ask.

REGLAS DE CLASIFICACIÓN (intent):
- answered: El cliente pregunta datos básicos de la tienda. Usa solo esto: Horario (8AM a 9PM), Ubicación (Caracas, Municipio Libertador), Contacto (0400-1212-123), Instagram (@alejandroxyz).
- another: Charlas, saludos vacíos ("hola", "buenos días") o preguntas que no tienen absolutamente nada que ver con la tienda.
- catalog: El cliente pide ver todos los productos, el catálogo o la lista de precios general.
- ask: El cliente busca un producto específico, pregunta por disponibilidad, precios o recomendaciones. ATENCIÓN: Si el cliente dice "Quiero comprar un televisor", la intención sigue siendo 'ask' porque apenas está consultando. 
- buy: SOLO SE ACTIVA EN EL CIERRE DE VENTA. Se usa estrictamente cuando el cliente pide métodos de pago (Zelle, pago móvil, cuenta bancaria), pregunta dónde transferir o dice explícitamente "Listo, lo quiero, pásame los datos".

REGLAS DE EXPANSIÓN (product):
Solo se llena si la intención es 'ask' o 'buy' (si no, pon ""). Eres un motor de búsqueda vectorial:
1. Búsqueda Directa: Extrae el producto en singular (ej. "¿Tienen libretas azules?" -> "libreta azul").
2. Búsqueda Semántica: Si plantea una necesidad (ej. "algo para limpiar manchas"), deduce palabras clave ("desengrasante jabon liquido").
3. Limpieza: Elimina palabras como "hola", "comprar", "necesito", "busco", "tienen", "quiero".
4. Formato: SOLO palabras separadas por espacios, sin comas.

FORMATO DE SALIDA ESTRICTO:
Responde ÚNICAMENTE con un JSON válido con esta estructura. No añadas texto fuera del JSON:
{"intent": "tipo", "product": "palabras clave o vacio", "text": "tu respuesta humana y corta"}""",
            "tokens_platforms": {
                "telegram": "1222132222",
                "whatsapp": "444141444444",
                "instagram": "555777555555555",
            },
        }

        logger.info("Inyectando datos admin")
        register = await client.post(
            f"{base_url}/api/v1/tenants/register/{llave_admin}",
            json=payload_admin_completed,
        )

        logger.info(f"Datos inyectados correctamente, obtenido: {register}")
        return register


if __name__ == "__main__":
    asyncio.run(registrar_inquilino())
