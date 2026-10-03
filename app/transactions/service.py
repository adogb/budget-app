from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PendingTransaction, Transaction


def list_transactions(db: Session, account_id: int | None = None) -> list[Transaction]:
    """Newest first. Optionally only one account's transactions."""
    query = select(Transaction).order_by(
        Transaction.booking_date.desc(), Transaction.id
    )
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    return list(db.scalars(query))


def list_pending(db: Session) -> list[PendingTransaction]:
    """Newest first; rows without a booking date go first, as the most recent."""
    query = select(PendingTransaction).order_by(
        PendingTransaction.booking_date.desc().nulls_first(), PendingTransaction.id
    )
    return list(db.scalars(query))
