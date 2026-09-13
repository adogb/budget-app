from fastapi import Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.db.database import get_db
from app.services.account_service import AccountService
from app.services.setup_service import SetupService
from app.services.sync_service import SyncService
from app.services.transaction_service import TransactionService

templates = Jinja2Templates(directory="app/templates")

# Global instances for MVP
_client = None


def get_bank_client() -> GoCardlessBankDataClient:
    """
    Get the GoCardless bank client.
    For the MVP, we use a single global instance. The client mints and refreshes
    its own access tokens on demand from the configured secrets, so nothing needs
    to be loaded here.
    """
    global _client

    if _client is None:
        _client = GoCardlessBankDataClient()

    return _client


def get_account_service(
    db: Session = Depends(get_db),
) -> AccountService:
    """
    Get the AccountService instance.
    Creates a new instance on each request with database session.
    """
    return AccountService(db_session=db, user_id=1)


def get_transaction_service(
    db: Session = Depends(get_db),
) -> TransactionService:
    """
    Get the TransactionService instance.
    Creates a new instance on each request with database session.
    """
    return TransactionService(db_session=db, user_id=1)


def get_setup_service(
    bank_client: GoCardlessBankDataClient = Depends(get_bank_client),
    db: Session = Depends(get_db),
) -> SetupService:
    """
    Get the SetupService instance.
    Creates a new instance on each request with database session.
    """
    return SetupService(bank_client=bank_client, db_session=db, user_id=1)


def get_sync_service(
    db: Session = Depends(get_db),
    bank_client: GoCardlessBankDataClient = Depends(get_bank_client),
) -> SyncService:
    """
    Get the SyncService instance.
    Creates a new instance on each request with database session.
    """
    return SyncService(db_session=db, bank_client=bank_client, user_id=1)
