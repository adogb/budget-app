"""
Category models for Budget App.

This module defines the SQLAlchemy and Pydantic models for categories.
"""

from sqlalchemy import Column, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.db import Base


class CategoryModel(Base):
    """SQLAlchemy model for categories."""

    __tablename__ = "categories"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    color = Column(String, nullable=True)
    parent_id = Column(String, ForeignKey("categories.id"), nullable=True)

    # Define relationships
    children = relationship(
        "CategoryModel", back_populates="parent", cascade="all, delete-orphan"
    )
    parent = relationship("CategoryModel", back_populates="children", remote_side=[id])

    # We'll add relationship to transactions later
    # transactions = relationship("TransactionModel", back_populates="category")


# Pydantic models for API
class CategoryBase(BaseModel):
    """Base Pydantic model for categories."""

    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None


class CategoryCreate(CategoryBase):
    """Pydantic model for category creation."""

    pass


class Category(CategoryBase):
    """Pydantic model for category responses."""

    id: str

    class Config:
        orm_mode = True


class CategoryWithChildren(Category):
    """Pydantic model for categories with their children."""

    children: List["CategoryWithChildren"] = []

    class Config:
        orm_mode = True


# This is needed for the recursive Pydantic model
CategoryWithChildren.update_forward_refs()
