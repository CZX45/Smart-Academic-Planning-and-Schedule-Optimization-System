import os
from pathlib import Path

import uvicorn

from app.config import APP_DATA_DIR_NAME, settings
from app.runtime.discovery import (
    allocate_loopback_port,
    default_runtime_manifest_path,
    new_runtime_manifest,
    publish_runtime_manifest,
    read_runtime_manifest,
)

if __name__ == "__main__":
    port = settings.api_port or allocate_loopback_port()
    settings.api_port = port
    manifest_path = default_runtime_manifest_path(
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DATA_DIR_NAME
    )
    settings.runtime_manifest_path = manifest_path
    manifest = new_runtime_manifest(host=settings.api_host, port=port)
    publish_runtime_manifest(manifest_path, manifest)
    try:
        uvicorn.run("app.main:app", host=settings.api_host, port=port, reload=False)
    finally:
        current_manifest = read_runtime_manifest(manifest_path)
        if current_manifest is not None and current_manifest.instance_id == manifest.instance_id:
            manifest_path.unlink()
