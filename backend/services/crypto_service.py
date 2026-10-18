"""
Cryptographic Envelope Encryption & Secret Redaction Service.
Implements Milestone NR-1.2 secret management:
- Fernet envelope encryption with 'v1:' version tag
- Deterministic 32-byte urlsafe key derivation from DATA_ENCRYPTION_KEY / SECRET_KEY
- Plaintext backward compatibility for migrations
- Sensitive credential and URL redaction utilities
"""
import base64
import hashlib
import logging
import os
import re
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

ENCRYPTION_PREFIX = "v1:"
DEFAULT_DEV_FALLBACK = "dataspeakai-default-encryption-dev-key-32b"


def _get_fernet() -> Fernet:
    """Derives a deterministic 32-byte urlsafe base64 key for Fernet symmetric encryption."""
    key_material = os.getenv("DATA_ENCRYPTION_KEY") or os.getenv("SECRET_KEY") or DEFAULT_DEV_FALLBACK
    # Hash material to 32 bytes via SHA-256, then base64 urlsafe encode for Fernet specification
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_secret(plaintext: Optional[str]) -> Optional[str]:
    """Encrypts plaintext secret returning an envelope tagged with 'v1:'.
    
    If the input is None, empty, or already tagged with 'v1:', it is returned unchanged.
    """
    if plaintext is None or plaintext == "":
        return plaintext
    if plaintext.startswith(ENCRYPTION_PREFIX):
        return plaintext
    
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTION_PREFIX}{token}"


def decrypt_secret(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypts a 'v1:' envelope secret.
    
    If the value does not have the 'v1:' tag, it is treated as a legacy plaintext secret
    and returned as-is to preserve backward compatibility during online migrations.
    """
    if ciphertext is None or ciphertext == "":
        return ciphertext
    if not ciphertext.startswith(ENCRYPTION_PREFIX):
        return ciphertext
    
    token = ciphertext[len(ENCRYPTION_PREFIX):]
    f = _get_fernet()
    try:
        decrypted_bytes = f.decrypt(token.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as exc:
        logger.error("Failed to decrypt secret envelope: invalid token or mismatched encryption key.")
        raise ValueError("Failed to decrypt secret: invalid token or encryption key mismatch") from exc


def is_encrypted(value: Optional[str]) -> bool:
    """Returns True if the value is tagged with the current encryption version prefix."""
    return bool(value and value.startswith(ENCRYPTION_PREFIX))


def redact_secret(secret: Optional[str], show_prefix_len: int = 4) -> str:
    """Redacts a secret for safe display and logging (e.g. 'omq_live_***')."""
    if not secret:
        return ""
    if len(secret) <= show_prefix_len:
        return "***"
    return f"{secret[:show_prefix_len]}***"


def redact_connection_url(url: Optional[str]) -> str:
    """Masks database passwords in connection URLs (e.g. 'postgresql://user:***@host:5432/db')."""
    if not url:
        return ""
    # Matches :password@ in standard URI syntax
    return re.sub(r":([^/@:]+)@", ":***@", url)
