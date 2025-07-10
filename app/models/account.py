from pydantic import BaseModel
from typing import Optional


class Account(BaseModel):
    id: str
    name: str
    iban: Optional[str] = None
    balance: float
    currency: str
