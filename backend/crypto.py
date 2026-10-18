from services.crypto_service import encrypt_secret, decrypt_secret


def encrypt_password(raw_password: str) -> str:
    if not raw_password:
        return raw_password
    return encrypt_secret(raw_password) or raw_password


def decrypt_password(ciphertext: str) -> str:
    if not ciphertext:
        return ciphertext
    return decrypt_secret(ciphertext) or ciphertext
