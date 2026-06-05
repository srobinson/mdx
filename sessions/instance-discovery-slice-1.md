---
title: Instance Discovery Slice 1
type: sessions
tags: [backend, transport-matters, desktop-runtime, discovery, api-errors]
summary: Implemented the desktop runtime discovery seam with CLI and HTTP status surfaces, reviewer fixes, and full v1 API error helper consolidation.
status: active
source: backend-engineer
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Summary

Implemented slice 1 of instance discovery on branch `feat/instance-discovery` in amended commit `87b35af`, then completed the follow up v1 error helper consolidation in commit `22240b3`.

Key decisions:

- Moved shared desktop runtime discovery into package root seams so API code does not import CLI modules.
- Added a v2 desktop runtime record contract with `instance`, `cwd`, `storageDir`, and `version`, while preserving v1 read compatibility.
- Added explicit status states for discovery: `absent`, `live`, `stale`, and `unhealthy`.
- Exposed the same status contract through HTTP and CLI surfaces.
- Consolidated duplicated API v1 error helpers into `transport_matters.api.v1.errors` and refactored desktop runtime, run, space, session, and runtime template routes to use it.
- Changed invalid desktop runtime record JSON or schema to raise `desktop_runtime_invalid` instead of returning a stale status.

## API Contract

```typescript
type DesktopRuntimeState = "absent" | "live" | "stale" | "unhealthy";

interface DesktopRuntimeStatus {
  channel: string;
  state: DesktopRuntimeState;
  record?: {
    schemaVersion: 2;
    channel: string;
    instance: string;
    pid: number;
    proxyPort: number;
    webPort: number;
    cwd?: string | null;
    storageDir?: string | null;
    logPath: string;
    startedAt: string;
    version?: string | null;
  } | null;
  apiBaseUrl?: string | null;
  webBaseUrl?: string | null;
  reason?: string | null;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

Endpoint:

- `GET /v1/desktop-runtime`
  - Query: `channel?: string`
  - Response: `DesktopRuntimeStatus`
  - Errors: `ApiError` in FastAPI `detail`
    - `desktop_runtime_unavailable`: HTTP 503 for unreadable runtime record files.
    - `desktop_runtime_invalid`: HTTP 500 for invalid runtime record JSON or schema.

CLI:

- `transport-matters channel status [channel]`
- `transport-matters channel status [channel] --json`
- `transport-matters channel list` uses discovery status for live PID and ports.

Shared v1 API errors:

- `transport_matters.api.v1.errors.api_error(code, message, details)` returns the canonical JSON detail payload.
- `transport_matters.api.v1.errors.raise_api_error(status_code, code, message, details)` raises the canonical FastAPI `HTTPException`.

## Database Changes

No database migrations or schema changes.

## Security Considerations

- Discovery stays loopback scoped and validates the recorded API port before reporting `live`.
- Stale records are removed rather than trusted.
- Invalid JSON or malformed schema records are removed and reported through `desktop_runtime_invalid`.
- API discovery errors are mapped to a consistent machine readable error code.
- Shared seams avoid private CLI imports from API modules, preserving boundary enforcement.
- v1 routes now share one error payload helper, reducing drift in machine readable error responses.

## Performance Notes

- Discovery is file plus process status based and only performs a lightweight loopback `/api/meta` probe for candidate live records.
- Port readiness uses polling rather than fixed sleeps because mitmdump startup time varies.
- No database queries are introduced.
- New files and touched files stay below the 700 line project limit.

## Verification

- Focused regression gate passed: `24 passed in 0.28s` for import boundary, CLI desktop runtime, and HTTP desktop runtime tests.
- `just check` passed: desktop typecheck and tests, www format, lint, typecheck with pre existing warnings only, API ruff and mypy.
- Initial full gate passed: `just test`, `1731 passed in 53.80s`.
- Follow up v1 error helper consolidation proof: `rg "def _api_error|def _raise_api_error" api/src/transport_matters/api/v1` returned no duplicate helper definitions.
- Follow up full API gate passed: `just api test`, `1731 passed in 54.16s`.

## Open Items

- Future slices can build richer instance enumeration on top of the shared discovery seam.
- The current record source is per channel. Multi instance discovery should avoid adding parallel implementations and should extend the shared contract.
