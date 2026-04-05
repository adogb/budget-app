from pydantic import BaseModel
from typing import Optional
from datetime import date

# Not used at the moment, using TransactionResponse instead
# might be useful later
class Transaction(BaseModel):
    id: str
    account_id: str
    external_id: Optional[str] = None
    amount: float
    currency: str
    description: str
    notes: Optional[str] = None
    booking_date: date
    value_date: Optional[date] = None
    category: Optional[str] = None
