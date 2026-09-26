"""Tests for syncing an account's transactions and balance from the bank."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from app.bank.client import GoCardlessBankDataClient
from app.bank.sync import latest_booking_date, sync_account, transaction_exists
from app.models import Account, Transaction


@pytest.fixture
def test_account(db):
    """Create a test account."""
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
    db.refresh(account)
    return account


@pytest.fixture
def test_transactions(db, test_account):
    """Create test transactions."""
    transactions = [
        Transaction(
            id="trans_1",
            account_id=test_account.id,
            bank_transaction_id="ext_1",
            gc_transaction_id="gc_1",
            amount_minor=10000,
            currency="DKK",
            description="Transaction 1",
            booking_date=date(2026, 4, 1),
        ),
        Transaction(
            id="trans_2",
            account_id=test_account.id,
            bank_transaction_id="ext_2",
            gc_transaction_id="gc_2",
            amount_minor=20000,
            currency="DKK",
            description="Transaction 2",
            booking_date=date(2026, 4, 3),
        ),
    ]
    db.add_all(transactions)
    db.commit()
    return transactions


# Query helpers


def test_exists_by_bank_transaction_id_true(db, test_transactions):
    """transaction_exists is True for an imported bank transaction ID."""
    assert transaction_exists(db, "ext_1") is True


def test_exists_by_bank_transaction_id_false(db, test_transactions):
    """transaction_exists is False for an unknown bank transaction ID."""
    assert transaction_exists(db, "non_existent") is False


def test_get_latest_transaction_date(db, test_transactions):
    """Test getting the latest transaction date for an account."""
    latest_date = latest_booking_date(db, 1)
    assert latest_date == date(2026, 4, 3)


def test_get_latest_transaction_date_no_transactions(db, test_account):
    """Test getting latest transaction date when no transactions exist."""
    latest_date = latest_booking_date(db, test_account.id)
    assert latest_date is None


# sync_account


@pytest.fixture
def mock_bank_client():
    """Create a mock GoCardless bank client."""
    return Mock(spec=GoCardlessBankDataClient)


def test_sync_account_transactions_with_existing_transactions(
    db, test_account, test_transactions, mock_bank_client
):
    """Test syncing when account has existing transactions."""
    # Mock API response with new transactions
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {
            "booked": [
                {
                    "transactionId": "ext_3",
                    "internalTransactionId": "gc_3",
                    "transactionAmount": {"amount": "150.00", "currency": "DKK"},
                    "bookingDate": "2026-04-04",
                    "valueDate": "2026-04-04",
                    "remittanceInformationUnstructured": "New Transaction 3",
                }
            ],
            "pending": [],
        }
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1150.00", "currency": "DKK"}}]
    }

    # Call sync
    result = sync_account(db, mock_bank_client, test_account.id)

    # Verify API was called with correct date
    mock_bank_client.get_account_transactions.assert_called_once_with(
        "test_external_123", date_from="2026-04-03"
    )

    # Verify result
    assert result["new_transactions_count"] == 1
    assert "last_synced" in result

    # Verify transaction was created
    assert transaction_exists(db, "ext_3") is True


def test_sync_account_transactions_no_duplicates(
    db, test_account, test_transactions, mock_bank_client
):
    """Test that duplicate transactions are not inserted."""
    # Mock API response with existing transaction
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {
            "booked": [
                {
                    "transactionId": "ext_2",  # Already exists
                    "transactionAmount": {"amount": "200.00", "currency": "DKK"},
                    "bookingDate": "2026-04-03",
                    "valueDate": "2026-04-03",
                    "remittanceInformationUnstructured": "Transaction 2",
                }
            ],
            "pending": [],
        }
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1000.00", "currency": "DKK"}}]
    }

    # Call sync
    result = sync_account(db, mock_bank_client, test_account.id)

    # Verify no new transactions were added
    assert result["new_transactions_count"] == 0

    # Verify only 2 transactions exist (original ones)
    all_trans = db.scalars(
        select(Transaction).where(Transaction.account_id == test_account.id)
    ).all()
    assert len(all_trans) == 2


def test_sync_account_transactions_new_account(db, test_account, mock_bank_client):
    """Test syncing an account with no existing transactions (should fetch 90 days)."""
    # Mock API response
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {
            "booked": [
                {
                    "transactionId": "ext_new",
                    "transactionAmount": {"amount": "100.00", "currency": "DKK"},
                    "bookingDate": "2026-04-01",
                    "valueDate": "2026-04-01",
                    "remittanceInformationUnstructured": "First Transaction",
                }
            ],
            "pending": [],
        }
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1100.00", "currency": "DKK"}}]
    }

    result = sync_account(db, mock_bank_client, test_account.id)

    # Verify API was called with 90 days ago
    expected_date = (datetime.now(UTC).date() - timedelta(days=90)).isoformat()
    mock_bank_client.get_account_transactions.assert_called_once_with(
        "test_external_123", date_from=expected_date
    )

    # Verify transaction was created
    assert result["new_transactions_count"] == 1


def test_sync_account_transactions_updates_balance(
    db, test_account, test_transactions, mock_bank_client
):
    """Test that account balance is updated after sync."""
    initial_balance = test_account.balance_minor

    # Mock API response
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {"booked": [], "pending": []}
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "2500.50", "currency": "DKK"}}]
    }

    # Call sync
    sync_account(db, mock_bank_client, test_account.id)

    # Verify balance was updated
    db.refresh(test_account)
    assert test_account.balance_minor == 250050
    assert test_account.balance_minor != initial_balance


def test_sync_account_transactions_api_error(db, test_account, mock_bank_client):
    """Test error handling when API call fails."""
    # Mock API to raise an exception
    mock_bank_client.get_account_transactions.side_effect = Exception("API Error")

    # Call sync and expect exception
    with pytest.raises(Exception, match="API Error"):
        sync_account(db, mock_bank_client, test_account.id)


def test_sync_account_transactions_date_formatting(
    db, test_account, test_transactions, mock_bank_client
):
    """Test that date is correctly formatted as ISO string."""
    # Mock API response
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {"booked": [], "pending": []}
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1000.00", "currency": "DKK"}}]
    }

    # Call sync
    sync_account(db, mock_bank_client, test_account.id)

    # Verify date format (YYYY-MM-DD)
    call_args = mock_bank_client.get_account_transactions.call_args
    date_from = call_args[1]["date_from"]
    assert date_from == "2026-04-03"  # Latest transaction date


def test_sync_with_same_day_transactions(
    db, test_account, test_transactions, mock_bank_client
):
    """Test inclusive date fetching to not miss same-day transactions."""
    # Mock API response with same-day transaction
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {
            "booked": [
                {
                    "transactionId": "ext_same_day",
                    "transactionAmount": {"amount": "50.00", "currency": "DKK"},
                    "bookingDate": "2026-04-03",  # Same as latest
                    "valueDate": "2026-04-03",
                    "remittanceInformationUnstructured": "Same day transaction",
                }
            ],
            "pending": [],
        }
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1050.00", "currency": "DKK"}}]
    }

    # Call sync
    result = sync_account(db, mock_bank_client, test_account.id)

    # Verify date_from includes the same day (inclusive)
    mock_bank_client.get_account_transactions.assert_called_once_with(
        "test_external_123", date_from="2026-04-03"
    )

    # Verify new transaction was added
    assert result["new_transactions_count"] == 1


def test_sync_empty_response(db, test_account, test_transactions, mock_bank_client):
    """Test handling when API returns no new transactions."""
    # Mock API response with empty transactions
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {"booked": [], "pending": []}
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1000.00", "currency": "DKK"}}]
    }

    # Call sync
    result = sync_account(db, mock_bank_client, test_account.id)

    # Verify no transactions were added
    assert result["new_transactions_count"] == 0


def test_sync_pending_and_booked_transactions(
    db, test_account, test_transactions, mock_bank_client
):
    """Test that both booked and pending transactions are synced."""
    # Mock API response with both types
    mock_bank_client.get_account_transactions.return_value = {
        "transactions": {
            "booked": [
                {
                    "transactionId": "ext_booked",
                    "transactionAmount": {"amount": "100.00", "currency": "DKK"},
                    "bookingDate": "2026-04-04",
                    "valueDate": "2026-04-04",
                    "remittanceInformationUnstructured": "Booked Transaction",
                }
            ],
            "pending": [
                {
                    "transactionId": "ext_pending",
                    "transactionAmount": {"amount": "50.00", "currency": "DKK"},
                    "bookingDate": "2026-04-05",
                    "valueDate": "2026-04-05",
                    "remittanceInformationUnstructured": "Pending Transaction",
                }
            ],
        }
    }
    mock_bank_client.get_account_balances.return_value = {
        "balances": [{"balanceAmount": {"amount": "1150.00", "currency": "DKK"}}]
    }

    # Call sync
    result = sync_account(db, mock_bank_client, test_account.id)

    # Verify both transactions were added
    assert result["new_transactions_count"] == 2

    # Verify both exist in database
    assert transaction_exists(db, "ext_booked") is True
    assert transaction_exists(db, "ext_pending") is True
