from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.core import websocket_server
from app.core import get_logger

_lg = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ """

    _lg.debug("API initialization...")
    try:
        async with websocket_server:
            _lg.info("API initialized.")
            yield
    except Exception as e:
        _lg.critical(f"Failed to initialize API: {e}", exc_info=True)
        raise
    finally:
        _lg.debug("API closing...")
