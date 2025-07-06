from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.services.gc_bank_data import GoCardlessBankDataClient
from app.dependencies import get_bank_client
import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/setup", tags=["setup"])

# Simple file storage for our MVP (single user)
CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# In-memory storage for setup process
# In a real app, this would use proper session management
setup_data = {}

class Institution(BaseModel):
    id: str
    name: str
    logo: str = ""
    countries: List[str] = []

class SetupStatusResponse(BaseModel):
    status: str
    accounts: Optional[List[Dict]] = None
    next_step: Optional[str] = None

class CountryResponse(BaseModel):
    code: str
    name: str
    flag: Optional[str] = None

class AccountSelectionRequest(BaseModel):
    account_ids: List[str]

@router.get("/", response_model=None)
async def check_setup_status(request: Request):
    """Check if the initial setup has been completed and render the setup page"""
    return templates.TemplateResponse("setup/index.html", {"request": request})

@router.get("/api/status")
async def get_setup_status(request: Request):
    """API endpoint to check if the initial setup has been completed"""
    if os.path.exists(CONFIG_FILE):
        try:
            # Load the configuration
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            # Return the status template with "configured" status
            return templates.TemplateResponse(
                "setup/status.html", 
                {"request": request, "status": "configured"}
            )
        except Exception:
            # If we can't read the config, consider it not configured
            return templates.TemplateResponse(
                "setup/status.html", 
                {"request": request, "status": "not_configured"}
            )
    
    # Return the status template with "not_configured" status
    return templates.TemplateResponse(
        "setup/status.html", 
        {"request": request, "status": "not_configured"}
    )

@router.get("/countries", response_model=None)
async def get_countries(request: Request):
    """Get list of supported countries and render the country selection page"""
    # Add flag emojis for better visual representation
    countries = [
        {"code": "GB", "name": "United Kingdom", "flag": "🇬🇧"},
        {"code": "DE", "name": "Germany", "flag": "🇩🇪"},
        {"code": "FR", "name": "France", "flag": "🇫🇷"},
        {"code": "ES", "name": "Spain", "flag": "🇪🇸"},
        {"code": "IT", "name": "Italy", "flag": "🇮🇹"},
        {"code": "NL", "name": "Netherlands", "flag": "🇳🇱"},
        {"code": "FI", "name": "Finland", "flag": "🇫🇮"},
        {"code": "NO", "name": "Norway", "flag": "🇳🇴"},
        {"code": "SE", "name": "Sweden", "flag": "🇸🇪"},
        {"code": "DK", "name": "Denmark", "flag": "🇩🇰"},
        {"code": "BE", "name": "Belgium", "flag": "🇧🇪"},
        {"code": "AT", "name": "Austria", "flag": "🇦🇹"},
    ]
    
    return templates.TemplateResponse(
        "setup/countries.html", 
        {"request": request, "countries": countries}
    )

@router.get("/institutions/{country_code}")
async def get_institutions(request: Request, country_code: str, client: GoCardlessBankDataClient = Depends(get_bank_client)):
    """Get banks available for the selected country and render the institution selection page"""
    try:
        # Get institutions from GoCardless
        institutions_data = client.get_institutions(country_code)
        
        # Format the response for better usability
        institutions = []
        for institution in institutions_data:
            institutions.append({
                "id": institution.get("id", ""),
                "name": institution.get("name", ""),
                "logo": institution.get("logo", ""),
                "countries": institution.get("countries", [])
            })
        
        return templates.TemplateResponse(
            "setup/institutions.html", 
            {"request": request, "institutions": institutions}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get institutions: {str(e)}")

@router.post("/start-bank-link/{institution_id}")
async def start_bank_link(
    request: Request,
    institution_id: str, 
    redirect_url: Optional[str] = Query(None),
    client: GoCardlessBankDataClient = Depends(get_bank_client)
):
    """Start the bank linking process - creates a requisition and returns link for authentication"""
    try:
        # Set the default redirect URL to our callback endpoint
        callback_url = redirect_url or "http://localhost:8000/setup/bank-callback"
        
        # Generate a requisition (bank connection request)
        requisition = client.create_requisition(
            redirect_url=callback_url,
            institution_id=institution_id
        )
        
        # Store requisition ID in memory (would use a session in a real app)
        requisition_id = requisition.get('id')
        setup_data['requisition_id'] = requisition_id
        setup_data['institution_id'] = institution_id
        
        # Return the template with the link
        return templates.TemplateResponse(
            "setup/bank_link.html", 
            {
                "request": request, 
                "link": requisition.get('link'),
                "requisition_id": requisition_id
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create bank link: {str(e)}")

@router.get("/bank-callback")
async def bank_callback(request: Request, client: GoCardlessBankDataClient = Depends(get_bank_client)):
    """Handle callback after bank authentication"""
    try:
        # Get the requisition ID from our in-memory storage
        requisition_id = setup_data.get('requisition_id')
        if not requisition_id:
            raise HTTPException(status_code=400, detail="No active bank linking process found")
        
        # Get the requisition to see if it was successful
        requisition = client.get_requisition(requisition_id)
        
        # Check if the requisition has accounts
        accounts = requisition.get('accounts', [])
        if not accounts:
            # Return the pending template if authentication is still in progress
            return templates.TemplateResponse(
                "setup/bank_pending.html",
                {"request": request}
            )
        
        # Store the account IDs
        setup_data['accounts'] = accounts
        
        # Get details for each account
        account_details = []
        for account_id in accounts:
            try:
                details = client.get_account_details(account_id)
                
                # Get account name
                account_name = details.get('name', '<unnamed account>')
                
                account_details.append({
                    'id': account_id,
                    'name': account_name
                })
            except Exception as e:
                # Log the error but continue with other accounts
                print(f"Error fetching account {account_id}: {str(e)}")
        
        # Return the account selection template
        return templates.TemplateResponse(
            "setup/accounts.html",
            {"request": request, "accounts": account_details}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process bank callback: {str(e)}")

@router.post("/complete-setup")
async def complete_setup(
    request: Request,
    client: GoCardlessBankDataClient = Depends(get_bank_client)
):
    """Complete the setup by saving the selected accounts"""
    try:
        # Get form data
        form_data = await request.form()
        
        # Extract account IDs (may be a single value or a list)
        account_ids_raw = form_data.getlist("account_ids")
        
        # Ensure we have a list even if only one item was selected
        if not account_ids_raw:
            raise HTTPException(status_code=400, detail="No accounts selected")
        
        # Check if we have requisition data
        requisition_id = setup_data.get('requisition_id')
        if not requisition_id:
            raise HTTPException(status_code=400, detail="No active bank linking process found")
            
        # Get GoCardless tokens for future API calls
        token_data = client.save_tokens_to_dict()
        
        # Create config directory if it doesn't exist
        os.makedirs("config", exist_ok=True)
        
        # Create the config object
        config = {
            "tokens": token_data,
            "requisition_id": requisition_id,
            "institution_id": setup_data.get('institution_id', ''),
            "selected_accounts": account_ids_raw,
            "setup_complete": True,
            "setup_date": datetime.now().isoformat()
        }
        
        # Save the config to file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Clear setup data
        setup_data.clear()
        
        # Return the completion template
        return templates.TemplateResponse(
            "setup/complete.html",
            {"request": request}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to complete setup: {str(e)}")

@router.delete("/reset")
async def reset_setup(request: Request):
    """Reset the setup process by deleting the config file"""
    try:
        # Clear in-memory setup data
        setup_data.clear()
        
        # Remove the config file if it exists
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            
        # Return the reset template
        return templates.TemplateResponse(
            "setup/reset.html",
            {"request": request}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset setup: {str(e)}")

@router.get("")
async def setup_redirect():
    """Redirect /setup to /setup/"""
    return RedirectResponse(url="/setup/")

@router.get("/")
async def setup_index(request: Request):
    """Render the setup index page"""
    return templates.TemplateResponse(
        "setup/index.html", 
        {"request": request}
    )
