# LOCAL_DESKTOP Web UI package

Stage 7 packages the existing Next.js UI as static Tauri assets. The packaged
runtime does not start Node.js, pnpm, npm, or a Next.js server.

## Architecture

The UI is a client-side App Router page. The production build reports only
static routes (`/` and `/_not-found`) and uses the existing shared browser API
client for all API-backed workflows. `apps/web/next.config.ts` therefore uses
Next static export. A packaged Node server was rejected because no server-only
feature, route handler, middleware, server action, or dynamic route requires
one.

The Tauri shell starts the packaged FastAPI executable first, waits for its
ready runtime manifest and `/ready`, then loads:

```text
index.html?api_base_url=http://127.0.0.1:<discovered-port>
```

The Web UI reads `api_base_url` through `useSyncExternalStore` after hydration.
If the bridge is absent, development may still use the existing
`NEXT_PUBLIC_API_BASE_URL` environment value; no packaged fallback endpoint is
provided. Invalid runtime values fail closed as an offline UI state.

## Build

Developer-only requirements are Node.js with Corepack/pnpm and Rust for the
Tauri shell build. End users run only the produced Windows artifacts and need
no user-installed Node.js, pnpm, Python, Docker, or PostgreSQL.

From a clean checkout:

```powershell
corepack pnpm install --frozen-lockfile
corepack pnpm web:package:windows
```

The deterministic Web artifact is written to:

```text
dist/local-desktop-web/
```

It contains `index.html`, the `_next/static` JavaScript/CSS assets, and a
`build-manifest.txt` with the source commit, strategy, file count, byte count,
and runtime bridge contract. Tauri release builds use this directory through
`desktop-shell/src-tauri/tauri.conf.json`.

## Runtime behavior

- Debug Tauri builds preserve the existing Next development-server proof.
- Release Tauri builds compile out the Node/Next development-server launch.
- The API is ready before the packaged Web window is created.
- API restart may allocate a different port; the next shell start reads the new
  manifest and creates a fresh query bridge.
- Navigation and reload retain the query bridge because it is part of the
  document URL.
- Missing `index.html` produces an actionable Tauri startup error naming the
  Web packaging command.
- Missing or unavailable API data remains an actionable offline/advisory UI
  state; it does not silently use mock data as official data.

## Stage 7 proof record

The available proof environment is a controlled Windows developer machine, not
a clean VM or Windows Sandbox. The static Web packaging script completed with
28 output files and 1,133,023 bytes. Web Vitest, lint, and typecheck passed;
Tauri `cargo fmt --check`, `cargo check`, and release `cargo build` passed.
The artifact scan found no `localhost:8000`, `127.0.0.1:8000`, or developer
absolute-path literals in generated HTML, JavaScript, or CSS.

The no-Node/no-Python runtime simulation must be run against the combined
Stage 6 API artifact and release Tauri binary with a restricted PATH. A
developer machine with Python or Node installed elsewhere is not described as
a clean image. Installer, signing, updater, and packaged desktop E2E remain
outside Stage 7.

## Troubleshooting

- If the build reports missing `corepack`, install the declared developer
  tooling; this is a build-time requirement only.
- If Tauri reports a missing `index.html`, run
  `corepack pnpm web:package:windows` from the repository root.
- If the UI shows API offline, confirm the packaged API executable reached
  `/ready` and inspect its runtime manifest/log before retrying.
- Do not set a build-time dynamic port. The runtime manifest is the source of
  the packaged API URL.
