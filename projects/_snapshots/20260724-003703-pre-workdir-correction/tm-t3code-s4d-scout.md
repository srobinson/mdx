# t3code P1 — Slice 4d scout: real capture RPC + two-lifecycle teardown

Scouted against main @ 83ba36a (slices 0-4c merged). Design of record:
`~/.mdx/projects/tm-t3code-p1-spec.md` §2c (capture RPC seam) + §4 (two coupled
lifecycles). No code edits made. Symbols cited as file + symbol, never lines.

**One-line read: 4d is a thin wiring slice on the create path (the s4c seam pays off
exactly as designed) plus one genuinely new lifecycle feature: the §4 rule-4
capture-crash DEGRADED path, which nothing in the codebase implements today.**

---

## 1. Actual-state map: slice 3 built BOTH sides real

### TS client — complete, no changes expected

`packages/runtime/src/adapters/CaptureRpcClient.ts::CaptureRpcClient` is a full
`CapturePort` implementation (the exact interface `RunManager` consumes from
`packages/runtime/src/ports.ts::CapturePort`):

- `prepareCapture` → `POST /v1/capture/prepare`, `releaseCapture` →
  `POST /v1/capture/{runId}/release`, `captureHealth` → `GET /v1/capture/{runId}/health`.
- Every response field validated with `@tm/common` safe coercions; malformed payloads
  throw typed `CaptureRpcError` with `code` (+ HTTP `status` preserved for server
  errors, including FastAPI 422-list and Starlette string-detail shapes).
- Injectable `fetchImpl`, base URL path-prefix support, sends `origin` = its own target
  origin (passes the Python origin guard: `terminal_bridge.origin_allowed_from_headers`
  accepts origin == request origin, so same-host loopback self-origin is allowed).
- Exported from the barrel `packages/runtime/src/index.ts` already.

Pinned by `packages/runtime/src/adapters/CaptureRpcClient.test.ts` (10 tests: round
trips, all error-body shapes, path prefix, malformed responses, transport failure).

### Python RPC server — REAL, mounted, not a stub

- `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry` is the §2c
  `run_id → lease` registry, defaulting `prepare_run=prepare_captured_run` with
  `default_claude_run_dependencies()`. `prepare_capture` runs the real launch via
  `asyncio.to_thread` with session-store preflight, cancellation safety (shielded
  future + abandoned-lease close), closed-registry and duplicate-run-id lease cleanup.
  `release_capture` is idempotent (pop + `lease.close()`, returns bool).
  `capture_health` → `lease.alive()` or `CaptureLeaseNotFound`. `close()` releases all
  leases (this is §4 rule 5's Python-side self-release hook, already in place).
- `api/src/transport_matters/api/v1/capture_rpc_routes.py` translates domain errors:
  `web_runtime_unsupported` 400, `session_store_unavailable` 503, `bind_conflict` 409,
  `proxy_start_timeout` 503, `capture_already_registered` 409,
  `capture_registry_closed` 503, `capture_not_found` 404. Guarded by
  `run_routes.require_http_origin`. `PrepareCaptureRequest` mirrors the full
  `CapturedRunRequest` surface (directory, ports, storage/home dirs, runtime template,
  launch fields, space/worktree ids, defer_session_ownership, bypass_permissions).
- **Mounted and lifecycle-managed**: `main.py::create_app` does
  `app.include_router(capture_rpc_routes.router, prefix="/v1")`, creates the registry
  eagerly on `app.state.capture_registry`, and closes it in the lifespan teardown. Not
  env-gated; the origin guard is the only gate.
- Constraint to know: the registry rejects `web_runtime != embedded`
  (`CaptureExternalRuntimeUnsupported`) — external/shared-proxy routing is explicitly
  out of the RPC.

Pinned by `api/src/transport_matters/test_capture_rpc.py` (12 tests: spawn-spec
serialization via `capture_spawn_spec_payload`, release idempotency, health of a dead
proxy child, close-releases-all, external rejection, store preflight, cancellation,
duplicate run id, real-child `CapturedRunLease.alive`) and
`api/v1/test_capture_rpc_routes.py` (5 tests: round trip with fake prepare, origin
guard, external rejection, store-unavailable and bind-conflict translation).

### Envelope semantics that matter for the swap

`captured_claude.py::build_invocation` builds `client.env` via
`build_managed_child_env(env, ..., extra_env={"ANTHROPIC_BASE_URL": proxy_url})` where
`env` **is** the launch env — so `CapturedRunSpawnSpec.client.env` already embeds
`launch_env` plus the proxy pointer. Python's own
`run_manager.py::RunManager._start_run_terminal` spawns with `client.argv/env/cwd`
only. The TS `RunManager.create` doing the same is therefore **correct**; spec §4 rule
1's "spec.client + spec.launch_env" is satisfied through `client.env`. `launchEnv` on
the wire spec is informational (mitmdump-side env). No merge work needed.

Run-id minting: real capture mints `run_id` inside `prepare_captured_run`;
`StubCaptureAdapter` deliberately mimics this (`randomUUID`), and
`RunManager.register` keys off `spec.runId`. Swap-safe as designed.

### s4c Runtime state

`packages/gateway/src/main.ts::createDefaultRuntimeRouterDeps` constructs
`StubCaptureAdapter` with `stubHarnessClientSpec` (argv `[input.harness]`,
`process.env`, `process.cwd()`). This is the single swap point.
`RunManager` is fully wired against `CapturePort`; ordering rules 1-3 are implemented
and tested (see §4 below). `RunManager.create` currently sends **only `{ harness }`**
as `PrepareCaptureInput` and sets `view.sessionId = runId` (stub-ism; real spec
carries `managedSession.nativeSessionId`, which is what Python's
`ManagedRun.view` uses for `session_id`).

---

## 2. The precise 4d delta

### A. Gateway swap (the wiring)

`packages/gateway/src/main.ts`: when a new env var is set, construct
`CaptureRpcClient({ baseUrl })` instead of the stub; unset → keep the stub and warn
(exactly the `TRANSPORT_MATTERS_DATABASE_URL` / Activity-disabled pattern already in
this file). The s3 scout already reserved this config: "one Runtime-side setting for
the Python base URL (env var, mirror of `config.py::Settings.gateway_url`)".
Proposed name: `TRANSPORT_MATTERS_CAPTURE_RPC_URL` (matches the existing
`TRANSPORT_MATTERS_*` family). No Python server completion is needed — it is real and
mounted (see §1).

### B. Enrich `PrepareCaptureInput` on the create path

`RunManager.create` must forward what it already has: `spaceId` / `worktreeId` from
`CreateManagedRunInput`, plus a working `directory`. Today `directory` is never sent,
so a real prepare resolves the working dir to the **Python API process cwd** — wrong
workspace for every run.

**Open decision (recommend: keep 4d thin).** The canvas creates runs with
`worktreeId` only; worktree→cwd resolution lives in Python
(`run_routes._resolved_worktree` via `space/store.py::SpaceStore.resolve_worktree`).
Two options:

1. **4d minimal (recommended):** add optional `cwd` to the runtime router's
   `CreateRunBody` → `CreateManagedRunInput` → `PrepareCaptureInput.directory`. Real
   capture works end to end for direct API/dev consumers; worktree resolution moves
   into the Python prepare RPC in 4e where the canvas contract actually cuts over
   (Python owns `SpaceStore`; re-implementing resolution in TS would duplicate it).
2. 4d does the RPC-side worktree resolution now (extend the prepare route to resolve
   `worktreeId` → directory when `directory` is absent, reusing the `run_routes`
   helpers and error codes). Makes 4e a pure route flip but grows this slice into the
   space store surface.

Also fix the stub-ism while touching `register`: `view.sessionId =
spec.managedSession?.nativeSessionId ?? runId` (parity with Python
`ManagedRun.view`).

### C. Capture-crash DEGRADED path + `capture_health` (the real new work)

Nothing implements §4 rule 4 today — no health polling, no degraded handling, in
either language (Python's `RunState` has no DEGRADED either; this is new behavior the
spec assigns to the Runtime, not a parity port).

Plan:

- **Health monitor** in `RunManager`: per-RUNNING-run interval poll of
  `capturePort.captureHealth(runId)`. New options: `captureHealthPollMs` (default a
  few seconds; `undefined`/0 disables — keeps stub-backed tests and the stub gateway
  mode silent) and a small consecutive-failure threshold.
- **Degrade triggers:** `alive: false`, or `CaptureRpcError` with status 404
  (`capture_not_found`) → degrade immediately. Transport-level errors
  (`capture_rpc_unavailable`) → degrade only after N consecutive failures (a Python
  API restart genuinely kills the mitmproxy children, but a transient blip must not
  kill every run).
- **Degrade action = a third settle outcome** `{ kind: "capture-lost" }` through the
  existing memoized settle funnel: close fanout, kill PTY grace-then-force (the agent
  is proxyless), final state `FAILED` with `endReason: "capture-lost"` and a
  human-readable `view.error`; then the idempotent `releaseCapture` cleanup that
  already sits at the settle tail. Stop the poller on settle (any outcome).

### D. Make settle release best-effort (real client throws; stub never did)

Two latent bugs the real adapter activates:

- `RunManager.performSettle` tail: `await capturePort.releaseCapture(...)` — a throw
  rejects the memoized settle promise. On the natural-exit path the caller is
  `void this.settleRun(...)` inside `session.onExit` → **unhandled promise
  rejection**; on terminate it 500s the route after the PTY is already dead; on
  `close()` it fails gateway shutdown. Fix: catch release failures inside
  `performSettle`, log/record on `view.error`, never reject settle. Safe because
  `release_capture` is idempotent and `CaptureLeaseRegistry.close()` self-releases
  leaked leases at Python shutdown.
- `RunManager.create` rollback: `await this.capturePort.releaseCapture(spec.runId)`
  inside the catch — a second throw masks the original launch error. Wrap it.

### E. Error-code fidelity on create (small, worth doing now)

`create` collapses every prepare failure into `launch_failed` → HTTP 500 via
`runtimeRouter.RUN_MANAGER_HTTP_STATUS`. The real server distinguishes 409
`bind_conflict` / 503 `session_store_unavailable` / etc., and `CaptureRpcError`
carries `code` + `status`. Preserve the upstream status on `RunManagerError` (one
optional field) and let `replyRunManagerError` prefer it over the static map. Keeps
the canvas UX honest at 4e cutover without inventing new error vocabulary.

---

## 3. Does the run state union need a DEGRADED member? **No — recommend end reason, not state.**

- `packages/runtime/src/domain/runtimeRun.ts::RuntimeRunState` is
  `RUNNING | TERMINATING | TERMINATED | EXITED | FAILED`; Python
  `run_models.py::RunState` and the curated `run_routes.py::PublicRunState` have **no
  DEGRADED either** — adding one would be a Runtime invention with cross-plane ripple
  (router `stateFromQuery`, Python public union, canvas
  `www/packages/core/src/transport.ts` run state type at 4e).
- Degradation here is transient by construction: rule 4 says degrade → immediately
  tear down the PTY. `TERMINATING → FAILED` already expresses the transit; the durable
  product signal is **`endReason: "capture-lost"`** (add to
  `runtimeRun.ts::RuntimeRunEndReason`) plus `view.error`.
- Reconciliation note: Python `run_models.py::RunEndReason` is
  `TerminateReason | "natural-exit" | "failed"` and the Python
  `run_routes.py::RunViewModel.end_reason` literal matches today's TS union.
  "capture-lost" stays Runtime-plane-only until 4e touches the canvas types.

---

## 4. §4 ordering rules 1-4 — coverage audit

| Rule | Status | Where |
| --- | --- | --- |
| 1. Capture before PTY; prepare failure → reject, no PTY | **Covered** | `RunManager.create`: `prepareCapture` → `ptyPort.spawn`; failure → `launch_failed`. Tests: `RunManager.test.ts` "wraps a failing prepareCapture into launch_failed", "spawns a PTY from the capture envelope". Gap: input enrichment (§2B). |
| 2. Normal end: drain fanout, close attachments, THEN release | **Covered** | `performSettle`: `fanout.closeAll` → `session.dispose` → `releaseCapture` last. Test: "settles a natural exit as EXITED, closes viewers, and releases capture". Gap: release-throw tolerance (§2D). |
| 3. Explicit terminate: grace-then-force, wait exit, then release | **Covered** | `performSettle` terminate branch: SIGTERM → grace → SIGKILL → grace → TERMINATED → dispose → release. Tests: grace/escalation/concurrent-terminate suite. Same §2D gap. |
| 4. Capture dies first → degraded → teardown → idempotent release | **NOT covered** | No health poll, no degraded state anywhere. §2C is the new work. |

Rule 5 (sidecar self-release on Runtime SIGKILL) is slice 5, but note the Python half
already exists: `CaptureLeaseRegistry.close()` runs in the app lifespan.

---

## 5. Build plan for Fable

### TS

1. `packages/runtime/src/domain/runtimeRun.ts` — add `"capture-lost"` to
   `RuntimeRunEndReason`.
2. `packages/runtime/src/service/RunManager.ts` —
   - forward `directory`/`spaceId`/`worktreeId` into `prepareCapture` (§2B);
   - `sessionId` from `managedSession.nativeSessionId` when present;
   - health monitor (start on `register`, stop on settle; options
     `captureHealthPollMs` + failure threshold) and the `capture-lost` settle outcome
     (§2C);
   - best-effort release in `performSettle` and the `create` rollback (§2D);
   - optional upstream-status field on `RunManagerError` (§2E).
   File is ~340 lines; if the monitor pushes it past readable, extract
   `service/CaptureHealthMonitor.ts` rather than inlining (stay far from the 700
   limit).
3. `packages/runtime/src/server/runtimeRouter.ts` — optional `cwd` on
   `CreateRunBody` (per §2B decision); prefer upstream status in
   `replyRunManagerError`.
4. `packages/gateway/src/main.ts` — env-gated `CaptureRpcClient` construction with
   stub fallback + warn (§2A).
5. `packages/runtime/src/index.ts` — export nothing new unless the monitor is a
   separate module consumed outside the package (it should not be).

### Python

**Likely zero production changes.** The RPC server is complete and mounted. Python is
touched only if the §2B decision lands worktree resolution in 4d (then
`capture_rpc_routes.py` prepare grows resolution reusing the `run_routes` helpers +
route tests).

### Tests (all against gates `just check` and `just test`, verbatim)

- `RunManager.test.ts` (extend, stub/fake CapturePort):
  - prepare input carries directory/spaceId/worktreeId; sessionId adopts
    nativeSessionId.
  - capture-lost: fake port reports `alive: false` → PTY killed, viewers closed with
    run-ended, view `FAILED` + `endReason: "capture-lost"`, release called once;
    poller stops after settle; transport-error threshold (N-1 failures → still
    RUNNING, N → degrade); poll disabled when `captureHealthPollMs` unset.
  - release-throw tolerance: releaseCapture rejects → natural-exit settle still
    resolves EXITED (no unhandled rejection), terminate returns TERMINATED, create
    rollback surfaces the original launch error.
- **Integration (TS, no mitmproxy):** `RunManager` + real `CaptureRpcClient` against
  an in-process fake RPC server (fastify on `listen({ port: 0 })` — the exact pattern
  `CaptureRpcClient.test.ts` established). Cover: spawn-order (server records prepare
  before the fake PtyPort spawn), release-after-pty-exit ordering, capture-crash
  degrade via the health route flipping `alive: false`, 409/503 prepare failures
  surfacing with real statuses.
- `main.test.ts` (gateway): env set → CaptureRpcClient wired; unset → stub + warn.
- **Python:** existing `test_capture_rpc.py` fake-lease/injected-`prepare_run` pattern
  already proves the registry without mitmproxy (`FakeLease`, real-child `alive` test
  uses `sys.executable`, not mitmdump). No new Python tests unless §2B option 2.
- **Real mitmproxy E2E:** manual dogfood on the preview channel
  (`docs/CHANNELS.md`), not CI.

Cross-language contract: the wire payload is pinned on both ends
(`test_capture_rpc.py::test_prepare_registers_lease_and_serializes_spawn_spec` pins
`capture_spawn_spec_payload`; the TS client validators pin the parse). A shared JSON
fixture would be nice-to-have hardening, not required for 4d.

---

## 6. Drift, risks, open decisions

- **Decision for orchestrator/Stuart:** §2B — directory passthrough now + RPC-side
  worktree resolution in 4e (recommended), or pull resolution into 4d.
- **Threshold semantics:** treating RPC-unreachable as capture death is usually right
  here (mitmproxy children die with the Python API process), but only after N
  consecutive failures; pick N=3 and a poll interval ~2-5s, constants in one place.
- **Registry/API restart asymmetry:** runs are process-resident in the gateway; if
  the Python API restarts, its lifespan closes all leases → every run degrades via
  health. That is correct behavior, worth a line in the PR description.
- **External web runtime:** the RPC rejects `web_runtime: "external"`; the runtime
  router never sends it. Fine for 4d; shared-proxy routing stays Python.
- **Known s4c drift carried, still slice 5:** `node-pty` `kill()` signals pid only
  (no killpg/Job); ConPTY signal degradation. Do not touch in 4d.
- **Idempotency keys:** Python front door supports `idempotency_key`; the runtime
  create path has none. 4e-cutover concern, not 4d.
- No storage/persistence shape changes anywhere in this slice (no data-loss surface).
