"""
Categories router for Budget App.

This module provides API endpoints for managing categories.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.db import get_db
from app.models.category import Category, CategoryCreate, CategoryWithChildren
from app.services.category_manager import CategoryManager

router = APIRouter(prefix="/categories", tags=["categories"])

# Set up templates
templates = Jinja2Templates(directory="app/templates")


# API Endpoints
@router.get("/", response_model=List[Category])
async def get_categories(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    format: Optional[str] = None,
):
    """
    Get all categories.

    Optional query parameter 'format=html' to get HTML response.
    """
    categories = CategoryManager.get_categories(db, skip, limit)

    # Return HTML if format=html is specified
    if format == "html":
        return templates.TemplateResponse(
            "categories/index.html",
            {
                "request": request,
                "categories": categories,
                "tree": CategoryManager.build_category_tree(categories),
            },
        )

    return categories


@router.get("/tree", response_model=List[CategoryWithChildren])
async def get_category_tree(
    request: Request, db: Session = Depends(get_db), format: Optional[str] = None
):
    """
    Get category tree (hierarchical).

    Optional query parameter 'format=html' to get HTML response.
    """
    root_categories = CategoryManager.get_root_categories(db)

    # Return HTML if format=html is specified
    if format == "html":
        categories = CategoryManager.get_categories(db)
        return templates.TemplateResponse(
            "categories/tree.html",
            {
                "request": request,
                "categories": categories,
                "tree": CategoryManager.build_category_tree(categories),
            },
        )

    return root_categories


@router.post("/", response_model=Category)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    format: Optional[str] = None,
):
    """Create a new category."""
    db_category = CategoryManager.create_category(db, category)

    # If HTML format is requested, return the category item HTML
    if format == "html":
        return templates.TemplateResponse(
            "categories/category_item.html",
            {
                "request": None,  # Not needed for partial template
                "category": db_category,
            },
        )

    return db_category


@router.get("/{category_id}", response_model=Category)
async def get_category(
    category_id: str, db: Session = Depends(get_db), format: Optional[str] = None
):
    """Get a specific category by ID."""
    db_category = CategoryManager.get_category(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    # If HTML format is requested, return the category edit form
    if format == "html":
        return templates.TemplateResponse(
            "categories/edit.html",
            {
                "request": None,  # Not needed for partial template
                "category": db_category,
                "categories": CategoryManager.get_categories(
                    db
                ),  # For parent selection
            },
        )

    return db_category


@router.put("/{category_id}", response_model=Category)
async def update_category(
    category_id: str, category_data: dict = Body(...), db: Session = Depends(get_db)
):
    """Update a category."""
    db_category = CategoryManager.update_category(db, category_id, category_data)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category


@router.delete("/{category_id}")
async def delete_category(category_id: str, db: Session = Depends(get_db)):
    """Delete a category."""
    success = CategoryManager.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"detail": "Category deleted"}


# HTML Views (UI Routes)
@router.get("/ui", response_class=HTMLResponse)
async def categories_page(request: Request, db: Session = Depends(get_db)):
    """Render the categories management page."""
    categories = CategoryManager.get_categories(db)
    tree = CategoryManager.build_category_tree(categories)

    return templates.TemplateResponse(
        "categories/page.html",
        {"request": request, "categories": categories, "tree": tree},
    )
