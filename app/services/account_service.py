"""
Service for managing bank account operations.

Handles business logic for account data, using local database as primary source.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.repositories.account_repository import AccountRepository
from app.db.models import Account as AccountDB
from app.models.responses import AccountResponse


class AccountService:
    """Service for account-related operations using local database."""

    def __init__(self, db_session: Session, user_id: int = 1):
        """
        Initialize AccountService.

        Args:
            db_session: Database session for repository operations
            user_id: The user ID (default 1 for MVP single-user)
        """
        self.repo = AccountRepository(db_session)
        self.user_id = user_id

    def _to_response(self, account: AccountDB) -> AccountResponse:
        """
        Convert database model to API response model.

        Args:
            account: SQLAlchemy Account model

        Returns:
            AccountResponse for API
        """
        return AccountResponse(
            id=str(account.id),
            name=account.name,
            iban=account.iban,
            balance=account.balance,
            currency=account.currency,
        )

    def get_all_accounts(self) -> List[AccountResponse]:
        """
        Get all user's accounts.

        Returns:
            List of AccountResponse objects
        """
        accounts = self.repo.get_all(self.user_id)
        return [self._to_response(acc) for acc in accounts]

    def get_account_by_id(self, account_id: int) -> Optional[AccountResponse]:
        """
        Get a specific account by ID.

        Args:
            account_id: The account ID to fetch

        Returns:
            AccountResponse with account data, or None if not found
        """
        account = self.repo.get_by_id(account_id)
        if account and account.user_id == self.user_id:
            return self._to_response(account)
        return None

    def get_account_by_iban(self, iban: str) -> Optional[AccountResponse]:
        """
        Get account by IBAN.

        Args:
            iban: The IBAN to search for

        Returns:
            AccountResponse with account data, or None if not found
        """
        account = self.repo.get_by_iban(iban)
        if account and account.user_id == self.user_id:
            return self._to_response(account)
        return None
