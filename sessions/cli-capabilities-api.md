---
title: CLI Capabilities API
type: sessions
tags: [backend, transport-matters, cli, api, capabilities]
summary: Added a core CLI capabilities provider, API endpoint, and graceful version probe fix.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented slice #21 on `feat/cli-capabilities` and the follow up fix forward on `fix/capabilities-graceful`.

Merged feature PR:

- PR#67, commit `1aa9058`.
- Added `transport_matters.capabilities` as the neutral package root provider for Claude and Codex CLI detection.
- Moved runnable binary resolution primitives out of `cli/launch_runtime.py` into the core provider.
- Kept CLI launch error handling in `launch_runtime.resolve_client_binary()` as a thin Typer wrapper over the core resolver, preserving launch behavior.
- Added doctor capability lines for both managed CLIs.
- Added `GET /api/capabilities` so the UI can hide unavailable spawn actions.
- Added an API contract document at `/Users/alphab/.mdx/design/transport-matters-cli-capabilities-api.md` before endpoint implementation.

Fix forward PR:

- PR#68, branch `fix/capabilities-graceful`, commit `c5a048a`.
- Corrected graceful degradation: a present runnable CLI stays `installed: true` when `--version` times out or errors, with `version: null`.
- Offloaded API capability detection with `asyncio.to_thread(detect_clis)` so subprocess version probes do not block the event loop.
- Removed the redundant `disabled` argument pass from `resolve_client_binary()`.
- Made public `is_runnable_candidate()` strict for non existent paths while preserving synthetic `which` hook behavior inside `resolve_runnable_binary()` for existing launch tests.
- Kept the multi exception handler parenthesized in a formatter stable multi line form.

## API Contract

```typescript
type CliName = "claude" | "codex";

interface CliCapability {
  installed: boolean;
  path: string | null;
  version: string | null;
}

interface GetCapabilitiesResponse {
  clis: Record<CliName, CliCapability>;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

Endpoint:

```http
GET /api/capabilities
```

Example response:

```json
{
  "clis": {
    "claude": {
      "installed": true,
      "path": "/bin/claude",
      "version": "claude 1.2.3"
    },
    "codex": {
      "installed": false,
      "path": null,
      "version": null
    }
  }
}
```

A present CLI with a failed or timed out version probe returns `installed: true`, its path, and `version: null`.

## Database Changes

No schema changes. No migrations.

## Security Considerations

- The provider probes only fixed binary names: `claude` and `codex`.
- Version checks use `subprocess.run()` with argument arrays and no shell.
- Version checks use a bounded timeout and never raise through the API or doctor path.
- The API imports the core provider directly and does not import CLI modules.
- The API offloads subprocess probes to a worker thread to preserve event loop availability for other requests and websocket traffic.

## Performance Notes

- Capability detection performs at most two `--version` subprocess probes per request.
- Each version probe has a default 2 second timeout.
- API request handling no longer blocks the event loop while those probes run.
- No database access is added to `/api/capabilities`.
- `launch_runtime.py` is 651 lines after the fix forward.

## Verification

Feature PR#67 observed commands:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/test_capabilities.py src/transport_matters/cli/test_diagnose_capabilities.py src/transport_matters/api/v1/test_capabilities.py
# 7 passed in 0.48s, exit 0

cd api && .venv/bin/python -m pytest src/transport_matters/api/test_import_boundary.py
# 1 passed in 0.09s, exit 0

cd api && just ci
# ruff format: 324 files already formatted
# ruff check: All checks passed
# mypy: Success, no issues found in 324 source files
# pytest: 1281 passed in 22.86s, exit 0

git diff --check
# exit 0
```

Fix forward PR#68 observed commands:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/test_capabilities.py src/transport_matters/api/v1/test_capabilities.py src/transport_matters/api/v1/test_capabilities_async.py src/transport_matters/cli/test_diagnose_capabilities.py src/transport_matters/cli/test_diagnose_capabilities_graceful.py
# 10 passed in 0.54s, exit 0

cd api && .venv/bin/python -m pytest src/transport_matters/api/test_import_boundary.py
# 1 passed in 0.09s, exit 0

cd api && just ci
# ruff format: 326 files already formatted
# ruff check: All checks passed
# mypy: Success, no issues found in 326 source files
# pytest: 1284 passed in 22.52s, exit 0

git diff --check
# exit 0
```

Additional fix forward checks:

- Existing test modifications were limited to `api/src/transport_matters/test_capabilities.py`, which encoded the inverted timeout behavior and was explicitly allowed to change.
- Added `api/src/transport_matters/api/v1/test_capabilities_async.py` for event loop offload behavior.
- Added `api/src/transport_matters/cli/test_diagnose_capabilities_graceful.py` for doctor `version unknown` behavior.
- API to CLI import boundary stayed green.
- Branch pushed to `origin/fix/capabilities-graceful`.
- PR opened: https://github.com/littleorgans/transport-matters/pull/68
- Bus reply sent: `done: fix/capabilities-graceful c5a048a PR#68`.

## Open Items

- Frontend button gating remains intentionally out of scope for this backend slice.
- If future UX needs lower latency for repeated capability reads, cache the provider result with a short TTL at the API layer.
