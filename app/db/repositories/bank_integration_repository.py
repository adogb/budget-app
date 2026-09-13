"""
Repository for BankIntegration database operations.
Handles CRUD and queries for bank integrations.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import BankIntegration


class BankIntegrationRepository:
    """Repository for managing BankIntegration entities in the database."""

    def __init__(self, db: Session):
        """
        Initialize BankIntegrationRepository.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_by_id(self, integration_id: int) -> BankIntegration | None:
        """
        Get a bank integration by its ID.

        Args:
            integration_id: The integration ID

        Returns:
            BankIntegration object or None if not found
        """
        return (
            self.db.query(BankIntegration)
            .filter(BankIntegration.id == integration_id)
            .first()
        )

    def get_by_user_id(self, user_id: int) -> list[BankIntegration]:
        """
        Get all bank integrations for a user.

        Args:
            user_id: The user ID

        Returns:
            List of BankIntegration objects
        """
        return (
            self.db.query(BankIntegration)
            .filter(BankIntegration.user_id == user_id)
            .all()
        )

    def get_by_requisition_id(self, requisition_id: str) -> BankIntegration | None:
        """
        Get a bank integration by requisition ID.

        Args:
            requisition_id: The GoCardless requisition ID

        Returns:
            BankIntegration object or None if not found
        """
        return (
            self.db.query(BankIntegration)
            .filter(BankIntegration.requisition_id == requisition_id)
            .first()
        )

    def get_active_integration(self, user_id: int) -> BankIntegration | None:
        """
        Get the most recent active bank integration for a user.

        Args:
            user_id: The user ID

        Returns:
            BankIntegration object or None if not found
        """
        return (
            self.db.query(BankIntegration)
            .filter(BankIntegration.user_id == user_id)
            .order_by(BankIntegration.created_at.desc(), BankIntegration.id.desc())
            .first()
        )

    def create(self, integration: BankIntegration) -> BankIntegration:
        """
        Create a new bank integration.

        Args:
            integration: BankIntegration object to create

        Returns:
            Created BankIntegration object with ID populated
        """
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def update(self, integration: BankIntegration) -> BankIntegration:
        """
        Update an existing bank integration.

        Args:
            integration: BankIntegration object with updated data

        Returns:
            Updated BankIntegration object
        """
        integration.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def update_tokens(
        self,
        integration_id: int,
        access_token: str,
        refresh_token: str,
        access_valid_days: int = 90,
        refresh_valid_days: int = 90,
    ) -> BankIntegration | None:
        """
        Update tokens for a bank integration.

        Args:
            integration_id: The integration ID
            access_token: New access token
            refresh_token: New refresh token
            access_valid_days: Days until access token expires
            refresh_valid_days: Days until refresh token expires

        Returns:
            Updated BankIntegration object or None if not found
        """
        integration = self.get_by_id(integration_id)
        if integration:
            integration.access_token = access_token
            integration.refresh_token = refresh_token
            integration.access_valid_days = access_valid_days
            integration.refresh_valid_days = refresh_valid_days
            return self.update(integration)
        return None

    def delete(self, integration_id: int) -> bool:
        """
        Delete a bank integration.

        Args:
            integration_id: The integration ID

        Returns:
            True if deleted, False if not found
        """
        integration = self.get_by_id(integration_id)
        if integration:
            self.db.delete(integration)
            self.db.commit()
            return True
        return False
