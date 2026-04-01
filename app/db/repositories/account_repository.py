"""
Repository for Account database operations.
Handles CRUD and queries for bank accounts.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import Account


class AccountRepository:
    """Repository for managing Account entities in the database."""

    def __init__(self, db: Session):
        """
        Initialize AccountRepository.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_by_id(self, account_id: int) -> Optional[Account]:
        """
        Get an account by its ID.

        Args:
            account_id: The account ID

        Returns:
            Account object or None if not found
        """
        return self.db.query(Account).filter(Account.id == account_id).first()

    def get_by_iban(self, iban: str) -> Optional[Account]:
        """
        Get an account by its IBAN.

        Args:
            iban: The IBAN to search for

        Returns:
            Account object or None if not found
        """
        return self.db.query(Account).filter(Account.iban == iban).first()

    def get_by_external_id(self, external_id: str) -> Optional[Account]:
        """
        Get an account by its external ID (bank's account ID).

        Args:
            external_id: The external account ID from the bank

        Returns:
            Account object or None if not found
        """
        return self.db.query(Account).filter(Account.external_id == external_id).first()

    def get_all(self, user_id: int) -> List[Account]:
        """
        Get all accounts for a user.

        Args:
            user_id: The user ID

        Returns:
            List of Account objects
        """
        return self.db.query(Account).filter(Account.user_id == user_id).all()

    def create(self, account: Account) -> Account:
        """
        Create a new account.

        Args:
            account: Account object to create

        Returns:
            Created Account object with ID populated
        """
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update(self, account: Account) -> Account:
        """
        Update an existing account.

        Args:
            account: Account object with updated data

        Returns:
            Updated Account object
        """
        self.db.commit()
        self.db.refresh(account)
        return account

    def update_balance(self, account_id: int, new_balance: float) -> Optional[Account]:
        """
        Update the balance of an account.

        Args:
            account_id: The account ID
            new_balance: The new balance value

        Returns:
            Updated Account object or None if not found
        """
        account = self.get_by_id(account_id)
        if account:
            account.balance = new_balance
            return self.update(account)
        return None

    def delete(self, account_id: int) -> bool:
        """
        Delete an account.

        Args:
            account_id: The account ID to delete

        Returns:
            True if deleted, False if not found
        """
        account = self.get_by_id(account_id)
        if account:
            self.db.delete(account)
            self.db.commit()
            return True
        return False

    def exists_by_iban(self, iban: str) -> bool:
        """
        Check if an account with the given IBAN exists.

        Args:
            iban: The IBAN to check

        Returns:
            True if account exists, False otherwise
        """
        return self.db.query(Account).filter(Account.iban == iban).count() > 0
