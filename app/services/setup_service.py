"""
Service for managing setup workflow.

Handles business logic for initial bank connection and configuration.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.services.config_service import ConfigService
from app.services.exceptions import BankAPIError
from app.db.repositories.account_repository import AccountRepository
from app.db.repositories.bank_integration_repository import BankIntegrationRepository
from app.db.models import Account as AccountDB, BankIntegration as BankIntegrationDB


class CountryData(BaseModel):
    """Country information for bank selection."""

    code: str
    name: str
    flag: Optional[str] = None


class InstitutionData(BaseModel):
    """Bank institution information."""

    id: str
    name: str
    logo: str = ""
    countries: List[str] = []


class AccountData(BaseModel):
    """Account selection data."""

    id: str
    name: str


class SetupService:
    """Service for setup workflow orchestration."""

    # Supported countries with flag emojis
    SUPPORTED_COUNTRIES = [
        {"code": "GB", "name": "United Kingdom", "flag": "🇬🇧"},
        {"code": "DE", "name": "Germany", "flag": "🇩🇪"},
        {"code": "FR", "name": "France", "flag": "🇫🇷"},
        {"code": "ES", "name": "Spain", "flag": "🇪🇸"},
        {"code": "IT", "name": "Italy", "flag": "🇮🇹"},
        {"code": "NL", "name": "Netherlands", "flag": "🇳🇱"},
        {"code": "FI", "name": "Finland", "flag": "🇫🇮"},
        {"code": "NO", "name": "Norway", "flag": "🇳🇴"},
        {"code": "SE", "name": "Sweden", "flag": "🇸🇪"},
        {"code": "DK", "name": "Denmark", "flag": "🇩🇰"},
        {"code": "BE", "name": "Belgium", "flag": "🇧🇪"},
        {"code": "AT", "name": "Austria", "flag": "🇦🇹"},
    ]

    def __init__(
        self,
        bank_client: GoCardlessBankDataClient,
        config_service: ConfigService,
        db_session: Session,
        user_id: int = 1,
    ):
        """
        Initialize SetupService.

        Args:
            bank_client: Client for bank API operations
            config_service: Service for config operations (deprecated, will be removed)
            db_session: Database session for saving accounts
            user_id: The user ID (default 1 for MVP single-user)
        """
        self.bank_client = bank_client
        self.config_service = config_service
        self.account_repo = AccountRepository(db_session)
        self.integration_repo = BankIntegrationRepository(db_session)
        self.user_id = user_id

    def get_supported_countries(self) -> List[CountryData]:
        """
        Get list of supported countries.

        Returns:
            List of CountryData objects
        """
        return [CountryData(**country) for country in self.SUPPORTED_COUNTRIES]

    def get_institutions_for_country(self, country_code: str) -> List[InstitutionData]:
        """
        Get available bank institutions for a country.

        Args:
            country_code: ISO country code (e.g., 'GB', 'DE')

        Returns:
            List of InstitutionData objects

        Raises:
            BankAPIError: If fetching institutions fails
        """
        try:
            institutions_data = self.bank_client.get_institutions(country_code)

            institutions = []
            for institution in institutions_data:
                institutions.append(
                    InstitutionData(
                        id=institution["id"],
                        name=institution["name"],
                        logo=institution["logo"],
                        countries=institution["countries"],
                    )
                )

            return institutions
        except Exception as e:
            raise BankAPIError(f"Failed to get institutions: {str(e)}") from e

    def create_bank_link(
        self,
        institution_id: str,
        callback_url: str = "http://localhost:8000/setup/bank-callback",
    ) -> Dict[str, str]:
        """
        Create a bank linking requisition.

        Args:
            institution_id: Bank institution ID
            callback_url: URL to redirect to after authentication

        Returns:
            Dict with 'link' and 'requisition_id'

        Raises:
            BankAPIError: If creating requisition fails
        """
        try:
            requisition = self.bank_client.create_requisition(
                redirect_url=callback_url, institution_id=institution_id
            )

            return {
                "link": requisition.get("link", ""),
                "requisition_id": requisition.get("id", ""),
            }
        except Exception as e:
            raise BankAPIError(f"Failed to create bank link: {str(e)}") from e

    def get_requisition_accounts(self, requisition_id: str) -> List[str]:
        """
        Get account IDs from a requisition.

        Args:
            requisition_id: Requisition ID

        Returns:
            List of account IDs

        Raises:
            BankAPIError: If fetching requisition fails
        """
        try:
            requisition = self.bank_client.get_requisition(requisition_id)
            return requisition.get("accounts", [])
        except Exception as e:
            raise BankAPIError(f"Failed to get requisition: {str(e)}") from e

    def get_account_details_for_selection(
        self, account_ids: List[str]
    ) -> List[AccountData]:
        """
        Get account details for user selection.

        Args:
            account_ids: List of account IDs

        Returns:
            List of AccountData objects
        """
        account_details = []

        for account_id in account_ids:
            try:
                details = self.bank_client.get_account_details(account_id)
                account_name = details["account"].get("name", "Unnamed Account")

                account_details.append(AccountData(id=account_id, name=account_name))
            except Exception as e:
                # Log error but continue with other accounts
                print(f"Error fetching account {account_id}: {str(e)}")

        return account_details

    def complete_setup(
        self,
        requisition_id: str,
        institution_id: str,
        selected_account_ids: List[str],
        country_code: str = "GB",
    ) -> None:
        """
        Complete the setup process by saving bank integration and accounts to database.

        Args:
            requisition_id: GoCardless requisition ID
            institution_id: Bank institution ID
            selected_account_ids: List of selected account IDs
            country_code: Country code for the institution
        """
        # Get tokens from bank client
        token_data = self.bank_client.save_tokens_to_dict()

        # Save bank integration to database
        existing_integration = self.integration_repo.get_by_requisition_id(
            requisition_id
        )
        if not existing_integration:
            integration = BankIntegrationDB(
                user_id=self.user_id,
                institution_id=institution_id,
                country_code=country_code,
                requisition_id=requisition_id,
                access_token=token_data.get("access"),
                refresh_token=token_data.get("refresh"),
                access_valid_days=token_data.get("access_expires", 90),
                refresh_valid_days=token_data.get("refresh_expires", 90),
            )
            self.integration_repo.create(integration)
        else:
            # Update existing integration tokens
            existing_integration.access_token = token_data.get("access")
            existing_integration.refresh_token = token_data.get("refresh")
            existing_integration.access_valid_days = token_data.get(
                "access_expires", 90
            )
            existing_integration.refresh_valid_days = token_data.get(
                "refresh_expires", 90
            )
            self.integration_repo.update(existing_integration)

        # Also save to config file for backward compatibility (will remove later)
        self.config_service.create_complete_config(
            tokens=token_data,
            requisition_id=requisition_id,
            institution_id=institution_id,
            country_code=country_code,
        )

        # Get institution name
        bank_name = "Unknown Bank"
        try:
            institutions = self.bank_client.get_institutions(country_code)
            for inst in institutions:
                if inst["id"] == institution_id:
                    bank_name = inst["name"]
                    break
        except Exception as e:
            print(f"Error fetching institution name: {str(e)}")

        # Save accounts to database
        for account_id in selected_account_ids:
            try:
                # Get account details from API
                details = self.bank_client.get_account_details(account_id)
                balances = self.bank_client.get_account_balances(account_id)

                # Extract account information
                account_data = details["account"]  # required field
                iban = account_data.get("iban", "")  # NotRequired
                account_name = account_data.get("name", "Unknown Account")  # NotRequired
                currency = account_data.get("currency", "EUR")  # NotRequired

                # Get balance
                balance_list = balances["balances"]  # required field
                balance = 0.0
                if balance_list:
                    balance = float(
                        balance_list[0]["balanceAmount"]["amount"]  # both required
                    )

                # Check if account already exists by external_id (bank's account ID)
                existing_account = self.account_repo.get_by_external_id(account_id)
                if existing_account:
                    # Update existing account
                    existing_account.balance = balance
                    existing_account.name = account_name
                    existing_account.bank_name = bank_name
                    existing_account.iban = iban or existing_account.iban
                    self.account_repo.update(existing_account)
                else:
                    # Create new account
                    new_account = AccountDB(
                        user_id=self.user_id,
                        external_id=account_id,
                        name=account_name,
                        iban=iban or None,
                        balance=balance,
                        currency=currency,
                        bank_name=bank_name,
                    )
                    self.account_repo.create(new_account)
            except Exception as e:
                # Log error but continue with other accounts
                print(f"Error saving account {account_id} to database: {str(e)}")

    def reset_setup(self) -> None:
        """
        Reset the setup by deleting configuration.
        """
        self.config_service.delete_config()
