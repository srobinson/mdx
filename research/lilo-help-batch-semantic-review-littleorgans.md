---
title: lilo Help Batch Semantic Review
type: research
tags: [littleorgans, lilo, cli, help, semantic-review]
summary: Semantic review of the lilo help batch found stale wait prose, wait condition semantics drift, and delete namespace prose drift.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

## Executive Summary

The reviewed batch is the generated `lilo` help for ten session commands: `create`, `get`, `delete`, `label`, `mail`, `nudge`, `capture`, `logs`, `wait`, and `mcp`. The examples render and parse, but semantic review found conditional fixes in `wait` and `delete` prose.

## Project Metadata

- Language: Rust 2024 workspace, version `0.8.0`, `rust-version = "1.95"` in `Cargo.toml:31-39`.
- CLI framework: Clap derive, `clap = "4.5.51"` in `Cargo.toml:40-45`.
- Build system: Cargo workspace with 27 members in `Cargo.toml:1-28`; `just` exposes `check`, `build`, and `test` gates in `justfile:16-49` and `justfile:144-160`.
- Navigation: `.fmm.db` is present. fmm was used for topology, outlines, and symbol reads before direct inspection.
- Authored help source: `tools/schemas/cli.toml:51-243` for the reviewed command batch.

## Architecture

`tools/schemas/cli.toml` is the authored source for command help text and examples. Generated constants are consumed by Clap structs in `internal/session/app/src/cli/cli_def.rs`, and dispatch routes commands through `internal/session/app/src/cli.rs:36-54`.

Important review paths:

- `internal/session/app/src/cli/cli_def.rs:79-92`, `111-130`, `207-216`, `230-257`, `283-321`, `352-378` define the public argument surface for the reviewed commands.
- `internal/session/app/src/cli/get.rs:9-72`, `delete.rs:19-86`, `mail.rs:32-235`, `label.rs:10-35`, `logs.rs:14-37`, `wait.rs:9-32`, `nudge.rs:9-40`, `capture.rs:8-27`, and `mcp.rs:5-7` map parsed args to daemon requests.
- `internal/session/daemon/src/polish.rs:92-167` implements `wait` and logs resolution semantics.
- `internal/session/daemon/src/namespace.rs:85-168` implements namespace deletion and cascade cleanup.
- `internal/runtime/daemon/src/runtime_kill.rs:36-63` implements requested signal and `SIGKILL` escalation behavior.

## Key Patterns

- Help examples can pass parse tests while prose still drifts. The `wait` timeout issue is a concrete case: examples use `--timeout-secs`, while `long_about` still says `--timeout`.
- Selector examples need semantic review against handler cardinality. `logs` requires exactly one matching session, while `wait` uses any matching session for `running` and `terminated`.
- For generated surfaces, review the authored TOML, rendered help, Clap arg structs, and downstream handler behavior together.

## Detailed Findings

### 1. `wait` long_about names the wrong timeout flag

`tools/schemas/cli.toml:216-218` says the command times out after `--timeout` seconds. The real Clap field is `timeout_secs` with a bare `long`, so the rendered flag is `--timeout-secs` in `internal/session/app/src/cli/cli_def.rs:250-257`.

Recommended fix: change `--timeout` to `--timeout-secs` in the `wait` `long_about`.

### 2. `wait` prose and one example imply all matched sessions reach a condition

The `wait` `long_about` says the sessions a selector matches reach `running`, `terminated`, or `count=N` in `tools/schemas/cli.toml:216-218`. The terminated example says “Wait until matching sessions terminate” in `tools/schemas/cli.toml:224-226`.

Actual behavior is different. `wait_condition_met` uses `any` matching session for `running` and `terminated`, and exact length only for `count=N` in `internal/session/daemon/src/polish.rs:148-161`.

Recommended fix: reword to “Block until any matching session is running or terminated, or until exactly `count=N` sessions match.” Change the terminated example description to singular, or use an exact id selector.

### 3. `delete namespace` prose incorrectly says the namespace must be empty

`tools/schemas/cli.toml:99-114` says `delete namespace` removes an empty namespace, and the example repeats “Delete an empty namespace.” The code deletes nonempty namespaces by terminating sessions, removing namespace sessions from the catalog, deleting the namespace, and clearing a matching user context.

Evidence:

- CLI sends `NamespaceDelete` and clears matching binding in `internal/session/app/src/cli/delete.rs:47-86`.
- Daemon checks the namespace, calls `cascade_terminate_namespace`, then removes the namespace catalog in `internal/session/daemon/src/namespace.rs:85-109`.
- Cascade termination and catalog removal are in `internal/session/daemon/src/namespace.rs:112-168`.
- The subcommand about already says “Delete a namespace, terminate its sessions, and clear matching user context” in rendered help.

Recommended fix: drop “empty.” Suggested wording: “`delete namespace` removes a namespace, terminates its sessions, and clears matching user context.” Change the example description to “Delete a namespace and its sessions.”

### 4. `delete session` signal prose should describe the requested signal

The `delete` `long_about` says session deletion signals matching runtimes with `SIGTERM`, then `SIGKILL` after grace in `tools/schemas/cli.toml:99-102`. That is the default path, not the full behavior. The CLI accepts a requested signal with default `SIGTERM` in `internal/session/app/src/cli/cli_def.rs:207-216`. The session daemon passes `request.signal` through in `internal/session/daemon/src/handler/sessions.rs:111-117`. Runtime kill sends the requested signal, then sends `SIGKILL` only if the process is still alive and the requested signal was not already kill in `internal/runtime/daemon/src/runtime_kill.rs:46-60`.

Recommended fix: phrase the delete session part as requested signal, default `SIGTERM`, with `SIGKILL` escalation after grace when needed.

### 5. Clean semantic checks

No change was recommended for these areas:

- Selector grammar for `role:`, `namespace:`, `label:`, `dir:`, id, and `all` matches `Selector` variants in `internal/session/core/src/selector/types.rs:11-33`.
- `WaitCondition` accepts `running`, `terminated`, and `count=N` in `internal/session/core/src/proto/session.rs:71-98`.
- Client mail send accepts `request`, `result`, and `inform`; `receipt` is reserved for daemon system messages in `internal/session/core/src/mail.rs:52-72` and `85-99`.
- `--notify` accepts `wait` and `steer` in `internal/session/core/src/mail.rs:103-112`.
- `SIGKILL` is accepted because `RuntimeSignal::from_str` strips an optional `SIG` prefix in `crates/lilo-rm-core/src/types/runtime.rs:95-107`.
- `capture` requires an exact UUID in `internal/session/app/src/cli/cli_def.rs:241-246`.
- Label mutation accepts `key=value` and `key-` in `internal/session/core/src/label.rs:29-45`.
- `mcp` correctly bridges stdio to the local daemon in `internal/session/app/src/cli/mcp.rs:5-7`.

## Dependencies

Critical dependencies for this surface:

- `clap` drives parse shape and rendered help.
- `lilo-session-core` defines selectors, mail intents, wait conditions, and RPC payloads.
- `lilo-session-daemon` implements wait, logs, delete, mail, label, and namespace behavior.
- `lilo-rm-core` defines runtime signal parsing and runtime request types.

## Relevance to Helioy

This review reinforces the current generated surface rule: parse validity is necessary but not sufficient. For Helioy CLI docs, batch review should include semantic checks against handler behavior, especially selector cardinality, defaults, and condition semantics.

## Open Questions

- The top level `create` `about` says “session, label, or other resource” in `tools/schemas/cli.toml:55`, but `create` currently exposes only `namespace` and `session`. This was outside the requested `long_about` and examples scope, so it was not included in the sign off conditions.
