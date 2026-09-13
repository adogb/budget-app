"""
Response models for API endpoints.
"""

from datetime import date

from pydantic import BaseModel


class AccountResponse(BaseModel):
    """Response model for account data."""

    id: str
    name: str
    iban: str | None = None
    balance: float
    currency: str


class TransactionResponse(BaseModel):
    """Response model for transaction data."""

    id: str
    account_id: str
    amount: float
    currency: str
    description: str
    notes: str | None = None
    booking_date: date
    value_date: date | None = None
    category: str | None = None
