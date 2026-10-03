"""bank flow: link state, sync time, import key, pending

Revision ID: 01b3a6bac484
Revises: 2205b18c5b6e
Create Date: 2026-10-03 22:34:29.042042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models import Base


# revision identifiers, used by Alembic.
revision: str = '01b3a6bac484'
down_revision: Union[str, Sequence[str], None] = '2205b18c5b6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The initial migration created unnamed constraints. Rebuilding a table with the
# naming convention gives them the names app.models now expects.
NAMING = Base.metadata.naming_convention


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('pending_transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('amount_minor', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('payee', sa.String(length=255), nullable=True),
    sa.Column('booking_date', sa.Date(), nullable=True),
    sa.Column('value_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_pending_transactions_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pending_transactions'))
    )
    with op.batch_alter_table('accounts', naming_convention=NAMING) as batch_op:
        batch_op.add_column(sa.Column('bank_integration_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('last_synced_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_accounts_bank_integration_id_bank_integrations'), 'bank_integrations', ['bank_integration_id'], ['id'])

    with op.batch_alter_table('bank_integrations', naming_convention=NAMING) as batch_op:
        batch_op.add_column(sa.Column('reference', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('linked_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))
    # Any existing link gets a random reference before the column becomes NOT NULL.
    op.execute("UPDATE bank_integrations SET reference = lower(hex(randomblob(16))) WHERE reference IS NULL")
    with op.batch_alter_table('bank_integrations', naming_convention=NAMING) as batch_op:
        batch_op.alter_column('reference', existing_type=sa.String(length=36), nullable=False)
        batch_op.create_unique_constraint(batch_op.f('uq_bank_integrations_reference'), ['reference'])

    with op.batch_alter_table('transactions', naming_convention=NAMING) as batch_op:
        batch_op.add_column(sa.Column('payee', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('import_key', sa.String(length=100), nullable=True))
    # Same key the sync uses: transactionId, else internalTransactionId.
    op.execute("UPDATE transactions SET import_key = COALESCE(bank_transaction_id, gc_transaction_id)")
    with op.batch_alter_table('transactions', naming_convention=NAMING) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_transactions_account_id_import_key'), ['account_id', 'import_key'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('transactions', naming_convention=NAMING) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_transactions_account_id_import_key'), type_='unique')
        batch_op.drop_column('import_key')
        batch_op.drop_column('payee')

    with op.batch_alter_table('bank_integrations', naming_convention=NAMING) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_bank_integrations_reference'), type_='unique')
        batch_op.drop_column('expires_at')
        batch_op.drop_column('linked_at')
        batch_op.drop_column('reference')

    with op.batch_alter_table('accounts', naming_convention=NAMING) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_accounts_bank_integration_id_bank_integrations'), type_='foreignkey')
        batch_op.drop_column('last_synced_at')
        batch_op.drop_column('bank_integration_id')

    op.drop_table('pending_transactions')
