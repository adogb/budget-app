import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories.bank_integration_repository import BankIntegrationRepository
from app.dependencies import get_setup_service, templates
from app.services.setup_service import SetupService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])

# For single-user MVP
DEFAULT_USER_ID = 1


@router.get("/")
async def setup_home(
    request: Request, setup_service: SetupService = Depends(get_setup_service)
):
    """Render the country selection page at /setup"""
    countries = setup_service.get_supported_countries()
    return templates.TemplateResponse(
        request, "setup/countries.html", {"countries": countries}
    )


@router.get("/countries", response_model=None)
async def get_countries(
    request: Request, setup_service: SetupService = Depends(get_setup_service)
):
    """Get list of supported countries and render the country selection page"""
    countries = setup_service.get_supported_countries()

    return templates.TemplateResponse(
        request, "setup/countries.html", {"countries": countries}
    )


@router.get("/institutions/{country_code}")
async def get_institutions(
    request: Request,
    country_code: str,
    setup_service: SetupService = Depends(get_setup_service),
):
    """Get banks available for the selected country and render the institution selection page"""
    institutions = setup_service.get_institutions_for_country(country_code)

    # Store country_code in query params for the next step (stateless)
    return templates.TemplateResponse(
        request,
        "setup/institutions.html",
        {
            "institutions": institutions,
            "country_code": country_code,
        },
    )


@router.post("/start-bank-link/{institution_id}")
async def start_bank_link(
    request: Request,
    institution_id: str,
    country_code: str = Query(...),
    redirect_url: str | None = Query(None),
    setup_service: SetupService = Depends(get_setup_service),
    db: Session = Depends(get_db),
):
    """Start the bank linking process - creates a requisition and redirects to bank for authentication"""
    # Set the default redirect URL to our callback endpoint (same-tab redirect)
    callback_url = redirect_url or "http://localhost:8000/setup/bank-callback"

    # Create bank link
    link_data = setup_service.create_bank_link(institution_id, callback_url)

    # Starting a new link supersedes any prior one. Delete existing integrations
    # for this user so an abandoned requisition can't linger as orphaned data.
    # Saved accounts are keyed by the bank's external_id and are untouched;
    # re-completing setup updates them in place.
    repo = BankIntegrationRepository(db)
    for old in repo.get_by_user_id(DEFAULT_USER_ID):
        repo.delete(old.id)

    # Store new requisition data in database
    from app.db.models import BankIntegration

    integration = BankIntegration(
        user_id=DEFAULT_USER_ID,
        institution_id=institution_id,
        country_code=country_code,
        requisition_id=link_data["requisition_id"],
    )

    repo.create(integration)

    # Redirect to bank authentication
    return RedirectResponse(url=link_data["link"], status_code=302)


@router.get("/bank-callback")
async def bank_callback(
    request: Request,
    setup_service: SetupService = Depends(get_setup_service),
    db: Session = Depends(get_db),
):
    """Handle callback after bank authentication - user is redirected back here"""
    repo = BankIntegrationRepository(db)

    # Get the most recent integration for this user
    integration = repo.get_active_integration(DEFAULT_USER_ID)

    if not integration:
        raise HTTPException(
            status_code=400, detail="No active bank linking process found"
        )

    # Get accounts from requisition
    account_ids = setup_service.get_requisition_accounts(integration.requisition_id)

    if not account_ids:
        # Return the pending template
        return templates.TemplateResponse(
            request,
            "setup/bank_pending.html",
        )

    # Get account details for selection
    account_details = setup_service.get_account_details_for_selection(account_ids)

    # Return the account selection template
    return templates.TemplateResponse(
        request,
        "setup/accounts.html",
        {
            "accounts": account_details,
        },
    )


@router.post("/complete-setup")
async def complete_setup(
    request: Request,
    setup_service: SetupService = Depends(get_setup_service),
    db: Session = Depends(get_db),
):
    """Complete the setup by saving the selected accounts"""
    # Get form data
    form_data = await request.form()

    # Extract account IDs (may be a single value or a list)
    account_ids_raw = form_data.getlist("account_ids")

    # Ensure we have strings only
    account_ids: list[str] = [
        str(acc_id) for acc_id in account_ids_raw if isinstance(acc_id, str)
    ]

    # Ensure we have a list even if only one item was selected
    if not account_ids:
        raise HTTPException(status_code=400, detail="No accounts selected")

    # Get requisition data from database
    repo = BankIntegrationRepository(db)
    integration = repo.get_active_integration(DEFAULT_USER_ID)

    if not integration:
        raise HTTPException(
            status_code=400, detail="No active bank linking process found"
        )

    # Complete setup
    setup_service.complete_setup(
        requisition_id=integration.requisition_id,
        institution_id=integration.institution_id,
        selected_account_ids=account_ids,
        country_code=integration.country_code,
    )

    # Return the completion template
    return templates.TemplateResponse(
        request,
        "setup/complete.html",
    )


@router.post("/reset")
async def reset_setup(
    request: Request,
    db: Session = Depends(get_db),
):
    """Reset the setup process by deleting bank integrations"""
    # Delete all bank integrations for this user
    repo = BankIntegrationRepository(db)
    integrations = repo.get_by_user_id(DEFAULT_USER_ID)
    for integration in integrations:
        repo.delete(integration.id)

    # Redirect to setup start
    return RedirectResponse(url="/setup", status_code=303)
