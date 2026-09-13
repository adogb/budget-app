"""
Service for managing transaction operations.

Handles business logic for transaction data, using local database as primary source.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Transaction as TransactionDB
from app.db.repositories.transaction_repository import TransactionRepository
from app.models.responses import TransactionResponse


class TransactionService:
    """Service for transaction-related operations using local database."""

    def __init__(self, db_session: Session, user_id: int = 1):
        """
        Initialize TransactionService.

        Args:
            db_session: Database session for repository operations
            user_id: The user ID (default 1 for MVP single-user)
        """
        self.repo = TransactionRepository(db_session)
        self.user_id = user_id

    def _to_response(self, transaction: TransactionDB) -> TransactionResponse:
        """
        Convert database model to API response model.

        Args:
            transaction: SQLAlchemy Transaction model

        Returns:
            TransactionResponse for API
        """
        return TransactionResponse(
            id=str(transaction.id),
            account_id=str(transaction.account_id),
            amount=transaction.amount_cents / 100.0,  # Convert cents to currency
            currency=transaction.currency,
            description=transaction.description,
            notes=transaction.notes,
            booking_date=transaction.booking_date,
            value_date=transaction.value_date,
            category=transaction.category.name if transaction.category else None,
        )

    def get_transactions(
        self,
        account_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        category_id: int | None = None,
        limit: int | None = None,
    ) -> list[TransactionResponse]:
        """
        Get transactions with optional filtering from local database.

        Args:
            account_id: Optional specific account ID (None = all accounts)
            from_date: Optional start date (None = 30 days ago)
            to_date: Optional end date (None = today)
            category_id: Optional filter by category
            limit: Optional maximum number of results

        Returns:
            List of TransactionResponse objects, sorted by booking date (newest first)
        """
        # Set default date range if not provided
        if not from_date and not to_date:
            to_datetime = datetime.now(UTC)
            from_datetime = datetime.now(UTC) - timedelta(days=30)
        else:
            from_datetime = (
                datetime.combine(from_date, datetime.min.time())
                if from_date
                else datetime.now(UTC) - timedelta(days=30)
            )
            to_datetime = (
                datetime.combine(to_date, datetime.max.time())
                if to_date
                else datetime.now(UTC)
            )

        # Fetch transactions from database
        transactions = self.repo.get_all(
            user_id=self.user_id,
            account_id=account_id,
            from_date=from_datetime,
            to_date=to_datetime,
            category_id=category_id,
            limit=limit,
        )

        return [self._to_response(tx) for tx in transactions]

    def get_uncategorized_transactions(self) -> list[TransactionResponse]:
        """
        Get all transactions without a category.

        Returns:
            List of uncategorized TransactionResponse objects
        """
        transactions = self.repo.get_uncategorized(self.user_id)
        return [self._to_response(tx) for tx in transactions]

    def get_transaction_by_id(self, transaction_id: str) -> TransactionResponse | None:
        """
        Get a single transaction by ID.

        Args:
            transaction_id: The transaction ID

        Returns:
            TransactionResponse or None if not found
        """
        transaction = self.repo.get_by_id(transaction_id)
        if transaction:
            return self._to_response(transaction)
        return None

    def update_transaction_category(
        self, transaction_id: str, category_id: int | None
    ) -> TransactionResponse | None:
        """
        Update the category of a transaction.

        Args:
            transaction_id: The transaction ID
            category_id: The new category ID (None to remove category)

        Returns:
            Updated TransactionResponse or None if not found
        """
        transaction = self.repo.update_category(transaction_id, category_id)
        if transaction:
            return self._to_response(transaction)
        return None

    def update_transaction_notes(
        self, transaction_id: str, notes: str
    ) -> TransactionResponse | None:
        """
        Update the notes of a transaction.

        Args:
            transaction_id: The transaction ID
            notes: The new notes text

        Returns:
            Updated TransactionResponse or None if not found
        """
        transaction = self.repo.get_by_id(transaction_id)
        if transaction:
            transaction.notes = notes
            updated = self.repo.update(transaction)
            return self._to_response(updated)
        return None
