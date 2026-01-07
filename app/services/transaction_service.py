"""
Service for managing transaction operations.

Handles business logic for fetching and processing transaction data.
"""

from typing import List, Optional
from datetime import date, datetime, timedelta

from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.services.config_service import ConfigService
from app.services.exceptions import BankAPIError
from app.models.responses import TransactionResponse


class TransactionService:
    """Service for transaction-related operations."""

    def __init__(
        self, bank_client: GoCardlessBankDataClient, config_service: ConfigService
    ):
        """
        Initialize TransactionService.

        Args:
            bank_client: Client for bank API operations
            config_service: Service for config operations
        """
        self.bank_client = bank_client
        self.config_service = config_service

    def _get_default_date_range(self) -> tuple[date, date]:
        """
        Get default date range for transactions (last 30 days).

        Returns:
            Tuple of (from_date, to_date)
        """
        to_date = datetime.now().date()
        from_date = (datetime.now() - timedelta(days=30)).date()
        return from_date, to_date

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """
        Parse date string in YYYY-MM-DD format.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed date or None if empty/invalid
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _extract_transaction_from_raw(
        self, raw_tx: dict, account_id: str
    ) -> Optional[TransactionResponse]:
        """
        Extract and format a single transaction from raw API response.

        Args:
            raw_tx: Raw transaction data from API
            account_id: Account ID the transaction belongs to

        Returns:
            TransactionResponse or None if extraction fails
        """
        try:
            # Extract transaction details
            tx_id = raw_tx.get("internalTransactionId", "")
            booking_date_str = raw_tx.get("bookingDate", "")
            value_date_str = raw_tx.get("valueDate", "")

            # Parse the amount
            amount_str = raw_tx.get("transactionAmount", {}).get("amount", "0")
            currency = raw_tx.get("transactionAmount", {}).get("currency", "")

            # Get transaction description
            description = raw_tx.get("remittanceInformationUnstructured", "")
            if not description:
                description = raw_tx.get("additionalInformation", "")

            # Parse dates
            booking_date = self._parse_date_string(booking_date_str)
            value_date = self._parse_date_string(value_date_str)

            # Create transaction response
            return TransactionResponse(
                id=tx_id,
                account_id=account_id,
                amount=float(amount_str),
                currency=currency,
                description=description,
                booking_date=booking_date,
                value_date=value_date,
                category=None,  # Categorization to be implemented later
            )
        except Exception as e:
            print(f"Error processing transaction in account {account_id}: {str(e)}")
            return None

    def _fetch_transactions_for_account(
        self, account_id: str, date_from: str, date_to: str
    ) -> List[TransactionResponse]:
        """
        Fetch transactions for a single account.

        Args:
            account_id: Account ID to fetch transactions for
            date_from: Start date in ISO format
            date_to: End date in ISO format

        Returns:
            List of TransactionResponse objects
        """
        transactions = []

        try:
            # Get transactions for this account with date filtering
            raw_transactions = self.bank_client.get_account_transactions_paginated(
                account_id, date_from=date_from, date_to=date_to
            )

            # Process booked transactions (confirmed)
            for raw_tx in raw_transactions.get("transactions", {}).get("booked", []):
                transaction = self._extract_transaction_from_raw(raw_tx, account_id)
                if transaction:
                    transactions.append(transaction)

        except Exception as e:
            print(f"Error fetching transactions for account {account_id}: {str(e)}")
            # Continue with other accounts instead of failing completely

        return transactions

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[TransactionResponse]:
        """
        Get transactions with optional filtering.

        Args:
            account_id: Optional specific account ID (None = all accounts)
            from_date: Optional start date (None = 30 days ago)
            to_date: Optional end date (None = today)

        Returns:
            List of TransactionResponse objects, sorted by booking date (newest first)

        Raises:
            SetupNotCompleteError: If setup hasn't been completed
        """
        # Ensure setup is complete
        self.config_service.require_setup_complete()

        # Determine which accounts to query
        if account_id:
            account_ids = [account_id]
        else:
            account_ids = self.config_service.get_selected_accounts()

        if not account_ids:
            return []

        # Set default date range if not provided
        if not from_date or not to_date:
            default_from, default_to = self._get_default_date_range()
            from_date = from_date or default_from
            to_date = to_date or default_to

        # Convert to ISO format strings for API
        date_from = from_date.isoformat()
        date_to = to_date.isoformat()

        # Fetch transactions for each account
        all_transactions = []
        for acc_id in account_ids:
            account_transactions = self._fetch_transactions_for_account(
                acc_id, date_from, date_to
            )
            all_transactions.extend(account_transactions)

        # Sort by booking date (newest first)
        all_transactions.sort(key=lambda x: x.booking_date, reverse=True)

        return all_transactions
