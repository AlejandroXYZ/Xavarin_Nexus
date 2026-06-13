def format_html(textos: list, mensaje_ia: str):
    """Prepara el texto para inyectarlo en el chat de Odoo"""
    transcripcion_html = "<h3>Resumen de la IA:</h3><hr>"
    for msg in textos:
        if msg["role"] == "system":
            continue
        remitente = "Cliente" if msg["role"] == "user" else "BOT IA"
        color = "blue" if remitente == "Cliente" else "green"
        transcripcion_html += (
            f"<p><b style='color:{color}'>{remitente}:</b> {msg['content']}</p>"
        )

    transcripcion_html += (
        f"<hr><p><b style='color: green'> BOT IA:</b> {mensaje_ia} </p><hr>"
    )
    transcripcion_html += "<hr><p><i>El cliente requiere atención humana.</i></p>"
