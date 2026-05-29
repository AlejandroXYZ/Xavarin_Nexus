from cryptography.fernet import Fernet
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
