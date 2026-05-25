---
title: Session Runtime Port C4 Doctor Migration
type: sessions
tags: [backend, littleorgans, session-runtime-port, runtime-port, doctor, audit]
summary: Migrated session doctor to RuntimePort while preserving user-visible output and deferring mutating spawn self-RPCs to WS4.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented WS2 C4 as doctor-only migration in commit `5ef264d` on `feat/session-runtime-port`.

Key decisions:

- `polish.rs` now calls the injected `RuntimePort` for runtime doctor data.
- The doctor path no longer depends on `rtmd_socket_path` for in-process operation.
- The runtime-side `Action::Doctor` door audit row is intentionally removed for this read path; the session-side doctor audit remains.
- The three spawn lifecycle self-RPCs remain deferred to WS4 because mutating spawn and recovery kill need the domain state-change audit work to land atomically.

## API Contract

No public API schema changed.

User-visible doctor output remains stable. A CLI render test proves outer `RuntimeDoctorReport.socket_path` and `code` changes do not affect rendered output when the runtime doctor payload exists.

Audit contract changed intentionally for session doctor:

- Before: session doctor produced two `Action::Doctor` rows, session door plus runtime self-dial door.
- After: session doctor produces one `Action::Doctor` row, the session door.

## Database Changes

No migrations or schema changes.

Audit row count expectations changed in `assert_delete_flow_audit` from two Doctor rows to one Doctor row.

## Security Considerations

Doctor is a read path. Dropping the runtime-side door audit row is the intended removal of self-dial tax for reads. No replacement domain audit is required for reads under the locked §4 audit split.

Mutating spawn lifecycle self-RPCs were not de-RPCed in C4. They remain on `handle_rpc` until WS4 can land domain state-change audit and de-duplication.

## Performance Notes

Session doctor avoids the local runtime socket self-dial in the composed daemon path and uses the in-process runtime port directly.

## Verification

Commands run:

- `cargo test -p lilo-session-daemon --test handler doctor_includes_runtime_matters_payload -- --nocapture`
- `cargo test -p lilo-session-app runtime_matters_render_is_equal_when_transport_fields_leave_report -- --nocapture`
- `cargo test -p lilo-session-daemon --test handler doctor_reports_runtime_matters_unavailable -- --nocapture`
- `cargo build -p lilo`
- `cargo test -p lilo-session-app --test mcp_protocol_test tools_call_can_run_list_get_and_delete_agent -- --nocapture`
- `cargo test --workspace`
- `just check`
- `just build`
- `just test`
- `git diff --check`

Results:

- All commands passed.
- `just test` reported `170 passed, 1 leaky, 0 skipped`, exit 0.
- Acceptance grep after commit: `RuntimeClient::new` remains only in the socket adapter `internal/session/driver/src/rtmd.rs`; `handle_rpc` remains only at the three deferred `spawn.rs` self-RPC sites, compose wire/session doors, and test socket plumbing.

## Open Items

- WS4 must move the three deferred `spawn.rs` self-RPC sites to the runtime port with the domain state-change audit and de-duplication model.
- C6 owns removing `rtmd_socket_path` and the remaining field-gated reconcile behavior.
