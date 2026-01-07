from fastapi import APIRouter, Depends, Query
from app.dependencies import get_transaction_service
from app.services.transaction_service import TransactionService
from app.models.responses import TransactionResponse
from typing import List, Optional
from datetime import date

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    account_id: Optional[str] = None,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """List transactions with optional filtering"""
    return transaction_service.get_transactions(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date
    )
