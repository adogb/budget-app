from fastapi import Depends
from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.services.config_service import ConfigService
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService
from app.services.setup_service import SetupService

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
    bank_client: GoCardlessBankDataClient = Depends(get_bank_client),
    config_service: ConfigService = Depends(get_config_service),
) -> AccountService:
    """
    Get the AccountService instance.
    Creates a new instance on each request.
    """
    return AccountService(bank_client=bank_client, config_service=config_service)


def get_transaction_service(
    bank_client: GoCardlessBankDataClient = Depends(get_bank_client),
    config_service: ConfigService = Depends(get_config_service),
) -> TransactionService:
    """
    Get the TransactionService instance.
    Creates a new instance on each request.
    """
    return TransactionService(bank_client=bank_client, config_service=config_service)


def get_setup_service(
    bank_client: GoCardlessBankDataClient = Depends(get_bank_client),
    config_service: ConfigService = Depends(get_config_service),
) -> SetupService:
    """
    Get the SetupService instance.
    Creates a new instance on each request.
    """
    return SetupService(bank_client=bank_client, config_service=config_service)
