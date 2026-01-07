"""
Response models for API endpoints.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import date


class AccountResponse(BaseModel):
    """Response model for account data."""
    
    id: str
    name: str
    iban: Optional[str] = None
    balance: float
    currency: str


class TransactionResponse(BaseModel):
    """Response model for transaction data."""
    
    id: str
    account_id: str
    amount: float
    currency: str
    description: str
    booking_date: date
    value_date: Optional[date] = None
    category: Optional[str] = None
