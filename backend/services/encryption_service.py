"""
Encryption service adapter leveraging DataSpeakAI's Fernet-based crypto module.
"""
from crypto import encrypt_password, decrypt_password

class EncryptionService:
    def encrypt(self, text: str) -> str:
        return encrypt_password(text)

    def decrypt(self, text: str) -> str:
        return decrypt_password(text)

encryption_service = EncryptionService()
