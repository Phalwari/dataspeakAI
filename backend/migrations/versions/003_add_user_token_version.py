"""Add token version column to users table for session revocation

Revision ID: 003_add_user_token_version
Revises: 002_add_platform_admin
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_add_user_token_version"
down_revision: Union[str, None] = "002_add_platform_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add token_version column to users table with server_default=1."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col["name"] for col in inspector.get_columns("users")]
    
    if "token_version" not in existing_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "token_version",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("1"),
                )
            )


def downgrade() -> None:
    """Drop token_version column from users table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col["name"] for col in inspector.get_columns("users")]
    
    if "token_version" in existing_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("token_version")
