# Tauri desktop-shell proof and packaged Web UI

Debug builds remain a minimal Stage 5 development proof: they start the
existing Next.js development server at `http://127.0.0.1:3000` and the
FastAPI process with `LOCAL_DESKTOP` and file-backed SQLite. Release builds use
the Stage 7 static Web artifact and do not start Node.js or a Next.js server.
They wait for the versioned runtime manifest plus `/ready`, pass the discovered
API URL to the packaged page, and stop the API child when the Tauri window
exits.

It does not package the API, install Node or Python, build an installer, pair
the browser extension, or implement localhost request protection. Those remain
later stages in `docs/LOCAL_DESKTOP_EXECUTION_PLAN.md`.

## Run the proof

From the repository root, launch the shell. It starts the Web UI and API
children itself:

```powershell
cargo run --manifest-path desktop-shell/src-tauri/Cargo.toml
```

The debug shell uses the current user Python and Node.js runtimes. It does not
use Docker or PostgreSQL. Closing the Tauri window terminates both children.

## Release Web proof

Build the static Web artifact first:

```powershell
corepack pnpm web:package:windows
```

Then build the release shell:

```powershell
$env:SAPSOS_API_EXECUTABLE = (Resolve-Path "dist\local-desktop-api\sapsos-api\sapsos-api.exe")
cargo build --release --manifest-path desktop-shell/src-tauri/Cargo.toml
```

The release binary consumes `dist\local-desktop-web` through the Tauri
`frontendDist` setting. It fails with an actionable missing-`index.html` error
and has no compiled Node/Next development-server path.
