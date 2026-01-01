"""
Accounts router for Budget App.

This module provides API endpoints for managing bank accounts.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.dependencies import get_bank_client
from app.services.gc_bank_data import GoCardlessBankDataClient
from app.services.account_manager import AccountManager, AccountResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=List[AccountResponse])
def list_accounts(client: GoCardlessBankDataClient = Depends(get_bank_client)):
    """List all connected bank accounts."""
    # Check if setup has been completed
    if not AccountManager.is_setup_completed():
        raise HTTPException(
            status_code=400,
            detail="Bank setup not completed. Please visit /setup first.",
        )

    try:
        accounts = AccountManager.get_all_accounts(client)
        return accounts
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str, client: GoCardlessBankDataClient = Depends(get_bank_client)
):
    """Get details for a specific account."""
    try:
        account = AccountManager.get_account_by_id(account_id, client)
        if not account:
            raise HTTPException(
                status_code=404, detail=f"Account {account_id} not found"
            )
        return account
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve account: {str(e)}"
        )
