---
title: TM NOTES Work-Remaining Audit — Resume & Session Model slice
type: research
tags: [transport-matters, resume, session-schema, work-remaining, notes-audit]
summary: The resume feature (startup screen, continuation, lineage, resume card, summary) is unbuilt; substrate (session-list API, timeline API, transcript-chat viewer, session-picker pane, typed run errors, client canvas persistence) exists. Schema columns session_purpose/session_visibility are absent and block S2/S4 and the summary enhancement.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Resume & Session Model — Work Remaining

Audit slice: **Resume & session model**. Four NOTES verified against committed code
(`git log`, ripgrep, source reads). NOTES checkboxes were ignored; only real repo
state counts. Repo root: `transport-matters`. Verified 2026-06-15 at `HEAD 16b95d7`.

## Per-Note Status

| Note | Status | One-line |
|------|--------|----------|
| `12-internal-user-session-schema.md` | **REMAINING** | Hard dependency. `session_purpose`/`session_visibility` columns absent. |
| `11-resume-startup-continuation.md` | **PARTIAL** | Substrate shipped (picker, transcript viewer, list/timeline APIs); resume feature unbuilt. |
| `13-resume-slices.md` | **PARTIAL** | Same feature as `11` at PR-slice granularity (S1–S6). DEDUPE. None of S1–S6 deliverables landed. |
| `13-capture-summary-future.md` | **REMAINING** | Future enhancement, parked out of the first resume slice. Nothing built. |

**Headline: the resume feature is not built.** No `/api/v2/*` route exists
(`absent: rg "api/v2|/v2/" api www -> 0 hits`), no continuation path, no startup
screen, no resume card, no MCP resume tools, no schema classification columns. What
exists is reusable *substrate* that the slices were designed to build on.

## Overlap & Dependency Map

- **`11` ⟷ `13-resume-slices` are the same feature.** `11` is the design memo;
  `13-resume-slices` is its ordered PR-sized plan (S1 startup → S2 list+card →
  S3 preview ⊥ S4 continuation → S5 linked run ⊥ S6 continuation layout). The
  consolidated remaining-work list below is organized by the S1–S6 slices and is
  the single source; do not double-count `11`.
- **`12` is a hard dependency of S2, S4, and `13-capture-summary-future`.** The
  user-visible session filter (S2), the continuation write that sets
  `sessionPurpose`/`sessionVisibility` (S4), and the hidden `internal_summary`
  session (summary note) all require the `session_purpose`/`session_visibility`
  columns that `12` proposes and that do not exist.
- **`13-capture-summary-future` depends on `12` and on the S1–S6 resume slices.**
  It is explicitly parked: both `11` ("Out Of Scope") and `13-resume-slices`
  ("Settled Decisions", "Out Of Scope For This Plan") exclude generated summaries
  from the first resume slice.

## Shipped Substrate (NOT remaining — build on these)

- Session-list API `GET /sessions` (`session_routes.py list_sessions`,
  `class SessionSummary`), filtered by `workspace_hash`/owner. Evidence:
  `session_routes.py:128 @router.get("/sessions")`.
- Transcript timeline API `GET /sessions/{id}/timeline` (+ `/timeline/stream`,
  `/events`, `/events/stream`) returning `TimelineResponse`. Evidence:
  `session_routes.py:182`.
- Rich transcript chat viewer `TranscriptChatPane` (renders `session-timeline`
  panes). Evidence: `www/src/session-canvas/viewers/registry.tsx:64 id:"transcript-chat"`.
- `SessionPickerPane` — lists sessions for the canvas `workspaceHash` via
  `useSessions` → `/api/sessions`, keyboard nav, opens a transcript pane. Evidence:
  `www/src/session-canvas/viewers/session-picker/SessionPickerPane.tsx`.
- Typed managed-run error codes `run_not_found/run_not_attachable/run_stale/run_stopped`
  (the note's PR #93 / `230503c` claim is accurate). Evidence: `run_manager.py:61-63`,
  `run_routes.py:49-51`. Substrate for S5 error-driven UI.
- Client-side canvas persistence: `PersistedCanvasState`,
  `createCanvasStorePersistOptions`, `canvasPanePersistence.ts` (PR #92 `be601cb`).
  Evidence: `www/src/session-canvas/persistence/canvasPanePersistence.ts:36`.
  **Client-only (zustand persist); no backend layout store.** Substrate for S6.
- Current `session` table columns the schema note relies on are all present:
  `owner, status, title, parent_session_id, forked_at_seq, source_descriptor,
  created_at, updated_at` (plus `forked_at_seq`/`parent_session_id` CHECK pairing).
  Evidence: `api/migrations/versions/0001_session_store_foundation.py:21-43`.
  `12`'s "Current Schema Facts" section is accurate.

## Consolidated Remaining Work

### Dependency 0 — Session classification schema (`12`) — REMAINING, blocks S2/S4/summary

- Add migration adding `session_purpose text NOT NULL DEFAULT 'user'` and
  `session_visibility text NOT NULL DEFAULT 'user_visible'` to `session`.
  `absent: rg "session_purpose|session_visibility" api -> 0 hits`; latest migration
  is `0003_event_dead_letter.py` (only 3 migrations exist).
- Enforce allowed values: 6 `session_purpose`
  (`user/continuation/internal_summary/internal_indexing/internal_eval/system_maintenance`)
  and 3 `session_visibility` (`user_visible/hidden/diagnostic`) via CHECK constraints.
  `absent: same grep -> 0 hits`.
- Surface both columns on `SessionSummary` / `SessionRow`. `absent: sessionVisibility
  in session_routes.py -> 0 hits`.
- Add optional `purpose` / `visibility` / `include_internal` query params to
  `list_sessions`, defaulting `visibility=user_visible`, `include_internal=false`;
  keep reads owner-scoped. Currently `list_sessions` accepts only `workspace_hash`
  (`session_routes.py:129`).

### S1 — Startup screen + recent working dirs + New Session — REMAINING

- Backend `GET /api/v2/workspaces` aggregating `SessionSummary` by `workspace_hash`,
  ordered by latest activity. `absent: rg "workspaces" api/src -> 0 hits`.
- Startup-screen shell with the two-column layout (left: recent working dirs;
  right: sessions for the selected dir). Today there is only a single in-canvas
  `SessionPickerPane`, not a startup screen. `absent: rg "StartupScreen" -> 0 hits`.
- `TRANSPORT_MATTERS_STARTUP_SCREEN` env disable control.
  `absent: rg "STARTUP_SCREEN" -> 0 hits`.
- `New Session` primary action on the startup screen funneling into the existing
  captured-run spawn path.

### S2 — User-visible session list + deterministic resume card — REMAINING (blocked on `12`)

- User-visible filter on the session list (depends on Dependency 0).
- Resume-card deterministic fields **`currentTurnCount`, `inheritedForkTurnCount`,
  `lastAgentMessage`, `lineageBadge`** kept current-vs-inherited separate. The
  current `SessionPickerPane`/`SessionRow` shows title/provider/cli/status/age/cwd/
  native only. `absent: rg "currentTurnCount|inheritedForkTurnCount|lineageBadge" -> 0 hits`.

### S3 — Rich transcript preview (orientation, not on working canvas) — REMAINING

- A *preview-only* surface that renders `TimelineResponse` for orientation and does
  **not** seed a pane on the working canvas. Current `spawnOrFocusTranscript` spawns
  the transcript pane **onto** the canvas — the opposite of the spec's selection-only
  preview. Evidence: `SessionPickerPane.tsx:43,59` (action), spec `11` "Rich
  Transcript Preview". Rendering substrate (`TranscriptChatPane`, timeline API) is
  shipped; the preview-mode interaction is not.
- Preview pagination via `nextFromSeq` cursor.

### S4 — Continuation creation with lineage — REMAINING (blocked on `12`)

- Backend `POST /api/v2/sessions/{priorSessionId}/continuations` minting a fresh
  user-visible session with `parentSessionId` = prior, `forkedAtSeq` = prior last
  visible event seq, `sessionPurpose="continuation"`, `sessionVisibility="user_visible"`.
  `absent: rg "continuation" route in api/src -> 0 hits` (existing `continuation`
  hits are track-manager fan-out / Codex response parsing, unrelated).
- `Resume From This Session` action wired from the resume card.
- Lineage display strings (`Continued from <date> session`, `Forked at turn N`,
  `X turns, Y inherited`), current vs inherited counts separate.

### S5 — Fresh captured run linked to the continuation — REMAINING

- Add optional `continuationId` to `CreateRunRequest` (currently only
  `cli/cwd/terminal/oscColorReplies`). Evidence: `run_routes.py:70 class
  CreateRunRequest`. `absent: rg "continuationId|continuation_id" run_routes.py -> 0 hits`.
- Mirror `continuationId` into the agent `resume-context.json` handoff.
  `absent: rg "resume-context|resume_context" -> 0 hits`.
- Drive run-pane UI from the typed run error codes (substrate already shipped).

### S6 — Continuation canvas layout fetch/save — REMAINING

- Backend `GET`/`PUT /api/v2/canvas-layouts/{canvasKey}` carrying
  `PersistedCanvasState`. `absent: rg "canvas-layout|canvasKey" api/src -> 0 hits`.
  Today persistence is client-side only.
- Composite `(workspaceHash, canvasId)` binding key (OPEN-1, decided but unbuilt).
- Persist the full `CanvasPaneRef` union incl. the `session-picker` pane (the union
  already includes `PickerPaneRef`; the backend store carrying it does not exist).

### Agent context injection (MCP) — REMAINING (mostly out-of-scope for first slice)

- Candidate MCP tools `tm.get_resume_card`, `tm.get_lineage`, `tm.search_transcript`,
  `tm.get_turns`, `tm.get_artifacts`, `tm.get_session_summary`.
  `absent: rg "get_resume_card|get_lineage|search_transcript|get_session_summary" -> 0 hits`.
  `13-resume-slices` marks the full MCP/skill/hook contract out-of-scope beyond the
  S5 `resume-context.json` handoff note.

### `13-capture-summary-future` — REMAINING (future enhancement; WONT-DO for first slice)

Explicitly parked out of the first resume slice by both `11` and `13-resume-slices`.
Nothing built: `absent: rg "resume_summary|internal_summary|artifact_kind|summary_version|generated_by_session" -> 0 hits`.
If/when enabled (all depend on Dependency 0):

- `internal_summary` hidden session purpose + visibility (depends on `12`).
- `resume_summary` derived-artifact store: `source_session_id`, `source_from_seq`,
  `source_to_seq`, `generated_by_session_id`, `summary_version/_prompt_version`,
  `model`, `provider`, `status` (`missing/generating/ready/stale/failed`), `text`.
- Background trigger on fork/resume; non-blocking; staleness when source events
  extend beyond `source_to_seq`.
- Summary agent reads via the B6 transcript API; writes only the artifact + its own
  hidden transcript.

## Confidence

High. Every "absent" anchor is a ripgrep over committed `api`/`www` source with
`node_modules` excluded; every "shipped" anchor is a file+symbol read. The only
interpretive call is classifying `11`/`13-resume-slices` as PARTIAL rather than
REMAINING: justified by the shipped session-list/timeline APIs, transcript-chat
viewer, and `SessionPickerPane`, none of which deliver a resume-specific surface.
