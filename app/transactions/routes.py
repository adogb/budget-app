from fastapi import APIRouter

from app.db import DbSession
from app.transactions.schemas import PendingTransactionOut, TransactionOut
from app.transactions.service import list_pending, list_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
def get_transactions(
    db: DbSession, account_id: int | None = None
) -> list[TransactionOut]:
    return [TransactionOut.from_model(t) for t in list_transactions(db, account_id)]


@router.get("/pending")
def get_pending_transactions(db: DbSession) -> list[PendingTransactionOut]:
    return [PendingTransactionOut.from_model(p) for p in list_pending(db)]
