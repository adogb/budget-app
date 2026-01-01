"""
Database module for Budget App.

This module handles the SQLite database connection and initialization.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Create database directory if it doesn't exist, the database file will be created there (if not present)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_DIR = PROJECT_ROOT / "db"
DB_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_DIR / 'budget.db'}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_db():
    """
    Get a database session.

    Usage:
        @app.get("/some-endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
