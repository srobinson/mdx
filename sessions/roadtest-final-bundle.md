---
title: ROADTEST final bundle implementation
type: sessions
tags: [backend, roadtest, cli, doctor, proto]
summary: Implemented config flag rejection, bounded doctor RPC probe, and proto reader dedup on fix/roadtest.
status: active
source: backend-engineer
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

## Summary

Implemented and pushed the ROADTEST final bundle on branch `fix/roadtest`.

Commits:

* `f37e623` `fix(lilo): reject unsupported config file flag`
* `7746a92` `fix(doctor): bound daemon health probe`
* `63c1491` `refactor(proto): deduplicate async json line readers`

Each item completed Phase A design review, Phase B diff review, and push through the `roadtest-signoff` bus thread. Reviewer signoff came from `littleorgans:helioy-tools:rust-engineer:5:6.1`.

## API Contract

No REST, GraphQL, or external service API contract changed.

CLI and protocol contract changes:

```typescript
// Global CLI flag behavior
// lilo --config <path> <command>
// lilo -c <path> <command>
interface ConfigFileRejectedDiagnostic {
  code: "input_validation";
  exitCode: 3;
  message: string; // names --config/-c and points to LILO_HOME, LILO_SOCKET_PATH, LILO_LOG
}
```

Runtime protocol reader behavior remains stable:

```typescript
interface JsonLineReaderBehavior {
  readJsonLineEmpty: "ProtocolError::Eof";
  readJsonLineEmptyIoError: "ProtocolError::Io";
  readOptionalJsonLineEmpty: "Ok(None)";
  readOptionalJsonLineEmptyIoError: "Ok(None)";
  readOptionalJsonLineMalformedPartial: "ProtocolError::Json";
}
```

Doctor behavior remains human and JSON compatible. A hung daemon Doctor RPC now resolves as daemon unreachable instead of hanging.

## Database Changes

No database schema, migration, or index changes.

## Security Considerations

* `--config` and `-c` now fail closed before command dispatch. This prevents users from assuming a file config was loaded when configuration is actually environment only.
* The rejection message names the supported environment variables and does not introduce file config parsing.
* The doctor timeout bounds a local daemon health probe and avoids unbounded client hangs against a wedged socket.
* Proto reader refactor preserves EOF, IO, malformed JSON, and optional read semantics with focused tests.

## Performance Notes

* `lilo doctor` uses a 3 second timeout for the daemon Doctor RPC health probe. Healthy local responses remain unchanged.
* The timeout helper delegates to the existing `send_request` implementation, avoiding duplicated connect, write, and read logic.
* Async JSON line readers share one read loop, reducing maintenance risk without changing public signatures.

## Verification

Item 6:

* `cargo test -p lilo config_file_flag -- --nocapture`: 2 passed
* `just codegen --check`: passed
* `cargo run -q -p lilo -- --config x.toml doctor`: exit `3`, clear env only diagnostic
* `cargo run -q -p lilo -- -c x.toml doctor`: exit `3`, clear env only diagnostic
* `cargo run -q -p lilo -- doctor`: exit `0`
* `just check && just build && just test`: 562 passed

Item 8:

* `cargo test -p lilo doctor_rpc_timeout -- --nocapture`: 1 passed
* `just check && just build && just test`: 563 passed

Item 9:

* `cargo test -p lilo-rm-core optional_json_line -- --nocapture`: 3 passed
* `cargo test -p lilo-rm-core proto::tests -- --nocapture`: 7 passed
* `just check && just build && just test`: 567 passed

Pushes:

* `fix/roadtest` pushed through `f37e623`
* `fix/roadtest` pushed through `7746a92`
* `fix/roadtest` pushed through `63c1491`

## Open Items

* Phase F PR creation remains for the orchestrator.
* No follow up code work is known from items 6, 8, or 9.
