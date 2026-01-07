from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import accounts, transactions, setup
from app.clients.gc_bank_data import GoCardlessBankDataClient
from app.services.exceptions import (
    SetupNotCompleteError,
    ConfigNotFoundError,
    BankAPIError,
    InvalidConfigError,
)
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a single client instance for dependency injection
bank_client = GoCardlessBankDataClient()

# Initialize the FastAPI app
app = FastAPI(title="Budget App")

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")


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
def read_root(request: Request):
    """Render the home page"""
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "Budget App - Home"}
    )
