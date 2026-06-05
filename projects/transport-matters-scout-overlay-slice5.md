# Scout: overlay Slice 5 — refresh seam, exact version carry, launch advisory behavior

HEAD: `037095982c3e64138b8026dc3511c9db179b0fc7` (clean tree, PR#377 merged). Fact pass only, no repository writes.

Controlling spec: `~/.mdx/projects/transport-matters-spec-overlay-registry.md` §Client behavior/Refresh (carry chain at "Refresh", triggers 1–3) and §Slice 5. Reason recording homes at "Every reason has one recording home". Read with `.warroomagents/fable5.md`, `docs/ARCHITECTURE.md` (Product-plane gateway), `docs/process/WARROOM.md`.

## Reuse Map — owners, writers, readers, precedence

All scheduling state already has one owner. The slice adds one field to existing DTOs, one injected notification, and one injected hook. Nothing in this slice creates a new state owner.

### Refresh scheduling

| State | Owning symbol | Writers | Readers | Precedence today |
| --- | --- | --- | --- | --- |
| In-flight refresh per tuple | `packages/overlay/src/service/OverlaySyncService.ts:OverlaySyncService.inFlight` | `schedule` only | `schedule` | Concurrent refreshes for one key collapse onto the pending task (spec-required) |
| Last known status per tuple | `OverlaySyncService.statusByRelease` | `schedule` (seeds empty), `refresh` (holds held/current, then result) | `statuses`, `refresh` | Later write wins; seeded before fetch so a tuple is visible from first schedule |
| Tuple key | `packages/overlay/src/domain/releaseKey.ts:overlayReleaseKey` = `[harness, harnessVersion]` | pure | service | Single spelling; do not fork |
| Explicit refresh entry (trigger 3) | `packages/overlay/src/server/overlayRouter.ts:createOverlayRouter` — `POST /v1/overlays/refresh` (mounted at `packages/gateway/src/app.ts:OVERLAY_CONTEXT_PREFIX`) | calls `schedule`, fire-and-forget, replies 202 | — | Closed field set `REFRESH_FIELDS` = {harness, harnessVersion}; always forces a refresh |
| Service composition | `packages/overlay/src/gatewayDeps.ts:createOverlayGatewayDeps` → `packages/gateway/src/main.ts:runGatewayProcess` | one construction | router | `overlayDeps` is built BEFORE `runtimeDeps` in `runGatewayProcess` — the hook wiring below needs no reorder |

**Missing and mandated**: the observation-driven dedupe ("differs from the last scheduled tuple", spec trigger 2). Sole legal owner is `OverlaySyncService`; `statusByRelease` is already the memory. The clean shape is one new method `observe(release)` that calls `schedule` only when `statusByRelease` lacks the key. RunManager keeping its own last-tuple memory would be a second writer to owned state with no precedence rule — reject in review.

### Startup emission (trigger 1)

| Concern | Owning symbol | Facts |
| --- | --- | --- |
| The one startup pass | `api/src/transport_matters/harnesses/state_refresh.py:refresh_harness_state` → `_refresh_harness` per registered harness | Capabilities come from one `detect_harnesses` call off the loop; `build_harness_observation` yields `observation.normalized_version` from that capability. No second probe exists or is needed. |
| Failure isolation | `_refresh_harness` per-harness try in `refresh_harness_state`; `run_startup_refresh` swallows the whole pass | Slice scope says preserve; the notification call must sit inside its own try (or the per-harness try) so a dead gateway cannot mark the pass failed |
| Composition | `api/src/transport_matters/main.py` lifespan: `services.harness_refresh = partial(refresh_harness_state, ExecutorEvidenceStore(...))`, launched via `asyncio.create_task(run_startup_refresh(refresh))` — startup never awaits it | The injected overlay refresh notification is a new keyword on `refresh_harness_state` (spec mandates exactly this extension), default None/no-op, bound in the same `partial` |
| Gateway address | `main.py:create_app`: `gateway_url = settings.gateway_url or (gateway_plan.url if gateway_plan else None)` — Python already resolves it to mount `api/v1/run_proxy.py` (httpx.AsyncClient toward the gateway) | The notification implementation is a best-effort POST of `{harness, harnessVersion}` to the existing `POST {gateway_url}/v1/overlays/refresh`. httpx is already in the tree. No gateway URL (D2 stub) ⇒ notification stays None |

**Observed tuples startup can actually emit**: at most one per registered harness (`claude`, `codex`, `grok`) — the pair (harness_id, `observation.normalized_version`) whenever the detection reports an installed, versioned binary. Grok qualifies despite having no embedded release: the observation upsert and its version do not depend on `embedded_release_entry` (the `_fallback_observation_revision` path exists for exactly this), so the emission guard is `normalized_version is not None`, placed after `build_harness_observation` and before the `entry is None` early return. One pass ⇒ each tuple once; `OverlaySyncService.inFlight` additionally collapses any race.

**New port or reuse?** Reuse. The TS side needs no new port and no new route: the product refresh entry is the existing `POST /v1/overlays/refresh` → `OverlaySyncService.schedule`. The only new injection is the Python-side notification callable on `refresh_harness_state` (spec-mandated wording "the injected overlay refresh notification"); it is a parameter, not a new hexagonal port in the overlay context.

**Startup ordering risk (decision needed)**: the gateway child is spawned by `gateway_supervisor` during the same lifespan that launches the refresh task, so the first startup POST can race gateway listen. Best-effort-and-logged is spec-compatible (launch/startup never depend on refresh; the next capture preparation reschedules the tuple). If the orchestrator wants stronger delivery, the notification can bounce off gateway readiness, but that is added machinery the spec does not require.

### Exact version carry (trigger 2)

Chain with current state, one owner per hop:

| Hop | Owning symbol | State at HEAD |
| --- | --- | --- |
| Version source | `api/src/transport_matters/harnesses/compatibility_service.py:CompatibilityGateDecision.normalized_version` | Sole production owner; written once in `_gate` from `match_release`; None on missing entry, not-installed, or advisory gate failure. `prepare_launch` passes `observe=(lambda _path: capability)` reusing the enablement probe — one `--version` per launch, none added |
| Launch carry | `api/src/transport_matters/cli/launch_runtime.py:LaunchPreparation.compatibility` | Exists, populated |
| Captured context | `api/src/transport_matters/captured/context.py:_prepare_launch_state` → `CapturedRunContext.prepared` | Exists |
| Python spawn DTO | `api/src/transport_matters/captured/models.py:CapturedRunSpawnSpec` | **No version field today.** One construction site only: `api/src/transport_matters/captured/run.py:prepare_captured_run` (has `ctx.prepared.compatibility` in scope). Add `harness_version: str | None`, set from `compatibility.normalized_version`, None-safe |
| Wire payload | `api/src/transport_matters/capture_rpc.py:capture_spawn_spec_payload` | Add `"harnessVersion"`. Served by `api/src/transport_matters/api/v1/capture_rpc_routes.py` (single call site) |
| TS spawn DTO | `packages/runtime/src/ports.ts:CapturedRunSpawnSpec` | Add `harnessVersion: string \| null` (recommend required-nullable, matching `runtimeHome`/`spaceId`; the parser's nullable readers demand field presence, so `StubCaptureAdapter.prepareCapture` and `packages/runtime/src/testSupport/fakePty.ts` must emit it — both currently omit only the `?:` optionals) |
| TS parser | `packages/runtime/src/adapters/CaptureRpcClient.ts:capturedRunSpawnSpec` | Add `nullableStringField(payload, "harnessVersion")`; reuse the existing field readers, no new coercions |
| Scheduler call | `packages/runtime/src/service/RunManager.ts:createNew` | After `prepareCapture` returns and never awaited: fire-and-forget hook with `{harness: spec.harness, harnessVersion}` when non-null; null schedules nothing (spec: null records `harness_version_unknown`, whose recording home is `CompatibilityFactArtifact` — that writer evolution is Slice 6 scope; Slice 5 asserts only PASSTHROUGH launch) |
| Hook injection | `packages/runtime/src/service/runManagerTypes.ts:RunManagerOptions` | New optional member typed against `@tm/contract/overlay:OverlayReleaseKey`. Runtime already imports `@tm/contract/overlay` (CaptureRpcClient); it must never import `@tm/overlay` — `www/packages/shell/src/testSupport/importGraphBoundary.test.ts` enforces and already lists `@tm/overlay/src/service/OverlaySyncService` |
| Composition | `packages/gateway/src/main.ts:createDefaultRuntimeRouterDeps` | Gains the hook from `overlayDeps.overlay.sync` (call `observe`). Injected `runtimeRouterDeps` (tests) simply omit it |

### Remote key discipline — validated at HEAD

`packages/overlay/src/adapters/httpOverlayRegistry.ts:fetchCurrent` sends exactly: query `harness` + `harness_version`, `Accept` media type, optional `Authorization: Bearer` (tenant is the signed subject resolved server-side from the token), optional `If-None-Match`. No model, path, fingerprint, bytes, or provider identity anywhere. `contract/overlay/wire.ts:OverlayReleaseKey` is two fields; `overlayRouter.ts:refreshRelease` rejects extra fields closed-set. Tenant + opaque harness + exact version are the only remote key components; the slice must not widen `OverlayReleaseKey` or the refresh body.

### Launch advisory behavior — validated at HEAD

- Startup: refresh runs as a named task, never awaited; `run_startup_refresh` swallows.
- Launch: `gate_launch_preparation` is advisory (logged-and-swallowed on failure); registry work never enters `prepare_launch` or `prepare_captured_run`.
- Gateway: router replies 202 fire-and-forget; `OverlaySyncService` failure paths degrade to held status or PASSTHROUGH reasons; registry outage is `{kind: "unavailable"}` after bounded retries with jittered backoff.
- The only awaited addition allowed by the slice is nothing: both new call sites are `void`-style dispatch.

## Quality Map

Measured sizes (hard limits: 700/file, ~150/function):

| File | LOC | Risk |
| --- | --- | --- |
| `packages/runtime/src/service/RunManager.ts` | 676 | **Decisive.** 24 lines of headroom. The createNew addition must stay a few lines (one hook call + option plumbing in `runManagerTypes.ts`, which is 106). If the diff would cross 700, extract first — natural seam: the settle/teardown cluster (`settleRun`..`exitedWithinGrace`) or the re-export block |
| `packages/runtime/src/service/RunManager.test.ts` | 647 | New tests do not belong here; the split pattern already exists (`RunManagerGrant.test.ts`, `RunManagerNudge.test.ts`) — add `RunManagerOverlayRefresh.test.ts` |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py` | 601 | One payload line; fine |
| `api/src/transport_matters/captured/context.py` | 547 | No change needed beyond none — carry already flows through `prepared` |
| `api/src/transport_matters/capture_rpc.py` | 494 | One payload entry |
| `api/src/transport_matters/captured/run.py` | 475 | One constructor field |
| `packages/runtime/src/adapters/CaptureRpcClient.ts` | 440 | One parser line |
| `api/src/transport_matters/cli/launch_runtime.py` | 401, `harnesses/compatibility_service.py` 391, `harnesses/state_refresh.py` 357 | `refresh_harness_state` gains one keyword + one guarded call; `_refresh_harness` is ~95 lines, stays under 150 |
| `packages/overlay/src/service/OverlaySyncService.ts` | 177 | Room for `observe` |
| `packages/gateway/src/main.ts` | 378, `app.ts` 98 | Wiring only |

Duplication and dead code: none found in scope. Searches run: `OverlaySyncService|overlay_sync|OverlayRefresh|RefreshPort` across `api/src`, `packages`, `www` (only the overlay package and the import-boundary listing); `CapturedRunSpawnSpec|capture_spawn_spec_payload` (owners above, no parallel DTO); `overlays/refresh` (router + its test only); no existing last-scheduled-tuple memory anywhere. The two duplication traps the build could introduce: a second scheduling memory outside `OverlaySyncService`, and a second spelling of the release key (always go through `overlayReleaseKey` / `OverlayReleaseKey`).

Gotcha: `api/` is Python 3.14 — PEP 758 unparenthesized except tuples appear in overlay modules; not a defect.

Existing test seams to reuse (no new harnesses):

- `api/src/transport_matters/harnesses/test_state_refresh.py` (431) — fake evidence store + probe fakes; add: each installed versioned harness notifies once, grok included, notification failure isolated, no-gateway means no notification, no added probe (`test_no_probe_without_release_installation_or_version` is the pattern).
- `api/src/transport_matters/test_capture_rpc_payload.py` (42) — golden `capture_spawn_spec_payload`; pins `harnessVersion` present and null-safe.
- `api/src/transport_matters/captured/test_run.py` — spawn spec construction carries `prepared.compatibility.normalized_version` unchanged; null decision carries null.
- `packages/runtime/src/adapters/CaptureRpcClient.test.ts` — parser round-trip for the new field.
- `packages/overlay/src/service/OverlaySyncService.test.ts` (396) — `observe` dedupe: unseen tuple schedules, seen tuple does not, explicit `schedule` still forces; concurrent collapse already pinned.
- `packages/overlay/src/server/overlayRouter.test.ts` — route unchanged; keep closed-field pin.
- new `packages/runtime/src/service/RunManagerOverlayRefresh.test.ts` over `testSupport/fakePty.ts` — hook fires after prepare with the exact carried version, never awaited (a hanging hook must not delay create), null version fires nothing, hook throw does not fail the launch.
- `packages/gateway/src/app.test.ts` / `runtimeFixtures` — composition smoke: gateway wires `observe` into RunManager.

## Plan (ordered, smallest slices; gates `just check`, `just test`, then CI)

1. **Contract carry, Python.** `CapturedRunSpawnSpec.harness_version` (models.py) + one construction site (run.py) + `capture_spawn_spec_payload` + payload golden test + captured/test_run.py pin. RED first on the payload golden.
2. **Contract carry, TS.** `ports.ts` field, `CaptureRpcClient` parser, `StubCaptureAdapter`, `fakePty`, parser test. Required-nullable so a real capture side can never silently drop the field.
3. **`OverlaySyncService.observe`.** Dedupe on `statusByRelease` presence; tests as above. This is the sole home of "differs from the last scheduled tuple".
4. **RunManager hook.** `runManagerTypes.ts` option + `createNew` fire-and-forget call + `RunManagerOverlayRefresh.test.ts` + gateway `createDefaultRuntimeRouterDeps` wiring.
5. **Startup notification, Python.** New keyword on `refresh_harness_state` (default None), guarded call in `_refresh_harness` after `build_harness_observation` when `normalized_version is not None`, httpx poster bound in the lifespan `partial` from the already-resolved gateway URL, per-call try/log. test_state_refresh.py additions. Decision surfaced above: accept best-effort delivery against the gateway-listen race.
6. **Slice tests from the spec list** not covered above: registry outage cannot fail startup (gateway-side, already pinned by sync tests — extend if gap), null version and newly observed version both launch PASSTHROUGH (Python launch tests; no overlay resolver exists at launch yet, so PASSTHROUGH is vacuously the state — pin at the status/metadata seam that Slice 4 built).

Builder note (gpt-sol, seam blindness): this slice is one field threaded through six existing owners plus two injections. Every hop reuses an existing symbol named above. Any new module, new port file, new route, second dedupe memory, or second release-key spelling is a defect even with green tests.
