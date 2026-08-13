import os
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken

def get_fernet_key() -> bytes:
    key_str = os.getenv("ENCRYPTION_KEY") or os.getenv("SECRET_KEY", "dataspeak_default_secret_key_change_me_in_prod")
    key_bytes = hashlib.sha256(key_str.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(key_bytes)

def encrypt_password(raw_password: str) -> str:
    if not raw_password:
        return raw_password
    fernet = Fernet(get_fernet_key())
    return fernet.encrypt(raw_password.encode('utf-8')).decode('utf-8')

def decrypt_password(ciphertext: str) -> str:
    if not ciphertext:
        return ciphertext
    try:
        fernet = Fernet(get_fernet_key())
        return fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception):
        # Fallback handling for existing unencrypted plaintext passwords
        return ciphertext
