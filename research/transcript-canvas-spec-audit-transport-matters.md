---
title: Transcript Canvas Spec Audit For Transport Matters
type: research
tags: [transport-matters, transcript-canvas, spec-audit, session-store, helioy]
summary: Audit of the transcript canvas specs verified prior review fixes, drove three consensus edits, and reached final signoff.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Executive Summary

Transport Matters is a context control plane for coding agents that proxies live agent traffic, captures turn artifacts, and can pause outbound requests before upstream release. The transcript canvas spec audit found that the prior Codex review findings 1 through 6 are incorporated, identified three child session transition gaps, verified the consensus edits landed, and sent final clean signoff.

The child session model is sound and buildable against the current session store. Slice 1 is not blocked if it stays read only over existing rows and uses the newly specified owner scoped raw bearing read for meta projection.

## Project Metadata

- **Repository:** `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- **Current HEAD during audit:** `3c47d3aa04240b455d2ebf3b8d4564e75beb219e`
- **fmm:** `.fmm.db` present. Initial topology from fmm showed 536 indexed files and 83,600 LOC across `api/`, `www/`, and `desktop/`.
- **Product role:** Transport Matters proxies live agent traffic, captures turn artifacts, presents a web UI, and can pause the next outbound request. It supports Claude Code via reverse proxy and Codex via explicit HTTPS proxy. See `README.md:5-11`.
- **Architecture role:** Active runtime has a live proxy path and a Postgres session store for correlated transcript history and live session events. See `PROJECT.md:3-7`.
- **Backend:** Python package requiring Python 3.14 with FastAPI, Pydantic settings, HTTPX, mitmproxy, Typer, psycopg, and Alembic. See `api/pyproject.toml:3-8` and `api/pyproject.toml:37-45`.
- **Backend build:** Hatchling plus hatch vcs, wheel includes the web bundle and migrations. See `api/pyproject.toml:80-101`.
- **Backend checks:** Ruff, strict mypy, pytest, and coverage are configured in `api/pyproject.toml:103-171`.
- **Frontend:** Vite, TypeScript, React 19, React Query, React Virtual, gesture support, Framer Motion, and Zustand. See `www/package.json:1-39`.
- **Frontend checks:** `pnpm lint`, `pnpm typecheck`, `pnpm test`, and `pnpm build` compose the CI script. See `www/package.json:10-29`.
- **Desktop:** Electron shell with TypeScript build, package smoke, Vitest, and typecheck scripts. See `desktop/package.json:1-29`.

## Architecture

Transport Matters keeps wire capture and transcript capture as separate streams. Tier 1 stores per run wire artifacts and transcript snapshots under `~/.transport-matters/workspaces/{slug}/{hash}/{run}/`; the Postgres session store provides owner scoped reads and live event streaming. See `PROJECT.md:69-84`.

The current session pipeline is:

1. `index/tailer.py` parses transcript records and threads cursor state through adapter normalization.
2. `session/ingest.py` maps raw records plus normalized turns into event writes.
3. `session/writer.py` upserts the session row and inserts events into Postgres.
4. `api/v1/session_routes.py` exposes owner scoped session list, event list, and event SSE routes.

Current code relevant to the canvas contract:

- `SessionRow` already carries child linkage fields `parent_session_id` and `forked_at_seq`. See `api/src/transport_matters/session/models.py:41-42`.
- The foundation migration creates those columns and enforces the paired null check. See `api/migrations/versions/0001_session_store_foundation.py:36-42`.
- Claude normalization maps native `isSidechain` and `parentUuid` into normalized turn fields. See `api/src/transport_matters/index/adapters/claude.py:127-128`.
- `build_event` currently writes normalized turns under `turn.session_id` and preserves `is_sidechain`. See `api/src/transport_matters/session/ingest.py:77-95`.
- `EventReadRow` exposes `native_turn_id`, `parent_native_id`, `parent_seq`, and `is_sidechain`, but omits `raw`. See `api/src/transport_matters/session/models.py:78-85` and `api/src/transport_matters/session/dao.py:48`.
- Existing event list and stream routes return lightweight `SessionEventView` objects. See `api/src/transport_matters/api/v1/session_routes.py:136-174`.

## Key Patterns

- **Index before projection columns.** The backend spec starts from existing `event.raw`, `event.ir`, `search_text`, and `content_tsv`, then adds JSONB and expression indexes before materializing projection cache columns. See `NOTES/transcript-canvas-ui-backend.md:516-525` and `NOTES/transcript-canvas-ui-backend.md:595-669`.
- **Resource identity is session scoped.** `session_resource` and `event_resource` use composite keys over `(session_id, resource_id)`, matching the session scoped content route. See `NOTES/transcript-canvas-ui-backend.md:548-593`.
- **Backlog and live share one projector.** The live stream contract requires the same projector as backlog reads. See `NOTES/transcript-canvas-ui-backend.md:501-514`.
- **Subagents are pane targets.** The overview and frontend specs model subagents as dedicated transcript panes rather than generic resources. See `NOTES/transcript-canvas-ui.md:119-123` and `NOTES/transcript-canvas-ui-frontend.md:50-54`.

## Detailed Findings

### 1. Codex review findings 1 through 6 are incorporated

The current specs include the fixes requested by `NOTES/transcript-canvas-ui-codex-review.md:58-224`.

1. **Composite session resource key:** `session_resource` has `PRIMARY KEY (session_id, resource_id)` and `event_resource` references the composite key. See `NOTES/transcript-canvas-ui-backend.md:555-591`.
2. **`LayoutHint` defined:** The backend response includes `layoutHints`, and the spec defines a narrow advisory `LayoutHint` without geometry. See `NOTES/transcript-canvas-ui-backend.md:60-83`.
3. **Full resource content response union:** `ResourceContentResponse` includes text, image, binary, JSON, exchange redirect, and missing variants with exact fields and failure reasons. See `NOTES/transcript-canvas-ui-backend.md:380-438`.
4. **Provider exchange scoping:** `PaneContentRef` includes `sessionId` for `provider-exchange`, and the resource endpoint can return an `ExchangeRedirectResponse`. See `NOTES/transcript-canvas-ui-frontend.md:50-54` and `NOTES/transcript-canvas-ui-backend.md:423-449`.
5. **Live envelope ids:** `TimelineStreamEnvelope` has `id`, `revision`, and `emittedAt`, with stable ids for timeline, resource, subagent, and session updates. See `NOTES/transcript-canvas-ui-backend.md:496-511`.
6. **Slice order aligned:** Overview, backend, and frontend slice orders match. See `NOTES/transcript-canvas-ui.md:169-180`, `NOTES/transcript-canvas-ui-backend.md:685-696`, and `NOTES/transcript-canvas-ui-frontend.md:276-287`.

### 2. Child session reshape is sound and the writer boundary is now specified

The canonical model maps subagents to child `session` rows linked by `parent_session_id` and `forked_at_seq`. The schema already has these fields and the paired null check, so the storage shape supports the decision. See `api/migrations/versions/0001_session_store_foundation.py:36-42` and `api/src/transport_matters/session/models.py:41-42`.

The current Claude path ingests sidechains inline under the parent session. `ClaudeAdapter.normalize` maps `isSidechain` into `is_sidechain`, and `build_event` writes that flag on the event. See `api/src/transport_matters/index/adapters/claude.py:127-128` and `api/src/transport_matters/session/ingest.py:77-95`.

The first audit found that saying "ingest is the only seam" was incomplete because `SessionWriter._commit_batch` upserts only `batch.session`, then inserts every event row. See `api/src/transport_matters/session/writer.py:70-76`. The amended spec now names the writer or batch boundary: `SessionWriter` currently upserts one session per batch, so minting child sessions requires multi session batches or split batches. See `NOTES/transcript-canvas-ui-backend.md:181-186`.

### 3. Slice 1 raw access is now explicit and owner scoped

Meta projection rules rely on native record type and attachment fields. See `NOTES/transcript-canvas-ui-backend.md:454-476`. The code persists raw meta records, but sets `ir=None` for meta events. See `api/src/transport_matters/session/ingest.py:101-119`.

The existing owner scoped read omits `raw`: `_EVENT_READ_COLUMN_NAMES` drops `raw`, and `_GET_EVENTS_FOR_OWNER_SQL` joins session for owner scope but selects only read columns. See `api/src/transport_matters/session/dao.py:48` and `api/src/transport_matters/session/dao.py:143-153`. The raw bearing `get_events` query selects full event rows, but it does not enforce owner scope. See `api/src/transport_matters/session/dao.py:135-142` and `api/src/transport_matters/session/dao.py:285-292`.

The amended spec now says slice 1 adds an owner scoped read that includes `raw` for meta classification, stays over existing rows, and adds no new storage. See `NOTES/transcript-canvas-ui-backend.md:492-499`.

### 4. Virtual sidechain rendering is now gated before slice 4

The transition mode emits `virtual-sidechain` refs for not yet normalized inline sidechains and says they resolve against the parent timeline filtered by a derived root native id. The deterministic id hashes that root native id. See `NOTES/transcript-canvas-ui-backend.md:209-225`. Slice 1 emits transitional refs and performs no normalization. See `NOTES/transcript-canvas-ui-backend.md:238-246`.

The frontend `subagent-timeline` pane ref carries `sessionId`, `subagentId`, `parentSessionId`, and `parentSeq`, but no `mode`, unhashed root native id, or filter key. See `NOTES/transcript-canvas-ui-frontend.md:50-54`. Current implemented pane records are narrower and support only session picker and session transcript refs. See `www/src/session-canvas/model/paneRecords.ts:28-30`.

The amended spec now gates virtual sidechain rendering before slice 4. It requires either root native id carried on `SubagentRef` and `PaneContentRef` plus a timeline filter param, or an explicit emit only placeholder. It also warns that `subagentId` changes from `subagent-sidechain:*` to `subagent-session:*` at backfill and must not be persisted. See `NOTES/transcript-canvas-ui-backend.md:227-236`.

### 5. Final signoff

After live reread of the amended backend spec, all three conditional issues were resolved in the filed text:

1. Writer or batch boundary for child normalization: `NOTES/transcript-canvas-ui-backend.md:181-186`.
2. Virtual sidechain rendering contract before slice 4: `NOTES/transcript-canvas-ui-backend.md:227-236`.
3. Owner scoped raw bearing read for meta projection: `NOTES/transcript-canvas-ui-backend.md:492-499`.

Final bus response on topic `canvas-spec-signoff` was: `I sign off on the canvas spec as currently filed`.

## Dependencies

Critical dependencies surfaced by this audit:

- **FastAPI:** session and timeline API surfaces. See `api/pyproject.toml:37-45`.
- **Pydantic:** frozen row and response models. See `api/src/transport_matters/session/models.py:24-45` and `api/src/transport_matters/api/v1/session_routes.py:34-94`.
- **psycopg and Alembic:** Postgres session store and migrations. See `api/pyproject.toml:43-45`.
- **React, React Query, React Virtual, Framer Motion, Zustand:** frontend canvas data, rendering, motion, and state stack. See `www/package.json:30-39`.
- **Electron:** detached desktop canvas viewer. See `desktop/package.json:20-29`.

## Relevance To Helioy

This spec sits on the Helioy session history and observability path. The resolved issues protect the shared transcript canvas from hidden raw access gaps, ambiguous subagent pane routing, and session writer assumptions that could fail during backfill or live tailing.

The same patterns apply to Little Organs session tooling: make child session identity explicit, keep operator visible panes backed by owner scoped APIs, and define transitional virtual entities before UI dedupe depends on their ids.

## Open Questions

1. Should the owner scoped raw bearing read return raw for every event in the page, or only for rows that project into meta, context, diagnostic, or state items?
2. Should virtual sidechain rendering be supported before backfill, or should virtual refs be badges only until sidechain normalization lands?
3. Should child session normalization split tailer batches by child session, or should `EventBatch` grow a multi session write contract?
4. How should `subagentId` stability behave across the virtual sidechain to child session backfill boundary?

## Verification Notes

- Read live specs and code from the working tree on 2026-06-08.
- Confirmed `.fmm.db` exists and used fmm for topology, file outlines, dependency graphs, and symbol reads before direct inspection.
- Rechecked amended `NOTES/transcript-canvas-ui-backend.md` before final signoff.
- Captured amended backend spec sha256: `24250f9f633617c4a47f082b33830dd69774438298e7f781a88eec66bef13517`.
- Earlier full spec hashes before consensus edits:
  - `NOTES/transcript-canvas-ui.md`: `5666e78ce6348cc16d3ce1e502954c89d6c481887fc394644f31ac734f63491b`
  - `NOTES/transcript-canvas-ui-backend.md`: `6c59b8340f8369eb34dfed806926ab3aa468483ba6e21e295539fed11a294f73`
  - `NOTES/transcript-canvas-ui-frontend.md`: `30e0c4655c091b397ac5a9a2b6068a69da84528618f5abb5ccc1bfeb30624d06`
  - `NOTES/transcript-canvas-ui-codex-review.md`: `12124a1e6bbfd6fe4271eb6ef73dfcc52a5ca2858e789e74908d917b6ad1178c`
