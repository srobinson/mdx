---
title: Desktop foreground workdir switch fix
type: sessions
tags: [backend, desktop, workdir, runtime-discovery]
summary: Fixed foreground desktop launch reuse so live backend cwd drives the existing reclaim switch.
status: active
source: backend-engineer
confidence: high
created: 2026-06-29
updated: 2026-06-29
---

## Summary

Implemented branch `fix/desktop-foreground-workdir-switch`, commit `82805b4`, PR #184.

`discover_desktop_runtime` now reads both channel and cwd from live `/api/meta`. When the live backend reports a cwd, that cwd is carried into `DesktopRuntimeStatus`, so the existing `prepare_desktop_runtime_for_launch_or_exit` and `_serves_requested_work_dir` reclaim switch stops a healthy same channel backend that serves a different workdir. No second stop or reclaim path was added.

## API Contract

No public API contract changed. The internal desktop runtime status contract now prefers live `/api/meta.cwd` over the desktop record cwd for live runtimes when the live meta endpoint returns a cwd.

## Database Changes

None.

## Security Considerations

The fix keeps the existing loopback `/api/meta` probe and tolerant failure behavior. Stop behavior continues through `stop_desktop_record`, preserving the existing liveness and termination policy.

## Performance Notes

Runtime discovery still performs one `/api/meta` request after health is live. The probe now parses one additional string field from the same response, so there is no extra network round trip.

Verified with:

- `cd api && uv run python -m pytest src/transport_matters/cli/test_desktop_idempotent.py src/transport_matters/cli/test_desktop_runtime.py -q`
- `just check`
- `just test`
- `fmm validate`

## Open Items

None.
