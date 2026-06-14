import logging
import json

logger = logging.getLogger(__name__)


def format_html(textos: list):
    """Prepara el texto para inyectarlo en el chat de Odoo"""
    transcripcion_html = "<h3>Resumen de la IA:</h3><hr>"
    for msg in textos:
        if msg["role"] == "system":
            continue
        remitente = "Cliente" if msg["role"] == "user" else "BOT IA"
        color = "blue" if remitente == "Cliente" else "green"
        if remitente == "BOT IA":
            contenido = json.loads(msg["content"])
            contenido = contenido.get("text", "")
            transcripcion_html += (
                f"<p><b style='color:{color}'>{remitente}:</b> {contenido}</p>"
            )
        else:
            transcripcion_html += (
                f"<p><b style='color:{color}'>{remitente}:</b> {msg['content']}</p>"
            )

    transcripcion_html += "<hr><p><i>El cliente requiere atención humana.</i></p>"
    return transcripcion_html
