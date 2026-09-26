from datetime import date
from typing import Self

from pydantic import BaseModel

from app.models import Transaction
from app.money import Money


class TransactionOut(BaseModel):
    id: str
    account_id: int
    booking_date: date
    value_date: date | None
    description: str
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
            notes=transaction.notes,
            amount=Money(
                amount=transaction.amount_minor, currency=transaction.currency
            ),
        )
