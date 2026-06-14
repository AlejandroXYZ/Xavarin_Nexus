import re
import unicodedata
import uuid


def generar_nombre_esquema(nombre_empresa: str) -> str:
    """
    Transforma un nombre complejo en un identificador seguro para Bases de Datos.
    """

    texto = (
        unicodedata.normalize("NFKD", nombre_empresa)
        .encode("ASCII", "ignore")
        .decode("utf-8")
    )
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = texto.strip("_")
    sufijo_unico = str(uuid.uuid4())[:5]
    nombre_seguro = f"{texto[:40]}-{sufijo_unico}"

    return nombre_seguro
