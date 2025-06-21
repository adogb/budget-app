from pydantic import BaseModel

class Account(BaseModel):
    id: int
    name: str
    balance: float
