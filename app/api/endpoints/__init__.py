__all__ = ["router"]

from fastapi import APIRouter
from .default import router as default_router
from .v1 import v1_router

router = APIRouter()

router.include_router(default_router)
router.include_router(v1_router, prefix="/v1", tags=["v1"])
