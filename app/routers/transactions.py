from fastapi import APIRouter
from app.models.transaction import Transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/", response_model=list[Transaction])
def list_transactions():
    return []
