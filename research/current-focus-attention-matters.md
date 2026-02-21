---
title: Current Status and Next Focus for attention-matters
type: research
tags: [attention-matters, rust, geometric-memory, validation, roadmap]
summary: Subagent review found a mature Rust geometric memory engine with the next work concentrated on validation, eval reproducibility, fmm freshness, chat hardening, and CI coverage.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

`attention-matters` is a Rust workspace for geometric memory on the S³ hypersphere. The core architecture is in place: pure math in `am-core`, SQLite persistence in `am-store`, and CLI, MCP, HTTP, chat, and sync surfaces in `am-cli`.

The next focus should move from core feature construction to operational proof: rebuild stale structural indexes, restore a reproducible semantic retrieval eval harness, make validation commands non mutating, add frontend and package smoke checks to CI, and harden the HTTP plus LLM proxy path.

## Project Metadata

| Field | Current state |
| --- | --- |
| Language | Rust 2024 edition for workspace crates; TypeScript for `chat/` |
| Workspace | `am-core`, `am-store`, `am-cli` in `Cargo.toml:1-7` |
| Version | `0.2.2` in `Cargo.toml:9-12` |
| Build system | Cargo workspace plus `justfile` recipes |
| Frontend | Next `16.1.6`, React `19.2.3`, TypeScript `5` in `chat/package.json:5-39` |
| Key Rust deps | `rusqlite`, `tokio`, `axum`, `reqwest`, `eventsource-stream`, `futures-util` in `Cargo.toml:17-36` |
| CI gates | fmt, clippy, nextest, doctests, audit, PR drift benchmark in `.github/workflows/ci.yml:32-77` |
| fmm status | `.fmm.db` exists, but local fmm rejected it: index built with fmm `0.2.1`, active fmm is `0.2.8` |

## Architecture

### Core product shape

README describes the engine as geometric memory where query activation causes quaternion drift, phasor interference, and Kuramoto phase coupling. The public model is documented in `README.md:1-31`.

The repo has three main Rust crates:

1. `am-core`: zero I/O math engine with quaternion positions, phasors, drift, interference, coupling, scoring, composition, batch query, feedback, salient extraction, and tokenizer modules. Public modules are exported in `crates/am-core/src/lib.rs:35-54`.
2. `am-store`: SQLite persistence, schema migrations, config, unified `brain.db`, and test store.
3. `am-cli`: CLI, MCP server, HTTP server, sync, import/export, garbage collection, and LLM proxy.

README confirms this crate split at `README.md:88-94`.

### Runtime surfaces

The MCP server exposes core memory tools through one dispatch point in `crates/am-cli/src/server/mod.rs:192-210`. Supported tools include query, indexed query, retrieve, activate response, salient, buffer, ingest, stats, export, import, feedback, batch query, episode list, and neighborhood inspection.

The HTTP server mirrors the memory API and adds chat at `/api/chat`; routes are defined in `crates/am-cli/src/http_server.rs:72-98`.

The `chat/` frontend has local scripts for `dev`, `build`, `lint`, `typecheck`, and `check` in `chat/package.json:5-12`.

## Key Patterns

1. **Clean crate boundaries**: `am-core` remains pure math. Persistence and transport live outside it.
2. **Hexagonal persistence port**: `am-core` exposes `AmStore`; `am-store` owns SQLite implementation.
3. **Serialized server mutation**: MCP server state is behind a single mutex. The code documents this as intentional for a single stdio client, with a future split into `RwLock<DAESystem>`, store mutex, and session mutex for multi client transports in `crates/am-cli/src/server/mod.rs:48-70`.
4. **Product surface expansion**: The repo now includes not only CLI and MCP, but also HTTP, chat, LLM proxy, npm wrapper, and release packaging. This shifts risk toward integration and delivery.

## Detailed Findings

### Current status

The workspace is clean according to `git status --short`. No local uncommitted changes were observed during this review.

Subagent architecture review found the main implementation pieces already present:

- `DAESystem` with episodes, conscious state, lazy indexes, and epoch tracking.
- `QueryEngine` with activate, drift, interference, coupling, and mutation manifests.
- Context composition across conscious, subconscious, and novel recall.
- Batch query for amortized multi query recall.
- Feedback loop for boost and demote signals.
- SQLite schema version 7 with WAL and migrations.
- HTTP and chat surfaces on top of the same AM server.

Subagent validation review found broad Rust coverage. It counted 467 tracked Rust test attributes and 10 tracked insta snapshots. Important test surfaces include CLI integration tests, MCP protocol tests, shutdown behavior, core integration tests, property tests, server tool snapshots, and store persistence tests.

### fmm needs attention first

A fresh local fmm call failed with:

```text
Index was built with fmm v0.2.1 but you are running v0.2.8. Run `fmm generate --force` to rebuild.
```

The architecture subagent also reported a stale fmm entry for `crates/am-autoresearch/src/main.rs`, while the crate is absent from disk and absent from workspace members in `Cargo.toml:3-7`.

This should be the first cleanup because fmm is the preferred structural context tool for Helioy work. Structural review should not proceed from a stale index.

### Validation command mismatch

Root `just check` is not a read only validation command. It depends on `fmt` and `clippy`; `clippy` runs with `--fix --allow-dirty` in `justfile:20-23`, so it can edit files.

CI uses non mutating commands instead:

- `cargo fmt --all -- --check` at `.github/workflows/ci.yml:32-33`
- `cargo clippy --workspace --all-targets -- -D warnings` at `.github/workflows/ci.yml:35-36`
- `cargo nextest run --workspace` and doctests at `.github/workflows/ci.yml:41-44`
- `cargo audit` at `.github/workflows/ci.yml:46-49`

Add a root `just validate` that mirrors CI exactly.

### Semantic retrieval eval is missing from tracked state

Prior memory says an autoresearch eval harness was built, including deterministic ingest, batch `query-index`, `eval.sh`, `program.md`, and a gold standard. Current tracked files do not contain a semantic eval harness or quality metrics such as nDCG, MRR, recall at k, or fixed corpus scoring.

This is the highest value product validation gap. The Rust tests prove mechanics and protocols. They do not prove retrieval quality over a stable corpus.

### Chat and LLM proxy are the highest risk runtime surface

The HTTP router exposes `/api/chat` at `crates/am-cli/src/http_server.rs:97`. The architecture subagent traced the LLM proxy through AM context query, OpenRouter streaming, SSE to client, post response buffer, response activation, and salient tag extraction.

Focused tests should cover:

- Missing API key.
- Upstream 429.
- Upstream 5xx.
- Malformed SSE.
- Client disconnect during stream.
- Post response buffer or activation failure.
- Recall context budget behavior before OpenRouter request construction.

### Frontend and package delivery are outside root CI

The chat app has `npm run check`, which chains lint and typecheck in `chat/package.json:9-11`. Root CI does not run it.

Release packaging builds native binaries and publishes the npm wrapper, but no install smoke was reported. Add smoke tests for help output and MCP handshake through the package path.

## Recommended Next Focus

1. **Refresh structural context**
   - Run `fmm generate --force`.
   - Confirm `crates/am-autoresearch` is gone from the index.
   - Re run the topology review from fresh fmm.

2. **Add non mutating validation command**
   - Add `just validate` with CI exact commands.
   - Keep `just check` if desired, but label it as formatting and fixing.

3. **Restore semantic retrieval eval harness**
   - Check whether prior `eval.sh`, `gold_standard.json`, and `program.md` were deleted, ignored, or created outside git.
   - Rebuild a tracked fixed corpus eval with nDCG at 10, MRR, recall at k, and deterministic ingest seed.
   - Gate obvious regressions locally before changing scoring.

4. **Harden chat and LLM proxy**
   - Add tests for upstream errors, malformed streams, disconnects, missing keys, and post stream side effects.
   - Verify memory injection respects strict token budgets.

5. **Expand CI surface**
   - Add `chat` lint and typecheck.
   - Add npm wrapper smoke tests.
   - Add MCP handshake smoke test from the packaged binary path.

6. **Revisit benchmark coverage**
   - Current PR benchmark gate covers `am-core` drift only.
   - Add store save/load and query pipeline benchmarks when stable baselines exist.

## Dependencies

Critical dependencies and roles:

- `rusqlite` with bundled SQLite: persistent brain store.
- `tokio`: async runtime for server surfaces.
- `axum` and `tower-http`: HTTP API and CORS.
- `reqwest`, `eventsource-stream`, `futures-util`, `async-stream`: OpenRouter and SSE streaming path.
- `clap`: CLI command surface.
- `serde` and `serde_json`: state import/export, MCP, HTTP payloads.
- Next, React, TypeScript, assistant UI packages: chat frontend.

## Relevance to Helioy

`attention-matters` is the organizational identity memory layer in Helioy. It complements `context-matters`, which stores structured memory, by surfacing associative geometric recall. The immediate Helioy concern is reliability under agent workloads: bounded output, reproducible recall quality, stable MCP behavior, and package install confidence.

## Open Questions

1. Was the semantic eval harness intentionally removed, never committed, or lost during a branch transition?
2. Should HTTP remain a localhost single user surface, or should it graduate to multi client support?
3. What exact token budget should `am_query`, `am_query_index`, `am_retrieve`, and chat context injection enforce by default?
4. Should release quality be measured mainly by Rust tests, package smoke tests, or semantic eval gates?
