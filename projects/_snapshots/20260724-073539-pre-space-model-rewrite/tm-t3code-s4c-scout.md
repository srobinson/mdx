---
title: Slice 4c Scout — real run lifecycle on the Runtime server over a stubbed spawn envelope
type: projects
tags: [transport-matters, t3code, p1, slice-4c, runtime, run-manager, pty, terminal, scout]
summary: Build plan for slice 4c. RunManager service in @tm/runtime wires PtyPort -> ScrollbackRing -> TerminalFanout -> WS, spawned from a stubbed CapturePort envelope. POST /runs spawns a real PTY, WS terminal streams with multi-viewer resume-from-seq, POST /runs/{id}/terminate is grace-then-force. No mitmproxy, no CaptureRpcClient, no Python changes.
status: active
source: fable scout pane (transport-matters:general:5:2.1), brief from orchestrator 5:1.1
created: 2026-07-07
---

# Slice 4c Scout — create + attach over a FAKE capture envelope

Design of record: `tm-t3code-p1-spec.md` §8 slice 4c. This doc reconciles it against
main @ f8fedaa (slices 0-4b merged) and hands the engineer a file-by-file plan.
Citations are file + symbol, never line numbers.

**4c in one sentence:** replace the s1 echo skeleton in
`packages/runtime/src/server/runtimeRouter.ts` with a real `RunManager` service that
spawns a PTY agent from a stubbed spawn envelope, streams it over the terminal WS with
multi-viewer resume-from-seq, and terminates it grace-then-force.

**No Python files change in 4c.** Route cutover and `pty_session.py` deletion are 4e.
`CaptureRpcClient` stays unwired (4d). All changes are in `packages/runtime` +
`packages/gateway` wiring.

---

## 1. Entry-point map

### TS, already built — reuse, do not re-invent

| File | Symbols 4c consumes |
| --- | --- |
| `packages/runtime/src/server/runtimeRouter.ts` | `createRuntimeRouter`, `RuntimeRunView`, `RuntimeRunState`, `RuntimeRunEndReason`, query helpers (`ownerFromQuery`, `cursorFromQuery`, `limitFromQuery`, `stateFromQuery`, `terminalSizeFromQuery`). The s1 `createInMemoryRuntimeRunStore` + echo WS is what 4c **deletes**. |
| `packages/runtime/src/adapters/NodePtyAdapter.ts` | `NodePtyAdapter` (`PtyPort` impl, `encoding: null` byte fidelity, 64 KiB pre-subscriber buffer, `onExit` replay for late subscribers, `isTerminalGoneError` swallowing on write/resize/kill after exit). |
| `packages/runtime/src/domain/terminal/ScrollbackRing.ts` | `ScrollbackRing`, `PtyChunk`, `DEFAULT_SCROLLBACK_BYTES`. Owned by the fanout; RunManager never touches it directly. |
| `packages/runtime/src/service/TerminalFanout.ts` | `TerminalFanout` (`attach`/`append`/`detach`/`closeAll`/`closeAttachment`), `AttachedTerminal` (`scrollback` snapshot + `startSeq`), `AttachmentClosed`, `TerminalQueueTakeCancelledError`, close codes `RUN_ENDED_CLOSE_CODE`/`SLOW_VIEWER_CLOSE_CODE`/`RUN_START_FAILED_CLOSE_CODE`, `DEFAULT_ATTACHMENT_QUEUE_SIZE`. `TerminalQueue` class is module-exported but **not in the barrel** (deliberate, 4b fix round); consume `attachment.queue` structurally, re-export the class only if a public signature must name it. |
| `packages/runtime/src/ports.ts` | `PtyPort`/`PtySession`/`PtySpawnInput`/`PtyExitEvent`; `CapturePort`/`PrepareCaptureInput`/`CapturedRunSpawnSpec`/`CaptureClientSpec` — the envelope **types** are the stub's contract even though `CaptureRpcClient` stays unwired. |
| `packages/runtime/src/index.ts` | The single barrel. Every new public symbol lands here (import-graph boundary test in `www/packages/shell/src/testSupport/importGraphBoundary.test.ts` fails closed on deep imports). |
| `packages/common/src/terminalContract.ts` | `serializeRunTerminalReadyFrame`, `serializeRunTerminalScrollbackEndFrame`, `serializeRunErrorFrame`, `parseTerminalResizeFrameText`, `terminalSizeFromQueryValues`, dimension constants. Single wire-contract source; add nothing run-specific outside it. |
| `packages/gateway/src/app.ts`, `main.ts` | `buildGateway` mounts the runtime router at `RUNTIME_CONTEXT_PREFIX = "/v1"`; `runGatewayProcess::createDefaultRuntimeRouterDeps` is where real deps get constructed; `installShutdownHandlers`/`closeGatewayResources` is where `RunManager.close()` must hook. |

### Python parity references (semantics, not line-for-line)

| File | What 4c re-expresses |
| --- | --- |
| `api/src/transport_matters/run_manager.py::RunManager` | The service shape: `spawn`/`get`/`list`/`attach`/`detach`/`terminate`/`close`; `_start_run_terminal` (PTY spawn + state RUNNING), `_drain_run`/`_handle_pty_readable` (PTY bytes -> `terminal_output.append`), `_teardown_run` (state transitions + close-all + kill + lease close), `_TERMINAL_STATES`. |
| `api/src/transport_matters/api/v1/run_routes.py` | `create_run`/`list_runs`/`get_run`/`terminate_run`/`run_terminal_socket`; `run_terminal_ready_frame` (replayedBytes = sum of snapshot chunk lengths, truncated from the ring); `bridge_attached_run_terminal` (ready -> snapshot bytes -> `scrollback-end` -> concurrent output/input pumps -> detach in finally); `_send_attachment_output` (PtyChunk -> binary; `AttachmentClosed` with `SLOW_VIEWER_CLOSE_CODE` -> `run.error attachment_overloaded` then close); `_PUBLIC_STATE_ALIASES` (STARTING surfaces as RUNNING); `_RUN_MANAGER_HTTP_STATUS`. |
| `api/src/transport_matters/api/v1/terminal_bridge.py::receive_websocket_input` | Input contract: binary frame -> PTY write; text frame -> resize control frame; invalid text -> `run.error invalid_terminal_control_frame` + WS close 1008. |
| `api/src/transport_matters/pty_session.py::terminate_terminal_pty`, `terminate_process_group` | Grace-then-force reference: SIGTERM -> wait `CHILD_EXIT_TIMEOUT_S = 1.0` -> SIGKILL -> wait 1.0s -> proceed regardless. |
| `www/packages/canvas/src/model/capturedRunStore.ts::stopRun` | Canvas driver: `terminateRun(runId)` from `@tm/core` `transport.ts::terminateRun` = `POST /v1/runs/{runId}/terminate`, **no body, no owner query**, void, best-effort (`.catch(() => {})`). The existing TS route shape already matches (owner defaults to `"local"` on both create and terminate, so default-owner round-trips). |
| `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts` | Client contract: sends binary input + `{"type":"resize",cols,rows}` text frames; receives binary output + JSON text frames (ready/scrollback-end/error), `binaryType = "arraybuffer"`. |

---

## 2. The stub spawn envelope

**Seam decision: RunManager depends on `CapturePort` (already in `ports.ts`), and 4c
wires a stub implementation of it.** This mirrors Python's injectable
`RunManager(prepare_run=prepare_captured_run)` and makes 4d a one-line swap
(`StubCaptureAdapter` -> `CaptureRpcClient`) with zero RunManager churn. Do not invent
a second, narrower envelope type; `CapturedRunSpawnSpec` is the envelope.

New adapter `packages/runtime/src/adapters/StubCaptureAdapter.ts` implementing
`CapturePort`:

- `prepareCapture(input)` mints `runId` (`crypto.randomUUID` — in the real system the
  capture side mints run ids, so the stub must too, keeping the 4d seam identical) and
  returns a `CapturedRunSpawnSpec` with:
  - **Real (consumed by RunManager):** `runId`; `client` (`argv`, `env`, `cwd`,
    `name`/`displayName`); `harness`; `workingDir`.
  - **Stubbed (present to satisfy the type, unused in 4c):** `proxyPort: 0`,
    `webPort: null`, `mitmdumpLog: ""`, `storageDir: ""`, `launchEnv: {}`,
    `managedSession: null`.
- `releaseCapture(runId)` -> `true` (no-op, idempotent — parity with
  `CapturedRunLease.close`). RunManager **must still call it** on every end path so the
  4d ordering (PTY exit -> release capture) is already exercised.
- `captureHealth(runId)` -> `{ runId, alive: true }`.
- Constructor takes a client-spec factory
  `(input: PrepareCaptureInput) => CaptureClientSpec` so tests inject `/bin/cat`-class
  argv and the gateway default can spawn the bare harness binary (uncaptured) if wanted.
  No hidden default argv baked into the adapter.

---

## 3. RunManager service: responsibilities + wiring

New file `packages/runtime/src/service/RunManager.ts`. Options:
`{ ptyPort: PtyPort, capturePort: CapturePort, clock: Clock, scrollbackBytes?,
attachmentQueueSize?, graceMs? (default 1000) }`.

Per run it owns: `owner`, the `RuntimeRunView` fields, the `PtySession | null`, one
`TerminalFanout`, the envelope, and an end-settlement promise (for terminate
idempotency).

**Create (eager spawn — locked by the brief):**
`POST /v1/runs` -> `capturePort.prepareCapture` -> envelope -> `ptyPort.spawn({ argv:
client.argv, env: client.env, cwd: client.cwd, cols, rows })` -> subscribe:

- `session.onData(bytes)` -> `fanout.append(bytes, { emittedAt: clock.now() })`;
  overloaded attachment ids are already closed by the fanout (slow-viewer path).
- `session.onExit` -> `endRun("natural-exit")` -> state `EXITED`, `endReason` omitted,
  `closeAll({ code: RUN_ENDED_CLOSE_CODE, retryable: false, message })`, then
  `capturePort.releaseCapture(runId)`.
- Success -> state `RUNNING`, return view. Failure of `prepareCapture` or `spawn` ->
  `releaseCapture` (idempotent), reject create with `launch_failed`; no run registered
  (parity with Python `_spawn_new` rollback: a failed create leaves no run behind).

**Attach:** guard exactly like Python `RunManager.attach` — `TERMINATED` ->
`run_terminated`; other terminal states -> `run_not_attachable`; else
`fanout.attach({ cols, rows, attachmentId })` -> `AttachedTerminal`. Each attach
snapshots independently: replayed chunks all have `seq < startSeq`, the live queue
delivers exactly `seq >= startSeq` — that IS resume-from-seq over the live socket, no
gap, no dup, any number of viewers.

**Write / resize:** `write(runId, bytes)` -> `session.write`; `resize(runId, cols,
rows)` -> `session.resize`. One PTY per run; last viewer resize wins (Python behaves
identically — any viewer's control frame sets the master winsize).

**Terminate (`POST /v1/runs/{id}/terminate`, NOT DELETE):** see §4.

**close() (manager shutdown):** mark closed, terminate every non-terminal run with
reason `"shutdown"`. Re-check the closed flag after every await inside spawn (cm lesson
019eac3f: the Python manager leaked runs registered mid-shutdown because `_closed` was
only checked at entry).

**Router rewire (`server/runtimeRouter.ts`):** `RuntimeRouterDeps` becomes
`{ runManager: RunManager }`. Keep the existing query parsing, owner scoping
(`?owner=`, default `"local"`), offset pagination, and 400 validations verbatim — the
existing router tests pin them. `CreateRunBody` gains optional
`terminal: { cols, rows }` (Python `CreateRunRequest.terminal`; eager spawn needs
dimensions at create; default 80x24 via the shared contract constants). Map
`RunManagerError` codes to HTTP like Python `_RUN_MANAGER_HTTP_STATUS`:
`run_terminated`/`run_not_attachable` 409, `launch_failed` 500, `run_manager_closed`
503, not-found 404.

**Terminal WS handler (the new core):**

1. Resolve run (owner-checked) or `run.error run_not_found` + close 1008; validate size
   via `terminalSizeFromQueryValues` or `run.error invalid_terminal_size` + close 1008
   (both already in the s1 route — keep).
2. `attach` -> send ready frame (`serializeRunTerminalReadyFrame`; `replayedBytes` =
   sum of snapshot chunk byte lengths, `truncated` from `fanout.scrollback.truncated`)
   -> send each snapshot chunk as a **binary** frame -> send
   `serializeRunTerminalScrollbackEndFrame()`. **The s1 stub omitted scrollback-end;
   Python sends it (`include_scrollback_end=True`) and the canvas client parses it —
   4c must add it.**
3. **Reader loop (carries the two 4b notes):** one `AbortController` per socket.
   ```
   while true:
     if attachment.closedReason !== null && attachment.queue.size === 0: break  // synthesize close
     item = await attachment.queue.take({ signal })
     if item is PtyChunk: socket.send(item.data, binary)
     else (AttachmentClosed): if code === SLOW_VIEWER_CLOSE_CODE send run.error
          attachment_overloaded; break
   ```
   - **R1 close-drop:** `closeAttachment` pop-then-`tryPush` drops the
     `AttachmentClosed` item when the queue is full (faithful Python parity, kept in
     4b). The drop can only happen while the queue is full, which means the reader has
     items to drain; once drained, the check-before-await on `closedReason` (set
     synchronously before the push) catches the close. Race-free, no hang.
   - **Abandoned-waiter loss:** exactly one reader loop per attachment; **every**
     `take` passes the socket's `AbortSignal`; `TerminalQueueTakeCancelledError` ->
     clean exit. Never fire a take you might not await.
4. **Input pump:** socket `message` -> binary payload -> `runManager.write`; text ->
   `parseTerminalResizeFrameText` -> `runManager.resize`; unparseable text ->
   `run.error invalid_terminal_control_frame` + close 1008 (Python
   `receive_websocket_input` parity).
5. Socket `close` -> `controller.abort()` -> `runManager.detach(runId, attachmentId)`
   (the `finally` of the handler, mirroring `bridge_attached_run_terminal`).
6. Run end closes every viewer: `closeAll(run-ended)` items flow through each queue and
   each reader loop closes its socket (normal closure 1000).

**Wire vocabulary (freeze now, 4b review note):** `run.error` codes snake_case
(`run_not_found`, `invalid_terminal_size`, `invalid_terminal_control_frame`,
`attachment_overloaded`, `run_terminated`, `run_not_attachable`); internal
`AttachmentClosed` codes kebab-case (`run-ended`, `retryable-overload`,
`run-start-failed` — never sent raw on the wire); WS close codes numeric 1000/1008.
This is exactly the inherited Python vocabulary; 4c freezes it into the TS contract.

---

## 4. Grace-then-force terminate semantics (preserve)

Python reference `terminate_process_group`: SIGTERM to the group -> `wait(1.0s)` ->
SIGKILL to the group -> `wait(1.0s)` -> proceed regardless (exit code from `poll()`).

TS 4c: `session.kill("SIGTERM")` -> race `onExit` against a `graceMs` (default **1000,
parity with `CHILD_EXIT_TIMEOUT_S`**, injectable for tests) timer -> on timeout
`session.kill("SIGKILL")` -> bounded wait again -> settle regardless.
`NodePtySession.kill` is already a no-op after exit and swallows gone-terminal errors,
so the force path is safe to fire unconditionally.

State transitions (single source: Python `_teardown_run`):

- `RUNNING -> TERMINATING -> TERMINATED`, `endReason: "explicit"` (terminate route) or
  `"shutdown"` (manager close).
- `RUNNING -> EXITED`, `endReason` omitted (natural PTY exit; Python nulls end_reason
  for `natural-exit`).
- `FAILED` exists in the public union; in eager-spawn 4c a spawn failure rejects the
  create instead of registering a FAILED run, and a mid-run PTY error surfaces as exit
  (NodePtySession maps terminal errors to `exit(1)`), so FAILED may be unreachable in
  4c. Keep the state; do not manufacture reachability.
- Terminate is idempotent: a second terminate (or terminate-after-exit) awaits/returns
  the settled view (Python `_teardown_run` early-returns on terminal state + closed
  terminal). Ordering on every end path: close attachments -> kill/settle PTY ->
  **then** `releaseCapture(runId)` — spec §4 rule 2/3, exercised now against the stub
  so 4d only swaps the adapter.

**Known 4c drift (accepted, feeds S5):** `node-pty` `kill()` signals the **pid only**;
Python `killpg`s the process **group**. Grandchildren (e.g. a codex agent's MCP
children) can orphan — live dogfood evidence cm 019f3c7f. Spawn-edge group/Job
ownership is slice 5 scope; 4c documents it and does not half-build it. On Windows
ConPTY, signal strings degrade to unconditional kill (grace collapses to force) —
acceptable, note in code.

---

## 5. Build plan for the engineer

### New files

1. `packages/runtime/src/service/RunManager.ts` — the service per §3/§4. Exports
   `RunManager`, `RunManagerError` (with a `code` union: `launch_failed`,
   `run_terminated`, `run_not_attachable`, `run_manager_closed`; not-found modeled like
   the current router's null returns or a `RunNotFoundError` — match Python's split),
   options interface. Keep it well under 700 lines; the WS pump does NOT live here.
2. `packages/runtime/src/adapters/StubCaptureAdapter.ts` — `CapturePort` stub per §2.
3. `packages/runtime/src/server/runTerminalConnection.ts` (or similar) — the WS
   attach/reader/input pump from §3 step 2-6, kept out of the router so
   `runtimeRouter.ts` stays a thin route table (700-line hard limit; the router is
   already ~285).

### Modified files

4. `packages/runtime/src/server/runtimeRouter.ts` — deps become `{ runManager }`;
   **delete** `createInMemoryRuntimeRunStore`, `RuntimeRunStore`, `StoredRuntimeRun`
   and the echo WS completely (DRY: no parallel path left behind); `CreateRunBody` +
   route handlers call the RunManager; error mapping per §3.
5. `packages/runtime/src/index.ts` — export `RunManager`, `RunManagerError`,
   `StubCaptureAdapter` + new types; **remove** the deleted stub-store exports.
   Re-export `TerminalQueue` only if a new public signature names it.
6. `packages/gateway/src/main.ts` — `createDefaultRuntimeRouterDeps` constructs
   `RunManager` (NodePtyAdapter + StubCaptureAdapter + system clock);
   `closeGatewayResources` also closes the RunManager (PTYs must die on gateway
   shutdown — this is the `"shutdown"` end-reason path).
7. `packages/gateway/src/app.test.ts` / `main.test.ts` — fixture updates for the new
   deps shape (fixture RunManager over a fake PtyPort; the gateway contract test stays
   port-less `fastify.inject()`).

### Test plan (Vitest; runtime devDeps already carry `ws` + `@types/ws`)

- `service/RunManager.test.ts` (fake `PtyPort`/`CapturePort`, tiny `graceMs`):
  create -> RUNNING + envelope consumed; onData -> fanout append; natural exit ->
  EXITED + close-all + releaseCapture called; terminate -> TERMINATING -> TERMINATED,
  SIGTERM then SIGKILL after grace, releaseCapture ordering after PTY settle;
  terminate idempotency (double terminate, terminate-after-exit); attach guards
  (terminated/ended); spawn failure -> create rejected + releaseCapture + no run
  registered; close() terminates all with `"shutdown"`; closed-flag re-check after
  awaits (spawn racing close).
- `server/runtimeRouter.test.ts` (existing pattern: `app.inject()` for HTTP,
  `app.listen({ port: 0 })` + real `ws` client for the socket; fake PtyPort for
  determinism): ready frame -> snapshot binary replay -> **scrollback-end** ordering;
  **multi-viewer resume-from-seq** (viewer A streams live, bytes emitted, viewer B
  attaches late -> exact replay + live continuation, no dup/gap, both then receive the
  same live bytes); input pump (binary -> PTY write; resize frame -> resize; invalid
  text -> `invalid_terminal_control_frame` + 1008); slow-viewer overload -> drain
  yields `attachment_overloaded` error then close, other viewer unaffected; terminate
  while sockets open -> both sockets close (run-ended path), response view TERMINATED;
  run_not_found / invalid_terminal_size preserved; existing create/list/get/paginate
  assertions carried over to the RunManager-backed store.
- One end-to-end round trip over a **real** `NodePtyAdapter` (spawn `/bin/cat` via the
  stub envelope: WS binary in -> same bytes out; terminate kills the real process —
  assert pid dead). Everything else uses fakes; 4a already proves the adapter.

### Gates (verbatim — repo recipes, confirmed against the root justfile)

```
just check
just test
```

(`just test` runs `pnpm --filter @tm/runtime test` and the gateway/shell/api suites
serially. `just ci` does **not** exist — do not cite it. No bare tsc/vitest as the
gate; targeted runs are inner-loop extras only.)

---

## 6. Drift / risks the build must reconcile

1. **pid-kill vs killpg** — §4. Accepted 4c drift, S5 owns the spawn-edge group/Job.
2. **Eager spawn vs Python `start_on_attach=True`** — Python creates in STARTING and
   spawns the PTY on first attach; the brief locks eager spawn at POST. Public surface
   is identical (Python aliases STARTING -> RUNNING via `_PUBLIC_STATE_ALIASES`), and
   pre-attach output now lands in scrollback and replays. Consequence: create must
   accept terminal dimensions (§3). No STARTING member is needed in the TS union.
3. **scrollback-end frame missing from the s1 stub** — must be added or the canvas
   client's replay handling diverges from Python.
4. **R1 close-drop + abandoned-waiter** — handled structurally by the reader-loop
   design (§3 step 3); do not "fix" the fanout drop itself, it is pinned faithful.
5. **Owner scoping and plain-offset cursors are TS-only s1 decisions** (Python
   `list_runs` has no owner param and encodes filters into cursors). Keep the TS
   behavior; cutover parity is a 4e question, not 4c.
6. **Out of 4c entirely** (Python keeps serving the real canvas until 4e): worktree
   resolution via SpaceStore, `continueFromSessionId` continuation, `idempotencyKey`,
   runtime templates, OSC 10/11 color responder, viewerless idle reaping, run
   lifecycle event emission (SessionWriter), shared-proxy web runtime. Do not stub
   route parameters for these into the TS surface yet.
7. **`FAILED` possibly unreachable** in 4c (§4) — fine; the union is already public.
8. **Wire vocabulary freeze** (§3) — snake_case error codes / kebab-case close codes /
   numeric WS closes; decide-by-doing now, it is the contract 4d/4e inherit.
