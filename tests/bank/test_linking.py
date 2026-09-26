"""Tests for linking a bank and saving its accounts."""

from unittest.mock import Mock

import pytest
from sqlalchemy import select

from app.bank.linking import (
    SUPPORTED_COUNTRIES,
    complete_setup,
    create_bank_link,
    find_integration,
    get_account_choices,
    get_institutions,
    get_requisition_account_ids,
)
from app.models import Account, BankIntegration


def all_accounts(db) -> list[Account]:
    return list(db.scalars(select(Account)))


def all_integrations(db) -> list[BankIntegration]:
    return list(db.scalars(select(BankIntegration)))


@pytest.fixture
def mock_bank_client() -> Mock:
    """Create a mock bank client."""
    client = Mock()
    client.get_institutions.return_value = [
        {
            "id": "SANDBOXFINANCE_SFIN0000",
            "name": "Sandbox Finance",
            "logo": "https://example.com/logo.png",
            "countries": ["GB"],
        }
    ]
    client.create_requisition.return_value = {
        "id": "test-requisition-123",
        "link": "https://bank.example.com/auth",
    }
    client.get_requisition.return_value = {
        "id": "test-requisition-123",
        "accounts": ["acc-123", "acc-456"],
    }
    client.get_account_details.return_value = {
        "account": {
            "iban": "GB33BUKB20201555555555",
            "name": "Main Account",
            "currency": "GBP",
        }
    }
    client.get_account_balances.return_value = {
        "balances": [
            {
                "balanceAmount": {
                    "amount": "1000.50",
                    "currency": "GBP",
                }
            }
        ]
    }
    return client


class TestFindIntegration:
    def test_find_by_requisition_id(self, db):
        db.add(
            BankIntegration(
                institution_id="SANDBOXFINANCE_SFIN0000",
                country_code="GB",
                requisition_id="unique-req-456",
            )
        )
        db.commit()

        found = find_integration(db, "unique-req-456")

        assert found is not None
        assert found.requisition_id == "unique-req-456"
        assert found.institution_id == "SANDBOXFINANCE_SFIN0000"


class TestLinking:
    def test_supported_countries(self):
        """Test getting list of supported countries."""
        countries = SUPPORTED_COUNTRIES

        assert len(countries) > 0
        assert any(c.code == "GB" for c in countries)
        assert any(c.code == "DE" for c in countries)

    def test_get_institutions_for_country(self, mock_bank_client):
        """Test getting institutions for a country."""
        institutions = get_institutions(mock_bank_client, "GB")

        assert len(institutions) == 1
        assert institutions[0].id == "SANDBOXFINANCE_SFIN0000"
        assert institutions[0].name == "Sandbox Finance"
        mock_bank_client.get_institutions.assert_called_once_with("GB")

    def test_institution_without_logo_or_countries(self, mock_bank_client):
        mock_bank_client.get_institutions.return_value = [
            {"id": "BANK_X", "name": "Bank X"}
        ]

        institutions = get_institutions(mock_bank_client, "DK")

        assert institutions[0].logo == ""
        assert institutions[0].countries == []

    def test_account_choices_skip_malformed_details(self, mock_bank_client):
        mock_bank_client.get_account_details.side_effect = [
            {"account": {"name": "Checking"}},
            {"unexpected": {}},
        ]

        choices = get_account_choices(mock_bank_client, ["acc-1", "acc-2"])

        assert [c.id for c in choices] == ["acc-1"]

    def test_create_bank_link(self, mock_bank_client):
        """Test creating a bank link."""
        result = create_bank_link(
            mock_bank_client,
            "SANDBOXFINANCE_SFIN0000",
            "http://localhost:8000/callback",
        )

        assert result["link"] == "https://bank.example.com/auth"
        assert result["requisition_id"] == "test-requisition-123"
        mock_bank_client.create_requisition.assert_called_once()

    def test_get_requisition_accounts(self, mock_bank_client):
        """Test getting accounts from requisition."""
        accounts = get_requisition_account_ids(mock_bank_client, "test-requisition-123")

        assert accounts == ["acc-123", "acc-456"]
        mock_bank_client.get_requisition.assert_called_once_with("test-requisition-123")

    def test_complete_setup_creates_integration_and_accounts(
        self, db, mock_bank_client
    ):
        """complete_setup saves the bank integration and the chosen accounts."""

        # Mock account details and balances for both accounts
        def mock_get_account_details(account_id):
            return {
                "account": {
                    "iban": f"GB33BUKB2020155555555{account_id[-1]}",
                    "name": f"Account {account_id}",
                    "currency": "GBP",
                }
            }

        def mock_get_account_balances(account_id):
            return {
                "balances": [
                    {"balanceAmount": {"amount": "1000.00", "currency": "GBP"}}
                ]
            }

        mock_bank_client.get_account_details.side_effect = mock_get_account_details
        mock_bank_client.get_account_balances.side_effect = mock_get_account_balances

        # Complete setup
        complete_setup(
            db,
            mock_bank_client,
            requisition_id="test-req-123",
            institution_id="SANDBOXFINANCE_SFIN0000",
            selected_account_ids=["acc-123", "acc-456"],
            country_code="GB",
        )

        # Check bank integration was created
        integration = find_integration(db, "test-req-123")

        assert integration is not None
        assert integration.institution_id == "SANDBOXFINANCE_SFIN0000"
        assert integration.country_code == "GB"

        # Check accounts were created
        accounts = all_accounts(db)

        assert len(accounts) == 2
        assert any(acc.name == "Account acc-123" for acc in accounts)
        assert any(acc.name == "Account acc-456" for acc in accounts)
        assert all(acc.bank_name == "Sandbox Finance" for acc in accounts)
        assert all(acc.balance_minor == 100000 for acc in accounts)

    def test_complete_setup_updates_existing_integration(self, db, mock_bank_client):
        """complete_setup must not create a duplicate for an existing requisition."""
        # Create an existing integration
        existing = BankIntegration(
            institution_id="SANDBOXFINANCE_SFIN0000",
            country_code="GB",
            requisition_id="test-req-123",
        )
        db.add(existing)
        db.commit()

        # Mock minimal account data
        mock_bank_client.get_account_details.return_value = {
            "account": {"iban": "GB123", "name": "Test", "currency": "GBP"}
        }
        mock_bank_client.get_account_balances.return_value = {
            "balances": [{"balanceAmount": {"amount": "100", "currency": "GBP"}}]
        }

        # Complete setup with same requisition
        complete_setup(
            db,
            mock_bank_client,
            requisition_id="test-req-123",
            institution_id="SANDBOXFINANCE_SFIN0000",
            selected_account_ids=["acc-999"],
            country_code="GB",
        )

        # Check that the existing integration was reused, not duplicated
        integrations = all_integrations(db)
        assert len(integrations) == 1
        assert integrations[0].requisition_id == "test-req-123"


class TestCompleteSetupFlow:
    """Integration tests for the complete setup flow."""

    def test_full_setup_flow(self, db, mock_bank_client):
        """Test the complete setup flow from country selection to completion."""
        # Step 1: Get supported countries
        countries = SUPPORTED_COUNTRIES
        assert len(countries) > 0

        # Step 2: Get institutions for GB
        institutions = get_institutions(mock_bank_client, "GB")
        assert len(institutions) == 1
        selected_institution = institutions[0].id

        # Step 3: Create bank link
        link_data = create_bank_link(mock_bank_client, selected_institution)
        requisition_id = link_data["requisition_id"]
        assert requisition_id == "test-requisition-123"

        # Step 4: Get accounts from requisition
        account_ids = get_requisition_account_ids(mock_bank_client, requisition_id)
        assert len(account_ids) == 2

        # Step 5: Get account details for selection
        account_details = get_account_choices(mock_bank_client, account_ids)
        assert len(account_details) == 2

        # Mock for complete setup - return different IBANs for each account
        def mock_get_account_details(account_id):
            return {
                "account": {
                    "iban": f"GB33BUKB2020155555555{account_id[-1]}",
                    "name": f"Account {account_id}",
                    "currency": "GBP",
                }
            }

        mock_bank_client.get_account_details.side_effect = mock_get_account_details
        # Step 6: Complete setup
        complete_setup(
            db,
            mock_bank_client,
            requisition_id=requisition_id,
            institution_id=selected_institution,
            selected_account_ids=account_ids,
            country_code="GB",
        )

        # Verify database state
        integration = find_integration(db, requisition_id)
        assert integration is not None
        assert integration.institution_id == selected_institution

        accounts = all_accounts(db)
        assert len(accounts) == 2
