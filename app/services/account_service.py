"""
Service for managing bank account operations.

Handles business logic for fetching and processing account data.
"""

from typing import List

from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.services.config_service import ConfigService
from app.services.exceptions import BankAPIError
from app.models.responses import AccountResponse


class AccountService:
    """Service for account-related operations."""

    def __init__(
        self, bank_client: GoCardlessBankDataClient, config_service: ConfigService
    ):
        """
        Initialize AccountService.

        Args:
            bank_client: Client for bank API operations
            config_service: Service for config operations
        """
        self.bank_client = bank_client
        self.config_service = config_service

    def _extract_account_balance(self, balances_data: dict) -> tuple[str, str]:
        """
        Extract the available balance from balances API response.

        Args:
            balances_data: Raw balances response from bank API

        Returns:
            Tuple of (balance_amount, currency)
        """
        balance_amount = "0"
        currency = ""

        for balance in balances_data.get("balances", []):
            if balance.get("balanceType") == "interimAvailable":
                balance_amount = balance.get("balanceAmount", {}).get("amount", "0")
                currency = balance.get("balanceAmount", {}).get("currency", "")
                break

        return balance_amount, currency

    def _fetch_account_response(self, account_id: str) -> AccountResponse:
        """
        Fetch account details and balances, return formatted response.

        Args:
            account_id: The account ID to fetch

        Returns:
            AccountResponse with account data

        Raises:
            BankAPIError: If fetching account data fails
        """
        try:
            # Fetch account details and balances
            details = self.bank_client.get_account_details(account_id)
            balances = self.bank_client.get_account_balances(account_id)

            # Extract account name
            account_name = details.get("account", {}).get("name", "Account")

            # Extract balance and currency
            balance_amount, currency = self._extract_account_balance(balances)

            # Create account response
            return AccountResponse(
                id=account_id,
                name=account_name,
                iban=details.get("account", {}).get("iban", ""),
                balance=float(balance_amount),
                currency=currency,
            )
        except Exception as e:
            raise BankAPIError(
                f"Failed to fetch account data: {str(e)}", account_id=account_id
            ) from e

    def get_all_accounts(self) -> List[AccountResponse]:
        """
        Get all user's configured bank accounts.

        Returns:
            List of AccountResponse objects

        Raises:
            SetupNotCompleteError: If setup hasn't been completed
            BankAPIError: If fetching account data fails
        """
        # Ensure setup is complete
        self.config_service.require_setup_complete()

        # Get selected account IDs
        account_ids = self.config_service.get_selected_accounts()
        if not account_ids:
            return []

        # Fetch details for each account
        accounts = []
        for account_id in account_ids:
            try:
                account = self._fetch_account_response(account_id)
                accounts.append(account)
            except BankAPIError as e:
                # Log the error but continue with other accounts
                print(f"Error fetching account {account_id}: {str(e)}")
                # In production, use proper logging instead of print
                continue

        return accounts

    def get_account_by_id(self, account_id: str) -> AccountResponse:
        """
        Get a specific account by ID.

        Args:
            account_id: The account ID to fetch

        Returns:
            AccountResponse with account data

        Raises:
            BankAPIError: If fetching account data fails
        """
        return self._fetch_account_response(account_id)
