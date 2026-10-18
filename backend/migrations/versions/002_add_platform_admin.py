"""Add explicit platform administrator authority flag to users table

Revision ID: 002_add_platform_admin
Revises: 001_initial_baseline
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_platform_admin"
down_revision: Union[str, None] = "001_initial_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_platform_admin column to users table with server_default=0 (False)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col["name"] for col in inspector.get_columns("users")]
    
    if "is_platform_admin" not in existing_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_platform_admin",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )


def downgrade() -> None:
    """Drop is_platform_admin column from users table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col["name"] for col in inspector.get_columns("users")]
    
    if "is_platform_admin" in existing_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("is_platform_admin")
