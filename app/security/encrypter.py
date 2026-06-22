from cryptography.fernet import Fernet
import json
import os

llave_encriptada = os.getenv(
    "ENCRYPTION_KEY", "u4b-Z6Xv8zN_8m1V7p2pXzW4Kz7-u_fV7p2pXzW4Kz4="
)
encrypter = Fernet(llave_encriptada.encode())


def encriptar(token: str) -> str:
    token = str(token)
    token_bytes = token.encode("utf-8")
    token_encriptado = encrypter.encrypt(token_bytes)
    return token_encriptado.decode("utf-8")


def desencriptar(token: str) -> str:
    token = str(token)
    token_bytes = token.encode("utf-8")
    token_desencriptado = encrypter.decrypt(token_bytes)
    return token_desencriptado.decode("utf-8")


def preparar_tokens_para_db(tokens: dict[str, str], accion: str) -> str:
    """
    Recibe un diccionario con los tokens planos y devuelve un JSON string
    donde solo los valores están encriptados.
    """
    tokens_listos = {}

    if accion == "encriptar":
        for plataforma, token in tokens.items():
            if token:
                token_bytes = token.encode("utf-8")
                token_cifrado = encrypter.encrypt(token_bytes).decode("utf-8")
                tokens_listos[plataforma] = token_cifrado
            else:
                tokens_listos[plataforma] = None
        return json.dumps(tokens_listos)
    elif accion == "desencriptar":
        for plataforma, token in tokens.items():
            if token:
                token_bytes = token.encode("utf-8")
                token_desencriptado = encrypter.decrypt(token_bytes).decode("utf-8")
                tokens_listos[plataforma] = token_desencriptado
            else:
                tokens_listos[plataforma] = None
        return json.dumps(tokens_listos)
