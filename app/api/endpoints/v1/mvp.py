"""MVP эндпоинты не предназначенные для прода."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(prefix="/mvp", tags=["mvp"])

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "static"


@router.get("/sync-test", name="sync_test_page")
async def sync_test_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "sync_test.html", media_type="text/html")


@router.get("/test")
async def sync_test_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(url=request.url_for("sync_test_page"))
