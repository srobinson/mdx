---
title: Activity bounded context scout for Transport Matters
type: research
tags: [transport-matters, activity, scout, architecture, reuse-map]
summary: Existing proxy, breakpoint, transcript tailer, index, and run lifecycle seams can support Activity with targeted extraction and explicit fact writing.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Executive Summary

Transport Matters already has most of the producer seams needed for the Activity bounded context. The main gaps are a durable per run `facts.jsonl` writer, a workspace scoped Activity live channel, a neutral jsonl tailer extraction, symmetric breakpoint release facts, and detached run lifecycle facts.

## Project Metadata

- Language: Python backend with FastAPI, mitmproxy, Postgres, Pydantic, and React TypeScript frontends.
- Build shape: Python package under `api/src/transport_matters`, pnpm workspaces under `www/`, desktop TypeScript under `desktop/`.
- fmm: `.fmm.db` exists and indexed 943 files, 149,493 LOC.
- Scout inputs: `~/.mdx/projects/tm-activity-spec.md` sections 2, 5, 7, 10, and 11.

## Architecture

The existing write path is proxy first. `api/src/transport_matters/addon_handlers.py` routes Claude HTTP, Codex websocket, and Codex HTTP fallback flows into recorder functions. `api/src/transport_matters/exchange_recorder.py` owns Claude and Codex HTTP tier 1 writes through `persist_http_provisional_exchange`, `persist_http_exchange`, `_finalize_http_provisional_exchange`, and `persist_exchange`. `api/src/transport_matters/codex/exchange.py` owns Codex websocket tier 1 writes through `persist_codex_provisional_exchange`, `_persist_codex_exchange`, and `finalize_codex_provisional_exchange`. `api/src/transport_matters/storage/disk.py` `DiskStorageBackend.persist_exchange` and `_write_exchange_files` are the concrete disk writers.

The live stream surface is split. `api/src/transport_matters/broadcast.py` and `api/src/transport_matters/api/v1/stream.py` provide an in process, run scoped inspector SSE path. `api/src/transport_matters/session/listen.py` and `api/src/transport_matters/api/v1/session_routes.py` provide the Postgres notify backed session SSE path. Neither is a ready workspace scoped Activity channel from shared proxy to API.

`api/src/transport_matters/index/` is live transcript infrastructure, not the retired legacy index database. `PROJECT.md` states it survives as a compatibility namespace for transcript adapters, tailing, and deterministic session id synthesis. `index/tailer.py` contains reusable jsonl mechanics, but `TranscriptTailer` itself is coupled to `SessionBinding`, `TranscriptAdapter`, normalized transcript turns, and `SessionWriter` commits.

Run lifecycle has two owners. Canvas runs are process resident in `api/src/transport_matters/run_manager.py` through `RunManager._start_run_terminal`, `_drain_run`, and `_teardown_run`. Detached local CLI runs are owned by launch helpers such as `api/src/transport_matters/cli/runner.py` `run_client_children_until_outcome`, `api/src/transport_matters/captured_run.py` `prepare_captured_run`, and `api/src/transport_matters/launch_manifest.py` `run_with_workspace_manifest`.

## Key Patterns

- Tier 1 first: recorder code persists artifacts before optional observers such as `api/src/transport_matters/storage/exchange_sink.py` `emit_to_index`.
- Boundaries by injection: transcript snapshot writing and exchange sinks are injected into lower level tailer and storage paths rather than importing upper layers.
- Shared proxy registration: `api/src/transport_matters/shared_proxy/run_preparation.py` builds `ProxyRunBinding` with per run storage and registers it with the shared proxy.
- Breakpoint common seam: `api/src/transport_matters/pause_session.py` `_run_pause` covers HTTP and Codex websocket pauses in one place.

## Detailed Findings

1. Proxy write path fit is confirmed for Claude reverse proxy and Codex HTTPS proxy. The missing capability is the per run Activity fact writer. Searches: `fmm_search facts`, `rg facts.jsonl`, and `rg Fact` found only session facts and Codex derived artifacts.
2. A wire to run SSE channel exists, but it is process local and run scoped. Activity needs either a new workspace SSE surface or an explicit bridge for shared proxy processes.
3. Jsonl tailing should reuse `index/tailer.py` `iter_complete_records` and cursor ideas, not `TranscriptTailer` as is.
4. Breakpoint hold is already signaled through `_run_pause` and `broadcast.emit`; release is not symmetric. Emit `RequestHeld` and `RequestReleased` from `_run_pause`.
5. `index/` is live but should not receive Activity projection or status code. Move generic jsonl primitives to a neutral module if needed.
6. RunStarted and RunExited facts belong in `RunManager` for canvas runs. Detached runs need lifecycle emission around launcher outcomes or per run proxy lease close. `initial_prompt_ref` has no current owner.

## Dependencies

Critical dependencies in this scout are mitmproxy for proxy interception, FastAPI for API and SSE surfaces, Postgres LISTEN/NOTIFY for session events, Pydantic for event and storage models, and fmm for structural code navigation.

## Relevance to Helioy

Activity can become the standard downstream context pattern for Helioy feature work if it keeps producer facts self contained, storage owned, and downstream only. The scout reinforces the new context package rule: producers emit facts, Activity owns interpretation, and no status computation leaks outside `activity/`.

## Open Questions

- Should fact append failure block the proxy write path or be logged as a non fatal side write?
- Should Activity SSE be a sibling workspace endpoint or a shared hub that bridges proxy processes?
- Do `RequestReleased` facts include drop and timeout outcomes?
- Should jsonl tail primitives move out of `index/` before Activity imports them?
- Is `initial_prompt_ref` nullable for slice 1, or does launch need a new prompt artifact?
- For detached runs, is the authoritative `RunExited` source the launcher outcome or proxy lease close?
