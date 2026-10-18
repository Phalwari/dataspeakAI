"""Encrypt database connection strings with Fernet envelope

Revision ID: 007_encrypt_connection_strings
Revises: 006_hash_api_keys_and_encrypt_db_credentials
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from services.crypto_service import encrypt_secret, decrypt_secret

# revision identifiers, used by Alembic.
revision: str = "007_encrypt_connection_strings"
down_revision: Union[str, None] = "006_hash_api_keys_and_encrypt_db_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfills database_connections with Fernet envelope encryption for connection_string."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "database_connections" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("database_connections")}
        if "connection_string" in existing_cols:
            db_conn_tbl = table(
                "database_connections",
                column("id", sa.Integer),
                column("connection_string", sa.String),
            )
            conn_rows = bind.execute(
                sa.select(db_conn_tbl.c.id, db_conn_tbl.c.connection_string)
                .where(db_conn_tbl.c.connection_string.isnot(None))
            ).fetchall()
            for row in conn_rows:
                conn_id, raw_conn_str = row[0], row[1]
                if raw_conn_str and not str(raw_conn_str).startswith("v1:"):
                    encrypted = encrypt_secret(raw_conn_str)
                    bind.execute(
                        db_conn_tbl.update()
                        .where(db_conn_tbl.c.id == conn_id)
                        .values(connection_string=encrypted)
                    )


def downgrade() -> None:
    """Reverts Fernet encryption for connection_string where possible."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "database_connections" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("database_connections")}
        if "connection_string" in existing_cols:
            db_conn_tbl = table(
                "database_connections",
                column("id", sa.Integer),
                column("connection_string", sa.String),
            )
            conn_rows = bind.execute(
                sa.select(db_conn_tbl.c.id, db_conn_tbl.c.connection_string)
                .where(db_conn_tbl.c.connection_string.isnot(None))
            ).fetchall()
            for row in conn_rows:
                conn_id, enc_conn_str = row[0], row[1]
                if enc_conn_str and str(enc_conn_str).startswith("v1:"):
                    decrypted = decrypt_secret(enc_conn_str)
                    bind.execute(
                        db_conn_tbl.update()
                        .where(db_conn_tbl.c.id == conn_id)
                        .values(connection_string=decrypted)
                    )
