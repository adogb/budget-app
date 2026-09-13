"""drop token columns from bank_integrations

Access/refresh tokens are app-level credentials the bank client mints on demand
from the configured secrets, not per-integration data. These columns were always
written NULL, so no data is lost.

Revision ID: 50447ee7a0de
Revises: e32f50497d37
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50447ee7a0de"
down_revision: Union[str, Sequence[str], None] = "e32f50497d37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Batch mode is required for SQLite, which cannot ALTER TABLE ... DROP COLUMN
    # directly.
    with op.batch_alter_table("bank_integrations") as batch_op:
        batch_op.drop_column("access_token")
        batch_op.drop_column("refresh_token")
        batch_op.drop_column("access_valid_days")
        batch_op.drop_column("refresh_valid_days")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("bank_integrations") as batch_op:
        batch_op.add_column(
            sa.Column("refresh_valid_days", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("access_valid_days", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("refresh_token", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("access_token", sa.Text(), nullable=True))
