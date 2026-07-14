# Stage 8A — Secure Local Extension Pairing

Stage 8A establishes a user-initiated pairing relationship between one running
`LOCAL_DESKTOP` instance and one Chromium Extension installation. It does not
implement the complete localhost request boundary; that is the separately
reviewable Stage 8B.

## Protocol

- Protocol version: `1`. A mismatch is rejected with an actionable error.
- The desktop UI creates a one-time code with `secrets.token_urlsafe(15)`
  (at least 120 bits of entropy) and a five-minute expiry.
- The Extension completes pairing from its `chrome-extension://` origin. The
  code is consumed before a credential is issued, so it cannot be reused.
- The issued credential is a 256-bit random value prefixed with
  `sapsos_ext_`. The desktop stores only its SHA-256 verifier and never logs or
  returns it again.
- The Extension stores the credential in `chrome.storage.local`, owned by the
  background service worker API client. Popup code receives status/results, not
  the credential. Content scripts do not store or receive it.

The current dynamic API handoff is the existing runtime-discovered API base URL
shown to the user by the local app and entered in the Extension popup. Port
`8000` is not assumed. A stale runtime URL fails as an unavailable local app;
LAN and cloud discovery are not used.

## Persistence and lifecycle

The verifier and pairing metadata are stored atomically in `pairing.json` next
to the existing local runtime manifest under the `LOCALAPPDATA\SAPSOS` app-data
directory. The file contains no plaintext pairing code or credential. Its
protection relies on the per-user Windows app-data ACL; full local-machine
compromise remains outside scope. A runtime instance ID scopes the file to the
currently running app instance, and a reset/reinstall that removes local app
data or Extension storage requires pairing again. Revocation marks the verifier
inactive; a later pairing session rotates the credential.

## Threat model status

Stage 8A addresses one-time-code capture/reuse, guessing rate limits, stale
pairing state, protocol mismatch, verifier-only desktop persistence, and
credential isolation from page JavaScript/content scripts. It preserves the
read-only, explicit import and review/apply workflow.

Stage 8B now adds the centralized loopback Host/Origin boundary, the paired
custom authorization header, request replay protection, protected `/api/v1`
classification, dynamic paired-origin CORS, and failed-auth rate limiting.
CORS remains a browser policy, not the sole authorization boundary; Host
validation, verifier-backed credentials, and replay checks enforce the local
request policy.

Neither stage protects against malware with the user's privileges, a fully
compromised browser, school-portal compromise, or school authentication
bypass. The pairing credential is never a school password, portal token,
cookie, or cloud identity and is never sent to the school portal.
