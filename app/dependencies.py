from fastapi import Depends
from sqlalchemy.orm import Session

from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.services.config_service import ConfigService
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService
from app.services.setup_service import SetupService
from app.db.database import get_db
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

# Global instances for MVP
_client = None
_config_service = None


def get_config_service() -> ConfigService:
    """
    Get the ConfigService instance.
    For the MVP, we use a single global instance.
    """
    global _config_service

    if _config_service is None:
        _config_service = ConfigService()

    return _config_service


def get_bank_client(
    config_service: ConfigService = Depends(get_config_service),
) -> GoCardlessBankDataClient:
    """
    Get the GoCardless bank client, loading saved tokens if available.
    For the MVP, we use a single global instance.
    """
    global _client

    # Initialize if not already done
    if _client is None:
        _client = GoCardlessBankDataClient()

        # Try to load saved tokens if configuration exists
        tokens = config_service.get_tokens()
        if tokens:
            _client.load_tokens_from_dict(tokens)

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
    config_service: ConfigService = Depends(get_config_service),
    db: Session = Depends(get_db),
) -> SetupService:
    """
    Get the SetupService instance.
    Creates a new instance on each request with database session.
    """
    return SetupService(
        bank_client=bank_client, config_service=config_service, db_session=db, user_id=1
    )
