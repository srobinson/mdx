---
title: Unified lilo Command Surface Planning for littleorgans ALP-2816
type: research
tags: [littleorgans, lilo, cli, linear, rust, architecture]
summary: ALP-2816 intent holds after Phase 7, with shim naming, codegen, docs, Linear hygiene, and readiness contract gaps to close.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Executive Summary

ALP-2816 remains the correct owner for the unified `lilo` command surface after ALP-2817. The detailed planning artifact is `~/.mdx/projects/littleorgans-ALP-2816-fleshout--codex.md`.

## Project Metadata

- Language: Rust 2024.
- Build system: Cargo workspace plus `just` and Moon metadata.
- Rust toolchain: `1.95` from `rust-toolchain.toml`.
- Workspace: 26 members including `crates/lilo`, `internal/runtime/app`, `internal/session/app`, `internal/db`, and `tests/integration`.
- Structural index: `.fmmrc.toml` exists and repo-local `fmm validate` passed for 350 indexed files.

## Architecture

The current tree has a top-level `lilo` binary with real `doctor`, real `daemon`, a hidden shim route, and placeholders for the remaining user and operator verbs. The session app already implements `run` and `create session` through `SessionRpc::Spawn`; the runtime daemon already enforces raw runtime identity gating and keeps raw spawns out of session tables.

## Key Patterns

- Session-backed spawn uses two transactions around the runtime side effect: Tx A writes audit, pending intent, and Forking lifecycle; Tx B writes session, Running lifecycle, and resolved intent.
- Raw runtime spawn is identified by absence of `session_spawn_intents` and `session_sessions` rows.
- The daemon resolves the shim executable via `std::env::current_exe`, but live argv still uses `__shim` while the locked contract says `__runtime-shim`.

## Detailed Findings

See `~/.mdx/projects/littleorgans-ALP-2816-fleshout--codex.md` for the verification table and five-worker decomposition. Important source anchors include:

- `crates/lilo/src/cli/mod.rs:71-79`: top-level placeholder dispatch.
- `internal/session/app/src/cli/run.rs:15-86`: session run and create-session dispatch.
- `internal/session/daemon/src/handler/spawn.rs:101-230`: session spawn Tx A and Tx B.
- `internal/runtime/daemon/src/identity.rs:9-61`: raw runtime RPC authorization and audit.
- `internal/runtime/daemon/src/shim_socket.rs:76-80`: current daemon shim argv.
- `crates/lilo/src/cli/daemon.rs:35-38`: current `daemon status` success return.

## Dependencies

Critical crates for Phase 6 are `clap`, `tokio`, `sqlx`, `lilo-db`, `lilo-paths`, `lilo-runtime-app`, `lilo-runtime-daemon`, `lilo-session-app`, `lilo-session-daemon`, `lilo-session-store`, and `lilo-im-core`.

## Relevance to Helioy

This plan closes the public local-first command surface for littleorgans v0.8.0. It preserves the substrate boundary that lets session behave like the API server while runtime remains the kubelet-shaped diagnostic substrate.

## Open Questions

- ALP-2894 readiness contract choice.
- Direct rename from `__shim` to `__runtime-shim`.
- Whether `lilo identity audit | whoami` must be implemented in Phase 6.
- Removal of canceled ALP-2815 from ALP-2816 blockers.
- Canonical clean-room smoke agent config for `lilo run`.
