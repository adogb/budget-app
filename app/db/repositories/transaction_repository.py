"""
Repository for Transaction database operations.
Handles CRUD and queries for financial transactions.
"""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.db.models import Transaction


class TransactionRepository:
    """Repository for managing Transaction entities in the database."""

    def __init__(self, db: Session):
        """
        Initialize TransactionRepository.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """
        Get a transaction by its ID.

        Args:
            transaction_id: The transaction ID

        Returns:
            Transaction object or None if not found
        """
        return (
            self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        )

    def get_all(
        self,
        user_id: int,
        account_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Transaction]:
        """
        Get transactions with optional filtering.

        Args:
            user_id: The user ID (required)
            account_id: Filter by specific account (optional)
            from_date: Filter transactions from this date (optional)
            to_date: Filter transactions to this date (optional)
            category_id: Filter by category (optional)
            limit: Maximum number of results (optional)

        Returns:
            List of Transaction objects ordered by booking date (newest first)
        """
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)

        # Apply filters
        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        if from_date:
            query = query.filter(Transaction.booking_date >= from_date)

        if to_date:
            query = query.filter(Transaction.booking_date <= to_date)

        if category_id:
            query = query.filter(Transaction.category_id == category_id)

        # Order by booking date (newest first)
        query = query.order_by(desc(Transaction.booking_date))

        # Apply limit if specified
        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_account(
        self, account_id: int, limit: Optional[int] = None
    ) -> List[Transaction]:
        """
        Get all transactions for a specific account.

        Args:
            account_id: The account ID
            limit: Maximum number of results (optional)

        Returns:
            List of Transaction objects ordered by booking date (newest first)
        """
        query = (
            self.db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(desc(Transaction.booking_date))
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_date_range(
        self, user_id: int, from_date: datetime, to_date: datetime
    ) -> List[Transaction]:
        """
        Get transactions within a date range.

        Args:
            user_id: The user ID
            from_date: Start date
            to_date: End date

        Returns:
            List of Transaction objects
        """
        return (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.booking_date >= from_date,
                    Transaction.booking_date <= to_date,
                )
            )
            .order_by(desc(Transaction.booking_date))
            .all()
        )

    def create(self, transaction: Transaction) -> Transaction:
        """
        Create a new transaction.

        Args:
            transaction: Transaction object to create

        Returns:
            Created Transaction object with ID populated
        """
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def create_bulk(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Create multiple transactions in bulk.

        Args:
            transactions: List of Transaction objects to create

        Returns:
            List of created Transaction objects with IDs populated
        """
        self.db.add_all(transactions)
        self.db.commit()
        for transaction in transactions:
            self.db.refresh(transaction)
        return transactions

    def update(self, transaction: Transaction) -> Transaction:
        """
        Update an existing transaction.

        Args:
            transaction: Transaction object with updated data

        Returns:
            Updated Transaction object
        """
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def update_category(
        self, transaction_id: str, category_id: Optional[int]
    ) -> Optional[Transaction]:
        """
        Update the category of a transaction.

        Args:
            transaction_id: The transaction ID
            category_id: The new category ID (None to remove category)

        Returns:
            Updated Transaction object or None if not found
        """
        transaction = self.get_by_id(transaction_id)
        if transaction:
            transaction.category_id = category_id
            return self.update(transaction)
        return None

    def delete(self, transaction_id: str) -> bool:
        """
        Delete a transaction.

        Args:
            transaction_id: The transaction ID to delete

        Returns:
            True if deleted, False if not found
        """
        transaction = self.get_by_id(transaction_id)
        if transaction:
            self.db.delete(transaction)
            self.db.commit()
            return True
        return False

    def get_uncategorized(self, user_id: int) -> List[Transaction]:
        """
        Get all transactions without a category.

        Args:
            user_id: The user ID

        Returns:
            List of uncategorized Transaction objects
        """
        return (
            self.db.query(Transaction)
            .filter(
                and_(Transaction.user_id == user_id, Transaction.category_id.is_(None))
            )
            .order_by(desc(Transaction.booking_date))
            .all()
        )

    def count_by_account(self, account_id: int) -> int:
        """
        Count transactions for a specific account.

        Args:
            account_id: The account ID

        Returns:
            Number of transactions
        """
        return (
            self.db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .count()
        )

    def exists_by_bank_transaction_id(self, bank_transaction_id: str) -> bool:
        """
        Check if a transaction with the given bank transaction ID exists.

        Args:
            bank_transaction_id: The bank's transaction ID

        Returns:
            True if transaction exists, False otherwise
        """
        return (
            self.db.query(Transaction)
            .filter(Transaction.bank_transaction_id == bank_transaction_id)
            .count()
            > 0
        )

    def get_latest_transaction_date(self, account_id: int) -> Optional[date]:
        """
        Get the most recent transaction booking date for an account.

        Args:
            account_id: The account ID

        Returns:
            The latest booking_date (as date object), or None if no transactions exist
        """
        result = (
            self.db.query(Transaction.booking_date)
            .filter(Transaction.account_id == account_id)
            .order_by(desc(Transaction.booking_date))
            .first()
        )
        return result[0] if result else None
