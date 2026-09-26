from typing import Self

from pydantic import BaseModel

from app.models import Account
from app.money import Money


class AccountOut(BaseModel):
    id: int
    name: str
    bank_name: str
    iban: str | None
    balance: Money

    @classmethod
    def from_model(cls, account: Account) -> Self:
        return cls(
            id=account.id,
            name=account.name,
            bank_name=account.bank_name,
            iban=account.iban,
            balance=Money(amount=account.balance_minor, currency=account.currency),
        )
