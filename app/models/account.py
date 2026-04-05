from pydantic import BaseModel
from typing import Optional

# Not used at the moment, using AccountResponse instead
# might be useful later
class Account(BaseModel): 
    id: str
    name: str
    iban: Optional[str] = None
    balance: float
    currency: str
