"""
Seed the database with initial data.

Run this script to add sample categories.
"""

from app.db import SessionLocal
from app.models.category import CategoryModel
import uuid


def seed_categories():
    """Add sample categories to the database."""
    db = SessionLocal()

    try:
        # Check if we already have categories
        existing_count = db.query(CategoryModel).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} categories. Skipping seed.")
            return

        # Define categories
        categories = [
            # Root categories
            {
                "id": str(uuid.uuid4()),
                "name": "Housing",
                "color": "#4A6FA5",
                "parent_id": None,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Food",
                "color": "#C03221",
                "parent_id": None,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Transportation",
                "color": "#047C84",
                "parent_id": None,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Entertainment",
                "color": "#799351",
                "parent_id": None,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Health",
                "color": "#F26430",
                "parent_id": None,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Personal",
                "color": "#FFBC42",
                "parent_id": None,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Income",
                "color": "#4CBB17",
                "parent_id": None,
            },
        ]

        # Store IDs for parent references
        category_ids = {}

        # Add root categories
        for category_data in categories:
            category = CategoryModel(**category_data)
            db.add(category)
            category_ids[category.name] = category.id

        # Add subcategories with references to parents
        subcategories = [
            # Housing subcategories
            {
                "id": str(uuid.uuid4()),
                "name": "Rent/Mortgage",
                "color": "#5D81B9",
                "parent_id": category_ids["Housing"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Utilities",
                "color": "#7393C0",
                "parent_id": category_ids["Housing"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Home Insurance",
                "color": "#89A5C8",
                "parent_id": category_ids["Housing"],
            },
            # Food subcategories
            {
                "id": str(uuid.uuid4()),
                "name": "Groceries",
                "color": "#D14B3B",
                "parent_id": category_ids["Food"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Restaurants",
                "color": "#E37567",
                "parent_id": category_ids["Food"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Takeout",
                "color": "#F09F93",
                "parent_id": category_ids["Food"],
            },
            # Transportation subcategories
            {
                "id": str(uuid.uuid4()),
                "name": "Public Transit",
                "color": "#05999E",
                "parent_id": category_ids["Transportation"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Car Payment",
                "color": "#06B6B6",
                "parent_id": category_ids["Transportation"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Gas",
                "color": "#07D3CE",
                "parent_id": category_ids["Transportation"],
            },
            # Entertainment subcategories
            {
                "id": str(uuid.uuid4()),
                "name": "Movies",
                "color": "#8BA966",
                "parent_id": category_ids["Entertainment"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Concerts",
                "color": "#9DBF7B",
                "parent_id": category_ids["Entertainment"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Subscriptions",
                "color": "#AFD591",
                "parent_id": category_ids["Entertainment"],
            },
            # Income subcategories
            {
                "id": str(uuid.uuid4()),
                "name": "Salary",
                "color": "#5DD728",
                "parent_id": category_ids["Income"],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Freelance",
                "color": "#7CE54C",
                "parent_id": category_ids["Income"],
            },
        ]

        # Add subcategories
        for subcategory_data in subcategories:
            subcategory = CategoryModel(**subcategory_data)
            db.add(subcategory)

        db.commit()
        print(
            f"Added {len(categories)} root categories and {len(subcategories)} subcategories."
        )

    except Exception as e:
        db.rollback()
        print(f"Error seeding categories: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding categories...")
    seed_categories()
    print("Done!")
