from pydantic import BaseModel


class Country(BaseModel):
    code: str
    name: str
    flag: str | None = None


class Institution(BaseModel):
    id: str
    name: str
    logo: str = ""
    countries: list[str] = []


class LinkAccount(BaseModel):
    """An account the bank shared, offered for the user to tick."""

    external_id: str
    name: str
    iban: str | None
    currency: str
    # Only accounts in the budget currency can be added (spec D1).
    eligible: bool
    # Matches an account we already have, e.g. when renewing consent.
    already_linked: bool
