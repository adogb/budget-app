from fastapi import APIRouter, Depends, HTTPException
from app.models.account import Account
from app.dependencies import get_bank_client
from app.services.gc_bank_data import GoCardlessBankDataClient
import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel

# Path to the user configuration file
CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountResponse(BaseModel):
    id: str
    name: str
    iban: Optional[str] = None
    balance: float
    currency: str


@router.get("/", response_model=List[AccountResponse])
def list_accounts(client: GoCardlessBankDataClient = Depends(get_bank_client)):
    """List all connected bank accounts"""
    # Check if setup has been completed
    if not os.path.exists(CONFIG_FILE):
        raise HTTPException(
            status_code=400,
            detail="Bank setup not completed. Please visit /setup first.",
        )

    try:
        # Load the configuration file
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        # Get the selected accounts from the config
        account_ids = config.get("selected_accounts", [])
        if not account_ids:
            return []

        # Fetch details for each account
        accounts = []
        for account_id in account_ids:
            try:
                details = client.get_account_details(account_id)
                balances = client.get_account_balances(account_id)

                # Get account name and current balance
                account_name = details.get("account", {}).get("name", "Account")

                balance_amount = "0"
                currency = ""
                for balance in balances.get("balances", []):
                    if balance.get("balanceType") == "interimAvailable":
                        balance_amount = balance.get("balanceAmount", {}).get(
                            "amount", "0"
                        )
                        currency = balance.get("balanceAmount", {}).get("currency", "")
                        break

                # Create account response
                accounts.append(
                    AccountResponse(
                        id=account_id,
                        name=account_name,
                        iban=details.get("account", {}).get("iban", ""),
                        balance=float(balance_amount),
                        currency=currency,
                    )
                )
            except Exception as e:
                # Log the error but continue with other accounts
                print(f"Error fetching account {account_id}: {str(e)}")

        return accounts
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str, client: GoCardlessBankDataClient = Depends(get_bank_client)
):
    """Get details for a specific account"""
    try:
        # Fetch the account details
        details = client.get_account_details(account_id)
        balances = client.get_account_balances(account_id)

        # Get account name and current balance
        account_name = details.get("account", {}).get("name", "Account")

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
            iban=details.get("account", {}).get("iban", ""),
            balance=float(balance_amount),
            currency=currency,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve account: {str(e)}"
        )
