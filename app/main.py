from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.accounts import routes as accounts
from app.bank import routes as bank
from app.bank.errors import BankAPIError, LinkError, LinkNotFoundError
from app.config import FRONTEND_DIST
from app.transactions import routes as transactions

# Domain errors become HTTP errors with the message as `detail`, the same shape
# FastAPI uses for its own errors.
ERROR_STATUS = {
    LinkError: 400,
    LinkNotFoundError: 404,
    BankAPIError: 502,  # The bank failed, not us.
}


def add_error_handlers(app: FastAPI) -> None:
    def handle(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=ERROR_STATUS[type(exc)])

    for error in ERROR_STATUS:
        app.add_exception_handler(error, handle)


def serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built React app, sending unknown paths to index.html.

    React Router handles URLs like /transactions in the browser, so on a page
    refresh the server must answer them with index.html too.
    """
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        file = (root / path).resolve()
        if file.is_file() and file.is_relative_to(root):
            return FileResponse(file)
        return FileResponse(root / "index.html")


# No automatic /api/x/ -> /api/x redirects: the frontend catch-all would
# otherwise make them behave differently depending on whether dist/ exists.
app = FastAPI(title="Budget App", redirect_slashes=False)
add_error_handlers(app)
app.include_router(accounts.router)
app.include_router(bank.router)
app.include_router(transactions.router)

if FRONTEND_DIST.exists():
    serve_frontend(app, FRONTEND_DIST)
