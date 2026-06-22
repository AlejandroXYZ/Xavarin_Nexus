from groq import AsyncGroq
import asyncio
import os
import logging
from dotenv import load_dotenv
import json

logger = logging.getLogger(__name__)
api_key = os.getenv("API_KEY_IA", "12121")
client = AsyncGroq(api_key=api_key)


async def groq(
    historial_mensajes: list[dict[str, str]],
) -> dict[str, str | bool | None]:
    try:
        if not api_key:
            logger.info("No se encuentra la API KEY en las variables de entorno")
            return {"status": False, "mensaje": "No se puede acceder a la IA"}

        messages = historial_mensajes

        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        contenido_crudo = response.choices[0].message.content
        try:
            answer = json.loads(contenido_crudo)
            logger.info(f"Respuesta de IA: {answer}")
            return answer
        except json.JSONDecodeError:
            logger.error(
                f"Groq no devolvió un JSON válido. Respuesta cruda: {contenido_crudo}"
            )
            return {
                "status": False,
                "mensaje": "Error en formato de respuesta",
                "raw": contenido_crudo,
            }

    except Exception as e:
        raise e


if __name__ == "__main__":
    asyncio.run(groq("hola", message="hola, quiero saber la dirección de su tienda"))
