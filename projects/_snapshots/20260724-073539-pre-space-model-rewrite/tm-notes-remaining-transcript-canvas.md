---
title: TM NOTES Work-Remaining Audit — Transcript Canvas UI slice
type: research
tags: [transport-matters, notes-audit, transcript-canvas, work-remaining]
summary: Backend timeline projection + viewers shipped; the frontend reader never consumes /timeline, the Evidence Drawer is unbuilt, and file-capture + projection-persistence remain deferred.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Work-Remaining Audit: Transcript Canvas UI

Read-only audit. NOTES/ is gitignored scratch, so the notes' own status lines are
NOT evidence. Every classification below is verified against committed code
(`git log`, grep of real symbols/routes/migrations, source reads). Repo root:
`transport-matters`. Audited 2026-06-15 @ HEAD `16b95d7`.

Cross-cutting verdict: the **backend timeline projection is real and tested**, but
the **product UI does not consume it** (the transcript reader still reads the
legacy event/IR stream), and two whole layers (Evidence Drawer, file capture)
plus projection persistence are unbuilt. The component inventory the notes call
"slices 1-7 shipped" is largely accurate at the *part* level; the *integration*
that makes it a product is the main remaining work.

---

## 1. NOTES/transcript-canvas-ui.md (product overview)

**Status: PARTIAL** (core endpoints + viewers DONE; one product layer unconsumed,
two layers + persistence REMAINING)

Shipped/DONE (hard evidence):
- Timeline endpoint `GET /api/sessions/{id}/timeline` over `project_timeline()` —
  `session_routes.py:182`, `session/timeline.py:project_timeline`, commit `17b166c` (#50).
- Live stream `GET /api/sessions/{id}/timeline/stream` — `session_routes.py:274`,
  `session/timeline_stream.py`, commit `71f444f` (#51).
- Resource content endpoint `GET /api/sessions/{id}/resources/{rid}` —
  `session_routes.py:217`, `session/resource_content.py`, commit `e6ad3b0` (#57).
- Real resource viewers — `www/src/session-canvas/viewers/resource/` (Markdown,
  Image, Text, Json, Binary, ProviderExchange), commit `53824e8` (#58).
- `paneRecords.ts` ref expansion, `exchange_correlation.py`,
  `resource_content_rendering.py`, `resource_ids.py` all present.

REMAINING:
- **Frontend never consumes the timeline projection** (cross-cutting; see notes 2 & 3).
  `absent: grep -rn '/timeline' www/src -> 0 product calls` (only a comment in
  `ProviderExchangeResourceViewer.tsx:38`). The transcript reader still maps the
  legacy event/IR stream. Confidence: high.
- **Slice 8 — projection persistence**: `session_resource` / `event_resource`
  tables and materialized projection columns are absent (deferred by design).
  `absent: grep 'session_resource (' api/migrations -> 0`;
  `absent: grep 'event_resource (' api/migrations -> 0`. Only migrations 0001/0002/0003 exist.
- **File capture — "persist everything the agent touches"** (Resolved Decision 6 +
  both Open Decisions): the `file-captured` resource scheme is reserved as a *parser
  branch only* (`resource_ids.py:71 if scheme == "file-captured"`) and is **never
  emitted** by any ingest path. `absent: find api/src -name '*.py' ! -name 'test_*'
  | xargs grep -l file-captured -> only resource_ids.py`. No file-capture link table,
  no drift-detection (live re-hash vs captured hash) code. Capture mechanism +
  drift-check timing are genuinely open.
- **Full-fidelity image serving** (Resolved Decision 4 "known mismatch"): the read
  path still hard-rejects images >1 MB. `resource_content_rendering.py:23
  IMAGE_BASE64_LIMIT = 1024*1024`, `:229/:244 _too_large_response reason="too-large"`.
  The planned raw-artifact-bytes endpoint is absent:
  `absent: grep 'artifact_bytes|artifacts/{hash}|raw_artifact_bytes' api/src -> 0`.

Evidence summary: all seven slice routes/symbols verified present in committed code,
but the product UI does not call `/timeline`, and file capture + full-fidelity media
+ projection persistence are unbuilt.

---

## 2. NOTES/transcript-canvas-ui-backend.md (backend spec)

**Status: PARTIAL** (mostly DONE; persistence + search + one cleanup REMAINING)

Shipped/DONE:
- Timeline endpoint, projector, the `TimelineItem` union and `LayoutHint`/`SourceRef`/
  `ResourceSummary`/`SubagentSummary` models — `session/timeline.py`,
  `session/timeline_models.py`.
- Resource content endpoint + typed response union + missing-reason taxonomy —
  `session/resource_content.py`, `session/resource_content_models.py`.
- Meta projection (owner-scoped raw-bearing read for meta classification) and
  exchange correlation — `session/exchange_correlation.py`.
- **Subagent projection as child sessions** — DONE, commit `16f96c7` (#53). Ingest
  writes `parent_session_id` + `forked_at_seq` (`session/ingest.py:77-78`); the
  projector emits `SubagentItem`/`SubagentSummary`/`SubagentRef` via
  `_append_child_subagents` (`session/timeline.py:208-233`); discovery infra in
  `index/subagents.py` (`SubagentSpawnLink`, `ChildTranscript`,
  `record_subagent_spawn_links`). The `virtual-sidechain` hash is removed
  (`absent: grep 'virtual.sidechain' api/src -> 0`).
- **Index-first strategy** — DONE: `migrations/0002_event_tier1_indexes.py:19`
  creates `event_raw_gin` + the `raw->>'type'`/`subtype` expression index.

REMAINING:
- **Resource tables** (`session_resource`, `event_resource`) and **materialized
  projection columns** (`projection_kind`, `display_title`, `resource_count`,
  `projection_version`): absent. `absent: grep 'session_resource (|event_resource (|
  projection_kind' api/migrations -> 0`. (Deferred slice 8.)
- **Later contract `GET /timeline/search`** (`TimelineSearchResponse`): absent.
  `absent: grep 'timeline/search' api/src (non-test) -> 0`.
- **Legacy `is_sidechain` path NOT deleted** — the Ingest section (step 4) states
  "the legacy inline `is_sidechain` path ... [is] deleted," but it is still live:
  `models.py:79,128 is_sidechain: bool`, `dao_statements.py:37,122,139,196
  (AND e.is_sidechain = false)`, `ingest.py:105,128`, `adapters/{codex,claude,base}.py`.
  Small residual cleanup; field is now defaulted-False/filtered, so low impact.
  Confidence: high that it persists; medium on whether removal is still intended.
- **Deferred subagent edges** (explicitly listed, unbuilt): depth>1 nested
  subagents, the Codex authenticated-websocket wire-side spawn surface, and
  zero-turn/orphan recordings.

Evidence summary: timeline/resource/stream/subagent/meta/correlation backend all
present and tested; only the projection-persistence tier, the search endpoint, and
the `is_sidechain` deletion remain.

---

## 3. NOTES/transcript-canvas-ui-frontend.md (frontend spec)

**Status: PARTIAL** (viewers + pane refs DONE; reader integration + Evidence Drawer
REMAINING)

Shipped/DONE:
- `PaneContentRef` variants — `paneRecords.ts:64-78` (session-timeline,
  subagent-timeline, resource×3, provider-exchange) + `LegacyPaneContentRef`
  session alias (`:159`).
- Viewer registry + all six resource viewers —
  `viewers/resource/{Markdown,Image,Text,Json,Binary,ProviderExchange}ResourceViewer.tsx`,
  `ResourcePane.tsx`, `useResourceContent.ts`.
- Provenance labels incl. the note's slice-8 fix — `provenance.tsx:17
  "raw-provider-debug": "Raw provider bytes (debug)"` (the `raw-bytes` -> 
  `raw-provider-debug` fix HAS landed despite slice 8 being "deferred";
  `absent: grep 'raw-bytes' www/src -> 0`). This note line is now stale/DONE.
- Transcript reader pane exists — `viewers/transcript-chat/TranscriptChatPane.tsx`,
  `TranscriptMessage.tsx`.

REMAINING:
- **Reader does not consume the backend `TimelineItem` union.** `TranscriptChatPane.tsx`
  imports `useSessionEvents` + `useSessionEventStream` + `mapSessionEventToChatItems`
  (`mapIrToChat`) — the legacy event/IR path — not a timeline hook
  (`TranscriptChatPane.tsx:2-7,15`). It renders no `state`/`context`/`diagnostic`/
  `subagent` item kinds: `absent: grep '"state"|"context"|"diagnostic"|"subagent"'
  www/src/session-canvas/viewers/transcript-chat -> 0`. Consequence: the "Timeline
  Rendering" contract (5 item kinds, state chips, context/diagnostic collapse,
  resourceRef-driven auto-open, in-line subagent markers) is **not realized** through
  the projector. Confidence: high.
- **Evidence Drawer — unbuilt.** No drawer component anywhere:
  `absent: grep -rli 'drawer' www/src -> 0`; no evidence-drawer commit. The
  Summary / Native raw JSON / IR / source path+line / Resources / Wire-evidence tabbed
  drawer (overview layer 5 + frontend §Evidence Drawer) does not exist. Confidence: high.
- **Search & Navigation surface** (span message text + resource titles/paths + tool
  previews): depends on the absent backend `/timeline/search`; unbuilt.
- **In-transcript subagent linkage/markers** (frontend AC 10): the
  `subagent-timeline` pane ref exists, but opening it from the reader depends on the
  reader consuming projector subagentRefs (see first bullet). Confidence: medium.

Evidence summary: the pane-ref model, all six viewers, and provenance labels are
shipped, but the transcript reader still runs on the legacy event/IR stream and the
Evidence Drawer is not built — so the frontend's signature timeline-reading
experience is not yet wired to the backend projection.

---

## Bottom line for the orchestrator

| Note | Status | Biggest remaining item |
|---|---|---|
| transcript-canvas-ui.md | PARTIAL | frontend doesn't consume `/timeline`; file capture + slice-8 persistence unbuilt |
| transcript-canvas-ui-backend.md | PARTIAL | projection-persistence tables, `/timeline/search`, `is_sidechain` cleanup |
| transcript-canvas-ui-frontend.md | PARTIAL | reader on legacy event/IR path; Evidence Drawer unbuilt |

Tally: 3 notes — 3 PARTIAL (0 fully DONE, 0 fully REMAINING). The deferred work
(slice 8 persistence, file capture, full-fidelity media, search) is intentional per
the notes; the **unflagged** gaps are the frontend-to-timeline integration and the
missing Evidence Drawer.
