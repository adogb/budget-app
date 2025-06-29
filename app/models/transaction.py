from pydantic import BaseModel
from typing import Optional
from datetime import date

class Transaction(BaseModel):
    id: str
    account_id: str
    amount: float
    currency: str
    description: str
    booking_date: date
    value_date: Optional[date] = None
    category: Optional[str] = None
