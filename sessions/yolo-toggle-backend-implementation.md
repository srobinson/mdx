---
title: Yolo Toggle Backend Implementation
type: sessions
tags: [backend, transport-matters, runs, launcher, permissions]
summary: Added the backend bypassPermissions carrier and harness argv flag mapping for captured runs.
status: active
source: backend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

## Summary

Implemented the backend side of the launcher "Bypass all permission checks" toggle. The public `bypassPermissions` boolean now threads through the captured run request path and reaches the concrete harness argv profiles. The argv mapping remains provider owned in `LaunchProfile` implementations.

## API Contract

```typescript
type CapturedRunHarness = "claude" | "codex";

interface CreateRunRequest {
  harness: CapturedRunHarness;
  cwd?: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
  continueFromSessionId?: string;
  idempotencyKey?: string;
  runtimeTemplate?: string;
  bypassPermissions?: boolean; // default false
}
```

Backend carrier path:

```text
CreateRunRequest.bypass_permissions
SpawnRun.bypass_permissions
CapturedRunRequest.bypass_permissions
build_claude_captured_invocation(..., bypass_permissions)
build_codex_captured_invocation(..., bypass_permissions)
LaunchProfile.client_argv(..., bypass_permissions)
```

Flag mapping:

```python
CLAUDE_BYPASS_PERMISSIONS_ARG = "--dangerously-skip-permissions"
CODEX_BYPASS_PERMISSIONS_ARG = "--yolo"
```

## Database Changes

None.

## Security Considerations

The API accepts a boolean only. It does not expose arbitrary argv passthrough. The default is `False`, and existing runs are unaffected. The two dangerous provider flags are appended only from concrete harness profiles.

## Performance Notes

No database or network hot path changed. The runtime cost is one boolean check while assembling the managed client argv.

## Verification

Focused fail first evidence:

```text
.venv/bin/python -m pytest selected yolo toggle tests
6 failed before implementation
TypeError: unexpected keyword argument 'bypass_permissions'
AttributeError: 'CapturedRunRequest' object has no attribute 'bypass_permissions'
```

Focused passing evidence:

```text
.venv/bin/python -m pytest selected yolo toggle tests
6 passed in 0.09s
```

Full API gate:

```text
cd api && just check && just test
ruff format: 403 files left unchanged
ruff check: All checks passed
mypy: Success: no issues found in 403 source files
pytest: 1589 passed in 47.58s
```

## Open Items

Frontend persists the global launcher setting and includes `bypassPermissions` on subsequent `POST /v1/runs` requests. No backend persistence is needed for this toggle.
