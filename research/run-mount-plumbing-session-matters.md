---
title: Run Mount Plumbing Verification in session-matters
type: research
tags: [session-matters, runtime-matters, mounts, verification, mcp, cli]
summary: Verified commit e9ceae2 adds sm run mount plumbing from CLI and MCP inputs through daemon launch and runtime-matters forwarding.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Executive Summary

Commit `e9ceae2` on `codex/sm-run-mounts` safely adds run mount plumbing. The change carries Docker bind mounts from `sm run --mount` and MCP `session_run` or `agent_run` arguments into `SpawnRequest`, daemon `SpawnLaunch`, and the runtime-matters client request, with host isolation rejected before launch.

## Project Metadata

- Language: Rust
- Workspace crates touched by the reviewed path: `sm-cli`, `sm-daemon`, `sm-core`, `sm-driver`
- Runtime dependency surface: `lilo-rm-core` and `lilo-rm-client` bumped from `0.7.0` to `0.7.1`
- Build system: Cargo workspace plus generated surfaces from `tools/*.toml`
- fmm status: `.fmm.db` validated clean with 107 indexed files

## Architecture

The mount data path is end to end:

1. CLI accepts repeated `--mount HOST:CONTAINER[:ro|:rw]` values as `Vec<MountSpec>` on `RunArgs`. See `crates/sm-cli/src/cli/cli_def.rs:79-101`.
2. CLI default isolation remains host, so `run` rejects nonempty mounts under host isolation before daemon I/O. See `crates/sm-cli/src/cli/run.rs:15-27` and `crates/sm-cli/src/cli/run.rs:105-110`.
3. CLI spawn includes `mounts` in the boxed `SpawnRequest`. See `crates/sm-cli/src/cli/run.rs:41-103`.
4. MCP `agent_run` and `session_run` parse the `mounts` array, use `MountSpec::from_str`, reject host isolation with mounts, and pass mounts into `SpawnRequest`. See `crates/sm-daemon/src/mcp_tools.rs:117-176` and `crates/sm-daemon/src/mcp_tools.rs:643-658`.
5. `sm-core::SpawnRequest` already owns the wire field with a serde default and empty vector omission. See `crates/sm-core/src/proto.rs:17-44`.
6. The daemon converts `request.mounts` into `SpawnLaunch.mounts`. See `crates/sm-daemon/src/handler.rs:609-647`.
7. `RtmdDriver::spawn` forwards `launch.mounts` into `lilo_rm_client::SpawnRequest`, which crosses into runtime-matters. See `crates/sm-driver/src/rtmd.rs:48-83`.

## Key Patterns

- `MountSpec` parsing stays owned by runtime-matters through `lilo_rm_core::MountSpec`, avoiding duplicate parser logic in session-matters.
- Host isolation rejection is mirrored at both entry surfaces, CLI and MCP, so invalid mount requests do not reach the spawn driver.
- `tools/run.toml` remains the public surface source of truth. The reviewed change adds the `mounts` parameter there, then regenerates help, MCP schemas, snapshots, README text, and skill docs.
- Deprecated `agent_run` stays in parity with `session_run` for the new argument, which avoids alias drift.

## Detailed Findings

### CLI plumbing

`RunArgs` imports `MountSpec` and adds `mounts: Vec<MountSpec>` behind repeated `--mount` values. `run` computes the defaulted isolation once, rejects host mounts, and passes mounts into `spawn_session`. `create_session` preserves the old no mount behavior by passing `Vec::new()`.

Evidence:

- `crates/sm-cli/src/cli/cli_def.rs:86-91`
- `crates/sm-cli/src/cli/run.rs:15-27`
- `crates/sm-cli/src/cli/run.rs:29-39`
- `crates/sm-cli/src/cli/run.rs:41-103`
- `crates/sm-cli/src/cli/run.rs:105-110`

### MCP plumbing

MCP `session_run` and `agent_run` share `agent_run`, so one parsing path covers both. The optional `mounts` field is required to be an array of strings, and each item is delegated to `MountSpec::from_str`.

Evidence:

- `crates/sm-daemon/src/mcp_tools.rs:117-176`
- `crates/sm-daemon/src/mcp_tools.rs:643-658`

### Runtime forwarding

The daemon and driver path already had a mount capable contract. The reviewed commit fills the missing entry side so mount values can reach existing forwarding code.

Evidence:

- `crates/sm-core/src/proto.rs:17-44`
- `crates/sm-daemon/src/handler.rs:609-647`
- `crates/sm-driver/src/rtmd.rs:48-83`

### Generated surfaces

`tools/run.toml` defines `mounts` as an optional string array with `--mount`. Generated schema files for both `session_run` and `agent_run` include the same `mounts` property. `generated_help.rs`, `generated_instructions.rs`, `README.md`, `templates/SKILL.md`, and snapshots carry the same Docker bind mount description.

Evidence:

- `tools/run.toml:133-138`
- `crates/sm-cli/src/cli/generated_help.rs:19-22`
- `crates/sm-cli/src/mcp/generated_schema/session_run.json`
- `crates/sm-cli/src/mcp/generated_schema/agent_run.json`
- `crates/sm-cli/templates/SKILL.md`
- `README.md`

### Test coverage

New coverage asserts both rejection and forwarding:

- CLI rejects `--mount` when default host isolation is active before daemon contact. See `crates/sm-cli/tests/cli_isolation_test.rs:101-121`.
- MCP rejects host isolation with mounts and asserts no launch occurred. See `crates/sm-daemon/tests/mcp_tools.rs:58-81`.
- MCP docker launches assert parsed mount structs reach `SpawnLaunch`. See `crates/sm-daemon/tests/mcp_tools.rs:83-122`.

Verification commands run:

```text
git log -1 e9ceae2
git show --stat e9ceae2
git diff main..e9ceae2
fmm validate
cargo test -p sm-cli cli_isolation_test
cargo test -p sm-daemon mcp_tools
cargo build --workspace
cargo test -p sm-cli --test cli_isolation_test
cargo test -p sm-daemon --test mcp_tools
cargo test -p sm-cli --test mcp_schema_snapshot_test
cargo test -p sm-cli --test generated_surface_guard_test
cargo test -p sm-driver --test rtmd_spawn
python generated surface consistency script
git status --short
find . -name '*.snap.new' -print
```

Results:

- Requested cargo filter invocations exited 0, but selected 0 tests because the trailing argument is a test name filter.
- Exact integration test binaries also passed: CLI isolation 3 tests, daemon MCP tools 4 tests, MCP schema snapshots 3 tests, generated surface guard 4 tests, driver rtmd_spawn 2 tests.
- `cargo build --workspace` passed.
- Generated surface consistency script passed.
- `git status --short` produced no output.
- No `.snap.new` files existed.

## Dependencies

- `lilo-rm-core 0.7.1`: provides `IsolationPolicy`, `MountSpec`, spawn target helpers, and caller environment capture.
- `lilo-rm-client 0.7.1`: provides the runtime-matters spawn client request consumed by `RtmdDriver`.
- `serde_json`: parses MCP tool arguments and generated schemas.
- `clap`: parses CLI `--mount` values through `FromStr` on `MountSpec`.

## Relevance to Helioy

This preserves the intended split: session-matters stays the control plane and runtime-matters owns mount semantics and Docker execution. The commit is safe for the current pre-release posture and aligns with the larger isolation plumbing path.

## Open Questions

- None blocking. A future dedicated rtmd driver test could assert nonempty mounts in the runtime client payload directly, but current daemon MCP tests prove `SpawnLaunch.mounts`, and `RtmdDriver::spawn` visibly forwards that field.
