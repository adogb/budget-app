from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account


def list_accounts(db: Session) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.name)))
