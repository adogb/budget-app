"""Tests for syncing an account's transactions and balance from the bank."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from requests import HTTPError, Response
from sqlalchemy import select

from app.bank.client import GoCardlessBankDataClient
from app.bank.errors import BankAPIError
from app.bank.sync import balance_minor, import_keys, sync_account, sync_start
from app.models import Account, PendingTransaction, Transaction

TODAY = datetime.now(UTC).date()
# The fixture's latest transaction, recent enough to be inside the bank's history.
LATEST = TODAY - timedelta(days=3)


@pytest.fixture
def test_account(db):
    account = Account(
        id=1,
        external_id="test_external_123",
        name="Test Account",
        iban="DK1234567890",
        balance_minor=100000,
        currency="DKK",
        bank_name="Test Bank",
    )
    db.add(account)
    db.commit()
    return account


@pytest.fixture
def test_transactions(db, test_account):
    transactions = [
        Transaction(
            id="trans_1",
            account_id=test_account.id,
            import_key="ext_1",
            bank_transaction_id="ext_1",
            amount_minor=10000,
            currency="DKK",
            description="Transaction 1",
            booking_date=LATEST - timedelta(days=2),
        ),
        Transaction(
            id="trans_2",
            account_id=test_account.id,
            import_key="ext_2",
            bank_transaction_id="ext_2",
            amount_minor=20000,
            currency="DKK",
            description="Transaction 2",
            booking_date=LATEST,
        ),
    ]
    db.add_all(transactions)
    db.commit()
    return transactions


@pytest.fixture
def mock_bank_client():
    client = Mock(spec=GoCardlessBankDataClient)
    client.get_account_transactions.return_value = bank_response()
    client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1000.00", "currency": "DKK"}}]
    }
    return client


def bank_response(booked=(), pending=()):
    return {"transactions": {"booked": list(booked), "pending": list(pending)}}


def booked(
    transaction_id: str | None = "ext_new",
    amount: str = "-35.00",
    booking_date: str = "2026-04-04",
    **extra: Any,
) -> Any:
    """A bank row. Typed `Any` so tests can build malformed rows too."""
    row = {
        "transactionAmount": {"amount": amount, "currency": "DKK"},
        "bookingDate": booking_date,
        "valueDate": booking_date,
        "remittanceInformationUnstructured": "Coffee",
        **extra,
    }
    if transaction_id:
        row["transactionId"] = transaction_id
    return row


def stored(db) -> list[Transaction]:
    return list(db.scalars(select(Transaction).order_by(Transaction.booking_date)))


# Sync window


def test_window_starts_7_days_before_latest(db, test_transactions):
    assert sync_start(db, 1, today=TODAY) == LATEST - timedelta(days=7)


def test_first_sync_goes_back_90_days(db, test_account):
    assert sync_start(db, 1, today=date(2026, 10, 3)) == date(2026, 7, 5)


def test_window_never_goes_past_the_banks_history(db, test_transactions):
    # The latest transaction is 200 days old, e.g. a dormant savings account.
    today = LATEST + timedelta(days=200)

    assert sync_start(db, 1, today=today) == today - timedelta(days=90)


def test_window_is_passed_to_the_bank(
    db, test_account, test_transactions, mock_bank_client
):
    sync_account(db, mock_bank_client, test_account.id)

    mock_bank_client.get_account_transactions.assert_called_once_with(
        "test_external_123", date_from=(LATEST - timedelta(days=7)).isoformat()
    )


# Importing


def test_imports_new_booked_transactions(
    db, test_account, test_transactions, mock_bank_client
):
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [booked("ext_3", amount="150.00", creditorName="Netto")]
    )

    count = sync_account(db, mock_bank_client, test_account.id)

    assert count == 1
    new = db.scalars(select(Transaction).where(Transaction.import_key == "ext_3")).one()
    assert new.amount_minor == 15000
    assert new.payee == "Netto"


def test_already_imported_rows_are_skipped(
    db, test_account, test_transactions, mock_bank_client
):
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [booked("ext_2", booking_date="2026-04-03")]
    )

    assert sync_account(db, mock_bank_client, test_account.id) == 0
    assert len(stored(db)) == 2


def test_same_day_as_latest_is_still_imported(
    db, test_account, test_transactions, mock_bank_client
):
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [booked("ext_same_day", booking_date="2026-04-03")]
    )

    assert sync_account(db, mock_bank_client, test_account.id) == 1


def test_empty_response(db, test_account, test_transactions, mock_bank_client):
    assert sync_account(db, mock_bank_client, test_account.id) == 0


# Pending


def pending_descriptions(db) -> list[str]:
    return list(db.scalars(select(PendingTransaction.description)))


def test_booked_only_into_transactions(db, test_account, mock_bank_client):
    mock_bank_client.get_account_transactions.return_value = bank_response(
        booked=[booked("ext_booked")],
        pending=[booked("ext_pending", remittanceInformationUnstructured="Taxi")],
    )

    assert sync_account(db, mock_bank_client, test_account.id) == 1
    assert [t.import_key for t in stored(db)] == ["ext_booked"]
    assert pending_descriptions(db) == ["Taxi"]


def test_pending_replaced_each_sync(db, test_account, mock_bank_client):
    taxi = booked("p-1", remittanceInformationUnstructured="Taxi")
    mock_bank_client.get_account_transactions.return_value = bank_response(
        pending=[taxi]
    )
    sync_account(db, mock_bank_client, test_account.id)

    # The bank has booked the taxi under a new ID; it is no longer pending.
    mock_bank_client.get_account_transactions.return_value = bank_response(
        booked=[booked("b-1", remittanceInformationUnstructured="Taxi")]
    )
    sync_account(db, mock_bank_client, test_account.id)

    assert pending_descriptions(db) == []
    assert [t.description for t in stored(db)] == ["Taxi"]


def test_pending_without_booking_date_keeps_the_window(
    db, test_account, test_transactions, mock_bank_client
):
    undated = booked("p-1")
    del undated["bookingDate"]
    mock_bank_client.get_account_transactions.return_value = bank_response(
        pending=[undated]
    )

    sync_account(db, mock_bank_client, test_account.id)

    assert db.scalars(select(PendingTransaction.booking_date)).one() is None
    assert sync_start(db, test_account.id, today=TODAY) == LATEST - timedelta(days=7)


# Dedup keys


def test_key_falls_back_to_internal_id_then_hash():
    keys = import_keys(
        [
            booked("bank-id", internalTransactionId="gc-id"),
            booked(None, internalTransactionId="gc-id"),
            booked(None),
        ]
    )

    assert keys[:2] == ["bank-id", "gc-id"]
    assert keys[2].startswith("hash:")


def test_rows_without_ids_are_imported_once(db, test_account, mock_bank_client):
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [booked(None, internalTransactionId="gc-1"), booked(None, amount="-99.00")]
    )

    assert sync_account(db, mock_bank_client, test_account.id) == 2
    assert sync_account(db, mock_bank_client, test_account.id) == 0


def test_identical_rows_same_day_are_both_kept(db, test_account, mock_bank_client):
    coffee = booked(None)
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [coffee, dict(coffee)]
    )

    assert sync_account(db, mock_bank_client, test_account.id) == 2
    assert sync_account(db, mock_bank_client, test_account.id) == 0


def test_duplicate_id_in_one_response_is_inserted_once(
    db, test_account, mock_bank_client
):
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [booked("dup"), booked("dup")]
    )

    assert sync_account(db, mock_bank_client, test_account.id) == 1


def test_booked_row_without_a_date_is_skipped(db, test_account, mock_bank_client):
    undated = booked("no-date")
    del undated["bookingDate"], undated["valueDate"]
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [undated, booked("ok")]
    )

    assert sync_account(db, mock_bank_client, test_account.id) == 1


# Descriptions


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"remittanceInformationUnstructuredArray": ["Line 1", "Line 2"]}, "Line 1"),
        ({"remittanceInformationUnstructuredArray": []}, "Coffee"),
        (
            {
                "remittanceInformationUnstructured": None,
                "additionalInformation": "Extra",
            },
            "Extra",
        ),
        ({"remittanceInformationUnstructured": None, "debtorName": "Bob"}, "Bob"),
        ({"remittanceInformationUnstructured": None}, "No description"),
    ],
)
def test_description_fallbacks(db, test_account, mock_bank_client, fields, expected):
    mock_bank_client.get_account_transactions.return_value = bank_response(
        [booked(**fields)]
    )

    sync_account(db, mock_bank_client, test_account.id)

    assert stored(db)[0].description == expected


# Balance, sync time and errors


def balance(balance_type: str, amount: str) -> Any:
    return {
        "balanceType": balance_type,
        "balanceAmount": {"amount": amount, "currency": "DKK"},
    }


def test_balance_prefers_booked_over_available():
    balances = [
        balance("interimAvailable", "15000.00"),
        balance("interimBooked", "5000.00"),
    ]

    assert balance_minor(balances) == 500000


def test_balance_falls_back_to_the_first_unknown_type():
    assert balance_minor([balance("someBankSpecific", "12.34")]) == 1234


def test_no_balances_is_zero():
    assert balance_minor([]) == 0


def test_updates_balance_and_sync_time(db, test_account, mock_bank_client):
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "2500.50", "currency": "DKK"}}]
    }

    sync_account(db, mock_bank_client, test_account.id)

    db.refresh(test_account)
    assert test_account.balance_minor == 250050
    assert test_account.last_synced_at is not None


def test_failed_balance_refresh_keeps_imported_transactions(
    db, test_account, mock_bank_client
):
    mock_bank_client.get_account_transactions.return_value = bank_response([booked()])
    mock_bank_client.get_account_balances.side_effect = HTTPError("503")

    assert sync_account(db, mock_bank_client, test_account.id) == 1
    assert len(stored(db)) == 1


def test_client_error_becomes_bank_api_error(db, test_account, mock_bank_client):
    response = Response()
    response.status_code = 429
    response._content = b'{"summary": "Rate limit exceeded", "detail": "Try later"}'
    mock_bank_client.get_account_transactions.side_effect = HTTPError(response=response)

    with pytest.raises(BankAPIError, match=r"Rate limit exceeded \(Try later\)"):
        sync_account(db, mock_bank_client, test_account.id)
