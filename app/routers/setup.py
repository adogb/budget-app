from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.setup_service import SetupService
from app.services.config_service import ConfigService
from app.dependencies import get_setup_service, get_config_service, templates
from typing import List, Dict, Optional

router = APIRouter(prefix="/setup", tags=["setup"])

# In-memory storage for setup process
# In a real app, this would use proper session management
setup_data = {}


@router.get("/", response_model=None)
async def check_setup_status(request: Request):
    """Check if the initial setup has been completed and render the setup page"""
    return templates.TemplateResponse("setup/index.html", {"request": request})


@router.get("/api/status")
async def get_setup_status(
    request: Request, config_service: ConfigService = Depends(get_config_service)
):
    """API endpoint to check if the initial setup has been completed"""
    if config_service.is_setup_complete():
        return templates.TemplateResponse(
            "setup/status.html", {"request": request, "status": "configured"}
        )

    return templates.TemplateResponse(
        "setup/status.html", {"request": request, "status": "not_configured"}
    )


@router.get("/countries", response_model=None)
async def get_countries(
    request: Request, setup_service: SetupService = Depends(get_setup_service)
):
    """Get list of supported countries and render the country selection page"""
    countries = [country.dict() for country in setup_service.get_supported_countries()]

    return templates.TemplateResponse(
        "setup/countries.html", {"request": request, "countries": countries}
    )


@router.get("/institutions/{country_code}")
async def get_institutions(
    request: Request,
    country_code: str,
    setup_service: SetupService = Depends(get_setup_service),
):
    """Get banks available for the selected country and render the institution selection page"""
    institutions = [
        inst.dict() for inst in setup_service.get_institutions_for_country(country_code)
    ]

    return templates.TemplateResponse(
        "setup/institutions.html",
        {"request": request, "institutions": institutions},
    )


@router.post("/start-bank-link/{institution_id}")
async def start_bank_link(
    request: Request,
    institution_id: str,
    redirect_url: Optional[str] = Query(None),
    setup_service: SetupService = Depends(get_setup_service),
):
    """Start the bank linking process - creates a requisition and returns link for authentication"""
    # Set the default redirect URL to our callback endpoint
    callback_url = redirect_url or "http://localhost:8000/setup/bank-callback"

    # Create bank link
    link_data = setup_service.create_bank_link(institution_id, callback_url)

    # Store requisition ID in memory (would use a session in a real app)
    setup_data["requisition_id"] = link_data["requisition_id"]
    setup_data["institution_id"] = institution_id

    # Return the template with the link
    return templates.TemplateResponse(
        "setup/bank_link.html",
        {
            "request": request,
            "link": link_data["link"],
            "requisition_id": link_data["requisition_id"],
        },
    )


@router.get("/bank-callback")
async def bank_callback(
    request: Request, setup_service: SetupService = Depends(get_setup_service)
):
    """Handle callback after bank authentication"""
    # Get the requisition ID from our in-memory storage
    requisition_id = setup_data.get("requisition_id")
    if not requisition_id:
        raise HTTPException(
            status_code=400, detail="No active bank linking process found"
        )

    # Get accounts from requisition
    account_ids = setup_service.get_requisition_accounts(requisition_id)

    if not account_ids:
        # Return the pending template if authentication is still in progress
        return templates.TemplateResponse(
            "setup/bank_pending.html", {"request": request}
        )

    # Store the account IDs
    setup_data["accounts"] = account_ids

    # Get account details for selection
    account_details = [
        acc.dict()
        for acc in setup_service.get_account_details_for_selection(account_ids)
    ]

    # Return the account selection template
    return templates.TemplateResponse(
        "setup/accounts.html", {"request": request, "accounts": account_details}
    )


@router.post("/complete-setup")
async def complete_setup(
    request: Request,
    setup_service: SetupService = Depends(get_setup_service),
):
    """Complete the setup by saving the selected accounts"""
    # Get form data
    form_data = await request.form()

    # Extract account IDs (may be a single value or a list)
    account_ids_raw = form_data.getlist("account_ids")

    # Ensure we have a list even if only one item was selected
    if not account_ids_raw:
        raise HTTPException(status_code=400, detail="No accounts selected")

    # Check if we have requisition data
    requisition_id = setup_data.get("requisition_id")
    if not requisition_id:
        raise HTTPException(
            status_code=400, detail="No active bank linking process found"
        )

    # Complete setup
    setup_service.complete_setup(
        requisition_id=requisition_id,
        institution_id=setup_data.get("institution_id", ""),
        selected_account_ids=account_ids_raw,
    )

    # Clear setup data
    setup_data.clear()

    # Return the completion template
    return templates.TemplateResponse("setup/complete.html", {"request": request})


@router.delete("/reset")
async def reset_setup(
    request: Request, setup_service: SetupService = Depends(get_setup_service)
):
    """Reset the setup process by deleting the config file"""
    # Clear in-memory setup data
    setup_data.clear()

    # Reset setup
    setup_service.reset_setup()

    # Return the reset template
    return templates.TemplateResponse("setup/reset.html", {"request": request})


@router.get("")
async def setup_redirect():
    """Redirect /setup to /setup/"""
    return RedirectResponse(url="/setup/")


@router.get("/")
async def setup_index(request: Request):
    """Render the setup index page"""
    return templates.TemplateResponse("setup/index.html", {"request": request})
