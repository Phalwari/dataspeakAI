"""Add connection-level insights cache version

Revision ID: 010_insights_cache_version
Revises: 009_document_storage_and_lifecycle
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "010_insights_cache_version"
down_revision: Union[str, None] = "009_document_storage_and_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add an idempotent, non-null cache generation to database connections."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "database_connections" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("database_connections")}
    if "insights_cache_version" not in existing_columns:
        with op.batch_alter_table("database_connections") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "insights_cache_version",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )


def downgrade() -> None:
    """Remove the cache generation when it exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "database_connections" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("database_connections")}
    if "insights_cache_version" in existing_columns:
        with op.batch_alter_table("database_connections") as batch_op:
            batch_op.drop_column("insights_cache_version")
