"""Add is_custom_title flag to conversations table

Revision ID: 008_title_customized_flag
Revises: 007_encrypt_connection_strings
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "008_title_customized_flag"
down_revision: Union[str, None] = "007_encrypt_connection_strings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds is_custom_title boolean column to conversations table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "conversations" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("conversations")}
        if "is_custom_title" not in existing_cols:
            op.add_column(
                "conversations",
                sa.Column("is_custom_title", sa.Boolean(), nullable=False, server_default=sa.text("false"))
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "conversations" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("conversations")}
        if "is_custom_title" in existing_cols:
            op.drop_column("conversations", "is_custom_title")
