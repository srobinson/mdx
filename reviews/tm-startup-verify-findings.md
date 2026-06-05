# Review: startup provider verification wiring (feat/startup-access-wiring)

Reviewer pass over `main..HEAD` (4493f1f9, b9232312, 8696e7ad). Gates not re-run; the
orchestrator reported `just check` and `just test` green on HEAD and nothing below needs
a re-run to stand.

Counts: Major 0, Minor 6, Note 3.

## Standing question 1: does the guard hold on all three backends

Proven by tracing the chain, not by the tests.

**Desktop backend (verifies).** Every desktop backend variant goes through
`cli/desktop_cmd:prepare_desktop_launch` -> `_build_desktop_backend_env`, which now sets
`STARTUP_ACCESS_VERIFICATION=1`: the in-process serve (`run_desktop_launch` ->
`serve_desktop_backend` -> `_apply_desktop_backend_env` writes it into `os.environ`), the
detached backend (`run_desktop_detached` popens with `plan.env`), and the Electron-owned
`_desktop-backend` command (`run_desktop_backend_server` also calls
`prepare_desktop_launch`, so the flag is set by Python regardless of what
`desktop/src/backendProcess.ts:buildBackendLaunch` passes). `settings.toml` cannot
enable it: `config:Settings.load_from` copies only `database` from the toml.

**Embedded captured-run backend (must not verify).** The embedded web runtime is hosted by
the mitmdump process: `addon_runtime:load_runtime` calls `get_settings()` from that
process's environment and starts a lifespan only for `web_runtime == "embedded"`. That
environment is exactly the launch env: `cli/runner.py` spawns mitmdump with
`{**mitmdump_env, "PYTHONUNBUFFERED": "1"}` and `sup.spawn("mitmdump", ..., env=mitmdump_env)`,
and `mitmdump_env` is the value returned by `launch/environment:build_launch_env` (the only
two production callers are `captured/claude.py:_build_claude_captured_invocation`, which
codex and grok reach through `captured/invocations.py`, and `cli/explicit_proxy.py`).
`build_launch_env` now pops the key unconditionally before anything else. The gateway
cannot reintroduce it: `packages/runtime/src/service/RunManager.ts` spawns the client with
`browserPtyEnvironment(client.env, ...)` where `client.env` comes from
`build_managed_child_env(base_env=launch_env)`; it never merges `process.env` into a
captured run. So the desktop backend's `os.environ` (which carries the flag after
`_apply_desktop_backend_env`) reaches no captured run.

**Test suite (must not verify).** `Settings.startup_access_verification` defaults False,
and `api/conftest.py:_scrub_inherited_session_env` deletes every `TRANSPORT_MATTERS_*` key
except an explicit test-infra allowlist, so a developer shell that happens to carry the flag
cannot enable it under `just test`. `test_main:test_startup_access_verification_defaults_off`
covers the in-app guard on the real lifespan.

Verdict: holds on all three. One test-placement finding below (Minor 3).

## Standing question 2: `_resolve_launch_target` behaves identically

Confirmed by diffing the assembly, not by the test.

Old inline assembly vs `resolver_snapshots:create_resolver_snapshot_reader`, per call:
`local_executor_id()` per request (factory is constructed inside `_resolve_launch_target`,
so per request as before); `resolve_channel_id(None, os.environ)` same; `instant` is
`datetime.now(UTC).isoformat()` inside `read`, so per call; `ExecutorEvidenceStore(
resolve_session_store_url(settings), pool)` same; intent lookup same query and same filter;
`ensure_native_connection=True` same. The one deliberate change is
`ExecutorBlockStore(database_url, pool)` in place of `ExecutorBlockStore("", pool)`.
`harnesses/blocks_store:ExecutorBlockStore` is a dataclass whose `database_url` is read only
by the sync write methods (`create_block` and siblings open `connect(self.database_url)`);
`active_blocks` reads through the pool. Read behaviour is unchanged and the brief asked for
the real URL.

The only test edit, `api/v1/test_capture_rpc_access_policy.py`, swaps three monkeypatches
(`local_executor_id`, `HarnessEnablementStore`, `resolver_snapshots_for_harness`) for one
(`create_resolver_snapshot_reader`) and removes the local `_IntentStore`. Every assertion on
route behaviour is untouched; the executor-id assertion that lived in `_IntentStore` now
lives in `test_resolver_snapshots:test_snapshot_reader_reassembles_live_per_harness_snapshots`.
Seam-only claim verified.

## Findings

Ranked by value.

### Minor 1. `access_verification:_run_captured_turn` is an untyped generic wrapper for one call site

`Callable[..., object]`, `*args: object`, `**kwargs: object`, returns `object`. It discards
type checking on the only call whose argument shape matters, and mypy cannot check that
`cancelled=cancelled.is_set` satisfies `captured_turn:run_captured_turn`'s
`Callable[[], bool] | None`. It also reimplements a pattern the repo already has:
`capture_rpc:CaptureLeaseRegistry.prepare_capture` does
`ensure_future(asyncio.to_thread(...))` + `await asyncio.shield(...)` + `except CancelledError`
for exactly this "worker thread cannot be interrupted" case.

Fix: give it the real signature (`request: CapturedRunRequest`, keyword `scenario_id`,
`timeout`, `capture_dependencies`, return `CapturedTurn`) and call `run_captured_turn`
directly (module-level lookup, so the existing monkeypatch in
`test_cancelling_verification_stops_captured_turn_workers` still intercepts). Replace
`asyncio.wait((worker,))` + `worker.result()` with `await asyncio.shield(worker)`; same
semantics, the idiom the codebase already uses.

### Minor 2. `main:_start_harness_access_verification` uses `assert` as a control-flow guard

`assert refresh_task is not None` in the production startup path. The invariant does hold
today: `lifespan` creates the refresh task whenever `services.session_pool` is not None,
because `_start_session_backed_services` sets `services.harness_refresh` on the same branch
that sets the pool. But the invariant spans two call sites and under `-O` a violation becomes
`await None` inside `run_startup_verification`, swallowed by its `except Exception` as a
logged "verification failed". Express it as the guard it is: `if not
settings.startup_access_verification or session_pool is None or refresh_task is None:
return`. No refresh means no observation to verify against, which is exactly the "nothing to
do" case, and it matches the refresh guard's shape.

### Minor 3. `cli/test_runtime_home.py` was already over 700 lines and this PR adds to it

731 lines on main, 749 now. Repo rule: files over 700 are refactored before code is added.
The new test is also misplaced: it is about `launch/environment:build_launch_env` dropping an
inherited key, which is the subject of `launch/test_identity_env.py` (73 lines, see
`test_launch_without_identity_drops_stale_inherited_identity`). Move
`test_build_launch_env_drops_parent_startup_access_verification` there, and parametrize
`web_runtime` over `embedded` and `external`: the pop is unconditional, and the external case
is the one where the sibling `GATEWAY_SUPERVISE` test shows the two keys diverge.

### Minor 4. `create_resolver_snapshot_reader` is read-named but reconciles (persists) the native connection

`ensure_native_connection=True` is bound in, so every read runs
`native_connections:reconcile_native_connection`, which upserts. Correct for both consumers:
`_resolve_launch_target` always did this, and verification precedes a launch (the receipt
needs the connection row) and its read-back reconcile is idempotent. The docstring should
say it: one line that the reader reconciles the native connection because both callers
precede a launch, so a future read-only consumer (inventory, which the brief excluded for
that reason) does not pick it up by name.

### Minor 5. Startup verification outcomes are discarded

`run_startup_verification` takes `Callable[[], Awaitable[object]]` and drops the
`tuple[HarnessAccessVerification, ...]` that `verify_provider_access` returns. After a
startup pass the only trace is the evidence rows. One `logger.info` line summarising
`harness_id: outcome` per harness gives an operator the "did it run, what did it find" answer
without querying the store. Refresh has the same gap, but verification launches processes
and is the thing the startup screen waits on, so it earns the line.

### Minor 6. `docs/plans/AUTOPILOT-WIRE-PLAN.md` "Shipped" table goes stale on merge

The #400 row reads "No production callers" in bold and the paragraph below says two of three
are inert. This PR is the slice that closes that; update the row in the same PR so the plan
does not claim inertness the day it stops being true.

## Notes (no change required)

### Note A (orchestrator item d). `captured_turn:_wait_for_correlated_exchange` raising `CapturedTurnError` on cancel

`cancelled` defaults to None and `baseline_harvest` passes nothing, so its behaviour is
byte-identical; blast radius nil. Inside verification the error is raised in the worker
thread and swallowed by the cancel path, which then re-raises `CancelledError`, so cancellation
and failure are not conflated where it matters. `run_captured_turn`'s `finally` still
`terminate_all()`s the harness child and closes the lease, so a cancelled turn leaves no
process behind. A `CapturedTurnCancelled(CapturedTurnError)` subclass would be tidier but
nothing reads the distinction; skip.

### Note B. Cancelling the verification task cancels the refresh task if it is still running

`run_startup_verification` awaits the refresh `Task` directly; `Task.cancel` forwards to the
awaited future. The only cancel path is lifespan teardown, which cancels the refresh task on
the next line anyway, so this is harmless. `asyncio.shield(refresh_task)` would decouple them;
not worth the churn.

### Note C. Brief item 5, the shutdown finding, for the PR description

Without cooperative cancellation the `to_thread` worker would be joined by
`loop.shutdown_default_executor()` when uvicorn's `asyncio.run` exits, blocking interpreter
exit for up to `DEFAULT_VERIFICATION_TIMEOUT_S`. With it, `lifespan` teardown blocks only until
each worker observes the flag (the wait loop polls at 0.1s) plus any uncancellable window
inside `prepare_captured_run` and spawn. The builder's fix is warranted; the main.py comment
states the effect, the PR description should state the mechanism.
