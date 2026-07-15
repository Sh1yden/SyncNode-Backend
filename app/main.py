from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from app.api.endpoints import router as main_router
from app.api.lifespan import lifespan
from app.core import get_logger, setup_logging, settings

from importlib.metadata import version, PackageNotFoundError

try:
    _version = version("SyncNode")
except PackageNotFoundError:
    _version = "1.0.0"

_lg = get_logger("SyncNode")
setup_logging(settings.LOG_LEVEL)

_lg.debug("Creating the app...")

app: FastAPI = FastAPI(
    title="SyncNode",
    version=_version,
    root_path="/SyncNode",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
    default_response_class=JSONResponse,
)

# icon
app.mount("/app/static", StaticFiles(directory="app/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")


# docs
@app.get("/docs", include_in_schema=False)
async def custom_swagger():
    return get_swagger_ui_html(
        title=app.title,
        openapi_url=app.openapi_url,  # type: ignore
        swagger_favicon_url="/app/static/favicon.ico",
    )


# routes
@app.get("/routes", include_in_schema=False)
def get_all_routes():
    routes_list = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes_list.append(
                {"path": route.path, "methods": list(route.methods), "name": route.name}  # type: ignore
            )
    return {"routes": routes_list}


app.include_router(main_router)
