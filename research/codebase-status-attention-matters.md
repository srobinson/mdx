---
title: attention-matters codebase status review
type: research
tags: [attention-matters, rust, architecture, status-review, helioy]
summary: Read-only status review of attention-matters architecture, implementation state, gaps, and next focus areas.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

`attention-matters` is a Rust 2024 workspace for a DAE geometric memory engine with a clean three-crate core: pure math, SQLite persistence, and CLI/MCP/HTTP transport. The main implementation is substantial and tested, with an additional Next.js chat frontend and npm distribution wrapper outside the Rust workspace.

The most notable status risks are operational rather than conceptual: fmm has at least one stale indexed path, the HTTP/LLM path is newer and concurrency-constrained by design, and there are no inline TODOs marking remaining work.

## Project Metadata

- Workspace: Rust Cargo workspace, resolver 3, edition 2024, version 0.2.2 (`Cargo.toml:1-12`).
- Workspace members: `crates/am-core`, `crates/am-store`, `crates/am-cli` (`Cargo.toml:3-7`).
- Important dependencies: `rusqlite` bundled SQLite, `clap`, `tokio`, `axum`, `reqwest` with `rustls-tls`, `eventsource-stream`, `serde`, `uuid` (`Cargo.toml:14-36`).
- Frontend: Next 16, React 19, assistant-ui, TanStack Query, TypeScript (`chat/package.json:5-39`).
- Distribution: npm wrapper package downloads or invokes native `am` binary (`npm/attention-matters/bin/am:1-35`, `npm/attention-matters/scripts/install.js:75-113`).
- fmm: repo has `.fmm.db`, but the index appears stale for `crates/am-autoresearch`, which fmm lists while the directory is absent on disk.

## Architecture

### Workspace and crate topology

fmm reports 100 indexed files and 28,458 LOC, with 65 files under `crates`, 34 under `chat`, and 1 under `npm`. The actual Rust workspace contains three crate members (`Cargo.toml:3-7`):

1. `am-core`: pure math engine, 23 source files, 8,866 LOC by fmm.
2. `am-store`: SQLite persistence and config, 16 source files, 4,510 LOC by fmm.
3. `am-cli`: CLI, MCP server, HTTP server, sync, LLM proxy, 17 source files, 6,682 LOC by fmm.

README documents the intended separation directly: `am-core` is zero I/O math, `am-store` is persistence, `am-cli` is CLI plus MCP server (`README.md:88-94`).

### am-core

`am-core` exports the main modules for activation statistics, batch, composition, constants, episodes, feedback, neighborhoods, occurrences, phasors, quaternions, query, salient extraction, serde compatibility, store trait, surface, system, time, and tokenizer (`crates/am-core/src/lib.rs:35-54`). Its top-level doc states the crate is a zero I/O pure math engine (`crates/am-core/src/lib.rs:1-13`).

Important implemented modules:

- `DAESystem`: owns subconscious episodes, a single conscious episode, lazy word and neighborhood indexes, and epoch state (`crates/am-core/src/system.rs:68-161`). It explicitly replaced sentinel addressing with `EpisodeRef::Conscious` and `EpisodeRef::Subconscious` (`crates/am-core/src/system.rs:11-22`).
- `QueryEngine`: implements tokenize, activate, drift, interference, Kuramoto coupling, and mutation manifest tracking (`crates/am-core/src/query.rs:11-25`, `crates/am-core/src/query.rs:87-166`). It switches from pairwise drift to centroid drift for large activation sets (`crates/am-core/src/query.rs:168-206`).
- `compose`: ranks and formats conscious, subconscious, and novel recall, with budgeted composition and token estimates (`crates/am-core/src/compose.rs:12-105`, `crates/am-core/src/compose.rs:165-203`).
- `batch`: amortizes multi-query activation, drift, interference, and context composition for Nancy or multi-agent use cases (`crates/am-core/src/batch.rs:1-10`, `crates/am-core/src/batch.rs:72-91`).
- `feedback`: implements boost and demote feedback with manifests for incremental persistence (`crates/am-core/src/feedback.rs:1-10`, `crates/am-core/src/feedback.rs:18-39`, `crates/am-core/src/feedback.rs:102-129`).
- `store_trait`: defines the hexagonal persistence port owned by core and implemented by store adapters (`crates/am-core/src/store_trait.rs:8-20`).

### am-store

`am-store` provides SQLite and an in-memory test adapter. Schema version is 7 with WAL, foreign keys, busy timeout, autocheckpoint, tables for metadata, episodes, neighborhoods, occurrences, and conversation buffer, plus migration steps through v7 (`crates/am-store/src/schema.rs:6-77`, `crates/am-store/src/schema.rs:79-147`).

Important implemented modules:

- `config`: resolves config from env, project config, global config, and defaults, then validates absolute `data_dir` and DB constraints (`crates/am-store/src/config.rs:53-74`, `crates/am-store/src/config.rs:83-107`, `crates/am-store/src/config.rs:109-168`).
- `project`: `BrainStore` uses one `~/.attention-matters/brain.db`, migrates the old project/global DB layout, and runs startup GC if configured (`crates/am-store/src/project.rs:25-72`, `crates/am-store/src/project.rs:78-193`, `crates/am-store/src/project.rs:199-218`).
- `memory_store`: in-memory `AmStore` implementation for handler tests, explicitly not production (`crates/am-store/src/memory_store.rs:1-5`, `crates/am-store/src/memory_store.rs:27-38`, `crates/am-store/src/memory_store.rs:84-100`).

### am-cli and transport

`am-cli` defines commands for serve, query, ingest, stats, export, import, inspect, sync, GC, forget, and init (`crates/am-cli/src/main.rs:45-203`). The MCP server dispatches 14 tools: query, query-index, retrieve, activate-response, salient, buffer, ingest, stats, export, import, feedback, batch-query, episodes, and episode-neighborhoods (`crates/am-cli/src/server/mod.rs:192-211`).

Server design is intentionally serialized behind one mutex for the current single-client stdio deployment, with a documented decomposition path for multi-client HTTP/SSE (`crates/am-cli/src/server/mod.rs:48-70`). Query mutations are persisted incrementally using `QueryManifest` via targeted position and activation updates (`crates/am-cli/src/server/mod.rs:118-142`).

The HTTP server exposes local-only Axum routes for AM APIs and `/api/chat`, with permissive local CORS and request tracing (`crates/am-cli/src/http_server.rs:64-175`). The LLM proxy queries AM memory first, builds an OpenRouter request, streams SSE output, then buffers the exchange, activates the response, and extracts salient tags after completion (`crates/am-cli/src/llm_proxy.rs:262-358`, `crates/am-cli/src/llm_proxy.rs:360-512`, `crates/am-cli/src/llm_proxy.rs:514-552`).

### chat frontend

`chat` is a separate Next.js app, not part of the Cargo workspace. It includes typed AM HTTP clients, assistant-ui runtime integration, settings, upload, chat, and memory explorer components. The client defaults to `http://localhost:3001` (`chat/src/lib/am-client.ts:27-29`) and maps memory tool endpoints directly (`chat/src/lib/am-client.ts:139-205`). The runtime stores per-message context metadata for the memory panel and classifies streaming errors (`chat/src/lib/am-runtime.ts:1-12`, `chat/src/lib/am-runtime.ts:103-125`, `chat/src/lib/am-runtime.ts:138-237`).

## Key Patterns

- Hexagonal persistence boundary: `am-core` owns `AmStore`, `am-store` implements it, and server handlers depend on the trait (`crates/am-core/src/store_trait.rs:8-20`).
- Mutation manifests: query and feedback paths return changed IDs so hot paths can persist targeted updates rather than rewriting the full system (`crates/am-core/src/query.rs:11-25`, `crates/am-cli/src/server/mod.rs:118-142`).
- Explicit conscious/subconscious references: enum based addressing replaces sentinel indexes (`crates/am-core/src/system.rs:11-22`).
- Budget-aware recall: context composition tracks categories, included IDs, and token estimates (`crates/am-core/src/compose.rs:48-105`).
- Single-client correctness first: server state is serialized behind a mutex, with an explicit future multi-client design note (`crates/am-cli/src/server/mod.rs:48-70`).

## Detailed Findings

### Implementation state

- Core math is implemented across quaternion, phasor, occurrence, neighborhood, episode, system, query, surface, compose, batch, feedback, scoring, recency, salient, activation stats, tokenizer, and serde compatibility modules (`crates/am-core/src/lib.rs:35-54`).
- Persistence is not just a full state dump. Schema v7 supports targeted occurrence activation and position updates, buffering, GC, import/export, and forget operations via the store trait (`crates/am-core/src/store_trait.rs:24-158`).
- MCP and HTTP surfaces are both present. MCP is JSON-RPC over stdio; HTTP mirrors memory endpoints and adds chat proxying (`crates/am-cli/src/server/mod.rs:192-211`, `crates/am-cli/src/http_server.rs:72-98`).
- Test coverage exists across crate internals, integration tests, CLI tests, MCP protocol tests, shutdown behavior, proptest, and benches. fmm shows large in-source test files: `compose_tests.rs`, `query_tests.rs`, `store/tests.rs`, `server/server_tests.rs`, and `sync_tests.rs`.
- Git workspace was clean at review time.

### Gaps and risks

- fmm index drift: `crates/am-autoresearch/src/main.rs` appears in fmm, but `crates/am-autoresearch` does not exist on disk and is not a Cargo workspace member. Rebuild or validate fmm before treating fmm counts as authoritative.
- No explicit TODO inventory: `rg TODO|FIXME|unimplemented|todo!` found no real code TODOs or stubs. This is good for cleanliness, but it means remaining work is not discoverable from markers.
- HTTP/chat path is newer than the core path. It depends on OpenRouter streaming, API key forwarding, SSE parsing, and post-response side effects. It deserves focused failure-mode testing (`crates/am-cli/src/llm_proxy.rs:262-552`, `chat/src/lib/am-runtime.ts:35-101`).
- Multi-client server support is not implemented by design. The current mutex serializes all tool calls and is correct for stdio, but a throughput limit for real concurrent HTTP clients (`crates/am-cli/src/server/mod.rs:48-70`).
- `am_query` token budget concerns have prior memory context: a previous session observed oversized recall output when `max_tokens` was not effectively bounded. Recheck the current `am_query` and `am_query_index` behavior before relying on them in constrained agent contexts.

## Dependencies

Critical dependencies and roles:

- `rusqlite` bundled: SQLite persistence and WAL (`Cargo.toml:18`).
- `tokio`, `axum`, `tower-http`: HTTP/SSE server and tracing layers (`Cargo.toml:29-32`).
- `reqwest`, `eventsource-stream`, `futures-util`, `async-stream`: OpenRouter streaming bridge (`Cargo.toml:33-36`).
- `clap`: CLI command surface (`Cargo.toml:23`).
- `serde`, `serde_json`, `uuid`: serialization, wire compatibility, and IDs (`Cargo.toml:19-22`).
- Next.js, React, assistant-ui, TanStack Query: chat frontend runtime and UI (`chat/package.json:13-39`).

## Recommended Next Focus Areas

1. Rebuild and validate fmm. The stale `am-autoresearch` entry is small but undermines structural confidence. Run `fmm validate` or equivalent and refresh `.fmm.db`.
2. Harden the HTTP and chat path. Add or review tests for OpenRouter errors, mid-stream disconnect, missing API key, context SSE metadata, and post-response buffer or salient failures (`crates/am-cli/src/llm_proxy.rs:262-552`).
3. Decide the concurrency roadmap. If HTTP is productized beyond localhost single-user use, implement the documented split between `RwLock<DAESystem>`, SQLite write locking, and session state (`crates/am-cli/src/server/mod.rs:48-70`).
4. Verify recall budget enforcement. Prior memory indicates `am_query` can emit very large contexts. Confirm `max_tokens` behavior across `am_query`, `am_query_index`, `am_retrieve`, and chat memory context.
5. Bring the chat frontend into the main quality loop. Rust `just check` does not cover `chat/package.json` scripts. Add a top-level task or CI target for `npm run check` in `chat` if the frontend is part of the product surface.

## Relevance to Helioy

The project is already a Helioy memory component. The clean separation between pure memory mechanics, persistence port, and transport adapters is a reusable pattern for Helioy services. The batch query module is specifically aligned with multi-agent orchestration and Nancy-style parallel worker contexts (`crates/am-core/src/batch.rs:1-10`).

## Open Questions

- Is `chat` intended to be released with the CLI, or only developed locally?
- Should HTTP mode remain localhost-only and single-user, or become a supported multi-client server?
- Is `am-autoresearch` intentionally removed, or should it return as an evaluation crate?
- What is the current target token budget policy for MCP memory recall?
