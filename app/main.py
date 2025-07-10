from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import accounts, transactions, setup
from app.services.gc_bank_data import GoCardlessBankDataClient
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
