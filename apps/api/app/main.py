from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.academic import router as academic_router
from app.config import settings
from app.db.session import engine
from app.schemas.health import HealthResponse, ReadinessResponse

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "PATCH", "POST"],
    allow_headers=["authorization", "content-type"],
)

app.include_router(academic_router)


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
        database_configured=settings.database_url.startswith("postgresql+psycopg://"),
    )


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
