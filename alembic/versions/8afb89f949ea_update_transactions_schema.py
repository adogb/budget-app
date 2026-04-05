"""update_transactions_schema

Revision ID: 8afb89f949ea
Revises: 
Create Date: 2026-04-05 15:33:59.194983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8afb89f949ea'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Changes:
    - Rename 'comment' to 'notes'
    - Rename 'booked_at' to 'booking_date'
    - Add 'value_date' column
    - Add 'currency' column (default 'DKK')
    - Add 'external_id' column
    """
    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        # Add new columns first
        batch_op.add_column(sa.Column('external_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('currency', sa.String(length=3), nullable=False, server_default='DKK'))
        batch_op.add_column(sa.Column('value_date', sa.DateTime(), nullable=True))

        # Rename columns (SQLite batch mode handles this by recreating the table)
        batch_op.alter_column('comment', new_column_name='notes')
        batch_op.alter_column('booked_at', new_column_name='booking_date')


def downgrade() -> None:
    """Downgrade schema - revert to original structure."""
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        # Rename columns back
        batch_op.alter_column('notes', new_column_name='comment')
        batch_op.alter_column('booking_date', new_column_name='booked_at')

        # Drop added columns
        batch_op.drop_column('value_date')
        batch_op.drop_column('currency')
        batch_op.drop_column('external_id')
