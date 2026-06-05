---
title: "B6 Curated API Proposal — Code-Grounded Feasibility Review"
type: review
tags: [transport-matters, b6, api, feasibility, code-review]
summary: Proposal is sound; 4 of 5 risky claims verified against code. One substantive issue — continuation is NOT free at the existing spawn seam ("no new infra" overclaims).
status: active
source: codebase-analyst
reviewer: transport-matters:helioy-tools:codebase-analyst:1:3.2
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# B6 Curated API — Feasibility Review

Verified against `HEAD 16b95d7`. Every verdict cites `file:line`/symbol or `absent: <grep> -> 0`.
Default skeptical. Per discipline, the substantive issue is **Claim 2**.

## Verdict table

| # | Claim | Verdict |
|---|-------|---------|
| 1 | Per-noun replace-and-delete is safe | **SUPPORTED** (with scoping caveat) |
| 2 | Continuation mints child session at existing spawn seam, no new infra | **ISSUE — overclaims** |
| 3 | `homeDir` droppable (no reader) | **CONFIRMED** |
| 4 | `turnCount`/`inheritedTurnCount` compute-at-read, no latency problem | **SUPPORTED** (with caveat) |
| 5 | canvas-layout correctly cut from B6 | **CONFIRMED** |

---

## Claim 1 — Blast radius of per-noun `/api/<noun>` deletion → SUPPORTED

**No generated client, no cross-noun runtime coupling in www.** Each noun can be cut in one PR.

Call-site map (non-test):
- **Run noun:** `www/src/api.ts:399` (POST `/api/runs`), `:414` (DELETE `/api/runs/{id}`), `:468` (GET `/api/runs`); `www/src/session-canvas/viewers/terminal/terminalSocket.ts:74` (WS `/api/runs/{id}/terminal`); consumed by `CapturedRunPane.tsx`.
- **Session noun:** `www/src/session-canvas/api/sessionClient.ts:52` (GET `/api/sessions`), `sessionEvents.ts:55,66` (`/events` + `/events/stream` SSE), `resourceContent.ts:132` (`/resources/{rid}`); SSE consumer `stream/useSessionEventStream.ts`; UI `SessionPickerPane.tsx`, `TranscriptChatPane.tsx`.

Why it is safe per noun:
- Clients are hand-written over `apiUrl()` + literal paths (`www/src/api.ts:29`); `absent: no codegen/openapi client in www`.
- **No www code joins run→session via `nativeSessionId`.** The session picker reads `session.native_session_id` for *display only* (`SessionPickerPane.tsx:92-93`); the run's `nativeSessionId` (`api.ts:436`) is a separate field never cross-referenced. So changing `Run` shape (drop `nativeSessionId`, add `sessionId`) is additive, not a coupling that forces a staged cut.

Caveats (scoping, not refutation):
- "noun" ≠ "single call site" for the **session** noun: it spans 3 client modules + 1 SSE hook + 2 UI consumers + a mirror type (`model/paneRecords.ts:171` re-declares `native_session_id`) + ~4 test files (`sessionClient.test.ts`, `sessionEvents.test.ts`, `useSessionEventStream.test.tsx`, `app.test.tsx`), and it carries a snake_case→camelCase field migration (today `SessionSummary` is snake_case, `session_routes.py:51`). The Run noun is already camelCase, so its cut is lighter.
- The events SSE stream and the resource sub-route live *under* the session noun, so they must move together with the list — they are intra-noun, so still one PR.

Bottom line: one-PR-per-noun replace-and-delete holds; the session-noun PR is larger than the wording implies.

---

## Claim 2 — Continuation at the existing spawn seam "without new infra" → ISSUE (overclaims)

Continuation is buildable and the architecture (TM-seeded, drop `homeDir`) is right, but the
proposal's framing that the **existing** spawn seam can "mint a child session ... setting
`parentSessionId`/`forkedAtSeq` ... without new infra" understates required plumbing.

What the spawn seam actually does today:
- `CreateRunRequest` has only `cli/cwd/terminal/oscColorReplies` — `absent: no session/continuation field` (`run_routes.py:70-77`).
- `_spawn_request` → `SpawnRun` carries no lineage (`run_routes.py:233-244`; `SpawnRun` fields `run_manager.py:109-127`); nor does `CapturedRunRequest` (`captured_run_models.py:49-63`).
- **The spawn path does NOT write the durable Postgres session.** `RunManager.spawn` only probes liveness (`run_manager.py:393 check_session_store`); it holds no session DAO. The Postgres row is written asynchronously by `SessionWriter` from the tailer (`session/writer.py:114 upsert_session`).
- The durable row is built by `build_session(binding)` (`session/ingest.py:62-80`); its `parent_session_id`/`forked_at_seq` come from **`binding`** (`ingest.py:77-78`), which is populated with lineage **only by the subagent fan-out** (`index/subagents.py:184-185,230-231`; `index/adapters/claude.py:128`). For a normal top-level session both default `None` (`index/adapters/base.py:42-43`). There is no path from a launch parameter to `binding` lineage.
- No single-session "last visible seq" read exists. The only `max(seq)` is the children-timeline aggregate (`dao_statements.py:203 max(e.seq) AS last_seq`), not a "get prior session's last seq" helper.

So implementing `continueFromSessionId` requires **new code**, via one of:
1. **Thread lineage** through `CreateRunRequest → SpawnRun → CapturedRunRequest → ManagedSession` mint (`cli/launch_profile.py:55`) → owned descriptor → `SessionBinding`, so `ingest.build_session` carries it (~5 layers; none exists today for non-subagent sessions); **plus** a new prior-last-seq read for `forkedAtSeq`.
2. **Route-layer pre-seed** (lighter): `run_routes` already has app-state DB access (`_dead_letter_counts_by_run` uses it; imports `session.async_dao`). After spawn, read prior last-seq and `upsert_session` a child row with parent/forked. This *can* survive the tailer's later NULL write because the UPSERT uses `parent_session_id = COALESCE("session".parent_session_id, EXCLUDED...)` (`dao_statements.py:93-94`) — but it still needs a new prior-seq read, a new write at the route, and the minted `session_id` to match what the tailer will use.

This issue is about the **TM-seeded** continuation model only — it is independent of native CLI
resume. Per authoritative product direction (owner): `transport-matters desktop` accepts **no**
passthrough CLI args (no `--resume`/`-c`); all continuation is handled internally by TM, and
native-CLI-resume is **off the table entirely**, not deferred. So `continueFromSessionId` is
unambiguously a TM-level concept (internal child-session minting + Postgres-sourced context priming),
which is exactly the path my finding targets: that path is still gated on the lineage plumbing below,
even with native resume removed from scope.

Severity: **Major to the build-order/effort claim** (step 4 is not "free at the existing seam"),
**not a Blocker** — the feature is clearly buildable and the TM-seeded model is the only one consistent
with both the ephemeral-home architecture and the no-passthrough product constraint. Recommend the
proposal drop "without new infra" and name the lineage-plumbing + prior-seq-read + DB-access work in
build-order step 4.

---

## Claim 3 — `homeDir` droppable → CONFIRMED

The durable `session.home_dir` (`session/models.py:48` `SessionRow`) is **write-only into Postgres**
and read by nothing except the response model being curated away.

- Writers: `ingest.py:75` (from `binding.home_dir`), `backfill.py:153` (from `owned.home_dir`), SQL `dao_statements.py:71,76,89`.
- Readers: `session_routes.py:64` (the `SessionSummary` field the proposal drops) and the **unused** www type decl `sessionClient.ts:14` + test fixture `testUtils.tsx:47`. `absent: no www component reads .home_dir/.homeDir for behavior`.
- **Every launch/relaunch/index path reads home from launch-time inputs, never the durable session row**: `request.home_dir`, `settings.agent_home_dir` (`addon_runtime.py:82`), `binding.home_dir`, `run.home_dir`, the disk descriptor/owned facts (`storage/session_facts.py`). `absent: no reader of SessionRow.home_dir outside the response model`.

Confirmed by the orchestrator's follow-up: `session.home_dir` is source/provenance, never the
transcript-bearing home. Dropping it from curated `Session` is safe. If provenance is ever surfaced,
prefer structured `template_provenance` over a raw path.

---

## Claim 4 — `turnCount`/`inheritedTurnCount` compute-at-read → SUPPORTED (with caveat)

Data exists and there is no N+1 *if* the list uses a batch aggregate.

- A turn = one `event` row with `kind='turn'`; PK `(session_id, seq)` (`migrations/0001_session_store_foundation.py`, event table). `turnCount = COUNT(*) WHERE session_id=? AND kind='turn'`.
- **The N+1 trap is already solved by an existing pattern**: `list_sessions` computes per-row dead-letter counts via a single `GROUP BY` over all session ids (`async_dao.py count_dead_letters_by_session`), not N queries. `turnCount` should follow the identical batch-GROUP-BY shape — `absent: no per-row event query in list_sessions today`.
- `inheritedTurnCount = COUNT(*) on parent WHERE seq <= forked_at_seq` — `parent_session_id`/`forked_at_seq` are on the row (`models.py:52-53`); PK-prefix indexed.

Caveat: there is **no `(session_id, kind)` index**, so the COUNT is a PK-prefix scan over a session's
rows then a `kind` filter. At hundreds–low-thousands of events/session × tens of sessions that is a
bounded scan, acceptable. The proposal's own escape hatch ("denormalize only if read latency demands
it") covers the tail; a `(session_id, kind)` partial index is the cheaper first mitigation. Correction
to "no latency problem": accurate **only** if LIST batches via GROUP BY, not per-row COUNT.

---

## Claim 5 — canvas-layout cut from B6 → CONFIRMED

No agent-domain (backend) consumer needs canvas-layout inside B6.

- `absent: rg "canvas-layout|canvas-layouts|canvasKey|PersistedCanvasPanes" api/src -> 0 hits`.
- The only matches are www: a CSS margin token `--canvas-layout-margin` (`engine/layout/types.ts:5`, `components/pane-dock.css:2,21`, `lab/CanvasLabRoute.tsx:215-216`) — unrelated to backend persistence — and client-side zustand persistence `PersistedCanvasPanes` (`session-canvas/persistence/canvasPanePersistence.ts:22`).

Desktop view-state, client-only today; it earns its own endpoint when resume S6 needs it. Cutting it
from B6 is correct.

---

## Net

Ship the proposal. Fix one thing: **Claim 2's "without new infra" is wrong** — continuation needs
lineage plumbing (or a route-layer pre-seed), a new prior-last-seq read, and DB access wired at the
spawn seam, because the Postgres session is tailer-minted and lineage is currently a subagent-only path.
Claims 3 and 5 are clean drops; Claims 1 and 4 are safe with the noted scoping/index caveats.
