"""Initial Reconciled 46-Table Baseline Schema

Revision ID: 001_initial_baseline
Revises: None
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Creates all 46 reconciled baseline tables using models metadata."""
    bind = op.get_bind()
    import models
    models.Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drops all baseline tables in reverse dependency order."""
    bind = op.get_bind()
    import models
    models.Base.metadata.drop_all(bind=bind)
