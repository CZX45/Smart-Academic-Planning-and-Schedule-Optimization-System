# SAPSOS Local Desktop shell and Windows package foundation

Debug builds remain a minimal Stage 5 development proof: they start the
existing Next.js development server at `http://127.0.0.1:3000` and the
FastAPI process with `LOCAL_DESKTOP` and file-backed SQLite. Release builds use
the Stage 7 static Web artifact and do not start Node.js or a Next.js server.
They wait for the versioned runtime manifest plus `/ready`, pass the discovered
API URL to the packaged page, and stop the API child when the Tauri window
exits.

The first Windows packaging foundation now uses one Tauri NSIS target. The
per-user package embeds the one-folder FastAPI runtime under the Tauri resource
directory and includes the static Web export. It does not install Node or
Python. Installer-level E2E, signing, auto-update, distribution, Beta, and RC
remain later milestones in `docs/LOCAL_DESKTOP_EXECUTION_PLAN.md`.

## Run the local development shell

From the repository root, launch the shell. It starts the Web UI and API
children itself:

```powershell
cargo run --manifest-path desktop-shell/src-tauri/Cargo.toml
```

The debug shell uses the current user Python and Node.js runtimes. It does not
use Docker or PostgreSQL. Closing the Tauri window terminates both children.

Desktop single-instance ownership uses a per-user Windows named mutex. The
`%LOCALAPPDATA%\SAPSOS\startup.lock` file is only a recoverable marker and is
safe to replace after an abnormal exit; `startup-lock-diagnostics.json` records
privacy-safe lock decisions locally. A second launch exits cleanly when the
mutex is owned by an active desktop instance.

## Build the Windows package foundation

Build the static Web artifact first:

```powershell
corepack pnpm web:package:windows
```

Then build the NSIS package:

```powershell
pnpm desktop:installer:windows
```

This single entry point validates shared/OpenAPI output, rebuilds the static
Web and packaged API outputs, validates staging exclusions and hashes, builds
the Tauri release/NSIS bundle, and validates the final installer manifest. It
cleans only validated child directories under build-output roots; it never
uses `git clean` or touches the LOCAL_DESKTOP data root.

The installer is emitted under `dist\windows-installer` with
`packaging-manifest.json`; `pnpm desktop:installer:validate` verifies the
manifested installer size, SHA-256, identity, mode, and commit. It installs
per-user under
`%LOCALAPPDATA%\Programs\SAPSOS Local Desktop` and keeps user data under
`%LOCALAPPDATA%\SAPSOS` across upgrade and uninstall by default. The current
foundation is unsigned and intentionally does not publish a release.
