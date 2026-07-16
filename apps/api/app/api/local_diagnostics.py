from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.db.session import engine
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
