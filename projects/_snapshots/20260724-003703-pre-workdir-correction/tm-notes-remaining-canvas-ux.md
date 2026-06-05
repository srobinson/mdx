---
title: TM NOTES Work-Remaining Audit — Canvas Surfaces & UX slice
type: research
tags: [transport-matters, captured-canvas, work-remaining, audit, ux]
summary: Six captured-canvas notes audited against committed code; 4 remaining, 2 partial, 0 done.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Canvas Surfaces & UX — work-remaining audit

Read-only audit of `NOTES/captured-canvas/`. Note checkboxes are NOT evidence;
every claim verified against committed code (git, grep, source). Repo root:
`/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`. HEAD `16b95d7`.

Tally: **6 notes — 4 REMAINING, 2 PARTIAL, 0 DONE/REF.**

| Note | Class | One-line |
|------|-------|----------|
| 01 ia-navigation | REMAINING | IA address model (wd/canvas/agent/view, director canvas, slick swap) unbuilt; flat Canvas\|Lab switcher still in place |
| 02 surfaces-inspect | PARTIAL | ExchangeDetail decoupled & reused as a `provider-exchange` pane; session-scoped live exchange-**list** inspect surface not built |
| 03 prompt-input | REMAINING | Transcript pane is read-only stream; no prompt write surface, no PTY stdin send, no ESC |
| 04 wire-curation | REMAINING | Breakpoint blocking model NOT retired (fully live); none of the 3 replacement surfaces built |
| 06 layout-persistence | PARTIAL | Persistence core + backend-ready seam + gridFit ordering + frozen-drag shipped; URL address + task-#18 layout modes parked |
| 15 dock-pane-previews | REMAINING | `truncateMiddle`/dock fallback shipped; preview affordance + snapshot capture + session-title identity unbuilt |

---

## 01 — IA & Navigation — REMAINING

Largely an unbuilt IA outline ("expand during planning"). Substrate exists
(`useUIStore.activeRoute`, `RouteSwitcher`, panes, `workspace_hash` launch
param) but the navigation **model** the note describes is not built.

Not-yet-built:
- Query-param address `?wd=<dir>&canvas=director` / `?wd&agent=<runId>&view=transcript|inspect|cli`. Canvas routing only reads `workspace_hash`/`cli`/`run_id`, not `wd`/`canvas`/`agent`/`view` — `route.ts parseCanvasLaunchContext` + `route.ts selectRootRoute` (returns `canvas|canvas-lab|legacy`).
- Supersede the flat `Canvas | Lab` switcher with the wd→canvas→agent/view rail. Flat switcher still shipped — `RouteSwitcher.tsx` (`{id:"canvas"…}`, `{id:"canvas-lab"…}`).
- Working-dir / workspace switcher at the top — `absent: grep -rE "workspaceSwitch|switchWorkspace|workingDir" www/src -> 0 hits`.
- "Director canvas" as a navigable IA surface (note's per-agent transcript|inspect|cli triad off one director). "director" exists only as a roster comment — `capturedRunStore.ts:144` ("director roster"); no canvas-triad navigation.
- Full-canvas "slick swap" transition between canvases — `absent: grep -riE "slick|swap" www/src/session-canvas -> 0 hits`.
- Title-bar affordance on an agent pane to jump to that run's transcript/inspect/cli — no such jump action (no agent/view route to target; see above).

Confidence: high. (Note self-labels as a planning outline, so parts are
REFERENCE; the concrete nav features are unbuilt → REMAINING.)

---

## 02 — Inspect Canvas (provider wire) — PARTIAL

Shipped (do not rebuild):
- `ExchangeDetail` decoupled via the slice-8 `onMissing`/`initialTab` seam and reused as a canvas pane — `ProviderExchangeResourceViewer.tsx` renders `<ExchangeDetail id={exchangeId} initialTab={…} onMissing={noop} />`.
- Registered as the `provider-exchange` viewer kind — `registry.tsx` (`id:"provider-exchange"`, `EXCHANGE_PANE_PREFIX${sessionId}:${exchangeId}`).
- No ARM/OVERLAYS on the canvas viewer (read-only) — the canvas pane is just `ExchangeDetail`; arm controls live only on the legacy `/intercept` route.

Not-yet-built:
- The session-scoped, **live** exchange-**list** inspect surface (the full INTERCEPT inspector: list + detail as one canvas). Today's pane is a single exchange keyed by `exchangeId`, not a `session_id`-scoped list — `registry.tsx` provider-exchange `paneId(ref)=…:${ref.exchangeId}`; no exchange-list canvas pane exists (`absent: grep -riE "exchangeList|ExchangeList" www/src/session-canvas -> 0 hits`).
- Live `pg_notify`-driven refresh of that list as a canvas surface (single-exchange `ExchangeDetail` is fetch-on-open, not a live session-scoped list).
- Final read-only pane naming decision ("Wire"/"Exchanges") — viewer title is `Exchange ${id.slice(0,8)}` — `registry.tsx` provider-exchange `title`.

Note's "foundation resolved 2026-06-11 (web-separation shipped)" is correct:
nested-run capture lands in Postgres (`test_captured_run_web_separation.py`).

Confidence: high.

---

## 03 — Prompt Input (chat) — REMAINING

The transcript canvas exists and is live, but the **write** surface the note
specs is entirely absent.

Shipped substrate (read-only):
- `TranscriptChatPane.tsx` renders a live, read-only session-event stream (`useSessionEventStream`, `useSessionEvents`) — display only.

Not-yet-built:
- Prompt input that types into the CLI PTY stdin over the run input WebSocket — `absent: grep -E "stdin|send|prompt|input|WebSocket|socket" TranscriptChatPane.tsx -> 0 hits`.
- ESC interrupt (send `0x1b` to the PTY), tested to the ctrl-c-delivery standard — `absent: grep -E "0x1b|ESC|escape" www/src/session-canvas/viewers/transcript-chat -> 0 hits`.
- Reuse of `terminalSession`/captured-run socket as the shared input channel from the transcript surface (one PTY WS, two input surfaces) — not wired; `terminalSession.ts` is consumed only by terminal/captured-run panes.
- Pending indicator for the stdin→CLI→tailer→Postgres→UI latency (render-from-capture echo) — no pending state in `TranscriptChatPane.tsx`.
- Image-upload-into-prompt investigation (best-effort) — not started.

Confidence: high.

---

## 04 — Wire Curation & Compaction — REMAINING

The note declares the blocking breakpoint "retired (as a surface)". It is
**not** retired — the arm→pause-next→release model is fully live. Per the
orchestrator brief, "retire X that still exists" is itself remaining work.

Retire-work remaining (breakpoint still live):
- Backend blocking control plane present — `breakpoint.py`; HTTP routes `api/v1/breakpoint_routes.py` serving `POST /api/breakpoint/arm` + `GET /api/breakpoint/status` (`test_cli_web_control_plane.py:56,61`).
- Frontend arm UI present and wired — `ArmToggle.tsx`; `routeLayout.tsx:67,101` (`<ArmToggle mode onToggle error/>`, `mode:"off"|"armed_once"`) on the `activeRoute==="intercept"` surface.
- Breakpoint editor family present — `BreakpointEditor.tsx`, `BreakpointEditorTabs.tsx`, `BreakpointEditorPanes.tsx`, `BreakpointEditorActions.ts`, `useBreakpoint.ts`, `types/breakpoints.ts`.

Replacement surfaces remaining (none built):
- Inspect-last + curate as a **non-blocking** override-forward/replay channel that crosses the nested-run boundary. Only the legacy in-breakpoint curate exists (`curated_ir` on `api.ts:196,202,311`, `types/overrides.ts curated_value`), which is the blocking editor path, not the eventually-applied channel — no inspect-last surface (`absent: grep -riE "inspect-last|inspectLast" www/src api/src -> 0 hits`).
- Prime-the-first-request via a hidden warm run — `absent: grep -riE "prime|warm.?run|hidden.?run" www/src api/src -> 0 hits`.
- Compaction (strip injected reminders / tool schemas, compact tool results, preset catalog) — `absent: grep -riE "compaction|compact preset" www/src api/src -> 0 hits`.
- Decide retire-vs-dormant for the legacy in-process breakpoint on the CLI path (open question, unresolved).

Override mechanism the replacements would build on exists — `override_state.py` (`OverrideStore`, `get_store`, `root_scope`), `overrides.py`, `api/v1/overrides.py`.

Confidence: high.

---

## 06 — Layout & Persistence — PARTIAL

Core shipped (#83–#95); confirmed. Report covers only parked leftovers.

Shipped (do not rebuild):
- localStorage Zustand `persist` of panes + view state — `canvasStore.persistence.ts`, `createCanvasPersistOptions` (#92 `be601cb`).
- Backend-ready pluggable storage seam (adapter swap, not rewrite) — `canvasPersistOptions.ts` `storage: createFrontendPersistStorage()`.
- gridFit consumes an ordered `paneIds` array (ordering = model concern, per doc-17 resolution) — `layoutPlanning.ts` `PlanInput.paneIds`; `engine/layout/types.ts`.
- Frozen-drag user-controlled pane order — `session-canvas/dnd/` (`useReorderSettle.ts`, `paneDndCallbacks.ts`, `CanvasPaneDnd.tsx`) (#95 `cf51be2`).
- Strategies registered: `grid-fit`, `grid-overflow` — `engine/layout/configs.ts`, `engine/layout/index.test.ts:9-10`.
- No-backcompat migrate-reset (stale caches reset) — `canvasPersistOptions.ts` `migrate: () => emptyPersistedCanvasState()`.

Not-yet-built (parked leftovers):
- URL/query-param **address** layer (which wd/canvas/agent-view), keyed persistence by `wd + canvas + agent/view`. Persistence keys on canvas name only; no wd/agent/view address (tie to note 01) — `route.ts parseCanvasLaunchContext` (no `wd`/`agent`/`view`).
- Task-#18 layout modes: freeform/slot strategy, snap-to-grid placement, Tidy/Reflow demotion — only `grid-fit`/`grid-overflow` registered — `absent: grep -riE "freeform|snap-to-grid|snapToGrid|Tidy|Reflow|slot" www/src/engine/layout -> 0 hits`.
- Per-agent (derived) canvas persistence vs pure projection (open question; "persist once manual placement lands") — no per-agent derived canvas exists yet (tie to note 01).

Confidence: high.

---

## 15 — Dock Pane Previews and Session Titles — REMAINING

Spec "not yet implemented"; confirmed. A couple of named primitives shipped;
the feature itself is unbuilt.

Shipped primitives:
- `truncateMiddle` — `lib/formatting.ts:38` (note's "(shipped)" correct).
- Dock middle-truncation with full title on hover — `PaneDock.tsx` (`DOCK_TITLE_MAX=44`, `truncateMiddle(title,…)`, `title={title}`).
- `titleForRef` fallback — `registry.tsx:169`; dock uses it as a tier — `PaneDock.tsx:126`.

Not-yet-built:
- `preview?(ref, snapshot)` member on the viewer registration — `ViewerRegistration` (`paneRecords.ts:197-206`) has no `preview` member.
- Per-kind preview rendering (image `img`, text/markdown/json first-lines, terminal/captured-run dimmed monospace via `colorizeLine`) and the fixed-size clipped preview box in the dropdown — `absent: grep -riE "preview" www/src/session-canvas/components/PaneDock.tsx -> 0 hits`.
- `snapshotRegistry` mirroring `pasteRegistry`, `captureSnapshot(): string`, `@xterm/addon-serialize` buffer-tail capture, `useTerminalSession` `paneId` capture option — `absent: grep -rE "snapshotRegistry|captureSnapshot|addon-serialize" www/src -> 0 hits` (`pasteRegistry.ts` exists; snapshot twin does not).
- `DockedPane.snapshot` optional field (harvested in `dismissPane`, excluded from persisted payload) — `absent: grep -rn "snapshot" paneRecords.ts PaneDock.tsx -> 0 hits`.
- Session-title-as-primary-identity: resolve `nativeSessionId` (on `RunViewModel`) against the session read surface (session `title` column) lazily on dropdown open. Dock resolves `pane.record?.title ?? titleForRef(ref) ?? paneId`, not a sessions-query join — `PaneDock.tsx:126`; `absent: grep -iE "nativeSessionId|sessions query" PaneDock.tsx -> 0 hits`.

Confidence: high.

---

## Method note

fmm not used (targeted grep/read on a known slice was faster and gives exact
evidence anchors). All anchors are file+symbol or `absent: <grep> -> 0 hits`
so each line is independently checkable. No files modified.
