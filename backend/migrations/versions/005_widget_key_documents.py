"""Add widget_key_documents association table for explicit document publication

Revision ID: 005_widget_key_documents
Revises: 004_add_conversation_shares
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_widget_key_documents"
down_revision: Union[str, None] = "004_add_conversation_shares"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create widget_key_documents association table with foreign keys and unique constraint."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "widget_key_documents" not in existing_tables:
        op.create_table(
            "widget_key_documents",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("widget_key_id", sa.Integer(), sa.ForeignKey("widget_keys.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("widget_key_id", "document_id", name="uq_widget_key_document")
        )
        inspector = sa.inspect(bind)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("widget_key_documents")} if "widget_key_documents" in inspector.get_table_names() else set()
    for idx_name, cols in [
        ("ix_widget_key_documents_id", ["id"]),
        ("ix_widget_key_documents_widget_key_id", ["widget_key_id"]),
        ("ix_widget_key_documents_document_id", ["document_id"]),
    ]:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, "widget_key_documents", cols, unique=False)


def downgrade() -> None:
    """Drop widget_key_documents table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "widget_key_documents" in existing_tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("widget_key_documents")}
        for idx_name in [
            "ix_widget_key_documents_document_id",
            "ix_widget_key_documents_widget_key_id",
            "ix_widget_key_documents_id",
        ]:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="widget_key_documents")
        op.drop_table("widget_key_documents")
