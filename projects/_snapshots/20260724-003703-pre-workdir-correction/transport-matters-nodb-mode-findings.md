---
title: Transport Matters no-DB startup — blast surface + store-picker onboarding
type: research
tags: [transport-matters, no-db, degraded-mode, session-store, onboarding, pgembed]
summary: TM deliberately refuses to launch with no Postgres via two guards; everything else already degrades. A capture-to-disk degraded mode + a local/docker/hosted store picker is reachable by relaxing two guards plus one net-new DB-status bootstrap signal. Frontend gate is exactly 3 mounted consumers, all under /canvas.
status: research-not-committed
source: warroom (3-pane blast-surface map + 2-pane MoE confirmation)
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# No-DB startup for Transport Matters

Investigated 2026-06-20 via two warrooms of `codebase-analyst` panes: a 3-pane
blast-surface map (lifecycle / API / frontend) and a 2-pane MoE (Claude + Codex)
confirmation of the `session_routes` frontend consumers. Raw slice artifacts:
`transport-matters-nodb-{lifecycle,api-surface,frontend,sessroutes-claude,sessroutes-codex}.md`.

Framing (from Stuart): a DB is required; embedded/no-DB is **not** a replacement
for docker/hosted but a zero-config no-brainer for non-technical users. So the
target is a graceful no-DB startup that guides the user into a store, while the
live capture product keeps working in the meantime.

## Headline

The app **deliberately refuses to launch with no Postgres today.** Only two
explicit guards enforce that. Everything downstream already tolerates a missing
store. So a degraded "capture-to-disk, watch the live run" mode plus a store
picker is much closer than it looks: relax two guards and add one net-new
DB-status signal to the UI.

## The two guards (entire "won't start" surface)

1. `cli/launch_runtime.py:preflight_session_store_or_exit` — front of every CLI
   launch path (`cli/start_cmd.py:run_start`, `cli/codex_cmd.py:run_codex`,
   `cli/desktop_cmd.py:serve_desktop_backend`). Calls
   `session_store_preflight.py:check_session_store`, then `exit(2)` BEFORE the
   proxy, run lock, manifest, agent, or web app start. This is why
   `transport-matters claude` cannot even write tier-1 with no DB from process
   start.
2. `run_manager.py:RunManager._ensure_session_store_available` — raises
   `session_store_unavailable` before preparing a captured canvas pane.
   Independently blocks `POST /v1/runs` (desktop/canvas spawn).

## Everything else already degrades cleanly (no new code)

- `addon_runtime.py:load_capture_runtime` / `_start_session_capture` — storage +
  binding built first; capture failure logs and returns no writer/tailer. Tier-1
  disk wire writes proceed via `storage/disk.py:DiskStorageBackend.persist_exchange`
  and `exchange_recorder.py:persist_http_exchange`.
- `main.py:lifespan` / `_start_session_store` — serves with
  `app.state.session_pool = None`; session routes 503.
- `session/writer.py:SessionWriter._ensure_open` / `_commit_batch` — exception
  swallowed; proxy survives.
- `session/listen.py:SessionEventListener` — reconnect loop logs and continues.

Tier-1 (the durable per-run source of truth) genuinely works DB-less; Postgres
transcript becomes best-effort. Backfill from tier-1 into the store already
exists (`SessionWriter` backfill path), so a session captured during the no-DB
window can be reconciled once a store is chosen.

## API blast surface: 8 HARD, 29 SOFT, 0 WRITE

HARD (503 `session_store_unavailable` with no pool) is one coherent cluster:
`session_routes` — `/v1/sessions`, `/v1/sessions/{id}`, `/events`, `/timeline`,
`/resources/{id}`, `/events/stream`, `/timeline/stream` — plus `POST /v1/runs`
(RunManager guard).

SOFT (work DB-less) includes health, overrides, breakpoint, meta, capabilities,
local-file, `WS /api/terminal`, runtime-templates, run list/get/terminate,
`WS /v1/runs/{id}/terminal`, and crucially **the per-run exchange reads**
(`/v1/runs/{id}/exchanges|{id}|turn-content|pipeline_tokens|meta|stream`).
Verified disk-backed: `api/v1/exchanges.py` resolves every read through
`api/v1/run_storage.py:resolve_run_storage_or_404` → `DiskStorageBackend`
(module docstring: "Run scoped disk storage resolution"); no `session_pool` in
that path.

## Frontend gate: 3 mounted consumers, all under `/canvas` (2-pane MoE confirmed)

`session_routes` are consumed through `www/src/session-canvas/api/*`, NOT
`www/src/api.ts` (which carries only the disk-backed per-run reads). Both MoE
panes independently converged on three mounted surfaces:

1. **Session picker / launch lookup** — `session-canvas/hooks/useSessions.ts:useSessions`
   → `session-canvas/api/sessionClient.ts:listSessions` → `GET /v1/sessions`. UI:
   `session-canvas/viewers/session-picker/SessionPickerPane`; also
   `session-canvas/hooks/useLaunchSession.ts:useLaunchSession`. Mounted by default
   on `/canvas` (`session-canvas/canvasStore.ts:createInitialCanvasModel` seeds it).
2. **Transcript chat pane** — `session-canvas/viewers/transcript-chat/TranscriptChatPane`
   → `useSessionEventStream` (SSE `/v1/sessions/{id}/events/stream`) +
   `session-canvas/hooks/useSessionEvents.ts:useSessionEvents`
   (`GET /v1/sessions/{id}/events`).
3. **Session resource viewers** — `session-canvas/hooks/useResourceContent.ts:useResourceContent`
   → `session-canvas/api/resourceContent.ts:loadResourceContent`
   (`GET /v1/sessions/{id}/resources/{id}`). UI:
   `session-canvas/viewers/resource/ResourcePane`. Reachable; current visible
   creation paths build local-file/URL refs, so db-resource refs may be rarely
   exercised today.

Not consumed by www (no gate needed): `GET /timeline`, `/timeline/stream`, and
bare `GET /v1/sessions/{id}`. The **default `/` legacy route consumes no
session_routes** (disk-backed per-run reads only).

→ One "DB connection required" gate at the `/canvas` route (or in `RootShell`
ahead of `session-canvas/route.ts:selectRootRoute`'s canvas fork) covers every
session_routes UI surface.

## The one genuinely net-new piece: a DB-status bootstrap signal

www learns DB status nowhere today: `Meta` / `CapabilitiesResponse` carry no db
field, and `/health` is polled only by the desktop wrapper
(`desktop/src/backendHealth.ts`), not www. Cleanest: add a `db_status` field to
`/api/meta` (SOFT, already fetched by `fetchMeta`), consumed once in
`www/src/rootShell.tsx:RootShell`. There is no reusable empty-state component;
the gate/picker is net-new UI.

## Onboarding store picker

Seam = `RootShell` ahead of the route fork (single mount point before any
DB-backed fetch; no client router, full-page nav). On `db_status = none`, render
the picker instead of the route fork. Options:

- **Local Postgres** — embedded `pgembed` (the zero-config no-brainer; see
  `transport-matters-litepg-{landscape,codebase}.md`). PostgreSQL 17, prebuilt
  wheels, no docker, no sudo.
- **Docker Postgres** — existing compose, with a "start Docker, we auto-detect"
  checklist.
- **Hosted service** — paste a DSN (Supabase / Neon / external).

Couples with NOW.md Next-up #1 (User onboarding): the picker shares the same
ENV/settings → edit-overlays surface; build the overlay model once.

## Minimal change set (if pursued)

1. Relax `preflight_session_store_or_exit` from `exit(2)` to warn-and-continue in
   a degraded mode (keep hard-exit as the default / `--require-db`).
2. Relax `RunManager._ensure_session_store_available` to allow tier-1-only canvas
   spawn when degraded.
3. Add `db_status` to `/api/meta`.
4. `RootShell` gate + store picker (local/docker/hosted) ahead of the canvas fork.
5. Gate the 3 `/canvas` session_routes consumers behind `db_status`.

Status: research, not yet a committed decision by Stuart.
