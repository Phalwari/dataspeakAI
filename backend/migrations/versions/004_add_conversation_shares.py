"""Add conversation_shares table for dashboard conversation privacy and sharing

Revision ID: 004_add_conversation_shares
Revises: 003_add_user_token_version
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_add_conversation_shares"
down_revision: Union[str, None] = "003_add_user_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create conversation_shares table with foreign keys and unique constraint."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "conversation_shares" not in existing_tables:
        op.create_table(
            "conversation_shares",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("shared_with_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("granted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("conversation_id", "shared_with_user_id", name="uq_conversation_shares_conv_user")
        )
        op.create_index("ix_conversation_shares_id", "conversation_shares", ["id"], unique=False)
        op.create_index("ix_conversation_shares_conversation_id", "conversation_shares", ["conversation_id"], unique=False)
        op.create_index("ix_conversation_shares_shared_with_user_id", "conversation_shares", ["shared_with_user_id"], unique=False)


def downgrade() -> None:
    """Drop conversation_shares table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "conversation_shares" in existing_tables:
        op.drop_index("ix_conversation_shares_shared_with_user_id", table_name="conversation_shares")
        op.drop_index("ix_conversation_shares_conversation_id", table_name="conversation_shares")
        op.drop_index("ix_conversation_shares_id", table_name="conversation_shares")
        op.drop_table("conversation_shares")
