"""
Repository for Category database operations.
Handles CRUD and queries for transaction categories.
"""

from sqlalchemy.orm import Session

from app.db.models import Category


class CategoryRepository:
    """Repository for managing Category entities in the database."""

    def __init__(self, db: Session):
        """
        Initialize CategoryRepository.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_by_id(self, category_id: int) -> Category | None:
        """
        Get a category by its ID.

        Args:
            category_id: The category ID

        Returns:
            Category object or None if not found
        """
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_all(self, user_id: int) -> list[Category]:
        """
        Get all categories for a user.

        Args:
            user_id: The user ID

        Returns:
            List of Category objects
        """
        return self.db.query(Category).filter(Category.user_id == user_id).all()

    def get_top_level(self, user_id: int) -> list[Category]:
        """
        Get all top-level categories (no parent) for a user.

        Args:
            user_id: The user ID

        Returns:
            List of top-level Category objects
        """
        return (
            self.db.query(Category)
            .filter(Category.user_id == user_id, Category.parent_id.is_(None))
            .all()
        )

    def get_children(self, parent_id: int) -> list[Category]:
        """
        Get all child categories of a parent category.

        Args:
            parent_id: The parent category ID

        Returns:
            List of child Category objects
        """
        return self.db.query(Category).filter(Category.parent_id == parent_id).all()

    def get_by_name(self, user_id: int, name: str) -> Category | None:
        """
        Get a category by name for a specific user.

        Args:
            user_id: The user ID
            name: The category name

        Returns:
            Category object or None if not found
        """
        return (
            self.db.query(Category)
            .filter(Category.user_id == user_id, Category.name == name)
            .first()
        )

    def create(self, category: Category) -> Category:
        """
        Create a new category.

        Args:
            category: Category object to create

        Returns:
            Created Category object with ID populated
        """
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, category: Category) -> Category:
        """
        Update an existing category.

        Args:
            category: Category object with updated data

        Returns:
            Updated Category object
        """
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category_id: int) -> bool:
        """
        Delete a category.

        Args:
            category_id: The category ID to delete

        Returns:
            True if deleted, False if not found
        """
        category = self.get_by_id(category_id)
        if category:
            self.db.delete(category)
            self.db.commit()
            return True
        return False

    def exists_by_name(self, user_id: int, name: str) -> bool:
        """
        Check if a category with the given name exists for a user.

        Args:
            user_id: The user ID
            name: The category name to check

        Returns:
            True if category exists, False otherwise
        """
        return (
            self.db.query(Category)
            .filter(Category.user_id == user_id, Category.name == name)
            .count()
            > 0
        )
