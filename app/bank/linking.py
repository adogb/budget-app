"""Linking a bank through GoCardless and saving its accounts.

The flow: pick a country → pick a bank → create a link and send the user to
the bank → the bank redirects back → choose accounts → complete_setup().
"""

import logging

from pydantic import BaseModel
from requests import RequestException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bank.client import GoCardlessBankDataClient
from app.bank.errors import BankAPIError
from app.models import Account, BankIntegration
from app.money import to_minor_units

logger = logging.getLogger(__name__)


class Country(BaseModel):
    code: str
    name: str
    flag: str | None = None


class Institution(BaseModel):
    id: str
    name: str
    logo: str = ""
    countries: list[str] = []


class AccountChoice(BaseModel):
    id: str
    name: str


SUPPORTED_COUNTRIES = (
    Country(code="GB", name="United Kingdom", flag="🇬🇧"),
    Country(code="DE", name="Germany", flag="🇩🇪"),
    Country(code="FR", name="France", flag="🇫🇷"),
    Country(code="ES", name="Spain", flag="🇪🇸"),
    Country(code="IT", name="Italy", flag="🇮🇹"),
    Country(code="NL", name="Netherlands", flag="🇳🇱"),
    Country(code="FI", name="Finland", flag="🇫🇮"),
    Country(code="NO", name="Norway", flag="🇳🇴"),
    Country(code="SE", name="Sweden", flag="🇸🇪"),
    Country(code="DK", name="Denmark", flag="🇩🇰"),
    Country(code="BE", name="Belgium", flag="🇧🇪"),
    Country(code="AT", name="Austria", flag="🇦🇹"),
)


def get_institutions(
    client: GoCardlessBankDataClient, country_code: str
) -> list[Institution]:
    try:
        institutions = client.get_institutions(country_code)
    except RequestException as e:
        raise BankAPIError(f"Failed to get institutions: {e}") from e
    return [
        Institution(
            id=inst["id"],
            name=inst["name"],
            logo=inst.get("logo", ""),
            countries=inst.get("countries", []),
        )
        for inst in institutions
    ]


def create_bank_link(
    client: GoCardlessBankDataClient,
    institution_id: str,
    callback_url: str = "http://localhost:8000/setup/bank-callback",
) -> dict[str, str]:
    """Returns the bank's login `link` and the `requisition_id` to remember."""
    try:
        requisition = client.create_requisition(
            redirect_url=callback_url, institution_id=institution_id
        )
    except RequestException as e:
        raise BankAPIError(f"Failed to create bank link: {e}") from e
    return {
        "link": requisition.get("link", ""),
        "requisition_id": requisition.get("id", ""),
    }


def get_requisition_account_ids(
    client: GoCardlessBankDataClient, requisition_id: str
) -> list[str]:
    try:
        requisition = client.get_requisition(requisition_id)
    except RequestException as e:
        raise BankAPIError(f"Failed to get requisition: {e}") from e
    return requisition.get("accounts", [])


def get_account_choices(
    client: GoCardlessBankDataClient, account_ids: list[str]
) -> list[AccountChoice]:
    """Name each bank account so the user can choose which ones to add."""
    choices = []
    for account_id in account_ids:
        try:
            name = client.get_account_details(account_id)["account"].get(
                "name", "Unnamed Account"
            )
        except (RequestException, KeyError):
            logger.exception("Could not fetch account %s, skipping it", account_id)
            continue
        choices.append(AccountChoice(id=account_id, name=name))
    return choices


def find_integration(db: Session, requisition_id: str) -> BankIntegration | None:
    query = select(BankIntegration).where(
        BankIntegration.requisition_id == requisition_id
    )
    return db.scalars(query).first()


def complete_setup(
    db: Session,
    client: GoCardlessBankDataClient,
    requisition_id: str,
    institution_id: str,
    selected_account_ids: list[str],
    country_code: str = "GB",
) -> None:
    """Save the bank link and the chosen accounts (creating or updating them)."""
    if find_integration(db, requisition_id) is None:
        db.add(
            BankIntegration(
                institution_id=institution_id,
                country_code=country_code,
                requisition_id=requisition_id,
            )
        )
        db.commit()

    bank_name = _institution_name(client, country_code, institution_id)

    for account_id in selected_account_ids:
        # One failing account shouldn't stop the others from being saved.
        try:
            _save_account(db, client, account_id, bank_name)
        except Exception:
            db.rollback()
            logger.exception("Could not save account %s", account_id)


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


def _save_account(
    db: Session, client: GoCardlessBankDataClient, account_id: str, bank_name: str
) -> None:
    details = client.get_account_details(account_id)["account"]
    balances = client.get_account_balances(account_id)["balances"]
    balance_minor = (
        to_minor_units(balances[0]["balanceAmount"]["amount"]) if balances else 0
    )
    name = details.get("name", "Unknown Account")
    iban = details.get("iban") or None

    account = db.scalars(
        select(Account).where(Account.external_id == account_id)
    ).first()
    if account is None:
        db.add(
            Account(
                external_id=account_id,
                name=name,
                iban=iban,
                balance_minor=balance_minor,
                currency=details.get("currency", "EUR"),
                bank_name=bank_name,
            )
        )
    else:
        account.name = name
        account.iban = iban or account.iban
        account.balance_minor = balance_minor
        account.bank_name = bank_name
    db.commit()
