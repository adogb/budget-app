"""Fetching new transactions and the balance for an account from the bank."""

import hashlib
import logging
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from requests import RequestException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.bank.client import GoCardlessBankDataClient
from app.bank.client_models import GCTransaction
from app.bank.errors import BankAPIError
from app.models import Account, BankIntegration, PendingTransaction, Transaction
from app.money import to_minor_units

logger = logging.getLogger(__name__)

FIRST_SYNC_DAYS = 90
# Banks sometimes book a transaction days after its booking date, so each sync
# looks back a week. The import key stops the overlap from creating duplicates.
OVERLAP_DAYS = 7


@dataclass
class SyncResult:
    account: Account
    new_transactions: int | None = None
    error: str | None = None


def sync_all(db: Session, client: GoCardlessBankDataClient) -> list[SyncResult]:
    """Sync every linked account. One failing account doesn't stop the others."""
    accounts = list(
        db.scalars(
            select(Account)
            .join(Account.bank_integration)
            .where(BankIntegration.linked_at.is_not(None))
            .order_by(Account.name)
        )
    )
    now = datetime.now(UTC)
    results = []
    for account in accounts:
        expires_at = account.bank_integration.expires_at
        if expires_at is not None and expires_at <= now:
            # Don't spend a rate-limited call on a request the bank will refuse.
            results.append(SyncResult(account, error="Consent expired: renew the link"))
            continue
        try:
            count = sync_account(db, client, account.id)
        except BankAPIError as e:
            db.rollback()
            results.append(SyncResult(account, error=str(e)))
        else:
            results.append(SyncResult(account, new_transactions=count))
    return results


def sync_account(db: Session, client: GoCardlessBankDataClient, account_id: int) -> int:
    """Import new booked transactions, replace the pending ones, refresh the
    balance. Returns the number of new booked transactions."""
    account = db.get(Account, account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found")
    if not account.external_id:
        raise ValueError(f"Account {account_id} has no external_id")

    date_from = sync_start(db, account_id)
    logger.info("Syncing %s from %s", account.name, date_from)
    try:
        response = client.get_account_transactions(
            account.external_id, date_from=date_from.isoformat()
        )
    except RequestException as e:
        raise BankAPIError.from_request(
            f"Could not fetch transactions for {account.name}", e
        ) from e
    bank_transactions = response.get("transactions", {})

    new_transactions = _new_transactions(
        db, account, bank_transactions.get("booked", [])
    )
    db.add_all(new_transactions)
    _replace_pending(db, account, bank_transactions.get("pending", []))
    _refresh_balance(client, account)
    account.last_synced_at = datetime.now(UTC)
    db.commit()
    logger.info("Imported %d new transactions", len(new_transactions))
    return len(new_transactions)


def sync_start(db: Session, account_id: int) -> date:
    latest = db.scalars(
        select(Transaction.booking_date)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.booking_date.desc())
    ).first()
    if latest is None:
        return datetime.now(UTC).date() - timedelta(days=FIRST_SYNC_DAYS)
    return latest - timedelta(days=OVERLAP_DAYS)


def import_keys(rows: Iterable[GCTransaction]) -> list[str]:
    """One dedup key per row: the bank's ID, or else a hash of its contents.

    Identical rows without an ID (two 35 kr coffees on the same day) get a
    counter in the hash so both are kept. The counter is the same on every sync
    because the sync window always covers whole days.
    """
    seen: Counter[str] = Counter()
    keys = []
    for data in rows:
        key = data.get("transactionId") or data.get("internalTransactionId")
        if not key:
            amount = data.get("transactionAmount", {})
            fingerprint = "|".join(
                [
                    data.get("bookingDate", ""),
                    amount.get("amount", ""),
                    amount.get("currency", ""),
                    _description(data),
                ]
            )
            occurrence = seen[fingerprint]
            seen[fingerprint] += 1
            digest = hashlib.sha256(f"{fingerprint}|{occurrence}".encode())
            key = f"hash:{digest.hexdigest()}"
        keys.append(key)
    return keys


def _new_transactions(
    db: Session, account: Account, rows: list[GCTransaction]
) -> list[Transaction]:
    keys = import_keys(rows)
    already_imported = set(
        db.scalars(
            select(Transaction.import_key).where(
                Transaction.account_id == account.id,
                Transaction.import_key.in_(keys),
            )
        )
    )
    new_transactions = []
    for key, data in zip(keys, rows, strict=True):
        if key in already_imported:
            continue
        if not (data.get("bookingDate") or data.get("valueDate")):
            logger.warning("Skipping booked transaction without a date: %s", data)
            continue
        # Also skips a key the bank repeats within one response.
        already_imported.add(key)
        new_transactions.append(_to_transaction(data, account, key))
    return new_transactions


def _to_transaction(data: GCTransaction, account: Account, key: str) -> Transaction:
    amount = data.get("transactionAmount", {})
    value_date = data.get("valueDate")
    return Transaction(
        account_id=account.id,
        import_key=key,
        bank_transaction_id=data.get("transactionId"),
        gc_transaction_id=data.get("internalTransactionId"),
        amount_minor=to_minor_units(amount.get("amount", "0")),
        currency=amount.get("currency", account.currency),
        description=_description(data),
        payee=_payee(data),
        booking_date=date.fromisoformat(data.get("bookingDate") or data["valueDate"]),
        value_date=date.fromisoformat(value_date) if value_date else None,
    )


def _replace_pending(db: Session, account: Account, rows: list[GCTransaction]) -> None:
    """Pending IDs change once booked, so keep only the bank's current list."""
    db.execute(
        delete(PendingTransaction).where(PendingTransaction.account_id == account.id)
    )
    for data in rows:
        amount = data.get("transactionAmount", {})
        booking_date = data.get("bookingDate")
        value_date = data.get("valueDate")
        db.add(
            PendingTransaction(
                account_id=account.id,
                amount_minor=to_minor_units(amount.get("amount", "0")),
                currency=amount.get("currency", account.currency),
                description=_description(data),
                payee=_payee(data),
                booking_date=date.fromisoformat(booking_date) if booking_date else None,
                value_date=date.fromisoformat(value_date) if value_date else None,
            )
        )


def _description(data: GCTransaction) -> str:
    candidates = [
        *data.get("remittanceInformationUnstructuredArray", []),
        data.get("remittanceInformationUnstructured"),
        data.get("additionalInformation"),
        _payee(data),
    ]
    return next((c for c in candidates if c), "No description")[:255]


def _payee(data: GCTransaction) -> str | None:
    payee = data.get("creditorName") or data.get("debtorName")
    return payee[:255] if payee else None


def _refresh_balance(client: GoCardlessBankDataClient, account: Account) -> None:
    # A failed balance refresh shouldn't undo the imported transactions.
    try:
        balances = client.get_account_balances(account.external_id)["balances"]
    except RequestException:
        logger.exception("Could not refresh the balance of %s", account.name)
        return
    if balances:
        account.balance_minor = to_minor_units(balances[0]["balanceAmount"]["amount"])
