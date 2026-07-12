from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import get_logger

_lg = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ """

    _lg.debug("API initialization...")
    try:
        _lg.info("API initialized.")
    except Exception as e:
        _lg.critical(f"Failed to initialize API: {e}", exc_info=True)
        raise

    yield

    try:
        _lg.debug("API closing...")

    except Exception as e:
        _lg.critical(f"Failed to close API: {e}", exc_info=True)
        raise
