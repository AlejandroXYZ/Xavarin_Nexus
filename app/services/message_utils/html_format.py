import logging
import json
import re

logger = logging.getLogger(__name__)


def format_html(textos: list):
    """Prepara el texto para inyectarlo en el chat de Odoo"""
    transcripcion_html = "<h3>Resumen de la IA:</h3><hr>"
    for msg in textos:
        if msg["role"] == "system":
            continue

        remitente = "Cliente" if msg["role"] == "user" else "BOT IA"
        color = "blue" if remitente == "Cliente" else "green"

        contenido = msg["content"]

        if remitente == "BOT IA":
            if isinstance(contenido, str):
                try:
                    # Intenta leerlo como JSON
                    datos_json = json.loads(contenido)
                    if isinstance(datos_json, dict):
                        contenido = datos_json.get("text", contenido)
                except ValueError:
                    # Si explota, es texto plano normal. Lo dejamos quieto.
                    pass
            elif isinstance(contenido, dict):
                # Por si acaso la base de datos ya lo devolvió como diccionario
                contenido = contenido.get("text", str(contenido))

        transcripcion_html += (
            f"<p><b style='color:{color}'>{remitente}:</b> {contenido}</p>"
        )

    transcripcion_html += "<hr><p><i>El cliente requiere atención humana.</i></p>"
    return transcripcion_html


def limpiar_html(texto_html: str):
    """Elimina etiquetas HTML utilizando expresiones regulares"""
    patron = re.compile(r"<[^>]+>")
    return patron.sub("", texto_html).strip()
