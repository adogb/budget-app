from datetime import datetime
from typing import Literal, Self

from pydantic import AnyHttpUrl, BaseModel

from app.models import BankIntegration

ConsentStatus = Literal["ok", "expiring", "expired"]


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


class StartLinkIn(BaseModel):
    institution_id: str
    country_code: str
    # Where the bank sends the user back to: the frontend's /link/callback.
    redirect_url: AnyHttpUrl


class StartLinkOut(BaseModel):
    link: str


class CompleteLinkIn(BaseModel):
    external_ids: list[str]


class BankLinkOut(BaseModel):
    id: int
    institution_id: str
    country_code: str
    bank_name: str
    expires_at: datetime | None
    consent_status: ConsentStatus
    account_ids: list[int]

    @classmethod
    def from_model(
        cls, integration: BankIntegration, consent_status: ConsentStatus
    ) -> Self:
        accounts = integration.accounts
        return cls(
            id=integration.id,
            institution_id=integration.institution_id,
            country_code=integration.country_code,
            bank_name=accounts[0].bank_name if accounts else integration.institution_id,
            expires_at=integration.expires_at,
            consent_status=consent_status,
            account_ids=[account.id for account in accounts],
        )


class SyncResultOut(BaseModel):
    account_id: int
    account_name: str
    # Set when the sync worked, otherwise `error` says why it didn't.
    new_transactions: int | None
    error: str | None
