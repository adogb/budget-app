"""
Service for managing setup workflow.

Handles business logic for initial bank connection and configuration.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel

from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.services.config_service import ConfigService
from app.services.exceptions import BankAPIError


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
        self, bank_client: GoCardlessBankDataClient, config_service: ConfigService
    ):
        """
        Initialize SetupService.

        Args:
            bank_client: Client for bank API operations
            config_service: Service for config operations
        """
        self.bank_client = bank_client
        self.config_service = config_service

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
                        id=institution.get("id", ""),
                        name=institution.get("name", ""),
                        logo=institution.get("logo", ""),
                        countries=institution.get("countries", []),
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
                account_name = details.get("name", "<unnamed account>")

                account_details.append(AccountData(id=account_id, name=account_name))
            except Exception as e:
                # Log error but continue with other accounts
                print(f"Error fetching account {account_id}: {str(e)}")

        return account_details

    def complete_setup(
        self, requisition_id: str, institution_id: str, selected_account_ids: List[str]
    ) -> None:
        """
        Complete the setup process by saving configuration.

        Args:
            requisition_id: GoCardless requisition ID
            institution_id: Bank institution ID
            selected_account_ids: List of selected account IDs
        """
        # Get tokens from bank client
        token_data = self.bank_client.save_tokens_to_dict()

        # Save complete configuration
        self.config_service.create_complete_config(
            tokens=token_data,
            requisition_id=requisition_id,
            institution_id=institution_id,
            selected_accounts=selected_account_ids,
        )

    def reset_setup(self) -> None:
        """
        Reset the setup by deleting configuration.
        """
        self.config_service.delete_config()
