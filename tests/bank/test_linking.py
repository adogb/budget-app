"""Tests for linking a bank, choosing accounts and renewing consent."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
from requests import HTTPError
from sqlalchemy import select

from app.bank.errors import BankAPIError, LinkError, LinkNotFoundError
from app.bank.linking import (
    SUPPORTED_COUNTRIES,
    complete_link,
    consent_status,
    get_institutions,
    list_link_accounts,
    start_link,
)
from app.models import Account, BankIntegration, Transaction

ACCOUNTS = {
    "acc-1": {"iban": "DK0001", "name": "Checking", "currency": "DKK"},
    "acc-2": {"iban": "DK0002", "name": "Shared", "currency": "DKK"},
    "acc-eur": {"iban": "DE0003", "name": "Euro savings", "currency": "EUR"},
}


@pytest.fixture
def client() -> Mock:
    client = Mock()
    client.get_institutions.return_value = [
        {"id": "BANK_DK", "name": "Danske Test", "logo": "logo.png"}
    ]
    client.create_requisition.return_value = {
        "id": "req-1",
        "link": "https://bank.example.com/auth",
    }
    client.get_requisition.return_value = {"id": "req-1", "accounts": list(ACCOUNTS)}
    client.get_account_details.side_effect = lambda account_id: {
        "account": ACCOUNTS[account_id]
    }
    client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1000.50", "currency": "DKK"}}]
    }
    return client


def add_link(db, reference="ref-1", requisition_id="req-1", linked=False):
    integration = BankIntegration(
        institution_id="BANK_DK",
        country_code="DK",
        requisition_id=requisition_id,
        reference=reference,
        linked_at=datetime.now(UTC) if linked else None,
    )
    db.add(integration)
    db.commit()
    return integration


def all_accounts(db) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.id)))


# Banks


def test_denmark_is_listed_first():
    assert SUPPORTED_COUNTRIES[0].code == "DK"


def test_get_institutions(client):
    institutions = get_institutions(client, "DK")

    assert [i.name for i in institutions] == ["Danske Test"]
    assert institutions[0].countries == []
    client.get_institutions.assert_called_once_with("DK")


def test_get_institutions_error(client):
    client.get_institutions.side_effect = HTTPError("503")

    with pytest.raises(BankAPIError, match="Could not list banks"):
        get_institutions(client, "DK")


# Starting a link


def test_start_link_saves_an_unlinked_integration(db, client):
    link = start_link(db, client, "BANK_DK", "DK", "http://localhost:5173/cb")

    assert link == "https://bank.example.com/auth"
    integration = db.scalars(select(BankIntegration)).one()
    assert integration.requisition_id == "req-1"
    assert integration.linked_at is None
    client.create_requisition.assert_called_once_with(
        redirect_url="http://localhost:5173/cb",
        institution_id="BANK_DK",
        reference=integration.reference,
    )


def test_start_deletes_only_unlinked_integrations(db, client):
    add_link(db, reference="abandoned", requisition_id="req-old")
    add_link(db, reference="linked", requisition_id="req-linked", linked=True)

    start_link(db, client, "BANK_DK", "DK", "http://localhost:5173/cb")

    references = set(db.scalars(select(BankIntegration.reference)))
    assert "abandoned" not in references
    assert "linked" in references
    assert len(references) == 2


# Choosing accounts


def test_list_link_accounts(db, client):
    add_link(db)

    choices = list_link_accounts(db, client, "ref-1")

    assert [(c.name, c.eligible, c.already_linked) for c in choices] == [
        ("Checking", True, False),
        ("Shared", True, False),
        ("Euro savings", False, False),
    ]


def test_list_marks_accounts_we_already_have(db, client):
    add_link(db)
    db.add(Account(name="Old", bank_name="B", currency="DKK", iban="DK0002"))
    db.commit()

    choices = list_link_accounts(db, client, "ref-1")

    assert [c.already_linked for c in choices] == [False, True, False]


def test_list_skips_malformed_details(db, client):
    add_link(db)
    client.get_requisition.return_value = {"accounts": ["acc-1", "acc-bad"]}
    client.get_account_details.side_effect = [
        {"account": ACCOUNTS["acc-1"]},
        {"unexpected": {}},
    ]

    choices = list_link_accounts(db, client, "ref-1")

    assert [c.external_id for c in choices] == ["acc-1"]


def test_unknown_reference(db, client):
    with pytest.raises(LinkNotFoundError):
        list_link_accounts(db, client, "nope")


# Completing a link


def test_complete_creates_accounts_and_sets_expiry(db, client):
    integration = add_link(db)

    complete_link(db, client, "ref-1", ["acc-1", "acc-2"])

    accounts = all_accounts(db)
    assert [a.name for a in accounts] == ["Checking", "Shared"]
    assert all(a.bank_name == "Danske Test" for a in accounts)
    assert all(a.balance_minor == 100050 for a in accounts)
    assert all(a.bank_integration_id == integration.id for a in accounts)
    db.refresh(integration)
    assert integration.linked_at is not None
    assert integration.expires_at == integration.linked_at + timedelta(days=90)


def test_non_dkk_refused(db, client):
    add_link(db)

    with pytest.raises(LinkError, match="Euro savings is in EUR"):
        complete_link(db, client, "ref-1", ["acc-1", "acc-eur"])

    assert all_accounts(db) == []


def test_account_not_in_the_link_refused(db, client):
    add_link(db)

    with pytest.raises(LinkError, match="Not part of this bank link: acc-other"):
        complete_link(db, client, "ref-1", ["acc-other"])


def test_nothing_chosen_refused(db, client):
    add_link(db)

    with pytest.raises(LinkError, match="at least one"):
        complete_link(db, client, "ref-1", [])


def test_bank_error_saves_nothing(db, client):
    integration = add_link(db)
    client.get_account_balances.side_effect = [
        {"balances": []},
        HTTPError("429"),
    ]

    with pytest.raises(BankAPIError, match="Could not read the balance"):
        complete_link(db, client, "ref-1", ["acc-1", "acc-2"])

    assert all_accounts(db) == []
    db.refresh(integration)
    assert integration.linked_at is None


def test_renewal_matches_by_iban_keeps_transactions(db, client):
    old_link = add_link(db, reference="old", requisition_id="req-old", linked=True)
    account = Account(
        name="Checking",
        bank_name="Danske Test",
        currency="DKK",
        iban="DK0001",
        external_id="acc-1-expired",
        bank_integration_id=old_link.id,
    )
    db.add(account)
    db.commit()
    db.add(
        Transaction(
            account_id=account.id,
            amount_minor=-100,
            currency="DKK",
            description="Coffee",
            booking_date=date(2026, 9, 1),
        )
    )
    db.commit()
    new_link = add_link(db, reference="new", requisition_id="req-new")

    complete_link(db, client, "new", ["acc-1"])

    accounts = all_accounts(db)
    assert [a.id for a in accounts] == [account.id]
    assert accounts[0].external_id == "acc-1"
    assert accounts[0].bank_integration_id == new_link.id
    assert len(accounts[0].transactions) == 1
    assert list(db.scalars(select(BankIntegration.reference))) == ["new"]


# Consent status


@pytest.mark.parametrize(
    ("days_left", "expected"),
    [(30, "ok"), (7.5, "ok"), (7, "expiring"), (1, "expiring"), (0, "expired")],
)
def test_consent_status(days_left, expected):
    now = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)

    assert consent_status(now + timedelta(days=days_left), now) == expected


def test_no_expiry_counts_as_expired():
    assert consent_status(None, datetime.now(UTC)) == "expired"


def test_start_link_without_a_login_link(db, client):
    client.create_requisition.return_value = {"id": "req-1"}

    with pytest.raises(BankAPIError, match="sent no link"):
        start_link(db, client, "BANK_DK", "DK", "http://localhost:5173/cb")

    assert db.scalars(select(BankIntegration)).all() == []
