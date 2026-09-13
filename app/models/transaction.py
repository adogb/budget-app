from datetime import date

from pydantic import BaseModel


# Not used at the moment, using TransactionResponse instead
# might be useful later
class Transaction(BaseModel):
    id: str
    account_id: str
    external_id: str | None = None
    amount: float
    currency: str
    description: str
    notes: str | None = None
    booking_date: date
    value_date: date | None = None
    category: str | None = None
