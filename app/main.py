from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.routers import accounts, transactions, setup
from app.services.exceptions import (
    SetupNotCompleteError,
    ConfigNotFoundError,
    BankAPIError,
    InvalidConfigError,
)
import os
from dotenv import load_dotenv
from app.dependencies import templates, get_account_service
from app.services.account_service import AccountService
from app.db.database import init_db

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Read why here: https://fastapi.tiangolo.com/advanced/events/#lifespan

    # Initialize the database before starting app request handling
    init_db()
    yield


# Initialize the FastAPI app
app = FastAPI(title="Budget App", lifespan=lifespan)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Global exception handlers
@app.exception_handler(SetupNotCompleteError)
async def setup_not_complete_handler(request: Request, exc: SetupNotCompleteError):
    """Handle setup not complete errors."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": "setup_not_complete"},
    )


@app.exception_handler(ConfigNotFoundError)
async def config_not_found_handler(request: Request, exc: ConfigNotFoundError):
    """Handle config not found errors."""
    return JSONResponse(
        status_code=404, content={"detail": str(exc), "error_type": "config_not_found"}
    )


@app.exception_handler(InvalidConfigError)
async def invalid_config_handler(request: Request, exc: InvalidConfigError):
    """Handle invalid config errors."""
    return JSONResponse(
        status_code=500, content={"detail": str(exc), "error_type": "invalid_config"}
    )


@app.exception_handler(BankAPIError)
async def bank_api_error_handler(request: Request, exc: BankAPIError):
    """Handle bank API errors."""
    error_detail = {
        "detail": str(exc),
        "error_type": "bank_api_error",
    }
    if exc.account_id:
        error_detail["account_id"] = exc.account_id

    return JSONResponse(status_code=502, content=error_detail)


# Include routers
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(setup.router)


@app.get("/", response_class=HTMLResponse)
def read_root(
    request: Request,
    account_service: AccountService = Depends(get_account_service),
):
    """Render the dashboard home page with account list"""
    accounts = []
    try:
        accounts = account_service.get_all_accounts()
    except (SetupNotCompleteError, ConfigNotFoundError, BankAPIError):
        # If setup not complete or error fetching accounts, show empty state
        pass

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Dashboard - Budget App", "accounts": accounts},
    )
