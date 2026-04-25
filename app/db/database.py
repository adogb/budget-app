from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

"""
Database session and engine setup for SQLite.
Single-user budget app with local SQLite database.
"""


# SQLite database file path
DATABASE_URL = "sqlite:///./db/budget.db"

# Create engine
# check_same_thread=False is needed for SQLite with FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for SQL query logging during development
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency function to get database session.
    Yields a session and ensures it's closed after use.
    Use with FastAPI's Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Call this on app startup to create all tables defined by Base.
    """
    # Import models to register them with Base
    from app.db.models import Base

    # Create all tables that inherit from Base and are not yet created
    Base.metadata.create_all(bind=engine)
