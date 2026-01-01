"""
CategoryManager module for Budget App.

This module provides functions for managing categories.
"""

from sqlalchemy.orm import Session
import uuid
from typing import List, Optional, Dict, Any
from app.models.category import (
    CategoryModel,
    Category,
    CategoryCreate,
    CategoryWithChildren,
)


class CategoryManager:
    """Service for managing categories."""

    @staticmethod
    def get_categories(
        db: Session, skip: int = 0, limit: int = 100
    ) -> List[CategoryModel]:
        """Get all categories."""
        return db.query(CategoryModel).offset(skip).limit(limit).all()

    @staticmethod
    def get_category(db: Session, category_id: str) -> Optional[CategoryModel]:
        """Get a category by ID."""
        return db.query(CategoryModel).filter(CategoryModel.id == category_id).first()

    @staticmethod
    def get_root_categories(db: Session) -> List[CategoryModel]:
        """Get root categories (those without a parent)."""
        return db.query(CategoryModel).filter(CategoryModel.parent_id == None).all()

    @staticmethod
    def create_category(db: Session, category: CategoryCreate) -> CategoryModel:
        """Create a new category."""
        db_category = CategoryModel(
            id=str(uuid.uuid4()),
            name=category.name,
            color=category.color,
            parent_id=category.parent_id,
        )
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category

    @staticmethod
    def update_category(
        db: Session, category_id: str, category_data: Dict[str, Any]
    ) -> Optional[CategoryModel]:
        """Update a category."""
        db_category = CategoryManager.get_category(db, category_id)
        if db_category:
            for key, value in category_data.items():
                setattr(db_category, key, value)
            db.commit()
            db.refresh(db_category)
        return db_category

    @staticmethod
    def delete_category(db: Session, category_id: str) -> bool:
        """Delete a category."""
        db_category = CategoryManager.get_category(db, category_id)
        if db_category:
            db.delete(db_category)
            db.commit()
            return True
        return False

    @staticmethod
    def build_category_tree(categories: List[CategoryModel]) -> List[Dict[str, Any]]:
        """Build a hierarchical tree of categories."""
        # Create a dictionary of categories by ID
        category_dict = {
            category.id: {
                "id": category.id,
                "name": category.name,
                "color": category.color,
                "parent_id": category.parent_id,
                "children": [],
            }
            for category in categories
        }

        # Build the tree
        root_categories = []
        for category_id, category in category_dict.items():
            parent_id = category["parent_id"]
            if parent_id:
                if parent_id in category_dict:  # Make sure parent exists
                    category_dict[parent_id]["children"].append(category)
            else:
                root_categories.append(category)

        return root_categories
