from decimal import Decimal

from pydantic import BaseModel


class Money(BaseModel):
    """An amount in the currency's minor unit (øre for DKK). Never a float."""

    amount: int
    currency: str


def to_minor_units(amount: str) -> int:
    """Convert a bank amount string like "-19.99" to minor units (-1999).

    Uses Decimal because float("-19.99") * 100 is -1998.9999…, which int()
    truncates to -1998. Assumes 2 decimal places, true for DKK/EUR/GBP.
    """
    return int(Decimal(amount) * 100)
