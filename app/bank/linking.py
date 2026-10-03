"""Linking a bank through GoCardless, and renewing the link when consent expires.

The flow: start_link() sends the user to their bank → the bank redirects back
to /link/callback?ref=<reference> → list_link_accounts() → the user ticks
accounts → complete_link(). Renewing is the same flow for the same bank; the
accounts are matched to the ones we have, so their transactions stay.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from requests import RequestException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.bank.client import GoCardlessBankDataClient
from app.bank.client_models import GCAccountDetail
from app.bank.errors import BankAPIError, LinkError, LinkNotFoundError
from app.bank.schemas import ConsentStatus, Country, Institution, LinkAccount
from app.config import BUDGET_CURRENCY
from app.models import Account, BankIntegration
from app.money import to_minor_units

logger = logging.getLogger(__name__)

# GoCardless's default agreement gives 90 days of access.
ACCESS_DAYS = 90
EXPIRY_WARNING_DAYS = 7

SUPPORTED_COUNTRIES = (
    Country(code="DK", name="Denmark", flag="🇩🇰"),
    Country(code="GB", name="United Kingdom", flag="🇬🇧"),
    Country(code="DE", name="Germany", flag="🇩🇪"),
    Country(code="FR", name="France", flag="🇫🇷"),
    Country(code="ES", name="Spain", flag="🇪🇸"),
    Country(code="IT", name="Italy", flag="🇮🇹"),
    Country(code="NL", name="Netherlands", flag="🇳🇱"),
    Country(code="FI", name="Finland", flag="🇫🇮"),
    Country(code="NO", name="Norway", flag="🇳🇴"),
    Country(code="SE", name="Sweden", flag="🇸🇪"),
    Country(code="BE", name="Belgium", flag="🇧🇪"),
    Country(code="AT", name="Austria", flag="🇦🇹"),
)


def get_institutions(
    client: GoCardlessBankDataClient, country_code: str
) -> list[Institution]:
    try:
        institutions = client.get_institutions(country_code)
    except RequestException as e:
        raise BankAPIError.from_request("Could not list banks", e) from e
    return [
        Institution(
            id=inst["id"],
            name=inst["name"],
            logo=inst.get("logo", ""),
            countries=inst.get("countries", []),
        )
        for inst in institutions
    ]


def start_link(
    db: Session,
    client: GoCardlessBankDataClient,
    institution_id: str,
    country_code: str,
    redirect_url: str,
) -> str:
    """Create a link and return the URL of the bank's login page."""
    # Links that were started but never completed are abandoned attempts.
    db.execute(delete(BankIntegration).where(BankIntegration.linked_at.is_(None)))
    reference = str(uuid4())
    try:
        requisition = client.create_requisition(
            redirect_url=redirect_url,
            institution_id=institution_id,
            reference=reference,
        )
    except RequestException as e:
        raise BankAPIError.from_request("Could not start the bank link", e) from e
    db.add(
        BankIntegration(
            institution_id=institution_id,
            country_code=country_code,
            requisition_id=requisition["id"],
            reference=reference,
        )
    )
    db.commit()
    return requisition["link"]


def find_link(db: Session, reference: str) -> BankIntegration:
    integration = db.scalars(
        select(BankIntegration).where(BankIntegration.reference == reference)
    ).first()
    if integration is None:
        raise LinkNotFoundError(f"No bank link with reference {reference}")
    return integration


def list_link_accounts(
    db: Session, client: GoCardlessBankDataClient, reference: str
) -> list[LinkAccount]:
    """The accounts the bank shared, for the user to choose from."""
    integration = find_link(db, reference)
    choices = []
    for external_id in _shared_account_ids(client, integration):
        try:
            details = _account_details(client, external_id)
        except KeyError:
            logger.exception("Malformed details for account %s", external_id)
            continue
        iban = details.get("iban") or None
        currency = details.get("currency", "")
        choices.append(
            LinkAccount(
                external_id=external_id,
                name=_account_name(details),
                iban=iban,
                currency=currency,
                eligible=currency == BUDGET_CURRENCY,
                already_linked=_existing_account(db, external_id, iban) is not None,
            )
        )
    return choices


@dataclass
class _ChosenAccount:
    external_id: str
    details: GCAccountDetail
    balance_minor: int


def complete_link(
    db: Session,
    client: GoCardlessBankDataClient,
    reference: str,
    external_ids: list[str],
) -> None:
    """Save the chosen accounts and mark the link as complete.

    Everything is fetched and checked before anything is saved, so a failure
    leaves the database as it was.
    """
    integration = find_link(db, reference)
    if not external_ids:
        raise LinkError("Choose at least one account.")
    not_shared = set(external_ids) - set(_shared_account_ids(client, integration))
    if not_shared:
        raise LinkError(f"Not part of this bank link: {', '.join(sorted(not_shared))}")

    chosen = [_fetch_account(client, external_id) for external_id in external_ids]
    for account in chosen:
        currency = account.details.get("currency", "")
        if currency != BUDGET_CURRENCY:
            raise LinkError(
                f"{_account_name(account.details)} is in {currency or 'an unknown'} "
                f"currency. Only {BUDGET_CURRENCY} accounts can be budgeted."
            )

    bank_name = _institution_name(
        client, integration.country_code, integration.institution_id
    )
    previous_links = set()
    for account in chosen:
        previous_links.add(_save_account(db, integration, account, bank_name))

    now = datetime.now(UTC)
    integration.linked_at = now
    integration.expires_at = now + timedelta(days=ACCESS_DAYS)
    db.flush()
    _delete_links_without_accounts(db, previous_links - {integration.id, None})
    db.commit()


def list_links(db: Session) -> list[BankIntegration]:
    """Completed links, soonest expiry first."""
    return list(
        db.scalars(
            select(BankIntegration)
            .where(BankIntegration.linked_at.is_not(None))
            .order_by(BankIntegration.expires_at)
        )
    )


def consent_status(expires_at: datetime, now: datetime) -> ConsentStatus:
    if expires_at <= now:
        return "expired"
    if expires_at - now <= timedelta(days=EXPIRY_WARNING_DAYS):
        return "expiring"
    return "ok"


def _shared_account_ids(
    client: GoCardlessBankDataClient, integration: BankIntegration
) -> list[str]:
    try:
        requisition = client.get_requisition(integration.requisition_id)
    except RequestException as e:
        raise BankAPIError.from_request("Could not read the bank link", e) from e
    return requisition.get("accounts", [])


def _account_details(
    client: GoCardlessBankDataClient, external_id: str
) -> GCAccountDetail:
    try:
        return client.get_account_details(external_id)["account"]
    except RequestException as e:
        raise BankAPIError.from_request("Could not read account details", e) from e


def _fetch_account(
    client: GoCardlessBankDataClient, external_id: str
) -> _ChosenAccount:
    details = _account_details(client, external_id)
    try:
        balances = client.get_account_balances(external_id)["balances"]
    except RequestException as e:
        raise BankAPIError.from_request("Could not read the balance", e) from e
    balance_minor = (
        to_minor_units(balances[0]["balanceAmount"]["amount"]) if balances else 0
    )
    return _ChosenAccount(external_id, details, balance_minor)


def _account_name(details: GCAccountDetail) -> str:
    return details.get("name") or details.get("displayName") or "Unnamed account"


def _existing_account(
    db: Session, external_id: str, iban: str | None
) -> Account | None:
    """Renewing gives accounts new external IDs, so fall back to the IBAN."""
    account = db.scalars(
        select(Account).where(Account.external_id == external_id)
    ).first()
    if account is None and iban:
        account = db.scalars(select(Account).where(Account.iban == iban)).first()
    return account


def _save_account(
    db: Session,
    integration: BankIntegration,
    chosen: _ChosenAccount,
    bank_name: str,
) -> int | None:
    """Create or update the account. Returns the link it belonged to before."""
    details = chosen.details
    iban = details.get("iban") or None
    account = _existing_account(db, chosen.external_id, iban)
    previous_link = None
    if account is None:
        account = Account(currency=details["currency"])
        db.add(account)
    else:
        previous_link = account.bank_integration_id
    account.external_id = chosen.external_id
    account.name = _account_name(details)
    account.iban = iban or account.iban
    account.bank_name = bank_name
    account.balance_minor = chosen.balance_minor
    account.bank_integration = integration
    return previous_link


def _delete_links_without_accounts(db: Session, integration_ids: set[int]) -> None:
    for integration_id in integration_ids:
        remaining = db.scalar(
            select(func.count())
            .select_from(Account)
            .where(Account.bank_integration_id == integration_id)
        )
        if remaining == 0:
            db.execute(
                delete(BankIntegration).where(BankIntegration.id == integration_id)
            )


def _institution_name(
    client: GoCardlessBankDataClient, country_code: str, institution_id: str
) -> str:
    try:
        institutions = client.get_institutions(country_code)
    except RequestException:
        logger.exception("Could not fetch institution name")
        return "Unknown Bank"
    for inst in institutions:
        if inst["id"] == institution_id:
            return inst["name"]
    return "Unknown Bank"
