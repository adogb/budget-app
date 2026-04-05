"""change_transaction_id_to_uuid

Revision ID: 136678746495
Revises: 8afb89f949ea
Create Date: 2026-04-05 15:43:35.528173

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '136678746495'
down_revision: Union[str, Sequence[str], None] = '8afb89f949ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change transaction ID from integer to UUID string.

    Since the table is currently empty, we can recreate it with the new schema.
    """
    # SQLite doesn't support changing primary key types directly
    # We need to recreate the table
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        # Drop the table and recreate with UUID primary key
        # This works because there's no data in the table yet
        batch_op.alter_column('id',
                              existing_type=sa.INTEGER(),
                              type_=sa.String(36),
                              existing_nullable=False)


def downgrade() -> None:
    """Revert transaction ID back to integer."""
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.alter_column('id',
                              existing_type=sa.String(36),
                              type_=sa.INTEGER(),
                              existing_nullable=False)
