# PR-2b review — Opus family

**PR #256** · branch `feat/activity-pr2b-vitals-strip` · scope `git diff origin/main...HEAD`
Single commit `d9ee4d4` "feat(canvas): always-on per-pane vitals strip (slice 4 PR-2b)".
Reviewed read-only; `git status --short` pristine before and after (HEAD `d9ee4d4`).
Protocol: high-effort `/code-review` (8 finder angles + 1-vote verify) + `/code-hygiene` inspection pass, then this brief's 6 criteria.

## Verdict

**issue — 0 major, 4 minor.** No correctness bug: all six brief criteria pass on the source. The one candidate regression (always-on strip renders empty) collapsed under verification — the launch-gating is deliberate and explicitly unit-tested, and the populated feed path works when the launch resolves. Findings are quality/hygiene, led by an incomplete-refactor DRY duplication the PR itself created.

---

## Brief criteria walkthrough (all PASS)

### 1. [highest] Stream mounts on `resolved.workspaceId`, guarded, feeds `applyFrames`, no leak — CONFIRMED

`SessionCanvasRoute.tsx::SessionCanvasRoute` calls `useWorkspaceActivityStream({ enabled: resolved !== undefined, workspaceId: resolved?.workspaceId ?? "", onEvents: applyActivityFrames })`.
- `resolved` = `launchResolution.data?.status === "resolved" ? launchResolution.data.session : undefined`, so the id passed is the FULL slug/hash `resolved.workspaceId`, **never** `launch.workspaceHash`. `workspaceIdParts` is never handed a hash-only id.
- Guard is double: `enabled: resolved !== undefined` at the route, and `useWorkspaceActivityStream` internally gates `enabled && workspaceId.length > 0`. No empty-id request pre-resolution.
- `onEvents: applyActivityFrames` where `applyActivityFrames = useRunVitalsStore((s) => s.applyFrames)` — folds into the store. ✓
- Lifecycle: stream lives in `useEventSource` (cleanup on unmount, native reconnect, no double-subscribe), plus `SessionCanvasRoute.tsx` has `useEffect(() => () => useRunVitalsStore.getState().clear(), [])` scrubbing the store on route unmount.
- Proven by `SessionCanvasRoute.test.tsx`: "mounts the workspace activity stream on resolved.workspaceId and folds into runVitalsStore" asserts the exact URL `/v1/workspaces/my-slug%2Fws-hash-abc/activity/stream?owner=local` and `byRunId["run-vitals"].status === "needs-you"`; the companion "does not open the activity stream without a resolved workspace id" asserts no stream on `/canvas` (no hash/harness).

### 2. PaneChrome slot non-disturbing; PaneWindow threads; terminal untouched — CONFIRMED

`PaneChrome.tsx` renders `{strip ? <div className="canvas-pane-window__strip">{strip}</div> : null}` between `__header` and `__body`. Absent strip → `null`, so non-captured / no-vitals panes render byte-identically to before. `PaneWindow.tsx` supplies `strip` only when `pane.contentRef.kind === "captured-run"`, else `undefined`. `CapturedRunPane` and terminal code are not in the diff.

### 3. RunVitalsStrip states, needs-you semantics, runKey→runId — CONFIRMED

`RunVitalsStrip.tsx::RunVitalsStrip` reads `useRunVitalsStore((s) => (runId ? s.byRunId[runId] : undefined))`; `runId` via `useCapturedRunStore((s) => s.runs[runKey]?.runId ?? null)`. Empty/no-vitals-yet → `data-empty="true"` and a null child (no crash, no NaN). `RunVitalsStrip.tsx::VitalsReadout` derives `needsYou = vitals.status === "needs-you"`; it does NOT attempt to distinguish AskUserQuestion — correct for needs-you v1 (server already collapses ANY waiting/idle to `needs-you`). All states covered by `RunVitalsStrip.test.tsx` (empty, running/Thinking, needs-you pill, exited, starting).
- Identity chain positively confirmed single-id-space: `capturedRunStore.runs[runKey].runId` ← POST /v1/runs `run.runId` ← `RunManager.register` `spec.runId` ← Python `prepared.run_id`; activity stream `run_id` ← `activityRouter.runToWire` `projection.runId` ← same Python `prepared.run_id`. The strip resolves live vitals.

### 4. contextTokens reuse; formatElapsedTime lift; no dead copy — CONFIRMED (one intentional, strictly-safer delta)

`RunVitalsStrip.tsx::tokenCount` calls `contextTokens(vitals.total_usage)` (core), not a re-inlined formula. `formatElapsedTime` moved to `core/src/formatting.ts::formatElapsedTime`; `ExchangeTurnCard.tsx` now imports it and the local copy is deleted; `formatRelativeAge` and the inspector stopwatch/span helpers are untouched.
- Not perfectly byte-identical: the lift adds a `nowMs = Date.now()` default param (evaluated per call, behavior-preserving) AND a NaN guard — the old inline version had none, so an unparseable ts yielded `Math.max(0, NaN) → "NaNs"`; the new version returns `ts` unchanged. Strictly safer; the only observable change is on malformed input the wire contract precludes. Not a regression.

### 5. Styling — CONFIRMED

`pane-window.css` `.run-vitals-strip*` is canvas-native BEM with CSS vars, zero Tailwind; `.run-vitals-strip__status--needs-you` mirrors the existing status-pill pattern (border/bg via `--color-*` tokens).

### 6. Tests adequate, non-tautological — CONFIRMED (one coverage gap → finding 3)

Unit tests assert observable end-state (DOM text/attrs, exact stream URL, store state) and would fail before the code. Empty-state and the resolved.workspaceId guard are both covered. Gap: the sole e2e only asserts the EMPTY slot as steady state (finding 3).

---

## Findings (all minor)

### MINOR 1 — [DRY, incomplete refactor] `useElapsedTick` duplicated across products

`RunVitalsStrip.tsx::useElapsedTick` is byte-identical to `ExchangeTurnCard.tsx::useElapsedTick` (inspector). This PR lifted the paired `formatElapsedTime` into `@tm/core` for exactly this sharing (its docstring names both call sites) but left the tick hook copied. Violates `~/.claude/CLAUDE.md` "DRY: no compromise" (zero tolerance). `@tm/core` already ships hooks (`useEventSource`, `useMeta`), so it is the proven home. Fix: export `useElapsedTick` from `@tm/core` beside `formatElapsedTime`, repoint both callers, delete both copies. Gate on full `pnpm --filter @tm/shell test` (the move crosses both product import graphs).

### MINOR 2 — [convention] em dash in new comment

`SessionCanvasRoute.tsx` adds `// Full slug/hash workspace id only — hash-alone throws in workspaceIdParts.` The em dash violates `~/.claude/CLAUDE.md` Writing rule "Never use em dashes". Replace with a period or restructure.

### MINOR 3 — [test-coverage] no e2e exercises a populated strip

`shell/tests/e2e/canvas-vitals-strip.spec.ts` launches the no-hash Space path (`?space_id=space-1&worktree_id=wt-1`) and asserts the strip stays `data-empty="true"` as steady state. A regression breaking the populated render (tokens/status/time) or the `resolved.workspaceId` stream wiring would still pass this e2e. The populated path is covered at unit level (`RunVitalsStrip.test.tsx` + `SessionCanvasRoute.test.tsx`), so this is a coverage gap, not a live bug. Optional: an e2e that resolves a launch and pushes one activity frame.

### MINOR 4 — [efficiency] fixed 1s tick re-renders past the seconds window

`RunVitalsStrip.tsx::useElapsedTick` runs a fixed 1s interval; once a run passes 60s, `formatElapsedTime` output changes only once per minute/hour, so ~59 of every 60 ticks re-render `VitalsReadout` to an identical DOM string, per active captured-run pane. Low impact (render scoped to `VitalsReadout`, few panes). An adaptive interval keyed to the current unit cuts re-renders ~60x; it belongs in the shared core hook from finding 1, so both ride one slice.

---

## Suggested fix order (if greenlit)
1. **[minor]** Extract `useElapsedTick` → `@tm/core` (closes findings 1 and 4 together).
2. **[minor]** Drop the em dash in the SessionCanvasRoute comment.
3. **[minor, optional]** Add a populated-strip e2e.

Gate: `pnpm --filter @tm/shell test` (full suite — the hook move touches both products' import graphs) + `just check`.

---

## Delta re-verify — live-wiring + slashful-id fix (HEAD `be8d57d`)

Two commits landed on top of the reviewed strip (`d9ee4d4..be8d57d`): `97e3df4` wired the strip live end-to-end (activity proxy, gateway DB env, canvas meta-fallback, populated e2e, folded all 4 prior minors), and `be8d57d` fixed a live slashful-workspace-id 404 in the proxy. Strip code already cleared is unchanged. Reviewed read-only; tree pristine at `be8d57d`.

### The 4 prior minors — all folded correctly
- `useElapsedTick` lifted to `@tm/core/useElapsedTick.ts` (exported via `index.ts`), both call sites (`RunVitalsStrip::VitalsReadout`, `ExchangeTurnCard`) rewired, both local copies deleted. DRY closed.
- The new hook is adaptive: 1s tick under a minute, 1m under an hour, then hourly (`useElapsedTick.ts::schedule`), with a `cancelled` guard + `clearTimeout` cleanup (no setState-after-unmount, no leak). Closes the tick-efficiency finding.
- Em dash removed from the `SessionCanvasRoute.tsx` workspace-id comment.

### 97e3df4 wiring — CONFIRMED
1. **Activity proxy** (`run_proxy.py`): `forward_sse` streams unbuffered (`stream=True`, `httpx.Timeout(None)`, `aiter_raw()`, `StreamingResponse`); the two routes only add gateway routing (no ingest/pgContracts/run_lifecycle touched). `test_run_proxy.py::test_activity_snapshot_and_stream_routes_forward_to_gateway` covers routing + `text/event-stream` content-type + never-SPA-fallback.
2. **Gateway DB threading** (`gatewayProcess.ts::resolveGatewayDatabaseUrl`, `env.ts`): threads `TRANSPORT_MATTERS_DATABASE_URL` (explicit env → channel `settings.toml [database].url`), rewrites only the db-name path segment via `databaseUrlWithDatabaseName` (prefix regex preserves scheme/host/credentials), sets the child env only when resolved so Activity mounts conditionally. No secret logged in the diff. `gatewayProcess.test.ts` pins the explicit-url + name-normalization path.
3. **Canvas meta-fallback** (`SessionCanvasRoute.tsx`): `activityWorkspaceId = resolved?.workspaceId ?? meta?.workspaceId ?? ""` — resolved stays PRIMARY; `meta.workspaceId` is the FULL slug/hash id (`meta.py::_meta_response` emits `workspace_id=f"{wid.slug}/{wid.hash}"`), so the fallback is never hash-alone and `workspaceIdParts` cannot throw; guard is `length > 0`.
4. **Populated e2e** (`canvas-vitals-strip.spec.ts`): a second test pushes a `thinking` snapshot (`context_tokens: 1234`) via a fake activity `EventSource` and asserts the strip is not `data-empty`, `data-status="thinking"`, `1,234 tok`, `Thinking`. Because it launches the no-hash Space path, it exercises the meta-fallback wiring end-to-end. Closes the prior "no populated e2e" finding.

### be8d57d slashful-id fix — CONFIRMED (fix is clean, fail-first)
`run_proxy.py::_workspace_activity_route_path(workspace_id, suffix)` re-encodes the ASGI-decoded raw-slash id via `quote(workspace_id, safe='')`, mirroring `_run_route_path`. Both routes now take `workspace_id: str` and pass the re-encoded `route_path` to `forward_http`/`forward_sse`.
- (a) Consistent with the runs proxy (identical `quote(..., safe='')`); GET → `/activity`, stream → `/activity/stream`. ✓
- (b) SSE mechanics untouched → still unbuffered. ✓
- (c) Test now pins the ENCODED forward (`...%2Fecd9b0df/activity` + `/activity/stream`); pre-fix forwarded the decoded raw slash, so the assertion genuinely fails without the fix. ✓
- (d) Handler param is already-decoded, `quote` encodes exactly once — no double-encoding. ✓

### Residual minors (both pre-existing from 97e3df4's proxy, NOT introduced by the fix; neither blocks merge)

**MINOR 5 — [test-coverage] the unbuffered SSE contract is not locked by a test.** `test_activity_snapshot_and_stream_routes_forward_to_gateway`'s `fake_send` ignores the `stream` kwarg and asserts only routing/content-type/non-SPA. A regression dropping `stream=True` or `httpx.Timeout(None)` (reverting `forward_sse` to buffered) would still pass. Given the brief flags unbuffered SSE as CRITICAL, assert `stream is True` on the captured send (and/or a slow-generator incremental-delivery check).

**MINOR 6 — [robustness, latent] `forward_sse` uses `aiter_raw()` (undecoded) but strips `content-encoding`.** `run_proxy.py::forward_sse` forwards the client `Accept-Encoding` upstream and yields raw bytes while dropping `content-encoding` from the response headers. Safe only while the gateway never compresses `text/event-stream` (Fastify default does not), so it does not manifest today, but it is a corruption trap for the next consumer. Conventional SSE-proxy shape is `aiter_raw` + pass `content-encoding` through, or forward `Accept-Encoding: identity`.

### Delta verdict
**issue — 0 major, 2 minor.** The live-wiring and the slashful-id fix are correct and fail-first tested; all brief criteria (fix a–d + rest-intact) pass. The two residual minors are proxy-hardening items in the SSE path, both minor, neither blocking merge on correctness. Tree pristine at `be8d57d`.
