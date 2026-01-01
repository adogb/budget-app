#!/usr/bin/env python3
"""
Setup script for the Budget App.

This script initializes the database and adds sample categories.
"""

import os
import sys

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.init_db import init_db
from app.db.seed_data import seed_categories


def setup():
    """Set up the Budget App."""
    print("Setting up Budget App...")

    # Initialize database
    print("\nInitializing database...")
    init_db()

    # Add sample categories
    print("\nAdding sample categories...")
    seed_categories()

    print("\nSetup complete! You can now run the app with:")
    print("uvicorn app.main:app --reload")


if __name__ == "__main__":
    setup()
