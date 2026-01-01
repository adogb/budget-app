"""
AccountManager module for Budget App.

This module provides functions for managing bank accounts and account data.
"""

import os
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.services.gc_bank_data import GoCardlessBankDataClient


class AccountResponse(BaseModel):
    """Response model for account data."""

    id: str
    name: str
    iban: Optional[str] = None
    balance: float
    currency: str


class AccountManager:
    """Service for managing bank accounts."""

    # Path to the user configuration file
    CONFIG_DIR = os.path.join(os.getcwd(), "config")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")

    @classmethod
    def is_setup_completed(cls) -> bool:
        """Check if bank setup has been completed."""
        return os.path.exists(cls.CONFIG_FILE)

    @classmethod
    def get_configured_account_ids(cls) -> List[str]:
        """Get the list of configured account IDs from user config."""
        if not cls.is_setup_completed():
            return []

        try:
            with open(cls.CONFIG_FILE, "r") as f:
                config = json.load(f)
            return config.get("selected_accounts", [])
        except Exception:
            return []

    @classmethod
    def fetch_account_details(
        cls, account_id: str, client: GoCardlessBankDataClient
    ) -> Optional[AccountResponse]:
        """
        Fetch account details and balances for a specific account.

        Args:
            account_id: The account ID to fetch
            client: The GoCardless bank data client

        Returns:
            AccountResponse object or None if error occurred
        """
        try:
            details = client.get_account_details(account_id)
            balances = client.get_account_balances(account_id)

            # Extract account information
            account_name = details.get("account", {}).get("name", "Account")
            iban = details.get("account", {}).get("iban", "")

            # Find the current balance
            balance_amount = "0"
            currency = ""
            for balance in balances.get("balances", []):
                if balance.get("balanceType") == "interimAvailable":
                    balance_amount = balance.get("balanceAmount", {}).get("amount", "0")
                    currency = balance.get("balanceAmount", {}).get("currency", "")
                    break

            return AccountResponse(
                id=account_id,
                name=account_name,
                iban=iban,
                balance=float(balance_amount),
                currency=currency,
            )
        except Exception as e:
            # Log the error but don't raise - let caller handle
            print(f"Error fetching account {account_id}: {str(e)}")
            return None

    @classmethod
    def get_all_accounts(
        cls, client: GoCardlessBankDataClient
    ) -> List[AccountResponse]:
        """
        Get all configured bank accounts.

        Args:
            client: The GoCardless bank data client

        Returns:
            List of AccountResponse objects
        """
        account_ids = cls.get_configured_account_ids()
        if not account_ids:
            return []

        accounts = []
        for account_id in account_ids:
            account = cls.fetch_account_details(account_id, client)
            if account:
                accounts.append(account)

        return accounts

    @classmethod
    def get_account_by_id(
        cls, account_id: str, client: GoCardlessBankDataClient
    ) -> Optional[AccountResponse]:
        """
        Get a specific account by ID.

        Args:
            account_id: The account ID to fetch
            client: The GoCardless bank data client

        Returns:
            AccountResponse object or None if not found
        """
        return cls.fetch_account_details(account_id, client)
