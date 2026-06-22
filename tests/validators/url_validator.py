from pydantic import TypeAdapter, HttpUrl


def validar_url(url: str) -> bool:
    try:
        TypeAdapter(HttpUrl).validate_python(url)
        return True
    except Exception:
        return False
