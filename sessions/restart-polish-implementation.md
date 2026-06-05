---
title: Restart polish implementation
type: sessions
tags: [backend, desktop, canvas, captured-run, restart]
summary: Implemented hosted desktop quit on backend loss and robust per-id captured-run reconciliation before canvas attach.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented restart polish on `feat/desktop-detach` in four commits:

- `a4a1dc3` `fix(desktop): quit hosted app on backend loss`
- `39a7756` `fix(canvas): prune stale captured runs before attach`
- `c5c6933` `fix(canvas): reconcile captured runs by id`
- `9999189` `fix(canvas): keep starting captured runs attachable`

Slice A changes hosted Electron restart behavior. Hosted backend liveness now quits the hosted app after the failure threshold instead of only closing the window. Hosted window lifecycle also has a hosted only `quitOnWindowAllClosed` option, while the foreground lifecycle keeps the default macOS app survival behavior.

Slice B changes `/canvas` restart behavior. `SessionCanvasRoute` gates only `captured-run` pane content while it reconciles remembered run ids. The fix rounds replaced first page `listRuns()` pruning with per remembered id `GET /v1/runs/{id}` lookup. The attachability predicate now matches the backend `RunManager.attach` contract: STARTING and RUNNING are attachable. Missing, EXITED, FAILED, TERMINATED, and TERMINATING remembered runs are pruned before terminal content mounts. Timeout or transient lookup failure releases the gate and preserves local state.

The captured run store shares one `forgetRunRecord()` helper between terminating `stopRun()` and non terminating `dropRun()`. Canvas and route tests share captured run fixtures through `www/src/session-canvas/testUtils.tsx`.

## API Contract

No backend API shape changed.

Existing backend API used by the frontend:

```typescript
// GET /v1/runs
interface ListRunsResponse {
  items: RunView[];
  nextCursor: string | null;
}

// GET /v1/runs/{id}
interface GetRunResponse {
  run: RunView;
}

interface RunView {
  runId: string;
  workspaceId: string;
  sessionId: string;
  harness: "claude" | "codex";
  state: "STARTING" | "RUNNING" | "TERMINATING" | "TERMINATED" | "EXITED" | "FAILED";
  endReason?: "explicit" | "idle-timeout" | "shutdown" | "deploy-restart";
  error?: string;
  createdAt: string;
}
```

Frontend contracts added or updated:

```typescript
interface RunLookupOptions {
  signal?: AbortSignal;
}

function getRun(runId: string, options?: RunLookupOptions): Promise<RunView | null>;

type CapturedRunReconciliation = "pending" | "released";

interface CanvasSurfaceProps {
  capturedRunsReady?: boolean;
  launch: CanvasLaunchContext;
  launchStatus: LaunchResolutionStatus;
  launchSessionId: string | null;
}

interface CapturedRunState {
  dropRun(runKey: CapturedRunKey): void; // local forget, no terminate request
}

interface CanvasStoreState {
  dropCapturedRunPane(runKey: string): void; // remove open and docked refs without close lifecycle
}
```

## Database Changes

None.

## Security Considerations

- No new public endpoint or auth surface.
- `dropRun()` is intentionally non terminating, so a stale local browser record cannot send a doomed terminate request to a fresh backend.
- Reconciliation deletes local state only after successful per id lookups prove a remembered run is missing or non attachable.
- STARTING is preserved because the backend can attach it and start the terminal during attach.
- Timeout and transient lookup failure keep local state and retry on the next route mount.
- The captured run content gate prevents the first render from opening `WS /v1/runs/{id}/terminal` for stale or terminal remembered ids.

## Performance Notes

- Canvas startup issues one bounded `GET /v1/runs/{id}` lookup per remembered captured run id.
- Reconciliation is bounded by a 3 second timeout.
- The per id lookup avoids first page pagination false prunes when the live run is beyond page 1 of `GET /v1/runs`.
- Non captured panes render immediately while reconciliation is pending.
- Candidate pruning snapshots `runKey -> runId` before the request, so runs spawned during the round trip are not pruned.
- Layout replanning runs only for removed captured run panes and uses existing canvas planning primitives.

## Verification

Observed final attachability fix gates:

- `cd www && pnpm test -- src/session-canvas/SessionCanvasRoute.test.tsx` passed. Vitest ran the full web suite, `140` files and `1003` tests, including `keeps a remembered STARTING captured run because backend attach accepts it`.
- `just check` passed. Desktop typecheck and `8` files with `41` tests passed; web format, lint, and typecheck passed with the existing `pane-dock.css` important style warnings; API ruff and mypy passed.
- `cd www && just test` passed. Web `140` files and `1003` tests passed.

Observed prior fix round gates:

- `cd www && just test` passed. Web `140` files and `1002` tests passed.
- `just check` passed. Desktop typecheck and `8` files with `41` tests passed; web format, lint, and typecheck passed with the existing `pane-dock.css` important style warnings; API ruff and mypy passed.
- `just test` passed. Desktop `8` files and `41` tests passed; web `140` files and `1002` tests passed; API `1666` tests passed.

Earlier Slice A and first Slice B verification:

- `just check` passed.
- `just test` passed with the earlier web count before the fix rounds.
- `cd desktop && just check && just package-smoke` passed. Package smoke returned `status: "main-window-created"`.
- `cd www && just test` passed.

Live smoke from the first implementation round:

- `just channel-restart preview` passed twice as requested, and a third controlled restart was run to prove the post patch app launcher exits.
- Preview backend pid advanced `76101 -> 77079 -> 79134`; no port conflict occurred.
- Prior post patch Electron launcher pid `77096` was gone after the controlled restart.
- `GET http://127.0.0.1:8798/health` returned `{"status":"ok"}`.
- `GET http://127.0.0.1:8798/v1/runs` returned `{"items":[],"nextCursor":null}`.
- A headless Playwright load of `http://127.0.0.1:8798/canvas` saw no `/v1/runs/{id}/terminal` WebSocket request, no failed HTTP responses, no console warnings or errors, and no failed reattach text.
- Pre existing stale preview Electron launchers `36638` and `38512` remained from before the patched run; the post patch launcher lifecycle was verified separately.

## Open Items

- Pre existing stale preview Electron launchers from before this patch may need manual cleanup outside the code change.
- The current solution validates and prunes process resident run ids. Durable run reconnect remains out of scope until there is a supervisor contract for process identity, PTY handles, fanout, leases, and scrollback rehydration.
