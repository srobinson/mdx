# Transport Matters restart-polish review (PR #160, feat/desktop-detach)

**Range reviewed:** `git diff 5aaddb1..39a7756` (HEAD = 39a7756). Working tree pristine (verified before and after).
**Scope:** the two restart-polish fixes only — a4a1dc3 (Slice A desktop app-quit) + 39a7756 (Slice B canvas prune+gate).
**Method:** xhigh adversarial pass — 10 finder angles + cross-file backend trace + gap sweep, each load-bearing claim verified against source.

## Verdict

**Slice A (desktop app-quit): CLEAN.** Verified directly:
- `quitHostedApp = appSource.quit.bind(appSource)` (main.ts:308) binds correctly; the 3-consecutive-failure path calls it (main.ts:392) only at `consecutiveFailures >= HOSTED_BACKEND_FAILURE_LIMIT`, never on a single transient failure.
- No timer leak: at the threshold `pendingTimeout` is already `undefined` (the firing timer cleared it at main.ts:369) and `scheduleNextProbe` is not called, so nothing dangles even though `hasClosed` stays false until Electron fires `closed` (main.ts:406-409 clears state).
- `quitOnWindowAllClosed` is hosted-only: passed only by `registerHostedDesktopLifecycle` (main.ts:341); the foreground/`registerAppLifecycle` path omits it, preserving macOS darwin-survival. Tests assert both directions, and `withProcessPlatform` restores `process.platform` via try/finally.
- DESKTOP_PACKAGE_SMOKE early-return is untouched and precedes lifecycle registration.
- Tests strengthened, not weakened (threshold test now asserts `quit` once AND `close` not called).

**Slice B (canvas prune+gate): 2 Major + 7 Minor.** The gate scoping, start-snapshot semantics, no-doomed-lifecycle (no terminate / no createCapturedRun), transient-failure-keeps-state, and `dropCapturedRunPane` open+docked removal are all correct as the brief claims. The defects are in what `listRuns()` actually returns versus what the prune assumes, plus a wedge and cleanup items.

---

## Major

### M1 — Pagination false-prune destroys a LIVE captured run
`www/src/session-canvas/SessionCanvasRoute.tsx:44-51`

The reconciliation treats "present in `listRuns()` result" as "alive," but `listRuns()` returns only the first page. Verified end-to-end:
- `listRuns()` (api.ts:491-501) returns `response.items` and **silently drops `nextCursor`**; it sends no `limit`.
- Route `GET /v1/runs` (run_routes.py:459-478) pages at `DEFAULT_RUNS_LIMIT = 50` and emits `nextCursor` when more remain.
- `RunManager.list()` (run_manager.py:212-221) returns `self._runs.values()` in **insertion order (oldest first)**; the only `_runs.pop` is registration rollback (run_manager.py:200) — terminal runs are **never evicted**, so `_runs` grows monotonically over a process lifetime.

Consequence: once >50 runs are resident, a genuinely live remembered run that sorts onto page 2+ is absent from `liveRunIds`, so `dropRun(runKey)` (line 50) + `dropCapturedRunPane(runKey)` (line 51) delete its mapping and pane while the backend PTY keeps running → orphaned process + destroyed user pane, silently. Ordering makes it worse: recent runs (the ones a user is actively viewing) sort last, so they are the first pushed off page 1. Reachable over a long-lived dogfooding API because terminal runs pad the list past 50.
**Fix direction:** reconcile against the complete set (page through `nextCursor`) and/or restrict "live" to attachable runs (see M-root below); equating one unfiltered page with the live set is the altitude error.

### M2 — No timeout on `listRuns()` wedges the gate "pending" forever
`www/src/session-canvas/SessionCanvasRoute.tsx:44-64`

Gate release happens only in `.finally` (line 58), which runs only when the `listRuns()` promise settles. `requestJson` (api.ts:75) uses bare `fetch` with **no AbortController, signal, or timeout** (verified — no such tokens in api.ts). On a hung backend (socket accepted, no response — distinct from a refused connection, which the `.catch` at line 54 handles), the promise never settles, `.finally` never runs, `capturedRunReconciliation` stays `"pending"`, and every captured-run pane is stuck on the `captured-run-reconciliation-placeholder` ("Checking captured run state…", `aria-busy`). There is no in-mount retry — the effect re-runs only when `capturedRunReconciliation` changes, which only `.finally` does. The user cannot reach any captured terminal until a full route remount. Only triggers when `hasRememberedCapturedRuns()` is true at mount.
**Fix direction:** add an AbortController/timeout to the reconciliation fetch (or to `requestJson`) so a hang releases the gate (treated as the transient-failure path, which already keeps local state).

---

## Minor

### m3 — Terminal runs counted as "live"; incomplete prune (shared root with M1)
`www/src/session-canvas/SessionCanvasRoute.tsx:47-49`

`listRuns()` sends no `state` filter, and `RunManager.list()` with no filter returns terminal runs too (`_TERMINAL_STATES` is excluded only in the active-count path run_manager.py:268, **not** in `list()`). So a remembered run that EXITED/FAILED is still in `items`, `liveRunIds.has(runId)` is true, and it is never pruned. The stale pane then mounts and `attach` is rejected (`run_not_attachable`, run_manager.py:237-238). The effect comment ("a fresh backend reports that a process-resident run no longer exists") assumes presence ⇒ alive, which is false for terminal runs. Not a regression (pre-diff there was no prune), but it misses the natural-exit cleanup the fix implies. Root shared with M1: "in the unfiltered first page" ≠ "live/attachable." A reconciliation that asks only for attachable (STARTING/RUNNING) runs fixes m3 and largely mitigates M1 (active runs rarely exceed 50). Caveat: the route's `state` query is single-valued, so STARTING+RUNNING in one call needs a route/`RunFilters` tweak or a dedicated reconciliation surface.

### m4 — Global captured-run gate withholds a newly-spawned run during pending
`www/src/session-canvas/components/CanvasSurface.tsx:156`

The placeholder gate keys off `pane.contentRef.kind === "captured-run" && !capturedRunsReady` for **all** captured-run panes, not just the snapshot candidates. A run the user spawns while reconciliation is pending (never a prune candidate) is also withheld behind the placeholder until release — and indefinitely if M2 wedges. The "preserves a run persisted during the round trip" test only asserts the new run renders **after** release, not during, so this is uncovered. Minor (gate normally releases fast), but it couples an unrelated new run to the reconciliation of old ones.

### m5 — `dropRun` duplicates `stopRun`'s record-removal block (DRY)
`www/src/session-canvas/model/capturedRunStore.ts:217-225`

`dropRun` repeats `cancelledKeys.delete`/`minimizedPendingKeys.delete` plus the identical `set((state) => { if (!state.runs[runKey]) return {}; const { [runKey]: _removed, ...runs } = state.runs; return { runs }; })` destructure already in `stopRun` (line 193-211, same destructure at 201). `dropRun` is effectively `stopRun` minus the `terminateRun` call. Extract a private `forgetRunRecord(runKey)` both call; a future change to how a mapping is cleared then can't diverge between them (exactly the orphan/zombie-run class the store's own comments guard against).

### m6 — Test fixtures duplicated instead of shared
`www/src/session-canvas/SessionCanvasRoute.test.tsx:35,39`

`capturedRunRef` (line 35) is byte-identical to the one in `model/canvasStore.test.ts:58`; `rememberCapturedRun` (line 39) mirrors `seedCapturedRun` in `canvasStore.test.ts`. The file already imports shared fixtures from `session-canvas/testUtils.tsx` — hoist both there. When the `captured-run` ref shape or `CapturedRunRecord` grows a field, divergent copies silently compile against a stale literal and mask the contract change.

### m7 — Reconciliation placeholder is a kind-specific special-case in the generic renderer (altitude)
`www/src/session-canvas/components/CanvasSurface.tsx:156-166`

The "Checking captured run state…" branch is the only per-pane-state inspection inside the generic `useCanvasPaneRenderer` loop, gated on `kind === "captured-run"`. Every other captured-run pane state (loading/spawn-error/Suspense fallback) lives in the viewer registry / `CapturedRunPane`. Threading a "not-yet-reconciled" state through the generic renderer means a future async-gated pane kind has two competing homes for pre-mount gating. Consider letting the captured-run viewer own the not-ready state (the route already drives it via a store flag) rather than branching in the shared renderer.

### m8 — Tautological no-terminate assertion
`www/src/session-canvas/model/canvasStore.test.ts:323`

`expect(terminateRunMock).not.toHaveBeenCalled()` cannot fail from `dropCapturedRunPane`: `canvasStore.ts` never imports the api/`terminateRun`, so the no-terminate property is structural, not exercised by this test. The load-bearing assertions (panes/layout.nodes/order/docked removal, lines 324-327) are genuine; this one gives false coverage confidence. (The sibling `dropRun`-no-terminate test in `capturedRunStore.test.ts` IS load-bearing, since that store does import `terminateRun`.)

### note (optional) — `dropCapturedRunPane` reset arithmetic vs `finalizePaneDismissal`
`www/src/session-canvas/model/canvasStore.ts:132-163`

`dropCapturedRunPane` hand-rolls the expanded-reset / framing-reset / `removeNode` / replan sequence that `finalizePaneDismissal` (paneAffordances.ts:227) already owns for single-pane dismissal. The genuine deltas (acts on a runKey spanning multiple open+docked panes, no close animation, must not terminate) justify not calling `dismissPane`, and it does reuse `removeNode`/`emptyFraming`/`planCanvasLayout` — so this is a low-confidence "consider routing the per-pane reset through the shared helper," not a defect. Flagging only because dismissal-semantics changes would need mirroring here.

---

## Checked and deliberately NOT flagged
- Slice A: all desktop concerns (quit binding, timer leak, hosted-only flag, smoke path, test strength) — clean.
- Gate scope: picker/transcript/resource/exchange panes DO render while pending (the `else` renders normally; only `captured-run` is gated) — the brief's CRITICAL point is satisfied and the "withholds…while picker renders" test proves it via a permanently-unresolved deferred.
- Start-snapshot prune: a run spawned during the fetch survives (not in the pre-fetch snapshot) — correct.
- No doomed lifecycle: `dropRun` + `dropCapturedRunPane` never call `terminateRun` or `createCapturedRun` — correct.
- `dropCapturedRunPane` `return {}` no-op, docked removal via both `entry.ref` and `entry.record?.contentRef`, `planCanvasLayout(nextState)` over corrected state, `removeNode` nulling focused pane — all correct.
- StrictMode double-mount: `cancelled` flag + per-invocation snapshot prevent double-prune / setState-after-unmount.
- `CanvasSurface` `capturedRunsReady` default `true`: test/stress callers that omit it render captured content immediately — no regression.
