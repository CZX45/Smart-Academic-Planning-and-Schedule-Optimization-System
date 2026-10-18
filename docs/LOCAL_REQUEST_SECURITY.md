# LOCAL_DESKTOP Request Security — Stage 8B

Stage 8B adds the request boundary that follows Stage 8A pairing. It protects
the local API from accidental exposure through a forged Host header, an
unapproved browser Origin, a local Bearer-token substitution, and replay of a
captured Extension request.

## Boundary classification

| Route class | Host policy | Origin policy | Credential policy |
| --- | --- | --- | --- |
| `/health`, `/ready`, `/runtime` | loopback and active runtime port | not required | not required |
| `/local/pairing/*` | loopback and active runtime port | desktop or pairing Extension bootstrap | pairing flow only |
| `/api/v1/*` from desktop UI | loopback and active runtime port | configured desktop/Tauri origin | no Bearer substitution |
| `/api/v1/*` from Extension | loopback and active runtime port | currently paired Extension origin | verifier-backed custom header plus nonce/timestamp |

`SERVER` mode bypasses this local boundary and continues to use its existing
Bearer authentication and server CORS configuration.

## Host authority

LOCAL_DESKTOP accepts only loopback hostnames or loopback IP literals and the
actual port published by runtime discovery. Wildcard hosts, public/LAN hosts,
malformed authorities, unbracketed IPv6 authorities, and stale or mismatched
ports are rejected. The active runtime manifest is the source of truth when
the API was started with a dynamic port.

## Origin and credential policy

Desktop origins are the explicit configured localhost origins plus the
packaged `http://tauri.localhost` origin. An Extension Origin is accepted for
protected API requests only when its 32-character ID matches the currently
paired verifier record. Pairing bootstrap endpoints allow a valid Extension
origin to complete the user-initiated pairing flow.

The local API never treats `Authorization: Bearer ...` as a replacement for
the local pairing boundary. Extension API calls use
`X-SAPSOS-Extension-Credential`; the plaintext credential remains in the
Extension background worker and the desktop stores only its verifier.

## Replay and failure limits

Each protected Extension request includes:

- `X-SAPSOS-Extension-Nonce`, a bounded random request nonce;
- `X-SAPSOS-Extension-Timestamp`, a Unix timestamp in milliseconds; and
- the paired custom credential header.

The API accepts timestamps within 60 seconds and consumes each nonce once.
The in-memory nonce cache is capped at 10,000 entries with a two-minute TTL.
The cache intentionally clears on process restart; the paired verifier does
not, and the timestamp window limits the usefulness of a stale capture after a
restart. Failed local authentication/replay attempts are rate-limited per
client/origin key to bound guessing and repeated abuse.

## CORS boundary

CORS never uses a wildcard. Desktop origins are configured explicitly. The
paired Extension origin is added dynamically to successful responses and
preflight responses only after the pairing/origin policy recognizes it. CORS
is browser policy; Host validation, pairing verification, and replay checks
remain the authorization boundary.

## Safety limits

This feature does not capture school credentials, read portal cookies, bypass
MFA/CAPTCHA, register or modify courses, or send requests to school systems.
Local academic data remains advisory and subject to the existing manual-review
and advisor-confirmation boundaries.
