from datetime import date
from typing import Self

from pydantic import BaseModel

from app.models import PendingTransaction, Transaction
from app.money import Money


class TransactionOut(BaseModel):
    id: str
    account_id: int
    booking_date: date
    value_date: date | None
    description: str
    payee: str | None
    notes: str | None
    amount: Money

    @classmethod
    def from_model(cls, transaction: Transaction) -> Self:
        return cls(
            id=transaction.id,
            account_id=transaction.account_id,
            booking_date=transaction.booking_date,
            value_date=transaction.value_date,
            description=transaction.description,
            payee=transaction.payee,
            notes=transaction.notes,
            amount=Money(
                amount=transaction.amount_minor, currency=transaction.currency
            ),
        )


class PendingTransactionOut(BaseModel):
    """Read-only: not yet booked, so it can't be categorised (spec D4)."""

    id: int
    account_id: int
    booking_date: date | None
    description: str
    payee: str | None
    amount: Money

    @classmethod
    def from_model(cls, pending: PendingTransaction) -> Self:
        return cls(
            id=pending.id,
            account_id=pending.account_id,
            booking_date=pending.booking_date,
            description=pending.description,
            payee=pending.payee,
            amount=Money(amount=pending.amount_minor, currency=pending.currency),
        )
