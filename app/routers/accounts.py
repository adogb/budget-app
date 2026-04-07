from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.dependencies import get_account_service, get_sync_service, get_transaction_service
from app.services.account_service import AccountService
from app.services.sync_service import SyncService
from app.services.transaction_service import TransactionService
from app.models.responses import AccountResponse
from typing import List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["accounts"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_model=List[AccountResponse])
def list_accounts(account_service: AccountService = Depends(get_account_service)):
    """List all connected bank accounts"""
    return account_service.get_all_accounts()


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str, account_service: AccountService = Depends(get_account_service)
):
    """Get details for a specific account"""
    return account_service.get_account_by_id(account_id)


@router.post("/sync", response_class=HTMLResponse)
def sync_accounts(
    request: Request,
    sync_service: SyncService = Depends(get_sync_service),
    account_service: AccountService = Depends(get_account_service),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Sync transactions for all accounts from the bank API.
    Returns updated HTML for transactions table, accounts sidebar, and sync status.
    """
    logger.info("Starting transaction sync...")
    total_new_transactions = 0
    sync_errors = []
    last_synced = datetime.now()

    # Get all accounts
    accounts = account_service.get_all_accounts()
    logger.info(f"Found {len(accounts)} accounts to sync")

    # Sync each account
    for account in accounts:
        try:
            logger.info(f"Syncing account {account.name} (ID: {account.id})...")
            result = sync_service.sync_account_transactions(int(account.id))
            total_new_transactions += result["new_transactions_count"]
            logger.info(
                f"Synced account {account.id}: {result['new_transactions_count']} new transactions"
            )
        except Exception as e:
            error_msg = f"Error syncing account {account.name}: {str(e)}"
            sync_errors.append(error_msg)
            logger.error(error_msg, exc_info=True)

    # Fetch updated data
    transactions = transaction_service.get_transactions(limit=100)
    updated_accounts = account_service.get_all_accounts()

    # Determine sync status message and style
    if sync_errors:
        sync_message = f"Synced with errors: {total_new_transactions} new transactions. {len(sync_errors)} account(s) failed."
        sync_status_class = "text-yellow-600"
    elif total_new_transactions > 0:
        sync_message = f"Success! Added {total_new_transactions} new transaction(s)."
        sync_status_class = "text-green-600"
    else:
        sync_message = "Already up to date. No new transactions."
        sync_status_class = "text-gray-600"

    # Render template response with HTMX OOB swaps
    return templates.TemplateResponse(
        "transactions/_sync_response.html",
        {
            "request": request,
            "transactions": transactions,
            "accounts": updated_accounts,
            "sync_message": sync_message,
            "sync_status_class": sync_status_class,
            "last_synced": last_synced,
        }
    )
