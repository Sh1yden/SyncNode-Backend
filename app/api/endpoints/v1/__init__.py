__all__ = ["v1_router"]

from fastapi import APIRouter
from .mvp import router as mvp_router
from .auth import router as auth_router
from .notes import router as note_router
from .sync import router as sync_router
from .users import router as users_router

v1_router = APIRouter()

v1_router.include_router(mvp_router)
v1_router.include_router(auth_router)
v1_router.include_router(note_router)
v1_router.include_router(sync_router)
v1_router.include_router(users_router)
