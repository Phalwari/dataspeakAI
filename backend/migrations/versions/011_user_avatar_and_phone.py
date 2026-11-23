"""Add avatar_url and phone to users

Revision ID: 011_user_avatar_and_phone
Revises: 010_insights_cache_version
Create Date: 2026-11-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "011_user_avatar_and_phone"
down_revision: Union[str, None] = "010_insights_cache_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add avatar_url and phone to users table idempotently."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "avatar_url" not in existing_columns:
            batch_op.add_column(
                sa.Column("avatar_url", sa.String(500), nullable=True)
            )
        if "phone" not in existing_columns:
            batch_op.add_column(
                sa.Column("phone", sa.String(50), nullable=True)
            )


def downgrade() -> None:
    """Remove avatar_url and phone from users table if present."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "phone" in existing_columns:
            batch_op.drop_column("phone")
        if "avatar_url" in existing_columns:
            batch_op.drop_column("avatar_url")
