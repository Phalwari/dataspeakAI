"""Add storage and lifecycle tracking columns to documents table

Revision ID: 009_document_storage_and_lifecycle
Revises: 008_title_customized_flag
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "009_document_storage_and_lifecycle"
down_revision: Union[str, None] = "008_title_customized_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds storage_key, content_sha256, version, ingestion_job_id, progress_step, last_heartbeat_at, and is_deleted to documents table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "documents" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("documents")}
        
        if "storage_key" not in existing_cols:
            op.add_column("documents", sa.Column("storage_key", sa.String(512), nullable=True))
            
        if "content_sha256" not in existing_cols:
            op.add_column("documents", sa.Column("content_sha256", sa.String(64), nullable=True))
            
        if "version" not in existing_cols:
            op.add_column("documents", sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")))
            
        if "ingestion_job_id" not in existing_cols:
            op.add_column("documents", sa.Column("ingestion_job_id", sa.String(64), nullable=True))
            
        if "progress_step" not in existing_cols:
            op.add_column("documents", sa.Column("progress_step", sa.String(64), nullable=True, server_default=sa.text("'queued'")))
            
        if "last_heartbeat_at" not in existing_cols:
            op.add_column("documents", sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True))
            
        if "is_deleted" not in existing_cols:
            op.add_column("documents", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "documents" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("documents")}
        for col_name in ["is_deleted", "last_heartbeat_at", "progress_step", "ingestion_job_id", "version", "content_sha256", "storage_key"]:
            if col_name in existing_cols:
                op.drop_column("documents", col_name)
