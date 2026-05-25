from cryptography.fernet import Fernet
import os

llave_encriptada = os.getenv("ENCRYPTION_KEY", "string")
encrypter = Fernet(llave_encriptada.encode())


def encriptar(token: str) -> str:
    token_bytes = token.encode("utf-8")
    token_encriptado = encrypter.encrypt(token_bytes)
    return token_encriptado.decode("utf-8")


def desencriptar(token: str) -> str:
    token_bytes = token.encode("utf-8")
    token_encriptado = encrypter.decrypt(token_bytes)
    return token_encriptado.decode("utf-8")
