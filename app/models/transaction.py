from pydantic import BaseModel

class Transaction(BaseModel):
    id: int
    account_id: int
    amount: float
    description: str
