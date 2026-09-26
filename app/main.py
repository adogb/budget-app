from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.accounts import routes as accounts
from app.config import FRONTEND_DIST
from app.transactions import routes as transactions


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
app.include_router(accounts.router)
app.include_router(transactions.router)

if FRONTEND_DIST.exists():
    serve_frontend(app, FRONTEND_DIST)
