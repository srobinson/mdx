---
title: "Transport Matters B6 — Curated Product API Proposal (v2, review-incorporated)"
type: proposal
status: reviewed — architecture validated, 0 blockers
author: orchestrator (claude-opus)
reviewers: backend-engineer + codebase-analyst x2 (Claude+Codex MoE), warroom b6-api-review
created: 2026-06-15
updated: 2026-06-15
tags: [transport-matters, b6, api, design-proposal]
---

# B6 Curated Product API — Proposal v2

Reviewed by a 3-agent warroom (1 design, 2 feasibility MoE). All three positively
justified the four load-bearing decisions; **zero blockers**. v2 folds in every
finding. Review artifacts: `~/.mdx/projects/tm-b6-review-design.md`,
`...-feasibility-claude.md`, `...-feasibility-codex.md`.

## Problem

The API is mechanism-shaped: `/api/runs` returns `RunViewModel` leaking
`proxyPort`/`webPort`/`storageDir`/`nativeSessionId`/`scrollback*`
(`run_routes.py:80`); `/api/sessions` is snake_case `SessionSummary` leaking
`nativeSessionId`/`sourceDescriptor`/`homeDir`, offset pagination
(`session_routes.py:51`). B6 puts a curated product contract behind the boundary.
R1 typed errors shipped (#93); R2 gate met (UI reads transcript from Postgres+SSE).

## Decision 1 — One converged namespace `/v1`, replace in place ✓ validated

Single curated `/v1`, no parallel `/api/v2`. Backend + www + desktop ship as one
install, runs are process-resident (die on deploy restart), so there is no
independently-deployed client holding a stale contract and no in-flight migration
window. Parallel versioning would buy perpetual drift for zero consumers.

**Migration unit = one complete route family per PR, path move separable from shape
change** (review m5: don't bundle path+casing+fields opaquely; keep separable
commits for bisection):

- **Runs** move as one PR: `POST`/`GET`/`GET {id}`/stop + `WS /v1/runs/{id}/terminal`
  (review m2: the terminal WS MUST move to `/v1` too, or it is the "never both live"
  violation; dropping `webPort`/`proxyPort` is only safe because the WS is API-origin
  proxied). Run blast radius is compact and centralized (`api.ts`, `capturedRunStore.ts`,
  `terminalSocket.ts`).
- **Sessions move as a family, not piecemeal** (review: the substantive finding). The
  session prefix serves list + single-get + events + events/stream + timeline +
  timeline/stream + resources, and www consumers (`TranscriptChatPane`, `ResourcePane`,
  `useSessionEventStream` gap-backfill, `SessionPickerPane`, `useLaunchSession`) span
  the whole family. Either migrate the entire family in one PR, or keep a temporary
  `/api/sessions` alias until every family consumer has moved. A list-only cut breaks
  the transcript and resource panes. **Alias removal guard:** if the temporary alias is
  used, it MUST be deleted in the same PR that completes the session-family migration,
  with a test asserting `/api/sessions` returns 404 — otherwise the "never both live"
  invariant re-opens as silent dual-surface drift.

## Decision 2 — canvas-layout is NOT a B6 noun ✓ validated

Captured-agent domain (B6: workspace, session, continuation, transcript-event, run,
resource) vs desktop view-state (canvas-layout). No agent-domain consumer of canvas
layout exists in `api/src` (`absent: canvas-layout|PersistedCanvasState -> 0`); it is
www-local zustand state. It gets a desktop-context endpoint when resume S6 needs one.

Consequence to handle (review m6): the desktop layout store persists `CanvasPaneRef`s
that reference capture-domain `sessionId`/`workspaceHash`. **No FK across the seam** —
the desktop store treats them as soft references and tolerates dangling (deleted
session → placeholder pane). Key the layout on the curated `workspaceId`, not
`workspaceHash`, so both contexts share one identity vocabulary.

## Decision 3 — Curated shapes

Thin projection layer (Pydantic models + mappers); internal `RunManager`/`SessionWriter`/
DAO stay mechanism-shaped. camelCase bodies; snake_case machine error codes (intentional,
called out).

- `Workspace { workspaceId, label, lastActivityAt, sessionCount }`
- `Session { sessionId, workspaceId, title, status, provider, cli, createdAt, lastActivityAt,
  purpose, visibility, lineage:{ parentSessionId, forkedAtSeq, forkedAtTurn }, turnCount,
  inheritedTurnCount, lastMessagePreview }`
  — drop `nativeSessionId`, `minted`, `sourceDescriptor`, `homeDir`; collapse
  `workspace_slug`+`workspace_hash` → `workspaceId`.
  - **`lastMessagePreview` added** (review M1): the resume card (resume S2) needs the last
    agent message; without it on the list shape, painting a card list is an N+1. It rides
    the same read path as the turn counts.
- `TranscriptEvent { seq, turnIndex, kind, role, ts, body, resourceRefs }`
  — drop `nativeTurnId`, `parentNativeId`, `sourcePath`, `sourceLine`, `searchText`, `createdAt`.
  - **`turnIndex` added** (review M2): `Session.turnCount` and `lineage.forkedAtTurn`
    ("Forked at turn N", resume S4) are first-class, but a bare event stream with no turn
    signal cannot reconstruct turn boundaries — and Codex carries incremental request
    payloads on later turns, so a naive user-message split is wrong. Expose a curated,
    non-native `turnIndex` (canonical seq→turn mapping owned by the projector).
  - **`body` is a `kind`-discriminated union** (review m4), not an opaque blob: `user` /
    `tool_use` / `tool_result` / wire-only-injected differ in shape, and wire-only injected
    content is the product's whole point. Document the per-`kind` body schema.
- `Run { runId, workspaceId, sessionId, cli, state, createdAt }`
  — drop `proxyPort`, `webPort`, `storageDir`, `scrollback*`, `viewerlessSince`, `nativeSessionId`.
- Naming convergence (review m3): applied — `lastActivityAt` is the single activity-timestamp
  name on both `Workspace` and `Session` (`createdAt` stays as creation time). `status`(session)
  vs `state`(run) stays, value sets differ; called out.
- `turnCount`/`inheritedTurnCount` computed at read (verified low-risk): one aggregate per
  page (no N+1), PK `(session_id, seq)` bounds the scan; `inheritedTurnCount` = parent
  visible turns where `seq <= forkedAtSeq`. No denormalized columns; add a partial
  `(session_id, kind, is_sidechain, seq)` index only if measured.

### `homeDir` drop — verified by review

Confirmed by all three reviewers: `session.home_dir` is write-mostly to Postgres
(`ingest.py`, `backfill.py`, COALESCE upsert `dao_statements.py:93`); the only consumer,
www, **types it and never reads it** behaviorally (`sessionClient.ts` type + test default,
zero behavioral reads); no relaunch/resume/launch path reads the durable row (launch reads
launch-scoped home inputs). It is also semantically a source/provenance value
(`settings.agent_home_dir`), never the transcript-bearing home — under the ephemeral-home
spec the real home is the per-run `descriptor_home` that is `rmtree`'d at teardown. Keep in
storage for forensics; if provenance is ever a product need, surface structured
`template_provenance`, not a raw path.

## Decision 4 — Continuation: TM-internal, launch-param, needs real plumbing

**Product constraint (owner):** `transport-matters desktop` accepts no passthrough CLI args
(no `--resume`/`-c`); all continuation is TM-internal. Native CLI resume is **excluded, not
deferred** — and is anyway impossible under ephemeral homes (the native session JSONL is
destroyed at teardown). So continuation is unambiguously a TM-level concept and TM owns its
correctness, including idempotency.

**Shape:** `continueFromSessionId` optional on `POST /v1/runs`; no standalone endpoint (the
resume UX never produces a pre-run continuation).

**This needs new plumbing (NOT "without new infra"** — review correction). The schema fields
exist (`session.parent_session_id`/`forked_at_seq`, `SessionBinding`, `build_session` persist,
COALESCE upsert), but they are populated today only by the subagent fan-out, and the durable
session is tailer-minted async, not written at the spawn seam. Required new work:
- Add `continueFromSessionId` to `CreateRunRequest` → `SpawnRun` → run context, and through the
  **`Settings`/launch-env hop into `_launch_run_context`** (review: `Settings` carries only
  run/cwd/cli/owned-ids/home today, so the lineage fields need an explicit new carry there).
- Overlay `parentSessionId`/`forkedAtSeq` onto the binding where `minted`/`source_descriptor`
  are already overlaid: `_register_owned_cursor` model_copy (`addon_runtime.py:96-101`) and
  `register_session_cursor` model_copy (`tailer.py:463-468`). Note `_launch_run_context`
  (`addon_runtime.py:67`) builds `RunContext` and carries neither today, so its new lineage fields
  come from `Settings` (above), not from a minted/source_descriptor carry. (Or a route-layer
  pre-seed upsert; the COALESCE at `dao_statements.py:93` lets a non-null parent survive the tailer NULL.)
- New "prior last visible seq" DAO helper to compute the fork point (none exists; only the
  children aggregate `max(seq)` at `dao_statements.py:203`).
- Owner-scoped validation of `priorSessionId`.
- **Idempotency via an explicit key** (review M4 + correction): a non-idempotent POST minting a
  child session means a retry or double-clicked "Resume From This Session" yields duplicate
  lineage. Use an explicit idempotency key on `POST /v1/runs`. Do NOT dedup on
  `(parentSessionId, forkedAtSeq)` — that natural key would forbid *intentional* multiple forks
  from the same parent at the same point, which is a legitimate user action.
- Prior-context priming sourced from the Postgres transcript (B6 transcript API), per resume §3.

**Copy note** (review): a TM-seeded continuation is a fork with re-injected context, not a
restored agent; lineage fields model it correctly, UI copy must not promise true resume.

## Decision 5 — Error envelope, verbs, pagination

- `ErrorEnvelope { code, message, details? }`. Code set: `workspace_not_found`,
  `session_not_found`, `session_store_unavailable`, `run_not_found`, `run_stale`,
  `run_stopped`, `run_not_attachable`, **`invalid_request`**, **`invalid_cursor`**
  (review M3: cursor paging + query params guarantee these paths). **Ownership outcome ruled:**
  a foreign/non-owner id returns `*_not_found` (no existence leak), no separate `forbidden`.
- **Stop verb** (review m1): use `POST /v1/runs/{id}/stop` returning the curated `Run`, not
  `DELETE`. `run_stopped` proves a stopped run stays addressable, so DELETE mislabels a
  lifecycle transition and is non-idempotent; `POST .../stop` matches behavior.
- **List envelope** (review m7): one shape `{ items, nextCursor }` reused on every list; one
  page-size param (`limit`, default + max defined); the cursor encodes and locks the active
  filter set so changing `purpose`/`visibility`/`workspaceId` mid-page cannot corrupt paging.

## Route set (end state)

```
GET    /v1/workspaces                          GET /v1/workspaces/{id}
GET    /v1/sessions  (cursor; workspaceId, purpose, visibility, includeInternal)
GET    /v1/sessions/{id}
GET    /v1/sessions/{id}/events  /events/stream  /timeline  /timeline/stream  /timeline/search
GET    /v1/sessions/{id}/resources/{rid}
GET    /v1/runs   POST /v1/runs   GET /v1/runs/{id}   POST /v1/runs/{id}/stop
WS     /v1/runs/{id}/terminal
```

## Build order (B6 is the keystone)

1. **§2 session schema** — `purpose`/`visibility` columns + defaults. Unblocks the curated
   `Session` filter and continuation's `purpose=continuation`.
2. **B6 runs family** — `/v1` router, curated `Run`, `POST /stop`, `WS /v1/.../terminal`, error
   envelope, list envelope + cursor. Migrate www run surfaces; delete `/api/runs` same PR.
3. **B6 sessions family** — curated `Session` (+`lastMessagePreview`, turn counts) + single-get +
   workspaces + events/streams/timeline/`timeline/search`/resources + curated `TranscriptEvent`
   (+`turnIndex`, discriminated `body`). Migrate the whole www session family in one PR or behind
   a temporary alias; delete `/api/sessions` when the family is fully moved.
4. **Continuation** — `continueFromSessionId` + lineage carry + fork-seq helper + idempotency +
   context priming. **Depends on step 3**: the Postgres context-priming reads the sessions-family
   transcript API, so continuation cannot precede the sessions migration. Unblocks resume §3.
5. **Canvas-layout store** (desktop context, soft refs, `workspaceId`-keyed) when resume S6 needs it.

## Review outcome

0 blockers. Architecture (in-place `/v1`, `homeDir` drop, TM-internal continuation, canvas-layout
cut, cursor paging) validated by all three agents. Open work concentrated in: (a) session-family
migration sequencing, (b) continuation plumbing + idempotency, (c) shape additions that keep B6
from under-serving resume (`lastMessagePreview`, `turnIndex`, discriminated `body`). All folded
above.
