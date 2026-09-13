from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_account_service, get_transaction_service
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def transactions_page(
    request: Request,
    account_id: int | None = None,
    transaction_service: TransactionService = Depends(get_transaction_service),
    account_service: AccountService = Depends(get_account_service),
):
    """Render transactions page"""
    transactions = transaction_service.get_transactions(
        account_id=account_id, limit=100
    )
    accounts = account_service.get_all_accounts()

    return templates.TemplateResponse(
        request,
        "transactions.html",
        {
            "transactions": transactions,
            "accounts": accounts,
            "selected_account_id": account_id,
        },
    )


@router.patch("/{transaction_id}/notes", response_class=HTMLResponse)
def update_transaction_notes(
    transaction_id: str,
    request: Request,
    notes: str = Form(...),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """Update transaction notes and return updated cell"""
    transaction_service.update_transaction_notes(transaction_id, notes)

    return f"""
    <td class="px-4 py-3 text-sm text-gray-600"
        hx-get="/transactions/{transaction_id}/notes-edit"
        hx-trigger="click"
        hx-swap="outerHTML">
        <span class="cursor-pointer hover:text-indigo-600">
            {notes if notes else '<span class="text-gray-400 italic">Add note...</span>'}
        </span>
    </td>
    """


@router.get("/{transaction_id}/notes-edit", response_class=HTMLResponse)
def edit_transaction_notes(
    transaction_id: str,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """Return edit form for notes"""
    transaction = transaction_service.get_transaction_by_id(transaction_id)
    notes_value = transaction.notes if transaction and transaction.notes else ""

    return f"""
    <td class="px-4 py-3">
        <form hx-patch="/transactions/{transaction_id}/notes"
              hx-swap="outerHTML"
              class="flex gap-2">
            <input type="text"
                   name="notes"
                   value="{notes_value}"
                   class="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                   autofocus />
            <button type="submit"
                    class="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700">
                Save
            </button>
            <button type="button"
                    hx-get="/transactions/{transaction_id}/notes-cancel"
                    hx-swap="outerHTML"
                    class="px-3 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                Cancel
            </button>
        </form>
    </td>
    """


@router.get("/{transaction_id}/notes-cancel", response_class=HTMLResponse)
def cancel_edit_notes(
    transaction_id: str,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """Cancel editing and return to display mode"""
    transaction = transaction_service.get_transaction_by_id(transaction_id)
    notes = transaction.notes if transaction and transaction.notes else ""

    return f"""
    <td class="px-4 py-3 text-sm text-gray-600"
        hx-get="/transactions/{transaction_id}/notes-edit"
        hx-trigger="click"
        hx-swap="outerHTML">
        <span class="cursor-pointer hover:text-indigo-600">
            {notes if notes else '<span class="text-gray-400 italic">Add note...</span>'}
        </span>
    </td>
    """
