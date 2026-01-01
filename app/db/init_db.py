"""
Initialize the database and create tables.

Run this script to create the database tables.
"""

from app.db import Base, engine
from app.models.category import CategoryModel


def init_db():
    """Create database tables."""
    # Create all tables
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("Done!")
