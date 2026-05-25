---
title: littleorgans dry fix phase 2 rm launchers report
type: research
tags: [littleorgans, dry-fix, rm-launchers]
summary: RM launcher lane deduplicated runtime protocol, serde, client response, and binary launcher production code; lane crates are clippy clean.
status: complete
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented the Phase 2 `rm-launchers` DRY lane in production code only. I did not run git, cargo fix, or cargo fmt.

## Files changed

- `crates/lilo-rm-core/src/proto.rs`
- `crates/lilo-rm-core/src/launcher.rs`
- `crates/lilo-rm-core/src/cli_output.rs`
- `crates/lilo-rm-core/src/version.rs`
- `crates/lilo-rm-core/src/tool_contracts.rs`
- `crates/lilo-rm-core/src/types/runtime.rs`
- `crates/lilo-rm-core/src/types/spawn.rs`
- `crates/lilo-rm-core/src/string_serde.rs`
- `crates/lilo-rm-core/src/lib.rs`
- `crates/lilo-rm-client/src/lib.rs`
- `internal/runtime/launchers/src/lib.rs`
- `internal/runtime/launchers/src/claude.rs`
- `internal/runtime/launchers/src/codex.rs`

## Dedupe completed

- Shared nonempty JSON line read handling between async and blocking protocol readers.
- Shared argv command extraction for launch specs and shell resumes.
- Replaced separate optional signed and unsigned integer display helpers with one generic optional number formatter.
- Added `string_serde` helper module for string based `Serialize` and `Deserialize` implementations and consumed it from runtime kind, tmux address, and runtime capability types.
- Shared schema description injection for tool parameter and output schema values.
- Added a typed runtime client response extraction helper and macro to centralize repeated response matches.
- Replaced separate Claude and Codex launcher implementations with one parameterized `BinaryLauncher` and thin per binary registrations.

## Verification

Orchestrator confirmed this lane is done and the remaining `rm-client --all-targets` failure belongs to Lane 1.

Passed:

- `cargo clippy -p lilo-rm-core --all-targets -- -D warnings`
- `cargo clippy -p lilo-runtime-launchers --all-targets -- -D warnings`
- `cargo clippy -p lilo-runtime-launchers --lib -- -D warnings`
- `cargo clippy -p lilo-rm-client --lib -- -D warnings`

Blocked:

- `cargo clippy -p lilo-rm-core -p lilo-rm-client -p lilo-runtime-launchers --all-targets -- -D warnings`
- `cargo clippy -p lilo-rm-client --all-targets -- -D warnings`

Both failures are outside this lane. Cargo compiles `internal/runtime/daemon/src/service.rs`, which currently fails with:

```text
error[E0599]: no method named `context` found for enum `std::result::Result<T, E>` in the current scope
  --> internal/runtime/daemon/src/service.rs:96:24
```

The compiler suggests importing `anyhow::Context`. I did not edit that file because it is outside the lane.

## Open items

None for this lane. Lane 1 owns the remaining `internal/runtime/daemon/src/service.rs` compile error.
