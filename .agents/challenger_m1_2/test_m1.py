import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from crypto import encrypt_password, decrypt_password, get_fernet_key
import models
from routers.databases import get_connection_url
from dependencies import get_current_admin_user
from fastapi import HTTPException

class TestMilestone1(unittest.TestCase):

    def test_crypto_encryption_decryption(self):
        raw = "my_secret_db_password_123!"
        encrypted = encrypt_password(raw)
        self.assertNotEqual(raw, encrypted)
        self.assertTrue(encrypted.startswith("gAAAAA")) # Standard Fernet prefix
        decrypted = decrypt_password(encrypted)
        self.assertEqual(raw, decrypted)

    def test_crypto_legacy_plaintext_fallback(self):
        plaintext = "legacy_unencrypted_pass"
        # Should gracefully return plaintext on InvalidToken
        decrypted = decrypt_password(plaintext)
        self.assertEqual(plaintext, decrypted)

    def test_crypto_empty_password(self):
        self.assertEqual(encrypt_password(""), "")
        self.assertEqual(decrypt_password(""), "")
        self.assertIsNone(encrypt_password(None))
        self.assertIsNone(decrypt_password(None))

    def test_sqlite_connection_url(self):
        sqlite_db = models.DatabaseConnection(
            db_type="sqlite",
            database="app.db",
            username=None,
            password=None,
            host=None
        )
        url = get_connection_url(sqlite_db)
        self.assertEqual(url, "sqlite:///app.db")

    def test_postgres_connection_url(self):
        pg_db = models.DatabaseConnection(
            db_type="postgresql",
            database="mydb",
            username="user",
            password=encrypt_password("pass123"),
            host="localhost"
        )
        url = get_connection_url(pg_db)
        self.assertEqual(url, "postgresql://user:pass123@localhost/mydb")

    def test_admin_authorization_dependency(self):
        admin_user = models.User(role="Admin", email="admin@test.com")
        member_user = models.User(role="Member", email="member@test.com")
        
        # Admin should pass
        res = get_current_admin_user(current_user=admin_user)
        self.assertEqual(res.role, "Admin")
        
        # Member should raise 403
        with self.assertRaises(HTTPException) as ctx:
            get_current_admin_user(current_user=member_user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Admin access required")

    def test_secret_removal(self):
        import auth
        self.assertNotEqual(auth.SECRET_KEY, "super_secret_key_for_fyp")
        self.assertTrue(len(auth.SECRET_KEY) >= 16)

if __name__ == "__main__":
    unittest.main()
