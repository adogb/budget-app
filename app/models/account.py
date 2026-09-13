from pydantic import BaseModel


# Not used at the moment, using AccountResponse instead
# might be useful later
class Account(BaseModel):
    id: str
    name: str
    iban: str | None = None
    balance: float
    currency: str
