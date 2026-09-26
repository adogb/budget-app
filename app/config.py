import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'db' / 'budget.db'}"
)

# The one place the budget currency is named; see spec.md §5.
BUDGET_CURRENCY = "DKK"

GOCARDLESS_SECRET_ID = os.getenv("NORDIGEN_SECRET_ID")
GOCARDLESS_SECRET_KEY = os.getenv("NORDIGEN_SECRET_KEY")

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
