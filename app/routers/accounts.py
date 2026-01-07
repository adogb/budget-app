from fastapi import APIRouter, Depends
from app.dependencies import get_account_service
from app.services.account_service import AccountService
from app.models.responses import AccountResponse
from typing import List

router = APIRouter(prefix="/accounts", tags=["accounts"])


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
