from fastapi import APIRouter
from app.models.account import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("/", response_model=list[Account])
def list_accounts():
    return []
