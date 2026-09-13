"""
Service for synchronizing transactions from external bank APIs.

Orchestrates the sync operation by coordinating AccountService, TransactionService,
and the GoCardless bank client.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.db.models import Transaction as TransactionDB
from app.db.repositories.account_repository import AccountRepository
from app.db.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class SyncService:
    """Service for syncing transactions from external bank APIs."""

    def __init__(
        self,
        db_session: Session,
        bank_client: GoCardlessBankDataClient,
        user_id: int = 1,
    ):
        """
        Initialize SyncService.

        Args:
            db_session: Database session for repository operations
            bank_client: GoCardless bank client for API operations
            user_id: The user ID (default 1 for MVP single-user)
        """
        self.transaction_repo = TransactionRepository(db_session)
        self.account_repo = AccountRepository(db_session)
        self.bank_client = bank_client
        self.user_id = user_id
        self.db_session = db_session

    def sync_account_transactions(self, account_id: int) -> dict[str, Any]:
        """
        Sync transactions for an account from the bank API.

        Fetches new transactions since the last sync (based on latest transaction date)
        and saves them to the database. Also updates the account balance.

        Args:
            account_id: The internal account ID

        Returns:
            Dict with 'new_transactions_count' (int) and 'last_synced' (datetime)

        Raises:
            ValueError: If account not found or bank_client not configured
            Exception: If API call fails
        """
        if not self.bank_client:
            raise ValueError("Bank client not configured for sync")

        # Get the account
        account = self.account_repo.get_by_id(str(account_id))
        if not account or account.user_id != self.user_id:
            raise ValueError(f"Account {account_id} not found")

        if not account.external_id:
            raise ValueError(f"Account {account_id} has no external_id")

        logger.info(f"Starting sync for account {account.name} (ID: {account_id})")

        # Determine the date_from parameter
        latest_transaction_date = self.transaction_repo.get_latest_transaction_date(
            account_id
        )

        if latest_transaction_date:
            # Use the latest transaction date (inclusive) to avoid missing same-day transactions
            date_from = latest_transaction_date.isoformat()
            logger.info(
                f"Syncing transactions from {date_from} (latest transaction date)"
            )
        else:
            # No transactions exist, fetch last 90 days
            date_from = (datetime.now(UTC).date() - timedelta(days=90)).isoformat()
            logger.info(
                f"No existing transactions, syncing from {date_from} (90 days ago)"
            )

        # Fetch transactions from the bank API
        logger.info(
            f"Fetching transactions from GoCardless for account {account.external_id}"
        )
        transactions_data = self.bank_client.get_account_transactions(
            account.external_id, date_from=date_from
        )

        # Extract booked and pending transactions
        all_transactions = []
        if "transactions" in transactions_data:
            all_transactions.extend(transactions_data["transactions"].get("booked", []))
            all_transactions.extend(
                transactions_data["transactions"].get("pending", [])
            )

        logger.info(f"Received {len(all_transactions)} transactions from API")

        # Convert API transactions to database models
        new_transactions = self._convert_transactions(
            all_transactions, account_id, account.currency
        )

        # Bulk insert new transactions
        if new_transactions:
            logger.info(f"Inserting {len(new_transactions)} new transactions")
            self.transaction_repo.create_bulk(new_transactions)
        else:
            logger.info("No new transactions to insert")

        # Update account balance
        self._update_account_balance(account)

        return {
            "new_transactions_count": len(new_transactions),
            "last_synced": datetime.now(UTC),
        }

    def _convert_transactions(
        self,
        api_transactions: list,
        account_id: int,
        default_currency: str,
    ) -> list[TransactionDB]:
        """
        Convert API transaction data to database models, filtering out duplicates.

        Args:
            api_transactions: List of transactions from GoCardless API
            account_id: The account ID to associate with
            default_currency: Default currency if not specified in transaction

        Returns:
            List of new Transaction database models (duplicates filtered out)
        """
        new_transactions = []

        for trans_data in api_transactions:
            # Get transaction IDs
            bank_transaction_id = trans_data.get("transactionId")
            gc_transaction_id = trans_data.get("internalTransactionId")

            if not bank_transaction_id:
                logger.warning(
                    f"Skipping transaction without transactionId: {trans_data}"
                )
                continue

            # Check if transaction already exists using bank_transaction_id
            if self.transaction_repo.exists_by_bank_transaction_id(bank_transaction_id):
                logger.debug(
                    f"Transaction {bank_transaction_id} already exists, skipping"
                )
                continue

            # Parse transaction data
            amount_str = trans_data.get("transactionAmount", {}).get("amount", "0")
            amount_cents = int(float(amount_str) * 100)

            booking_date_str = trans_data.get("bookingDate")
            value_date_str = trans_data.get("valueDate")

            # Parse dates (convert from ISO string to date object)
            booking_date = (
                datetime.strptime(booking_date_str, "%Y-%m-%d").date()
                if booking_date_str
                else datetime.now(UTC).date()
            )
            value_date = (
                datetime.strptime(value_date_str, "%Y-%m-%d").date()
                if value_date_str
                else None
            )

            # Get description (try array first, then fallback to single field)
            description = (
                trans_data.get("remittanceInformationUnstructuredArray", [None])[0]
                or trans_data.get("remittanceInformationUnstructured")
                or trans_data.get("additionalInformation")
                or "No description"
            )

            # Create transaction model
            transaction = TransactionDB(
                user_id=self.user_id,
                account_id=account_id,
                bank_transaction_id=bank_transaction_id,
                gc_transaction_id=gc_transaction_id,
                amount_cents=amount_cents,
                currency=trans_data.get("transactionAmount", {}).get(
                    "currency", default_currency
                ),
                description=description[:255],  # Truncate to fit column
                booking_date=booking_date,
                value_date=value_date,
            )
            new_transactions.append(transaction)

        return new_transactions

    def _update_account_balance(self, account) -> None:
        """
        Update account balance from the bank API.

        Args:
            account: Account database model to update
        """
        try:
            logger.info(f"Fetching balance for account {account.external_id}")
            balances_data = self.bank_client.get_account_balances(account.external_id)

            if balances_data.get("balances"):
                balance_amount = balances_data["balances"][0]["balanceAmount"]["amount"]
                old_balance = account.balance
                account.balance = float(balance_amount)
                self.account_repo.update(account)
                logger.info(
                    f"Updated balance for account {account.name}: "
                    f"{old_balance} -> {account.balance}"
                )
        except Exception as e:
            logger.error(f"Failed to update balance for account {account.name}: {e}")
            # Don't fail the whole sync if balance update fails
