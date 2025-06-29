from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.routers import accounts, transactions, setup
from app.services.gc_bank_data import GoCardlessBankDataClient

# Create a single client instance for dependency injection
bank_client = GoCardlessBankDataClient()

app = FastAPI(title="Budget App")

app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(setup.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Budget App",
        "setup_url": "/setup"
    }
