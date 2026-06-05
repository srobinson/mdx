---
title: TM NOTES Work-Remaining Audit — B6 API Surface
type: research
tags: [transport-matters, b6, api, work-remaining, notes-audit]
summary: B6 product-API facade (whether /v1 or /api/v2) is entirely unbuilt; the recording effort is in progress but the three spec docs contradict each other on namespace, canvas-layout inclusion, and continuation shape.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# B6 API Surface — Work Remaining (NOTES/captured-canvas)

Slice **B6 API surface** of the read-only NOTES work-remaining audit. Every claim verified against
committed code (`git log`, grep, source). NOTES checkboxes were NOT treated as evidence.

**Headline:** The B6 curated product-API facade is **not built**. No versioned namespace exists
(`grep -rn "api/v2\|/v2/" api/src -> 0 hits`; no `/v1` facade router either — `api/v1/router.py`
mounts the existing mechanism-split routes only). What ships today is the *source* surface the facade
would curate: mechanism-split `/api/runs` (camelCase via `RunViewModel`) and `/api/sessions`
(snake_case `SessionSummary`/`SessionEventView`). The B6 recording step (`spec.md` Near-Term step 3,
"Specify B6 API payloads") is in progress via notes 12/14/15, but those notes **disagree** and none is
committed to `spec.md`.

---

## OPEN CONTRADICTION (recorded, not resolved — per orchestrator instruction)

The B6 spec docs conflict on three axes. Note 12 (`12-b6-api-payloads.md`, dated 2026-06-11,
"Status: spec") presents decisions as fixed. Notes 14/15 (dated 2026-06-14, "Status: DRAFT … nothing
committed to spec.md") are later and self-describe as uncommitted. `spec.md` (2026-06-11) still lists
"Exact B6 API payloads and names" as an **Open Question** (`spec.md` "Open Questions"). Neither
recording is authoritative yet.

1. **Namespace + rollout.**
   - Note 12: new **`/api/v2`** namespace as a *parallel* surface; v1 keeps serving the current UI,
     v2 presents the frozen Lilo contract and normalizes casing (`12-b6-api-payloads.md` "Namespace").
   - Notes 14/15: a thin **`/v1`** façade with **staged migration** — www migrates onto `/v1` and the
     internal snake_case routes *retire* as it moves, ending at one API (`14-b6-foundations-runtime.md`
     "Shared Conventions" / "Open Decisions #1").
   - These are mutually exclusive (parallel-forever vs migrate-and-retire; `/api/v2` vs `/v1`).

2. **Canvas layout in or out of B6.**
   - Note 12 §5 and `spec.md` keep **canvas layout in** the B6 noun set (`spec.md` "B6 Migration
     Seam" lists "canvas layout"; line "canvas layout concept should draw its payload from
     PersistedCanvasPanes").
   - Notes 14/15 **cut canvas layout** from B6 ("Transport Matters' own product-UI bounded context …
     leaves the B6 noun set", `14-b6-foundations-runtime.md` "Open Decisions #2"). Note 14 itself flags
     this "contradicts the current spec.md … pending explicit confirm and a spec.md reconciliation
     pass. Not edited yet."

3. **Continuation modeling.**
   - Note 12: optional **`continuationId`** on the v2 run-create payload **plus** a standalone
     `POST /api/v2/sessions/{priorSessionId}/continuations` endpoint (`12-b6-api-payloads.md` §3,
     OPEN-2 "DECIDED").
   - Notes 14/15: continuation is a **launch parameter only** — `continueFromSessionId` on
     `POST /v1/runs`, with **no** standalone continuation endpoint (`15-b6-transcript-family.md`
     "Continuation"). Different field name and different shape.

---

## spec.md — REFERENCE

Master spec / entry point, current as of 2026-06-11. Not a buildable unit itself; it frames the B6
seam other notes detail. B6-relevant state:
- B6 noun set defined incl. canvas layout (`spec.md` "B6 Migration Seam").
- "Exact B6 API payloads and names" is still an **Open Question** (`spec.md` "Open Questions") →
  confirms B6 API uncommitted.
- Canvas Layout & Persistence Core (the frontend seam B6 §5 reuses) is **SHIPPED** (`spec.md`
  "Near Term Sequence" item 1 marked SHIPPED, PRs #83–#87; corroborated `git log` a15c5ea…f7a567e).
- Near-term step 2 "Implement app cleanup and typed managed run errors" = R1, shipped (#93).

No remaining work owned by this note within the B6-API slice beyond what 08-plan-b/12/14/15 carry.

## plan-b-design.md — REFERENCE

Boundary decisions + B6 design sketch (2026-06-11). "Current Shipped Contract" section is accurate.
Remaining B6 design it describes is unbuilt (see notes 12/14/15). Minor staleness, not work:
- Lists shipped run API as 4 endpoints and omits the single-get that actually exists
  (`run_routes.py:get_run` @ `GET /api/runs/{run_id}`). Documentation drift only.

## 08-plan-b.md — PARTIAL

Active remaining-work plan (R1/R2/R3). R1 done; R2 recording in progress + implementation remaining;
R3 not started.

Remaining (not-yet-built) items:
- **R2 implementation: the entire B6 API facade is unbuilt** — no versioned/curated product surface
  exists. `absent: grep -rn "api/v2\|/v2/" api/src -> 0 hits`; `api/v1/router.py` mounts only the
  existing mechanism routes (no facade router).
- **R2: the namespace/rollout call is unresolved** — see OPEN CONTRADICTION #1. `12-b6-api-payloads.md`
  "Namespace" (`/api/v2`) vs `14-b6-foundations-runtime.md` "Shared Conventions" (`/v1`).
- **R3 documentation cleanup** not started: `spec.md` Plan B section + runtime-subscription refs not
  yet reconciled to shipped-vs-remaining; note 14 canvas-layout cut not reflected in `spec.md`.
  `absent: spec.md still lists "Exact B6 API payloads and names" under Open Questions`.

Done within this note (evidence, not remaining):
- R1 typed errors + shutdown cleanup shipped (#93). `run_stale`/`run_stopped` codes present
  (`run_manager.py:62-63 RunManagerErrorCode`; mapped in `run_routes.py:50-51`).
- R2 gate "canvas does not depend on backend process memory for historical transcript display" met:
  durable Postgres transcript + SSE (`session_routes.py:list_session_events`, `get_session_timeline`,
  `stream_session_events`, `stream_session_timeline`).

## 12-b6-api-payloads.md — REMAINING

Detailed payload spec for a **`/api/v2`** surface (7 nouns + error envelope). It is a complete
*recording* artifact (satisfies R2's "record names+payloads before implementation"), but every API it
specifies is unbuilt. Not-yet-built items:
- `GET /api/v2/workspaces` (workspace aggregation over sessions). `absent: grep -rn "canvas-layouts\|/workspaces\"\|workspaces route" api/src -> 0 API-route hits` (only filesystem `workspaces/` dir hits).
- `GET /api/v2/sessions` + `GET /api/v2/sessions/{sessionId}` curated camelCase list/single-get.
  `absent: no bare GET /sessions/{session_id} in session_routes.py route decorators` (only
  `/events`, `/timeline`, `/resources`, streams).
- `POST /api/v2/sessions/{priorSessionId}/continuations`. `absent: grep -rn "continuation" api/src
  -> only track-manager subagent code, no continuation route/field`.
- `GET/PUT /api/v2/canvas-layouts/{canvasKey}` (backend layout persistence). `absent: no canvas-layouts route`.
- `POST/GET/DELETE /api/v2/runs` + `WS .../terminal` curated camelCase `Run` (drop transport
  internals). `absent: routes serve /api/runs not /api/v2/runs (RUNS_ROUTE_PREFIX = "/runs")`.
- `GET /api/v2/sessions/{sessionId}/resources/{resourceId}` curated. Source exists at v1
  (`session_routes.py:get_session_resource`); the v2/curated re-exposure does not.
- Forward-declared `sessionPurpose`/`sessionVisibility` (OPEN-3 "decided"). `absent: grep -rn
  "session_visibility\|session_purpose" api/src www/src -> 0 hits` (schema also unbuilt;
  `spec.md` "Internal And User Session Classification" still a proposal).
- Optional `continuationId` on run-create (OPEN-2 "decided"). `absent: CreateRunRequest has cli/cwd/
  terminal only (run_routes.py:70 CreateRunRequest)`.

Confidence: high that the v2 surface is absent; the OPEN-1/2/3 "DECIDED" markers here conflict with the
later notes 14/15 (see OPEN CONTRADICTION) — treat as unsettled, not built.

## 14-b6-foundations-runtime.md — REMAINING

DRAFT `/v1` façade spec, runtime/run bucket (explicitly uncommitted). The façade is unbuilt.
Not-yet-built items:
- Thin `/v1` façade namespace. `absent: grep -rn "/v1/" api/src as a route prefix -> 0 hits` (the
  `api/v1/` package is the *internal* module path, not a `/v1` URL facade).
- Curated camelCase `Run` dropping `proxyPort`/`webPort`/`storageDir`/`scrollback*`/`viewerlessSince`/
  `nativeSessionId`. `RunViewModel` today still exposes all of these (`run_routes.py:80 RunViewModel`).
- `sessionId` (durable session) added to `Run` for run↔transcript correlation. `absent: RunViewModel
  has native_session_id, no durable sessionId field`.
- `continueFromSessionId` on `POST /v1/runs`. `absent: CreateRunRequest (run_routes.py:70) has no
  session field`.
- `DELETE` returning the full `Run` (today returns ad-hoc `{run_id,state,stop_reason}`,
  `run_routes.py:111 StopRunResponse`).

Stale delta claim (NOT remaining — already shipped): note 14 lists "New `GET /v1/runs/{id}` (list-only
today)". A single-get **already exists**: `run_routes.py:323 get_run` @ `GET /api/runs/{run_id}`
returns a single run. Only the curated *shape* (camelCase `Run`) is pending, not the endpoint.

## 15-b6-transcript-family.md — REMAINING

DRAFT `/v1` façade spec, transcript family (workspace/session/continuation/transcript/resource),
explicitly uncommitted. The façade is unbuilt. Not-yet-built items:
- `GET /v1/workspaces` + `GET /v1/workspaces/{id}` (recent working dirs). `absent: no workspaces API route in api/src`.
- `GET /v1/sessions/{id}` single-get (resume-card source). `absent: no bare GET /sessions/{session_id}
  decorator in session_routes.py`.
- Curated camelCase `Session` dropping `nativeSessionId`/`minted`/`sourceDescriptor`/`homeDir`;
  `workspace_slug`+`workspace_hash` collapse to `workspaceId`. Today `SessionSummary`
  (`session_routes.py:51`) is snake_case and keeps the provenance fields.
- `cursor`/`nextCursor` paging (today `limit`/`offset`, `session_routes.py:list_sessions`).
- Curated camelCase `TranscriptEvent` dropping `nativeTurnId`/`parentNativeId`/`sourcePath`/
  `sourceLine`/`searchText`/`createdAt`. Today `SessionEventView` (`session_routes.py:82`) keeps them.
- `continueFromSessionId` launch-param continuation (mint with `parentSessionId`). `absent: no
  continuation field on CreateRunRequest`.
- Curated resource fetch dropping `includeDebug`. Source exists (`session_routes.py:get_session_resource`);
  curated v1 shape does not.

Note: `GET /v1/sessions/{id}/events|timeline|resources` + the two SSE streams have working *source*
endpoints today (`session_routes.py:159/183/217/257/275`); the façade re-presentation (camelCase,
curated fields, `/v1` mount) is what remains.

---

## Bottom line

| Note | Class |
| --- | --- |
| spec.md | REFERENCE |
| plan-b-design.md | REFERENCE |
| 08-plan-b.md | PARTIAL (R1 done; R2 recording in progress, impl remaining; R3 remaining) |
| 12-b6-api-payloads.md | REMAINING (`/api/v2` surface unbuilt) |
| 14-b6-foundations-runtime.md | REMAINING (`/v1` run façade unbuilt) |
| 15-b6-transcript-family.md | REMAINING (`/v1` transcript façade unbuilt) |

The B6 implementation is gated on resolving the three-way namespace/canvas-layout/continuation
contradiction first; until then "record before implement" (R2) is the only step partially in motion,
and it is itself inconsistent across the three recording docs.
