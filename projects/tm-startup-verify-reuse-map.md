# Startup provider verification: reuse map

Scout pass, warroom `grok-capture`, 2026-08-19. Worktree
`.claude/worktrees/startup-verify`, branch `feat/startup-verify-wiring` at 6f0b4a56.
Map only; no code written, no API designed.

Owners found 5/5, none_found 0. One of the five (capability 2) exists but has no
public accessor, which is where a new symbol lands.

## 1. Startup per-harness work off the event loop

**Owner: `main.py:lifespan`.**

- `main.py:lifespan` creates `app.state.harness_refresh_task` with
  `asyncio.create_task(run_startup_refresh(refresh), name="harness-state-refresh")`.
  It is the only caller of `harnesses/state_refresh:run_startup_refresh`.
- The callable comes from `main.py:_start_session_backed_services`, which sets
  `services.harness_refresh = partial(refresh_harness_state, ExecutorEvidenceStore(...))`.
  A pre-set `app.state.harness_state_refresh` wins over it (the test seam).
- Guard: no session pool means no task. The task is fire-and-forget; startup never
  awaits it.
- Teardown: the lifespan `finally` cancels the refresh task **before** closing the
  session pool, via `main.py:_close_lifespan_resource`.
- `harnesses/state_refresh:run_startup_refresh` is the guarded body: one pass,
  every exception logged and swallowed.
- `harnesses/state_refresh:refresh_harness_state` isolates failures per harness and
  routes every sync store write through `asyncio.to_thread`.
- Re-entry already exists: `api/v1/harnesses.py:refresh_harnesses` (`POST
  /v1/harnesses/refresh`) awaits the startup task, then runs the same callable under
  `app.state.harness_refresh_lock`. The FirstRun screen's "Refresh" button calls it.

A verification pass has a working precedent to copy in shape: a `partial` built in
`_start_session_backed_services`, a task created in `lifespan`, a guarded body, a
cancel in `finally`, an app-state lock for re-entry.

## 2. How a non-CLI caller obtains a `CapturedRunDependencies`

**Owner: `capture_rpc:create_capture_registry`. No public accessor: none found.**

- `captured/dependencies:default_claude_run_dependencies` is the one factory.
- In-app it is called exactly once, by `capture_rpc:create_capture_registry`, with
  `control_plane_grants=services.grant_store`.
- `main.py:lifespan` calls that and stores the result at `app.state.capture_registry`.
- The instance is held privately: `capture_rpc:CaptureLeaseRegistry.__init__` assigns
  `self._dependencies`. Searched `grep -rn 'CapturedRunDependencies|default_claude_run_dependencies|_dependencies' api/src/transport_matters`.
  There is no property, getter, or other public read of it.
- Other production callers, none of them the app: `cli/__init__.py:_run_dependencies`
  and `baseline_harvest.py` (`capture_dependencies=default_claude_run_dependencies()`).

So the app already builds the object the pass needs and keeps it private. Reaching
into `_dependencies` is not acceptable; calling the factory a second time in the
lifespan builds a divergent instance whose `control_plane_grants` must be kept in
sync by hand. This is new symbol candidate 1.

## 3. Building `ResolverSnapshots` per harness inside the app

**Owner: `harnesses/resolver_snapshots:resolver_snapshots_for_harness`.**

Its inputs and each input's owner:

| input | owner |
|---|---|
| `harness_id` | `harnesses:launch_eligible_harness_ids` (the pass already drives off it) |
| `executor_id` | `harnesses/executor_identity:local_executor_id` |
| `channel` | `channel:resolve_channel_id` |
| `instant` | `datetime.now(UTC).isoformat()` at both existing call sites |
| `evidence` | `harnesses/connections_store:ExecutorEvidenceStore(resolve_session_store_url(settings), pool)` |
| `blocks` | `harnesses/blocks_store:ExecutorBlockStore("", pool)` |
| `intent` | `harnesses/enablement_store:HarnessEnablementStore(pool).list_intents`, filtered by harness |
| `ensure_native_connection` | `True` at launch, default `False` for read-only inventory |

Two existing assemblers, both of which build that argument set inline:

- `harnesses/inventory:_harness_item` (read-only, `ensure_native_connection` default).
- `api/v1/capture_rpc_routes:_resolve_launch_target` (`ensure_native_connection=True`).

`verify_provider_access` wants a `SnapshotReader`
(`Callable[[HarnessId], Awaitable[ResolverSnapshots]]`), so the wiring needs the same
argument set bound once. **There is no shared factory that produces that binding**;
searched `grep -rn 'resolver_snapshots_for_harness'`, three hits total (definition
plus the two call sites). A third inline copy is the default outcome of this slice
and would be duplication. See risks.

`verify_provider_access` calls its reader twice per harness: once for the "current"
short-circuit, once in `_recorded_outcome` to read back what the proxy wrote. The
binding must therefore read live, not cache.

## 4. Frontend surface for per-harness readiness and progress

**Most of the startup screen already ships.** Owner:
`www/packages/canvas/src/firstrun/FirstRunScreen:FirstRunScreen`, mounted by
`launcher/CommandCenter` and `workbench/SessionCanvasRoute`.

Already on screen:

- `firstrun/harnessCards:harnessCard` renders four facts per harness: `installed`,
  `authenticated`, `access`, `models`.
- `firstrun/harnessCards:FactStatus` already has a `pending` tone documented as
  "evidence the startup refresh has not recorded yet", and
  `firstrun/harnessCards:installationState` is the three-world classifier (installed
  / absent / unknown) that stops an unknown rendering as a negative assertion.
- `firstrun/useHarnessInventory:useHarnessInventory` polls `GET /v1/harnesses` and
  **already accelerates while an access test is running** (`accessTestActive`
  argument feeding `inventoryPollInterval`).
- `firstrun/useLaunchReadiness:useLaunchReadiness` gates the infrastructure section.
- `FirstRunScreen:HarnessSection` owns `activeAccessTest` state, a 30s
  `ACCESS_TEST_POLL_TIMEOUT_MS` deadline, a `hasAccessObservationSince` completion
  check, and per-harness busy locking (`accessTestBusy` disables every other card's
  button).
- A per-harness **"Test `<harness>` access"** button already exists, gated on
  `harnessCards:HarnessCard.accessTestEligible`.
- A "Refresh" button already calls `POST /v1/harnesses/refresh`.

Not on screen: `compatibility.outcome`. It is computed, serialized
(`harnesses/inventory:HarnessCompatibilityInfo`) and typed on the client
(`www/packages/core/src/types/harnessInventory.ts`, including
`harness_update_required` and `harness_version_blocked`), but
`harnessCards:harnessCard` never reads it. Workflow steps 4 and 5 have data and
transport, and no rendering.

`screen_exists=partial`: the harness cards, the progress model, the polling and the
access-test affordance ship; the version prompt does not, and nothing renders a
whole-startup verification pass as distinct from per-card manual tests.

## 5. Observed version against supported release

**Owner: `harnesses/compatibility:match_release`.**

- Below `release.minimum_version` -> `harness_update_required` with
  `minimum_version` attached. That is workflow step 4.
- Above `release.maximum_version` -> `harness_version_blocked` with
  `block_reason_code="harness_version_unsupported"` and a
  `recommended_pin_version`. That is where workflow step 5 would hang.
- Unparseable version -> `harness_version_unknown`. Pure over injected snapshots, no
  clock and no store.
- `harnesses/compatibility:CompatibilityOutcome` is the whole vocabulary;
  `LaunchGateOutcome` adds only `harness_not_installed`.
- Called from `harnesses/inventory:_harness_item`, which is what puts the outcome on
  the wire to the screen.

The trigger condition the owner asked for is also already owned:
`harnesses/access_policy:scoped_access_observation` returns evidence attributed to
this exact harness version and **deliberately does not consult expiry** ("Absence is
what makes a fresh verification turn due"). `access_verification:_verify_harness`
already short-circuits to `outcome="current"` on it. First startup or version change,
never TTL lapse, is implemented; the wiring does not have to add it.

## Risks and duplication this wiring would walk into

**Two producers of the same access evidence.** `FirstRunScreen:HarnessSection`'s
`startAccessTest` already runs an access test today: `createCapturedRun(harnessId,
undefined, { providerAccessApproval: "diagnostic_test" })` through the capture RPC
route, as a visible run the user watches. `verify_provider_access` runs the same
`diagnostic_test` approval headless through `captured_turn:run_captured_turn`. Same
evidence row, same approval token, two different launch machineries. Decide which one
survives before wiring, or the screen will show a manual button that duplicates what
startup just did.

**Ordering: verification depends on refresh having landed.** `access_policy:_access_context`
returns unavailable when `receipt_harness_version` is None, and that version comes
from `snapshots.observation` which only `refresh_harness_state` writes. A verification
pass racing the refresh sees no observation and reports `not_launchable` for every
harness. The two passes are strictly ordered.

**One pass or two: two.** They have opposite cost profiles and opposite failure
policies. The refresh is advisory, cheap, fire-and-forget, and must never block
startup. Verification launches N real harness processes against real HOME
(`_verification_request` sets `home_dir=None` on purpose), each up to
`DEFAULT_VERIFICATION_TIMEOUT_S = 120.0`, all concurrently via `asyncio.gather`, and
it is the thing the startup screen is waiting on. Folding it into
`refresh_harness_state` would make the existing non-blocking guarantee false and would
make `POST /v1/harnesses/refresh` spawn N harnesses on every click. Two passes,
sequenced.

**Lock contention.** `api/v1/harnesses.py:refresh_harnesses` serializes manual refresh
against the startup task on `app.state.harness_refresh_lock`. A verification pass that
launches harnesses needs to be serialized against both that and a user launching from
the canvas; nothing today covers the third participant.

**Workflow step 5 has no comparator seam.** "Version newer than supported, run the
comparator" does not map onto anything shipped: above-maximum yields
`harness_version_blocked`, which blocks. No caller turns that outcome into a
comparator run. Flagging only; out of scope for this slice.

**`workspace` is an unbound input.** `verify_provider_access(workspace=...)` fills both
`directory` and `workspace_root` on the launch. At startup no user workdir is selected
yet, so the wiring has to choose one. Naming the gap, not choosing.

## Scope signal

**`new_symbols_needed=2`, and that holds only if capability 3's duplication is
accepted.**

1. A public read of the app's `CapturedRunDependencies`, so the pass uses the same
   instance `capture_rpc:create_capture_registry` built rather than a second one whose
   `control_plane_grants` drifts.
2. The startup verification task body, the analogue of
   `state_refresh:run_startup_refresh`, plus its `partial` in
   `_start_session_backed_services`. One symbol if the snapshot reader is a closure
   inside it.

Stated explicitly rather than designed around: doing capability 3 properly is a third
symbol, a shared per-harness snapshot-reader factory that
`inventory:_harness_item`, `capture_rpc_routes:_resolve_launch_target` and the new
pass all call. Without it this slice writes a third inline copy of the same eight
argument assembly. Three symbols with the duplication removed, two with it left in.
That is the owner's call, not the scout's.
