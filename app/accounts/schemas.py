from datetime import datetime
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
    bank_integration_id: int | None
    last_synced_at: datetime | None

    @classmethod
    def from_model(cls, account: Account) -> Self:
        return cls(
            id=account.id,
            name=account.name,
            bank_name=account.bank_name,
            iban=account.iban,
            balance=Money(amount=account.balance_minor, currency=account.currency),
            bank_integration_id=account.bank_integration_id,
            last_synced_at=account.last_synced_at,
        )
