from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.local_backup import router as local_backup_router
from app.api.local_data_removal import router as local_data_removal_router
from app.api.local_diagnostics import router as local_diagnostics_router
from app.api.local_pairing import router as local_pairing_router
from app.api.local_restore import router as local_restore_router
from app.api.v1.academic import router as academic_router
from app.config import settings
from app.db.bootstrap import initialize_database
from app.db.session import engine
from app.runtime.discovery import (
    RuntimeManifest,
    discover_runtime_manifest,
    publish_runtime_manifest,
)
from app.schemas.health import HealthResponse, ReadinessResponse
from app.security.local_request import local_request_boundary


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database(engine)
    manifest_path = settings.runtime_manifest_path
    if manifest_path is not None:
        manifest = discover_runtime_manifest(manifest_path)
        if manifest is not None:
            publish_runtime_manifest(manifest_path, manifest.model_copy(update={"status": "ready"}))
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.desktop_origin_list,
    allow_credentials=False,
    expose_headers=["Content-Disposition", "X-SAPSOS-External-Backup-Receipt"],
    allow_methods=["DELETE", "GET", "PATCH", "POST"],
    allow_headers=[
        "authorization",
        "content-type",
        "x-sapsos-extension-credential",
        "x-sapsos-extension-nonce",
        "x-sapsos-extension-timestamp",
    ],
)

app.include_router(academic_router)
app.include_router(local_pairing_router)
app.include_router(local_backup_router)
app.include_router(local_restore_router)
app.include_router(local_diagnostics_router)
if settings.product_mode == "LOCAL_DESKTOP":
    app.include_router(local_data_removal_router)


@app.middleware("http")
async def enforce_local_request_boundary(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    return await local_request_boundary(request, call_next)


def security_headers() -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cache-Control": "no-store",
    }
    if settings.is_production:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    for name, value in security_headers().items():
        response.headers.setdefault(name, value)
    return response


def check_database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        database_configured=settings.database_url.startswith(
            ("postgresql+psycopg://", "sqlite+pysqlite:///")
        ),
    )


@app.get("/runtime", response_model=RuntimeManifest, tags=["system"])
def runtime_manifest() -> RuntimeManifest | JSONResponse:
    manifest_path = getattr(settings, "runtime_manifest_path", None)
    if manifest_path is None:
        return JSONResponse(status_code=503, content={"detail": "Runtime manifest unavailable."})
    manifest = discover_runtime_manifest(manifest_path)
    if manifest is None:
        return JSONResponse(status_code=503, content={"detail": "Runtime manifest unavailable."})
    return manifest


@app.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
    tags=["system"],
)
def ready() -> ReadinessResponse | JSONResponse:
    database_ready = check_database_ready()
    payload = ReadinessResponse(
        status="ready" if database_ready else "not_ready",
        service=settings.app_name,
        database_ready=database_ready,
    )
    if database_ready:
        return payload
    return JSONResponse(status_code=503, content=payload.model_dump())
