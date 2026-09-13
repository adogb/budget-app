"""
Tests for the setup flow including bank integration and account creation.
"""

from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import BankIntegration, Base, User
from app.db.repositories.account_repository import AccountRepository
from app.db.repositories.bank_integration_repository import BankIntegrationRepository
from app.services.setup_service import SetupService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create a test user
    user = User(id=1, username="testuser")
    session.add(user)
    session.commit()

    yield session

    session.close()


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


@pytest.fixture
def setup_service(db_session, mock_bank_client) -> SetupService:
    """Create a setup service with mocked dependencies."""
    return SetupService(
        bank_client=mock_bank_client,
        db_session=db_session,
        user_id=1,
    )


class TestBankIntegrationRepository:
    """Test the BankIntegrationRepository."""

    def test_create_integration(self, db_session):
        """Test creating a new bank integration."""
        repo = BankIntegrationRepository(db_session)

        integration = BankIntegration(
            user_id=1,
            institution_id="SANDBOXFINANCE_SFIN0000",
            country_code="GB",
            requisition_id="test-req-123",
        )

        created = repo.create(integration)

        assert created.id is not None
        assert created.user_id == 1
        assert created.institution_id == "SANDBOXFINANCE_SFIN0000"
        assert created.requisition_id == "test-req-123"

    def test_get_by_requisition_id(self, db_session):
        """Test retrieving integration by requisition ID."""
        repo = BankIntegrationRepository(db_session)

        integration = BankIntegration(
            user_id=1,
            institution_id="SANDBOXFINANCE_SFIN0000",
            country_code="GB",
            requisition_id="unique-req-456",
        )
        repo.create(integration)

        found = repo.get_by_requisition_id("unique-req-456")

        assert found is not None
        assert found.requisition_id == "unique-req-456"
        assert found.institution_id == "SANDBOXFINANCE_SFIN0000"

    def test_get_active_integration(self, db_session):
        """Test getting the most recent integration."""
        repo = BankIntegrationRepository(db_session)

        # Create two integrations
        old = BankIntegration(
            user_id=1,
            institution_id="BANK_OLD",
            country_code="GB",
            requisition_id="old-req",
        )
        new = BankIntegration(
            user_id=1,
            institution_id="BANK_NEW",
            country_code="GB",
            requisition_id="new-req",
        )
        repo.create(old)
        repo.create(new)

        active = repo.get_active_integration(1)

        assert active is not None
        assert active.institution_id == "BANK_NEW"


class TestSetupService:
    """Test the SetupService."""

    def test_get_supported_countries(self, setup_service):
        """Test getting list of supported countries."""
        countries = setup_service.get_supported_countries()

        assert len(countries) > 0
        assert any(c.code == "GB" for c in countries)
        assert any(c.code == "DE" for c in countries)

    def test_get_institutions_for_country(self, setup_service, mock_bank_client):
        """Test getting institutions for a country."""
        institutions = setup_service.get_institutions_for_country("GB")

        assert len(institutions) == 1
        assert institutions[0].id == "SANDBOXFINANCE_SFIN0000"
        assert institutions[0].name == "Sandbox Finance"
        mock_bank_client.get_institutions.assert_called_once_with("GB")

    def test_create_bank_link(self, setup_service, mock_bank_client):
        """Test creating a bank link."""
        result = setup_service.create_bank_link(
            "SANDBOXFINANCE_SFIN0000",
            "http://localhost:8000/callback",
        )

        assert result["link"] == "https://bank.example.com/auth"
        assert result["requisition_id"] == "test-requisition-123"
        mock_bank_client.create_requisition.assert_called_once()

    def test_get_requisition_accounts(self, setup_service, mock_bank_client):
        """Test getting accounts from requisition."""
        accounts = setup_service.get_requisition_accounts("test-requisition-123")

        assert accounts == ["acc-123", "acc-456"]
        mock_bank_client.get_requisition.assert_called_once_with("test-requisition-123")

    def test_complete_setup_creates_integration_and_accounts(
        self, setup_service, db_session, mock_bank_client
    ):
        """Test that complete_setup creates bank integration and accounts in database."""

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
        setup_service.complete_setup(
            requisition_id="test-req-123",
            institution_id="SANDBOXFINANCE_SFIN0000",
            selected_account_ids=["acc-123", "acc-456"],
            country_code="GB",
        )

        # Check bank integration was created
        integration_repo = BankIntegrationRepository(db_session)
        integration = integration_repo.get_by_requisition_id("test-req-123")

        assert integration is not None
        assert integration.user_id == 1
        assert integration.institution_id == "SANDBOXFINANCE_SFIN0000"
        assert integration.country_code == "GB"

        # Check accounts were created
        account_repo = AccountRepository(db_session)
        accounts = account_repo.get_all(user_id=1)

        assert len(accounts) == 2
        assert any(acc.name == "Account acc-123" for acc in accounts)
        assert any(acc.name == "Account acc-456" for acc in accounts)
        assert all(acc.bank_name == "Sandbox Finance" for acc in accounts)
        assert all(acc.balance == 1000.0 for acc in accounts)

    def test_complete_setup_updates_existing_integration(
        self, setup_service, db_session, mock_bank_client
    ):
        """complete_setup must not create a duplicate for an existing requisition."""
        # Create an existing integration
        integration_repo = BankIntegrationRepository(db_session)
        existing = BankIntegration(
            user_id=1,
            institution_id="SANDBOXFINANCE_SFIN0000",
            country_code="GB",
            requisition_id="test-req-123",
        )
        integration_repo.create(existing)

        # Mock minimal account data
        mock_bank_client.get_account_details.return_value = {
            "account": {"iban": "GB123", "name": "Test", "currency": "GBP"}
        }
        mock_bank_client.get_account_balances.return_value = {
            "balances": [{"balanceAmount": {"amount": "100", "currency": "GBP"}}]
        }

        # Complete setup with same requisition
        setup_service.complete_setup(
            requisition_id="test-req-123",
            institution_id="SANDBOXFINANCE_SFIN0000",
            selected_account_ids=["acc-999"],
            country_code="GB",
        )

        # Check that the existing integration was reused, not duplicated
        integrations = integration_repo.get_by_user_id(1)
        assert len(integrations) == 1
        assert integrations[0].requisition_id == "test-req-123"


class TestCompleteSetupFlow:
    """Integration tests for the complete setup flow."""

    def test_full_setup_flow(self, setup_service, db_session, mock_bank_client):
        """Test the complete setup flow from country selection to completion."""
        # Step 1: Get supported countries
        countries = setup_service.get_supported_countries()
        assert len(countries) > 0

        # Step 2: Get institutions for GB
        institutions = setup_service.get_institutions_for_country("GB")
        assert len(institutions) == 1
        selected_institution = institutions[0].id

        # Step 3: Create bank link
        link_data = setup_service.create_bank_link(selected_institution)
        requisition_id = link_data["requisition_id"]
        assert requisition_id == "test-requisition-123"

        # Step 4: Get accounts from requisition
        account_ids = setup_service.get_requisition_accounts(requisition_id)
        assert len(account_ids) == 2

        # Step 5: Get account details for selection
        account_details = setup_service.get_account_details_for_selection(account_ids)
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
        setup_service.complete_setup(
            requisition_id=requisition_id,
            institution_id=selected_institution,
            selected_account_ids=account_ids,
            country_code="GB",
        )

        # Verify database state
        integration_repo = BankIntegrationRepository(db_session)
        account_repo = AccountRepository(db_session)

        integration = integration_repo.get_by_requisition_id(requisition_id)
        assert integration is not None
        assert integration.institution_id == selected_institution

        accounts = account_repo.get_all(user_id=1)
        assert len(accounts) == 2
