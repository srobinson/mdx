---
title: littleorgans dry-fix Phase 2 runtime daemon refactor
type: sessions
tags: [backend, littleorgans, rust, runtime-daemon, dry]
summary: Refactored runtime-daemon duplicate production paths and verified with clippy.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Completed the Phase 2 `runtime-daemon` DRY lane inside `internal/runtime/daemon/**`. The refactor consolidates event append persistence, docker stderr fallback, image inspect metadata, docker running probes, shim spawn evidence, daemon bootstrap and reconcile setup, and terminal lifecycle updates.

## API Contract

No HTTP or JSON wire API changed. New internal helpers are private or `pub(crate)` within `lilo-runtime-daemon`:

```rust
EventLog::append_recorded_event(event, ts_ms, sync_after_append)
docker_command::stderr_or(stderr, fallback)
DockerCliInspector::image_inspect_metadata(image, format, fallback)
container_running_args(session_id)
container_running_from_output(output)
spawn_via_shim(config, request)
server::bootstrap::prepare_runtime_bootstrap(config, db, local_uid)
server::bootstrap::start_runtime_reconcile(state, config)
TerminationCoordinator::record_terminal(state, session_id, evidence, mark_terminal)
```

## Database Changes

None.

## Security Considerations

No authorization or identity checks changed. Docker preflight error handling keeps the same typed runtime failures while removing duplicated command parsing and fallback text.

## Performance Notes

No new I/O paths were added. The bootstrap helper preserves startup ordering around socket binding by preparing bootstrap inputs before binding, then constructing state and starting reconcile after the listener is bound.

Verification completed:

```text
cargo clippy -p lilo-runtime-daemon --all-targets -- -D warnings
Finished `dev` profile [unoptimized + debuginfo] target(s) in 15.51s
```

## Open Items

None for this lane. Bus closeout sent on topic `dry-fix`: `runtime-daemon P2: 11 files, clippy clean`.
