import os
import sys
from pathlib import Path

import uvicorn

from app.config import APP_DATA_DIR_NAME, settings
from app.runtime.discovery import (
    allocate_loopback_port,
    default_runtime_manifest_path,
    new_runtime_manifest,
    publish_runtime_manifest,
    read_runtime_manifest,
    runtime_instance_id_from_environment,
)

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "local-data-remove":
        from app.services.local_data_removal import (
            FIXED_PLAN_PATH,
            execute_deletion_plan,
            resolve_app_data_root,
        )

        try:
            execute_deletion_plan(
                FIXED_PLAN_PATH,
                root=resolve_app_data_root(),
                application_version="0.1.0",
            )
        except Exception as error:
            print(f"Local data removal failed safely: {type(error).__name__}", file=sys.stderr)
            raise SystemExit(2) from error
        raise SystemExit(0)
    if len(sys.argv) == 2 and sys.argv[1] in {"preflight", "execute"}:
        from app.runtime.migration_contract import main as migration_main

        raise SystemExit(migration_main(sys.argv[1]))
    port = settings.api_port or allocate_loopback_port()
    settings.api_port = port
    manifest_path = default_runtime_manifest_path(
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DATA_DIR_NAME
    )
    settings.runtime_manifest_path = manifest_path
    manifest = new_runtime_manifest(
        host=settings.api_host,
        port=port,
        instance_id=runtime_instance_id_from_environment(),
    )
    publish_runtime_manifest(manifest_path, manifest)
    try:
        uvicorn.run("app.main:app", host=settings.api_host, port=port, reload=False)
    finally:
        current_manifest = read_runtime_manifest(manifest_path)
        if current_manifest is not None and current_manifest.instance_id == manifest.instance_id:
            manifest_path.unlink()
