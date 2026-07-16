from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import settings
from app.db.session import engine
from app.services.diagnostics.export import DiagnosticsBundleError, build_diagnostics_bundle
from app.services.diagnostics.models import DiagnosticsSnapshot
from app.services.diagnostics.service import collect_snapshot

router = APIRouter(prefix="/api/v1/local-diagnostics", tags=["local-diagnostics"])


@router.get("", response_model=DiagnosticsSnapshot)
def get_local_diagnostics() -> DiagnosticsSnapshot:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise HTTPException(
            status_code=404,
            detail={
                "code": "local_diagnostics_unavailable",
                "message": "Local diagnostics is unavailable in SERVER mode.",
            },
        )
    return collect_snapshot(engine)


@router.post("/export", response_class=Response)
def export_local_diagnostics() -> Response:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise HTTPException(
            status_code=404,
            detail={
                "code": "local_diagnostics_unavailable",
                "message": "Local diagnostics is unavailable in SERVER mode.",
            },
        )
    try:
        archive = build_diagnostics_bundle(collect_snapshot(engine))
    except DiagnosticsBundleError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": str(error), "message": "Diagnostics bundle could not be generated."},
        ) from error
    return Response(
        content=archive,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="sapsos-diagnostics.zip"',
            "Cache-Control": "no-store",
        },
    )
