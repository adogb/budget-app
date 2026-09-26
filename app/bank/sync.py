"""Fetching new transactions and the balance for an account from the bank."""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from requests import RequestException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bank.client import GoCardlessBankDataClient
from app.bank.client_models import GCTransaction
from app.models import Account, Transaction
from app.money import to_minor_units

logger = logging.getLogger(__name__)

FIRST_SYNC_DAYS = 90


def sync_account(
    db: Session, client: GoCardlessBankDataClient, account_id: int
) -> dict[str, Any]:
    """Import transactions since the latest one we have, then refresh the balance.

    Returns `new_transactions_count` and `last_synced`.
    """
    account = db.get(Account, account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found")
    if not account.external_id:
        raise ValueError(f"Account {account_id} has no external_id")

    # Inclusive, so transactions booked later on that same day aren't missed.
    latest = latest_booking_date(db, account_id)
    if latest is None:
        date_from = datetime.now(UTC).date() - timedelta(days=FIRST_SYNC_DAYS)
    else:
        date_from = latest
    logger.info("Syncing %s from %s", account.name, date_from)

    response = client.get_account_transactions(
        account.external_id, date_from=date_from.isoformat()
    )
    bank_transactions = response.get("transactions", {})
    fetched = bank_transactions.get("booked", []) + bank_transactions.get("pending", [])

    new_transactions = [
        _to_model(data, account) for data in fetched if _is_new(db, data)
    ]
    db.add_all(new_transactions)
    db.commit()
    logger.info("Imported %d new transactions", len(new_transactions))

    _refresh_balance(db, client, account)

    return {
        "new_transactions_count": len(new_transactions),
        "last_synced": datetime.now(UTC),
    }


def latest_booking_date(db: Session, account_id: int) -> date | None:
    query = (
        select(Transaction.booking_date)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.booking_date.desc())
    )
    return db.scalars(query).first()


def transaction_exists(db: Session, bank_transaction_id: str) -> bool:
    query = select(Transaction.id).where(
        Transaction.bank_transaction_id == bank_transaction_id
    )
    return db.scalars(query).first() is not None


def _is_new(db: Session, data: GCTransaction) -> bool:
    bank_transaction_id = data.get("transactionId")
    if not bank_transaction_id:
        logger.warning("Skipping transaction without transactionId: %s", data)
        return False
    return not transaction_exists(db, bank_transaction_id)


def _to_model(data: GCTransaction, account: Account) -> Transaction:
    amount = data.get("transactionAmount", {})
    booking_date = data.get("bookingDate")
    value_date = data.get("valueDate")
    description = (
        data.get("remittanceInformationUnstructuredArray", [None])[0]
        or data.get("remittanceInformationUnstructured")
        or data.get("additionalInformation")
        or "No description"
    )
    return Transaction(
        account_id=account.id,
        bank_transaction_id=data.get("transactionId"),
        gc_transaction_id=data.get("internalTransactionId"),
        amount_minor=to_minor_units(amount.get("amount", "0")),
        currency=amount.get("currency", account.currency),
        description=description[:255],
        booking_date=(
            date.fromisoformat(booking_date)
            if booking_date
            else datetime.now(UTC).date()
        ),
        value_date=date.fromisoformat(value_date) if value_date else None,
    )


def _refresh_balance(
    db: Session, client: GoCardlessBankDataClient, account: Account
) -> None:
    # A failed balance refresh shouldn't undo the imported transactions.
    try:
        balances = client.get_account_balances(account.external_id)["balances"]
    except RequestException:
        logger.exception("Could not refresh the balance of %s", account.name)
        return
    if balances:
        account.balance_minor = to_minor_units(balances[0]["balanceAmount"]["amount"])
        db.commit()
