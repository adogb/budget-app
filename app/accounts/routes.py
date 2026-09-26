from fastapi import APIRouter

from app.accounts.schemas import AccountOut
from app.accounts.service import list_accounts
from app.db import DbSession

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
def get_accounts(db: DbSession) -> list[AccountOut]:
    return [AccountOut.from_model(account) for account in list_accounts(db)]
