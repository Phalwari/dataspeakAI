"""Hash API keys with SHA-256 and encrypt database credentials with Fernet envelope

Revision ID: 006_hash_api_keys_and_encrypt_db_credentials
Revises: 005_widget_key_documents
Create Date: 2026-10-18 00:00:00.000000

"""
import hashlib
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = "006_hash_api_keys_and_encrypt_db_credentials"
down_revision: Union[str, None] = "005_widget_key_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Expands api_keys with hashed_key and key_prefix, backfills hashes, and encrypts db passwords."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Expand api_keys columns
    if "api_keys" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("api_keys")}
        with op.batch_alter_table("api_keys") as batch_op:
            if "key_prefix" not in existing_cols:
                batch_op.add_column(sa.Column("key_prefix", sa.String(length=16), nullable=True))
            if "hashed_key" not in existing_cols:
                batch_op.add_column(sa.Column("hashed_key", sa.String(length=64), nullable=True))
        
        # Add index on hashed_key
        inspector = sa.inspect(bind)
        indexes = {idx["name"] for idx in inspector.get_indexes("api_keys")}
        if "ix_api_keys_hashed_key" not in indexes:
            op.create_index("ix_api_keys_hashed_key", "api_keys", ["hashed_key"], unique=True)

        # 2. Backfill existing plaintext API keys with SHA-256 hashes
        api_keys_tbl = table(
            "api_keys",
            column("id", sa.Integer),
            column("key", sa.String),
            column("key_prefix", sa.String),
            column("hashed_key", sa.String),
        )

        rows = bind.execute(sa.select(api_keys_tbl.c.id, api_keys_tbl.c.key).where(api_keys_tbl.c.key.isnot(None))).fetchall()
        for row in rows:
            key_id, raw_key = row[0], row[1]
            if raw_key:
                hashed = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
                prefix = raw_key[:12] if len(raw_key) >= 12 else raw_key
                bind.execute(
                    api_keys_tbl.update()
                    .where(api_keys_tbl.c.id == key_id)
                    .values(hashed_key=hashed, key_prefix=prefix, key=None)
                )

    # 3. Backfill database_connections with Fernet envelope encryption
    if "database_connections" in existing_tables:
        from services.crypto_service import encrypt_secret
        db_conn_tbl = table(
            "database_connections",
            column("id", sa.Integer),
            column("password", sa.String),
        )
        conn_rows = bind.execute(sa.select(db_conn_tbl.c.id, db_conn_tbl.c.password).where(db_conn_tbl.c.password.isnot(None))).fetchall()
        for row in conn_rows:
            conn_id, raw_pwd = row[0], row[1]
            if raw_pwd and not raw_pwd.startswith("v1:"):
                encrypted_pwd = encrypt_secret(raw_pwd)
                bind.execute(
                    db_conn_tbl.update()
                    .where(db_conn_tbl.c.id == conn_id)
                    .values(password=encrypted_pwd)
                )


def downgrade() -> None:
    """Rolls back 006 migration by removing hashed_key and key_prefix columns."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "api_keys" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("api_keys")}
        if "ix_api_keys_hashed_key" in indexes:
            op.drop_index("ix_api_keys_hashed_key", table_name="api_keys")

        existing_cols = {col["name"] for col in inspector.get_columns("api_keys")}
        with op.batch_alter_table("api_keys") as batch_op:
            if "hashed_key" in existing_cols:
                batch_op.drop_column("hashed_key")
            if "key_prefix" in existing_cols:
                batch_op.drop_column("key_prefix")
