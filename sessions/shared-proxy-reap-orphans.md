---
title: Shared Proxy Orphan Reaping
type: sessions
tags: [backend, shared-proxy, process-lifecycle]
summary: Implemented PID backed shared proxy orphan reaping with process identity checks.
status: active
source: backend-engineer
confidence: high
created: 2026-06-28
updated: 2026-06-28
---

## Summary

Implemented shared proxy orphan reaping for branch `fix/shared-proxy-reap-orphans`, commit `b24f65514545f130ac6b1f51bc5f34ae693a21ea`, PR #183.

Key decisions:

- Keep ownership in `SupervisorSharedProxyProcess`, the concrete OS process seam that already owns `runtime_dir`, `control_socket`, and the child process.
- Persist `runtime_dir/shared-proxy.pid` after spawn using `write_atomic_json`.
- Reuse `desktop_runtime.is_pid_alive` for PID liveness.
- Verify PID identity before signaling by matching the persisted control socket and the live command marker `transport_matters.shared_proxy.subprocess`.
- Remove the PID file during clean terminate.

## API Contract

No API contract changes. This is internal shared proxy process lifecycle behavior.

## Database Changes

No database changes. No migrations.

## Security Considerations

- The reaper refuses to signal a live PID unless the recorded process name, recorded control socket, and live command all match the shared proxy subprocess.
- Dead, malformed, mismatched, or non matching PID records are unlinked rather than killed.
- Signaling prefers the process group only when `os.getpgid(pid) == pid`, reducing risk of signaling an unrelated group.

## Performance Notes

Startup now reads one small JSON PID record and, only when needed, probes a live process command through `/proc/<pid>/cmdline` or `ps -ww`. The path runs once per shared proxy process start.

## Verification

- `uv run python -m pytest src/transport_matters/shared_proxy/test_process.py -q`: 4 passed.
- `just check`: exit 0.
- `just test`: exit 0, including 1767 API tests plus desktop and www suites.

## Open Items

- None for this slice.
