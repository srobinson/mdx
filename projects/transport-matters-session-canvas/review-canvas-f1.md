# Review: canvas F1 shell (PR#39 `feat/canvas-f1-shell` @ 5da4ba4)

Reviewer: frontend-engineer/claude (FE architect, adversarial pass)
Date: 2026-06-06
Against: `fe-spec.md` (dual-signed F1-F2 spec) + `CHARTER.md` (ratified decisions)
Worktree under review: detached `5da4ba4` (== `origin/feat/canvas-f1-shell`)

## Verdict

**0 blockers, 4 majors, 4 minors.** Gates green. The content-agnostic engine seam (the
load-bearing littleorgans boundary) is clean and the prior build-blocker (artifact-redacted
image blocks) is correctly resolved. The four majors are spec-conformance gaps, not crashes:
each leaves the happy path working but violates an explicit spec clause or a ratified decision.

### Gates (all green)

- `cd www && pnpm lint` -> 0 (biome, 199 files)
- `cd www && pnpm typecheck` -> 0 (`tsc -b --noEmit`)
- `cd www && pnpm test` -> **404 passed / 404** (61 files, vitest)
- `cd api && uv run pytest tests/integration/test_static_canvas.py` -> **2 passed**

### Scope check (orchestrator's first question)

**transcript-chat + SSE are correctly IN F1.** `fe-spec.md` §12 F1 build list explicitly names
the `transcript-chat` viewer (backlog GET + SSE), the `session_id`/`seq` event reducer, and
spawn-or-focus on launch resolution. The ratified spawn-on-open decision (`CHARTER.md:43-50`,
`:30-32`) needs a chat pane to spawn into, so this is required F1 work, not F2 pulled early.
No F2 overrun observed: no tiling split-tree, no mode transitions. `efficientLayout.ts` exists
but is wired only to the stress harness (`SessionCanvasStressRoute.tsx:72`), not to live
spawn/close realign (live spawn uses static `rectForRef` cascade in `model/spawn.ts`), so F2's
"planner for spawn and close" is not active. Scope is correct.

---

## Majors

### MAJOR-1 — SPA fallback serves `index.html` for unknown `/api/*` paths

`api/src/transport_matters/main.py:51-64`

```python
class SpaStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or _looks_like_asset_path(path):
                raise
            return await super().get_response("index.html", scope)

def _looks_like_asset_path(path):
    return "." in Path(path).name or path.startswith("assets/")
```

The mount is at `/` and is evaluated after the `/api` router (`main.py:137,143`). An unknown
`/api/...` path matches no APIRoute, so it falls through to the catch-all mount. `_looks_like_asset_path("api/foo")`
is `False` (no dot in basename, not `assets/`), so the handler swallows the 404 and returns
`index.html` with **status 200**. API clients then receive HTML for any unknown/removed endpoint;
`requestApiJson` would try to parse HTML as JSON and throw a misleading error.

This violates **ratified open question 1** (`CHARTER.md:91-93`): "serve index.html for
**non-`/api`**, non-asset paths." The `/api` exclusion is part of the ratified contract and is
missing. `test_static_canvas.py:20-27` only covers `/assets/...`, so the `/api` case is untested
and the gap is invisible to CI.

Fix: re-raise when `path.startswith("api/")` (or check `scope["path"].startswith("/api")`), and
add a regression test asserting an unknown `/api/...` returns 404 JSON, not `index.html`.

### MAJOR-2 — All `meta` events are dropped from the transcript

`www/src/session-canvas/stream/mapIrToChat.ts:26-29`

```ts
function mapMetaEvent(event): TranscriptMessageModel | null {
  if (event.ir === null) return null;        // meta always has ir === null
  return buildMessage(event, "meta", [unknownBlock("meta", event.ir)]);
}
```

Meta events always carry `ir = null` (`session/ingest.py:101-119`, cited in `fe-spec.md` §10.4),
so `mapMetaEvent` returns `null` for **every** meta event and they never render. This contradicts
`fe-spec.md` §10.4 mapping order point 2, which requires meta to "render a metadata or system lane
item with `seq`, `native_turn_id`, `ts`, `model`, `source_path`, and `source_line`. Do not expect
`event.ir`." The behavior is locked by a test (`mapIrToChat.test.ts:18-20`, "drops meta events with
null ir"), so it is a deliberate deviation, not an oversight.

Impact: a "spatial transcript workbench" silently omits a documented class of events. If the
orchestrator intends meta to be deferred, the spec clause should be amended; otherwise build the
metadata-lane item from the event fields instead of returning `null`.

### MAJOR-3 — SSE gap is detected and displayed but never backfilled; banner never clears

`www/src/session-canvas/stream/sessionEventReducer.ts:36-44`,
`www/src/session-canvas/viewers/transcript-chat/TranscriptChatPane.tsx:38-50,60-72`

The reducer records `missingFromSeq` when a live event skips a seq, and `TranscriptStatus` renders
"gap from seq N". But nothing consumes `missingFromSeq` to perform the backfill. `fe-spec.md` §10.3
step 6 requires: "If `seq > highestSeq + 1`, fetch `GET /events?from_seq={highestSeq+1}&to_seq={seq-1}`,
merge missing events, then append the live event." That GET is not implemented, so a real gap leaves
a permanent hole in the transcript.

Worse, `missingFromSeq` never clears: `appendEvents` preserves it (`reducer.ts:36,44`) and only
`reset`/`buildState` zero it. So once a gap is recorded (even a transient/spurious one), the
"gap from seq N" banner stays forever until the pane remounts. `sessionEventReducer.test.ts:27-35`
asserts the gap is *recorded* but there is no test/impl for the *backfill request* that §13 calls for.

Practical trigger frequency is low (the backend yields ordered events from `last_seq+1`), but the
stuck banner is a definite UX defect regardless. Fix: on `missingFromSeq != null`, fire a bounded
backfill query for `[missingFromSeq .. highestSeq-1]`, merge, and clear the marker.

### MAJOR-4 — 60fps proof is not instrumented; no automated stress spec

`www/src/session-canvas/perf/SessionCanvasStressRoute.tsx:1-111`

The harness route exists and renders synthetic memoized panes at 1/2/4/8/16/30 counts, but it
**never measures frames**: `FrameMeter` (`engine/perf/frameMeter.ts`) is invoked only by its own
unit test (`frameMeter.test.ts`) and is not wired into the harness (no `requestAnimationFrame`
sampling around spawn/close/drag/resize/pan/zoom). The automated `perf/sessionCanvasStress.spec.ts`
named in `fe-spec.md` §3.2 (file plan) and §13 (verification plan) is **absent** from the PR.

So the harness is a manual visual toy that proves nothing. This fails `fe-spec.md` §7.4 + §12 F1
acceptance ("Stress harness proves initial pane motion target before signoff"; "a slice cannot
pass if it introduces motion without updating the harness") and re-opens old finding #7 ("60fps
claim unproved"), which the spec claimed F1 would resolve. Fix: instrument `FrameMeter` around the
transitions and land `sessionCanvasStress.spec.ts` with the p95-frame assertion.

---

## Minors

### MINOR-1 — Backlog is single-page; §10.2 infinite query not implemented

`www/src/session-canvas/hooks/useSessionEvents.ts:5-10`, `api/sessionEvents.ts:48-56`

`useSessionEvents` is a plain `useQuery` (`from_seq` omitted -> 0, `limit` 500) that ignores
`next_from_seq`. `fe-spec.md` §10.2 specifies an infinite query that appends pages while
`next_from_seq` is non-null. In practice the full history still loads because the SSE opens with
`last_seq = highestSeq` (=499 after page 1) and the backend replays everything from `last_seq+1`
as catch-up (§10.3) — so this is not a correctness hole, but it diverges from the documented
approach and pushes a potentially large catch-up onto a one-event-at-a-time SSE for long sessions.

### MINOR-2 — Turn with empty `parts` has no `search_text` fallback

`www/src/session-canvas/stream/mapIrToChat.ts:21-23`

A `turn` whose `ir.parts` is an empty array renders a header-only message with zero blocks.
`fe-spec.md` §10.4 mapping order point 5 requires: "If a turn has no renderable parts, render
`search_text` when present." Not honored.

### MINOR-3 — Extractor contract name/shape differs from the spec

`fe-spec.md` §10.4 documents `mapSessionEventToChatItems(event): ChatItem[]`; the impl ships
`mapEventToTranscriptMessage(event): TranscriptMessageModel | null` (one message with `blocks[]`
rather than `ChatItem[]`). Functionally equivalent (one event -> one role-keyed message), but the
public contract drifts from the spec; reconcile the spec or the name.

### MINOR-4 (nit) — `index.css` is now 1250 LOC (+431)

`www/src/index.css`. The CHARTER LOC gate scopes `<=700` to "www/ TS and api/ py"
(`CHARTER.md:149`), so CSS is technically out of that gate, but `fe-spec.md` §5.1 already offered
the `www/src/styles/tokens.css` extraction seam. Consider extracting the canvas token/style block
to keep the file maintainable.

---

## What is done well (credit)

- **Content-agnostic engine seam is clean (the load-bearing one).** `PaneNode` is geometry/lifecycle
  only (`engine/types.ts:18-24`); `PaneFrame` imports no session/viewer code (`PaneFrame.tsx:1-5`);
  `LayoutCanvas` renders via the `renderPane(paneId)` render prop (`LayoutCanvas.tsx:12,59`); the
  session-canvas joins `PaneRecord` -> viewer outside the engine (`CanvasSurface.tsx:44-72`). grep
  confirms zero `engine -> session-canvas` imports and zero upward content imports. littleorgans
  reuse boundary intact.
- **Prior build-blocker resolved:** artifact-redacted image blocks `{artifact_hash, media_type}`
  are mapped (`mapIrToChat.ts:95-111`), rendered as a placeholder keeping the F3 fetch seam
  (`TranscriptMessage.tsx:52-62`), and tested (`mapIrToChat.test.ts:22-34`). IR mapping branches on
  `kind` first and renders `parts` under `event.role` (`mapIrToChat.ts:18-23`).
- **SSE reconnect contract honored:** `es.close()` before reopen (`useSessionEventStream.ts:43,48-51`),
  fresh `EventSource` with `?last_seq={highestSeq}` (`sessionEvents.ts:58-69`), manual reconnect (no
  reliance on native retry), dedup by seq in the reducer Map (`sessionEventReducer.ts:35-43`).
- **Launch auto-resolve matches the lookup rule:** run_id preference then newest active
  `workspace_hash` match (cli constrained by the query), pending state, 1s poll until resolved
  (`launchResolution.ts:11-25`, `useLaunchSession.ts:9-26`).
- **Route + legacy preservation:** `selectRootRoute` + lazy code-split; legacy `App` retained, not
  deleted (`main.tsx:7-25`, `route.ts:10-12`). SPA-fallback exists for `/canvas` (modulo MAJOR-1).
- **DRY honored:** reuses `ContentBlocks` `blockKey`/`blockSummary` (`TranscriptMessage.tsx:1`);
  does **not** reuse `exchangeStreamEvents.ts` (grep clean); canvas state is a Zustand store matching
  `www/src/stores` with persistence correctly deferred to F2 (`canvasStore.ts`).
- **Repo invariants:** every changed TS/py file < 700 LOC; functions < 150 LOC; picker covers all
  required states incl. keyboard nav + "Waiting for live {cli} session" + live badge
  (`SessionPickerPane.tsx`).

---

## Fix round verification — `ae87e34` (2026-06-06)

Re-reviewed only the delta `5da4ba4..ae87e34` (13 files, +375/-53; **engine/** untouched).
Verdict: **fixes verified clean.** All 4 majors + MINOR-2/3 resolved with tests; engine seam intact.

| Item | Status | Evidence |
| --- | --- | --- |
| MAJOR-1 SPA `/api` swallow | FIXED | `main.py:57-72` adds `_looks_like_api_path(path, scope)` (checks `scope["path"]` == `/api` or startswith `/api/`) to the re-raise guard; new `test_unknown_api_path_does_not_use_spa_fallback` asserts 404 + `application/json` + no `<html>`. `Response`/`Scope` moved into `TYPE_CHECKING` (TC002 resolved; `ruff check src/` green). |
| MAJOR-2 meta dropped | FIXED | `mapMetaEvent` now returns a metadata-lane message (`role:"metadata"`) built from `kind/seq/native_turn_id/ts/model/source_path/source_line` (`mapIrToChat.ts`); drop-test replaced with a render-assertion test. |
| MAJOR-3 gap not backfilled / stuck banner | FIXED | `useSessionEventStream` gains `dispatchGapBackfill` -> `GET /events?from_seq&to_seq`, merges `[...backfill, live]`; `missingFromSeq` is now **derived** via `findMissingFromSeq(events)` so it clears after merge. Two new tests: reducer gap-clear + stream backfill (asserts the exact backfill GET then `[0,1,2]`). |
| MAJOR-4 60fps unproven | FIXED | `FrameMeter` wired into the stress route via `useStressFrameMeter` around spawn/close/focus/drag/resize/pan/zoom; readout exposes `data-stress-{action,frames,p95-frame}`; new `tests/perf/sessionCanvasStress.spec.ts` drives all ops and asserts `p95 <= 50ms`; `playwright.config.ts` adds a `perf` project that runs against a production `pnpm build && pnpm preview`. |
| MINOR-2 search_text fallback | FIXED | `fallbackBlocks(event)` renders `search_text` when a turn has empty parts; test added. |
| MINOR-3 extractor name | FIXED | Public API is now `mapSessionEventToChatItems(event): ChatItem[]` per spec §10.4; call sites + tests updated to `flatMap`. |

Deferred by orchestrator (not re-flagged): MINOR-1 (infinite query), MINOR-4 (css size).

Gates (re-run at `ae87e34`):
- `www`: `pnpm lint` 0 (200 files), `typecheck` 0, `vitest` **407 passed / 407**.
- `api`: `ruff format --check src/` + `ruff check src/` + `mypy src/` all green; canvas `test_static_canvas.py` **3/3** (incl. new `/api` 404 case).
- `api just ci` exits 1 **only** from 18 `MissingDatabaseConfigError` collection errors (session-store DB tests; no postgres / `TRANSPORT_MATTERS_TEST_DATABASE_URL` in the review sandbox). **1128 passed, 0 assertion failures**, none in the canvas delta. A DB-configured runner is needed to drive `just ci` to exit 0.
- The perf playwright spec was reviewed statically (present, p95<=50ms assertion, `perf` project) but not executed locally (needs a browser + production preview build).
