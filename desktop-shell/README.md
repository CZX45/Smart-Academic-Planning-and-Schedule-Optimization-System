# Tauri desktop-shell proof

This is a minimal Stage 5 proof only. It starts the existing Next.js
development server at `http://127.0.0.1:3000` and the existing FastAPI process
with `LOCAL_DESKTOP` and file-backed SQLite, waits for the versioned runtime
manifest plus `/ready`, and stops both child processes when the Tauri window
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

The shell uses the current user Python runtime for this proof. It does not use
Docker or PostgreSQL. Closing the Tauri window terminates the API child.
