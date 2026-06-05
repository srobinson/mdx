# tm-verify-diag: what the product does in this state

Read-only diagnostic. Repo `transport-matters`, main at `d4ce12a5`. Live **preview**
channel, executor `ef9cd166-7f7b-4ee0-9054-4d365393d509`, database
`transport_matters_preview` on `postgresql://tm:tm@localhost:55432`, backend PID 36819
untouched.

Method: read the code, then ran the real resolver in-process against the live preview
stores with `resolver_snapshots_for_harness(..., ensure_native_connection=False)` (the
read-only variant; the production reader's `ensure_native_connection=True` persists a
connection, which this never did). Cross-checked against the live backend's
`GET /v1/harnesses` and against `project_harness_launch_view` over the same inventory.
No writes, no provider turns, no restarts.

---

## Headline

The launch/verification split is **deliberate and correctly implemented**. It is not why
no baseline exists.

No baseline exists because **the shipped compatibility catalog contains zero `tested`
edges**. Every target in the product, on every harness, is `observed_unverified`. The
resolver's two `tested`-gated decisions therefore never fire, and the one flag that
lifts the gate, `allow_unverified_target`, has **no production writer anywhere in the
codebase**. The launch view tells the operator "opt in required" through an opt-in that
does not exist on any API.

Fixing the resolver would make verification fire. There is no second silent gate behind
it: every downstream precondition on this machine passes.

---

## ESTABLISHED

Everything in this section was measured on the live preview channel today, or read
directly from the source at `d4ce12a5`.

### E1. The catalog has no `tested` edge, for any harness

`api/src/transport_matters/harnesses/compatibility_releases_v1.json`, all 9 target edges
across all 3 releases:

| release | route | native_model_id | support_tier |
| --- | --- | --- | --- |
| claude-2.1.211-r2 | claude.anthropic.oauth | claude-opus-4-8 | observed_unverified |
| claude-2.1.211-r2 | claude.anthropic.oauth | claude-fable-5 | observed_unverified |
| claude-2.1.211-r2 | claude.anthropic.oauth | claude-sonnet-5 | observed_unverified |
| claude-2.1.211-r2 | claude.anthropic.oauth | claude-haiku-4-5 | observed_unverified |
| codex-0.144.4-r2 | codex.chatgpt.oauth | gpt-5-codex | observed_unverified |
| codex-0.144.4-r2 | codex.chatgpt.oauth | gpt-5.6-sol | observed_unverified |
| codex-0.144.4-r2 | codex.chatgpt.oauth | gpt-5.4-mini | observed_unverified |
| grok-1.0.4-r2 | grok.grok_com.account | grok-4.6 | observed_unverified |
| grok-1.0.4-r2 | grok.grok_com.account | grok-4.5 | observed_unverified |

`support_tier` is authored only by hand-editing that JSON. Nothing in
`certification_minting` or `certification_evidence` writes it. The literal `"tested"`
appears in exactly two places in the whole `api/src` tree outside tests: the
`SupportTier` type alias in `harnesses/compatibility.py`, and
`harnesses/resolver.py::_default_eligible`.

### E2. The release binds. Targets are healthy. Everything is `observed_unverified`.

Contrary to the framing that "no compatibility release binds": every harness binds its
release cleanly on this executor.

```
HARNESS claude  release=claude-2.1.211-r2 connections=1 targets=10 enabled=True
HARNESS codex   release=codex-0.144.4-r2  connections=1 targets=5  enabled=True
HARNESS grok    release=grok-1.0.4-r2     connections=1 targets=2  enabled=True
```

`launch_options` returns 17 options, `launchable=True` on all 17,
`support_tier=observed_unverified` on all 17, `exclusion_reasons=()` on all 17. Confirmed
independently through the live backend: `GET http://127.0.0.1:8798/v1/harnesses` reports
`launch_options: 10/5/2, launchable: 10/5/2, optin: 10/5/2, tiers: ['observed_unverified']`.

Two distinct mechanisms produce that tier, and both are active:

1. `harnesses/resolver_targets.py::decorate_target` falls back to `observed_unverified`
   when no catalog edge matches `(route_id, observation.native_model_id)`. The probe
   enumerates CLI selectors (`opus`, `sonnet`, `fable[1m]`, `gpt-5.5`); the catalog
   names canonical ids (`claude-opus-4-8`, `claude-sonnet-5`). **Zero of claude's 10
   observed targets match an edge** (`canonical_model_id=None` on all ten). Codex matches
   1 of 5 (`gpt-5.6-sol`); grok matches 2 of 2.
2. For the three that *do* match, the edge itself says `observed_unverified` (E1).

So even repairing the identity mismatch would change nothing while E1 stands.

### E3. Every default resolution rejects, on every harness

`resolve_target` with `model_id=None`:

```
claude -> target_unavailable {'reason': 'no_default_target'}
codex  -> target_unavailable {'reason': 'no_default_target'}
grok   -> target_unavailable {'reason': 'no_default_target'}
```

`harnesses/resolver.py::_default_eligible` requires `support_tier == "tested"`. No target
satisfies it, so `_select_edge`'s final branch returns `no_default_target`.

### E4. Every explicit resolution rejects, on all 17 targets

`resolve_target` with each observed selector: `target_unverified_opt_in_required` on all
17, from `harnesses/resolver.py::_validate_explicit_edge`.

### E5. `allow_unverified_target=True` resolves cleanly and produces a real cell

Same live snapshots, one field flipped:

```
claude/best      -> RESOLVED  cell=VerificationCell(harness='claude', model='best',    effort=None)
codex/gpt-5.2    -> RESOLVED  cell=VerificationCell(harness='codex',  model='gpt-5.2', effort='medium')
grok/grok-4.5    -> RESOLVED  cell=VerificationCell(harness='grok',   model='grok-4.5',effort=None)
```

One boolean is the entire distance between the current state and a verifiable cell.

### E6. `allow_unverified_target` has no production writer

Whole-repo grep. `harnesses/resolver.py:71` declares it, `harnesses/resolver.py:471`
reads it, and the only assignments are in four test modules
(`test_resolver.py`, `test_resolver_launch_options.py`, `test_resolver_model_identity.py`,
`test_state_refresh.py`). The single production construction site,
`api/v1/capture_rpc_routes.py::_resolve_launch_target`, builds

```python
ResolverRequest(kind="native", harness_id=harness_id, model_id=domain.model, effort=domain.effort)
```

and takes the `False` default. `PrepareCaptureRequest` (capture_rpc_routes.py:112-160) has
no opt-in field, and the MCP `launch` tool
(`api/v1/controlplane_mcp.py::create_control_plane_mcp.launch`) accepts
`workdir, harness, dispatch_id, model, effort, agent, name, first_prompt, grant` and
nothing else. The other production construction site,
`harnesses/access_verification.py:198`, also takes the default.

`docs/LAUNCH-CONTRACT.md:96` states the contract: "`observed_unverified` requires explicit
selection and `allow_unverified_target=true`". The resolver half is implemented. The
client half was never built.

### E7. Launches succeed because the route reads the advisory conditionally

`api/v1/capture_rpc_routes.py::_resolve_launch_target`:

```python
resolution = resolve_target(resolver_request, snapshots)
verification = launch_verification_cell(harness_id, resolution)   # unconditional
model, effort = domain.model, domain.effort
advisories: tuple[LaunchAdvisory, ...] = ()
if model is not None or effort is not None:                        # conditional
    try:
        model, effort, advisories = launch_target_advisory(resolver_request, resolution)
    except LaunchTargetRejected as exc:
        _raise_capture_error(...)
```

Measured, both branches:

- **CMDK (no model, no effort).** `launch_target_advisory` is never called, so
  `target_unavailable/no_default_target` never becomes an error. The harness picks its own
  default. Launch succeeds. Had the advisory been read, it would have raised:
  `harnesses/launch_target.py::_passes_to_harness` forwards `target_unavailable` only when
  `details["reason"] == "not_observed"`, and this is `no_default_target`.
- **Explicit model.** `_passes_to_harness` returns `True` for
  `target_unverified_opt_in_required`, so the rejection becomes an advisory. The requested
  model passes through as `rejection.details["model_id"]`. Launch succeeds, and the code
  lands in `launch_fields["launch_advisories"]` as
  `{"code": "target_unverified_opt_in_required", "details": {"model_id": "opus"}}`.

### E8. Verification declines at INFO, into nothing durable

`launch_verification.py::LaunchVerificationCoordinator.submit`:

```python
if not isinstance(cell, VerificationCell):
    reason = None if cell is None else cell.reason
    logger.info("launch baseline verification skipped: no verification cell reason=%s", reason)
    return False
```

`main.py::LOG_CONFIG` sets root level `INFO` with a single `StreamHandler` to console, so
the line *is* emitted. PID 36819's stdout is a tty with no file sink, and
`~/.transport-matters-preview/runtime/` holds only `access-verification/` and
`shared-proxy/` (no desktop log record). The decline is written to a scrollback buffer and
nowhere else. No table, no artifact, no API field records that a verification was declined.

### E9. Nothing downstream would block a capture on this machine

Every gate behind `submit`, checked live:

| gate | symbol | live result |
| --- | --- | --- |
| coordinator on `app.state` | `main.py::lifespan` | present. Created whenever `services.session_pool is not None`; the pool is up (the inventory route requires it and returns 200). The desktop path uses the **same** factory: `cli/desktop_cmd.py:470` calls `uvicorn.Config(create_app())`, and `main.py::create_app` passes `lifespan=lifespan`. No separate desktop wiring exists. |
| provider + executor attribution | `api/v1/launch_verification_routes.py::schedule_prepared_launch_verification` | `wire_provider` non-null for all three (`anthropic`, `codex`, `grok`); the access receipt is written into `launch_fields` earlier in the same function that resolves the target. |
| compatibility facts | `launch_verification.py::_run_candidate` -> `read_compatibility_facts(spawn_spec.storage_dir)` | 12 `compatibility.json` files exist under `~/.transport-matters-preview/workspaces/`, all 12 written today. Not a gate here. |
| quota | `read_known_quota_decision` | `run_live_status` holds zero `usage_limit_reached` rows of any kind. Returns `UNKNOWN`, which proceeds. |
| runtime template | `resolve_capture_baseline_template` | resolves for all three to `tm-capture` at `~/.agent-runtimes/runtimes/tm-capture`. |
| capture due | `_capture_is_due` | `~/.transport-matters-preview/baselines` does not exist, so no bundle and no attempt record. Returns `True`. |

`~/.transport-matters-preview/runtime/baseline-verification` also does not exist, which
confirms `_verify_under_lock` has never been entered on this channel.

### E10. The operator has no baseline surface at all

- `GET /v1/harnesses` has **no `baselines` field**. The only key matching `baseline*` in the
  live response is `channel.baseline_version`, which is the compatibility release's blessed
  *harness* version (`2.1.211`, `0.144.4`, `1.0.4`) and has nothing to do with wire
  baselines. It is non-null. The reported `baselines=None` does not correspond to anything
  this API serves.
- `www/packages/core/src/types/harnessInventory.ts:113` types `baseline_version`, and no
  component reads it. Grep across `www/packages/*/src` and `desktop/src`: zero renders.
- `HarnessInventoryActivity` (`harnesses/inventory.py:87`) has exactly two phases,
  `refreshing` and `verifying_access`. Baseline verification has no phase.
- `baseline_staleness.py::assess_baseline_staleness` has **zero production callers**. Its
  own docstring claims "the launch gate and the inventory projection both ask the
  question"; the only caller in the repo is `test_baseline_source_identity.py:128`.

The one advisory the operator does see, `effort_policy_unverified`, comes from
`harnesses/effort_policy.py::effort_policy_advisories` and means claude's *effort
vocabulary* has not been verified for this version. It is unrelated to baselines and
explains nothing about them.

### E11. The launch view advertises an opt-in that no API accepts

Live `project_harness_launch_view` over the live inventory: all three harnesses report
`launchable: true`, and every one of the 17 models carries
`"requires_unverified_opt_in": true`. Claude and codex render as
`VaryingEffortHarnessView` with the flag inline on each model; grok renders as
`UniformEffortHarnessView` with both models in `deviations`.

An agent reading the MCP `harnesses` tool is told, per model, that opt-in is required. Per
E6 there is no parameter to supply it. The advisory is unactionable by its own audience.

---

## Concrete issues

### I1. The catalog ships no `tested` edge, which disables both `tested`-gated resolver decisions

**Where:** `harnesses/compatibility_releases_v1.json` (all 9 `targets[].support_tier`);
consumed by `harnesses/resolver.py::_default_eligible` and
`harnesses/resolver.py::_validate_explicit_edge`.

**Failure:** An operator opens CMDK and launches claude. `resolve_target` returns
`target_unavailable/no_default_target`. `launch_verification_cell` returns
`NoVerificationCell(reason='target_unavailable')`. The coordinator logs one INFO line and
returns `False`. The run proceeds normally and the operator sees a working product. This
repeats for every launch, forever, on every harness and every channel, because the input
that would change the outcome is a static file in the wheel. Preview has done this 9 times
today.

### I2. `allow_unverified_target` is a contract with no client

**Where:** `harnesses/resolver.py::ResolverRequest.allow_unverified_target` (declared),
`harnesses/resolver.py::_validate_explicit_edge` (enforced),
`api/v1/capture_rpc_routes.py::PrepareCaptureRequest` and
`api/v1/controlplane_mcp.py::launch` (no field), `docs/LAUNCH-CONTRACT.md:96` (specified).

**Failure:** An operator reads the MCP launch view, sees
`{"id": "opus", "requires_unverified_opt_in": true}`, and tries to opt in. There is no
parameter. Calling `launch(model="opus")` returns 409 `target_unverified_opt_in_required`
if effort is also named, or launches with the advisory buried in `launch_fields` if it is
not. The product states a precondition it gives no way to satisfy. This is the single
change that would make E5's cell real.

### I3. Every verification decline is invisible

**Where:** `launch_verification.py::LaunchVerificationCoordinator.submit` (the `INFO`
branch), `harnesses/inventory.py::HarnessInventoryActivity` (no phase), the inventory
response (no field).

**Failure:** The operator has run preview for weeks with `PR #436` merged and believes
launch-triggered verification is working. Nothing in the UI, nothing in
`GET /v1/harnesses`, nothing in the MCP launch view, and no row in any table records that
17 cells have been declining verification on every launch. The only evidence is a console
line in a tty that has since scrolled. This is why the condition survived undetected long
enough to need a diagnostic.

### I4. `assess_baseline_staleness` is dead code whose docstring claims two live callers

**Where:** `baseline_staleness.py::assess_baseline_staleness`.

**Failure:** A reader trusting the docstring ("the launch gate and the inventory projection
both ask the question") concludes staleness is surfaced somewhere and looks for the bug in
the surface. It is not surfaced anywhere. The function is called only by
`test_baseline_source_identity.py`. The module's careful `unknown`-is-a-third-state
reasoning currently protects nothing.

### I5. The probe's native identity and the catalog's native identity disagree

**Where:** `harnesses/resolver_targets.py::decorate_target`
(`edges_by_native_identity.get((route_id, observation.native_model_id))`), against the
probe output in `harness_target_observation.native_model_id`.

**Failure:** Claude's catalog names `claude-opus-4-8`; the probe observes `opus`. All ten
claude targets miss their edge, so `canonical_model_id` is `None`, `lifecycle` silently
defaults to `active`, and `launch_adapter_revision` falls back to the release-level value
rather than the edge's. A future release that marks `claude-opus-4-8` `retired` or
`tested` would have no effect on this executor: the edge is never found. Codex is
partially affected (1 of 5 matches); grok is clean (2 of 2). This is masked by I1 today
and would surface the moment I1 is fixed for claude.

### I6. `certification_evidence._check_launch_profile` cannot pass against this evidence

**Where:** `harnesses/certification_evidence.py::_check_launch_profile`.

**Failure:** It builds `resolved` from `launch_options(...)` as
`(route_id, canonical_model_id or model_id, effort)` and compares it for equality against
`release_edge_set(entry)`. With claude's canonical ids all `None` (I5), `resolved` is keyed
by `best`/`default`/`opus`/... while `expected` is keyed by `claude-opus-4-8`/... The sets
cannot be equal, so minting raises `CertificationMintingError`. This is an offline
authoring gate, not an operator-facing path, so it degrades the ability to *mint* a
release with `tested` edges rather than the ability to run. Marked INFERRED below since I
did not execute minting.

---

## Answers

### Q1. Why a launch succeeds while verification refuses, on the same resolution

**Two causes, and neither is a bug.**

The first is `harnesses/launch_target.py`, whose module docstring states the split
explicitly:

> One resolution is read two ways here, and the split is load bearing.
> `launch_target_advisory` decides what the harness is told and raises on the rejections a
> launch must not survive. `launch_verification_cell` decides which concrete cell that
> launch will exercise and never raises, because a launch the caller left to the harness's
> own default must not begin failing on a resolution it never asked for.

`launch_verification_cell`'s own docstring then names this exact case:

> The rejections `launch_target_advisory` forwards to the harness land here too: an
> unverified target or an effort the model does not take still launches, and still
> resolves to no tuple worth verifying.

So `target_unverified_opt_in_required` is, by written design, survivable for actuation and
fatal for the cell. `_passes_to_harness` whitelists it; `launch_verification_cell` maps
every rejection to `NoVerificationCell(reason=rejection.code)`.

The second cause covers the CMDK case, and it is in the route rather than in
`launch_target.py`: `_resolve_launch_target` calls `launch_target_advisory` only when the
caller named a model or an effort. Its docstring:

> The cell is read unconditionally, because a launch that named no model still exercises
> one. The actuation is read only when the caller named a model or an effort, which is
> what it did before: a caller who named neither is asking the harness to choose, and
> resolving on its behalf would both overwrite that request and expose the launch to
> rejections it never used to face.

A CMDK launch resolves to `target_unavailable/no_default_target`, which is **not**
whitelisted by `_passes_to_harness`. It launches only because the advisory is never read.

**Deliberate, not an accident of #434.** The commit message for `ca8f2f8b` (#434) states
the intent in advance and in terms of exactly this condition: "A defaulted launch never
asked this resolver anything, so it must not begin failing on it: a harness with no tested
target still launches, and the answer is `NoVerificationCell`, never a guess."

The design is sound. Its premise, that *some* target is `tested`, is false in the shipped
catalog (I1). #434 built a correct mechanism on top of an input that never arrives.

### Q2. Is refusing to verify an unverified target correct?

**No. Nothing breaks if verification accepts one, and the refusal inverts the feature's
own purpose.**

Argued from the contracts:

1. **The stored artifact makes no certification claim.**
   `baseline_evidence.py::BaselineCell` carries `harness`, `provider`, `harness_version`,
   `launch_model`, `wire_model`, `request_shape`, `no_system_prompt`,
   `bypass_permissions`, `isolated_home`, `runtime_template`. There is no `support_tier`,
   no `release_id`, no certification field. A bundle captured for an `observed_unverified`
   cell asserts nothing that is false.

2. **No consumer keys off tier.** The only readers of the baseline store outside the
   verification path are `baseline_projection_store.py` (`read_current_gate_projections`,
   `read_gate_projection`) and its two CLI callers `baseline_compare.py` and
   `baseline_publish.py`. None consults `support_tier`, `LaunchOption`, or the resolver at
   all. `certification_evidence.py` never reads a baseline bundle; it reads compatibility
   facts and resolver edges.

3. **The store's own address does not include tier.**
   `launch_verification_lock_root` and `has_baseline_bundle_for_version` key on
   `(executor_id, harness, provider, model)` and `harness_version`. An unverified cell
   occupies its own address and collides with nothing.

4. **The unverified target is precisely the one lacking evidence.** The feature exists to
   spend 3 turns in an isolated home learning what an untested version puts on the wire.
   Gating that on the target already being tested makes the feature reachable only where it
   is least needed.

5. **The failure mode is already bounded.** If an unverified selector turns out to be
   bogus, `harvest_controlled_baseline` raises, `_verify_under_lock` writes
   `BaselineAttemptStatus.FAILED`, and `_capture_is_due` enforces a 24-hour cooldown. Cost
   of being wrong: one failed capture per cell per day.

**The counter-argument, stated fairly.** `_default_eligible`'s "defaults use tested,
active, locally ready targets only" is a *launch* policy: do not silently point an
operator at a target nobody certified. That policy is defensible for actuation. It has no
bearing on evidence-gathering, which is a different act with a different blast radius, and
`allow_unverified_target` already exists as the seam that separates the two.

**Owner's decision, framed:** verification should resolve with `allow_unverified_target=True`
regardless of what the actuation asked for, because it is an observation and not a launch.
The alternative, authoring `tested` edges into the catalog, fixes the symptom on three
hand-listed models and leaves every newly released model unverifiable on the day it ships,
which is the day the evidence matters most.

### Q3. Full blast radius of "zero resolvable targets"

Every consumer of a resolved target, and its behaviour in this state:

| # | Consumer | Symbol | Behaviour now |
| --- | --- | --- | --- |
| 1 | Capture route, cell read | `api/v1/capture_rpc_routes.py::_resolve_launch_target` | `NoVerificationCell` on **every** launch, all harnesses, all models. |
| 2 | Capture route, actuation read | same | Explicit model: launches with a `target_unverified_opt_in_required` advisory in `launch_fields`. Explicit model **and** effort: same. No model: advisory never read, launches on the harness default. |
| 3 | Launch verification | `launch_verification.py::LaunchVerificationCoordinator.submit` | Declines at INFO. Zero captures ever. `~/.transport-matters-preview/baselines` does not exist. |
| 4 | REST inventory | `harnesses/inventory.py::_harness_item` -> `launch_options` | Serves 17 launchable options, all `requires_unverified_opt_in: true`, all `support_tier: observed_unverified`, all `exclusion_reasons: []`. Live-confirmed. |
| 5 | MCP `harnesses` (launch view) | `api/v1/harness_launch_view.py::project_harness_launch_view` | All three `launchable: true`; every model flagged opt-in-required, with no way to opt in (I2). |
| 6 | MCP `harnesses` (full view) | `project_harnesses_view(view="full")` | Same inventory as #4. |
| 7 | MCP `launch` | `api/v1/controlplane_mcp.py::launch` | Works. No opt-in parameter, so an agent cannot act on what #5 told it. |
| 8 | Canvas first-run cards | `www/packages/canvas/src/firstrun/harnessCards.ts::supportFact` | Renders `Support: "Newer than blessed" / "blessed to 2.1.211, not compared yet"`, status **neutral**. That string is about the harness version against the blessed ceiling, not about targets. `requires_unverified_opt_in` and `support_tier` are typed in `www/packages/core/src/types/harnessInventory.ts:189,192` and **read by no component**. |
| 9 | Baseline harvest CLI | `baseline_harvest.py` | **Still works.** It reads the launch view's model list and calls `harvest_controlled_baseline` directly, bypassing the resolver's opt-in gate entirely. It requires a clean worktree (`require_clean_worktree(_source_root())`). This is the operator's current only route to a baseline. |
| 10 | Baseline comparison CLI | `baseline_compare.py` | No baselines exist to compare, so the drift gate has nothing to run against on this channel. |
| 11 | Release minting | `harnesses/certification_evidence.py::_check_launch_profile` | Cannot pass for claude (I6, INFERRED). Offline authoring path only. |
| 12 | Access verification | `harnesses/access_verification.py:198` | Constructs its own `ResolverRequest(model_id=None)`. Unaffected in outcome: `access` reads `available` for all three connections in the live inventory. |
| 13 | Baseline staleness | `baseline_staleness.py::assess_baseline_staleness` | Not called by anything (I4). |

**Degraded count: 5** (#1, #3, #5+#7 as one unactionable pair, #10, #11). Working but
uninformative: #4, #6, #8. Unaffected: #2, #9, #12.

### Q4. Is the operator being told any of this?

**Effectively no.** Tracing every surface:

- **Canvas.** One neutral fact, `Support: Newer than blessed / not compared yet`. It refers
  to the harness version against the blessed ceiling and would read identically on a fully
  certified machine that happens to run a newer CLI. Nothing about targets, tiers, opt-in,
  or baselines. The two fields that carry the real state are typed in TypeScript and
  rendered nowhere.
- **`GET /v1/harnesses`.** Carries the truth structurally, in
  `launch_options[].support_tier` and `launch_options[].requires_unverified_opt_in`, but
  frames it as `launchable: true` with an empty `exclusion_reasons`. An operator reading
  this response sees a healthy harness. There is no baseline field of any kind.
- **MCP launch view.** Carries `requires_unverified_opt_in: true` per model. This is the
  clearest signal in the product, and it is addressed to agents, not to the operator, and
  it names a remedy that does not exist.
- **The one advisory that does surface**, `effort_policy_unverified`, is about claude's
  effort vocabulary. An operator reasonably reads "unverified" as the answer and stops
  looking. It is a different subsystem.
- **Logs.** One INFO line per declined launch, to a tty, with no file sink on this channel.
- **Tables.** Nothing. No attempt row is written when the cell is absent, because
  `start_baseline_attempt` runs inside `_verify_under_lock`, which is never reached.

**This is itself the most consequential issue (I3).** A verification feature whose entire
failure mode is one INFO line will always be discovered by diagnostic rather than by
operation.

### Q5. Other silent-decline paths that would still block a capture

**None on this machine.** Fixing the resolver would make it fire.

Every gate in `submit` and `_run_candidate`, in order, measured (full table in E9):

1. `diagnostic_test` — false for an ordinary launch.
2. `not isinstance(cell, VerificationCell)` — **the current stop.**
3. `provider is None or executor_id is None` — both present.
4. `read_facts(facts_root)` returning `None` — facts are written; 12 `compatibility.json`
   on disk, all written today.
5. `facts.harness_id != cell.harness` — raises rather than declines; same resolution feeds
   both.
6. `quota is USAGE_LIMIT_REACHED` — zero `usage_limit_reached` rows in `run_live_status`.
7. `tasks.submit` capacity (`BoundedSemaphore(2)`) — logs at ERROR, and only under 3+
   concurrent verifications.
8. `submit_blocking` worker capacity — ERROR, same bound.
9. `_capture_is_due` — no bundle, no attempt record, returns True.
10. `WorkspaceLocked` — no lock directory exists.
11. `runtime_template_resolver` — resolves for all three to `tm-capture`.

**Coordinator on `app.state`, desktop path specifically:** present. There is exactly one
app factory. `cli/desktop_cmd.py:470` calls `uvicorn.Config(create_app())`;
`main.py::create_app` sets `lifespan=lifespan`; `main.py:431` creates the coordinator
whenever `services.session_pool is not None`. The session pool is up on this backend (the
inventory route returns 200, and `optional_session_pool` is its precondition). No
desktop-specific wiring exists to diverge.

**One residual risk, not currently active.** `self.source_identity(self.source_root)` is
evaluated inside `_verify_under_lock`. `identify_runtime_source` falls back to
`importlib.metadata.version("transport-matters")` when the checkout is absent, which would
raise in a packaged build with no git checkout and no installed distribution metadata. Here `_SOURCE_ROOT`
resolves to `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` and
`identify_runtime_source` returns `git_commit d4ce12a5a398fe841c5e1ac64bac713320f01c4a`,
so it succeeds (measured). In a shipped `.app` it
would fail into `_run_candidate`'s `except Exception: logger.exception(...)` — at ERROR,
so louder than the current decline, but still log-only.

**Next-gate count: 0.**

---

## INFERRED

Marked separately because I did not execute these paths.

- **I6, minting.** `_check_launch_profile` compares `resolved` against
  `release_edge_set(self._entry)` for set equality. Given claude's ten `canonical_model_id`
  values are all `None` (measured) and the catalog's four edges are keyed by canonical id
  (measured), the sets cannot match and `CertificationMintingError` follows. I did not run
  the minting CLI.
- **Repair ordering.** Setting `allow_unverified_target=True` on the verification read
  would produce a cell for all 17 targets (E5 measured for 3 of 17, one per harness) and,
  per Q5, no further gate would stop the capture. I did not execute a capture, as the brief
  forbids provider turns.

## Explicitly NOT attributed to this condition

Two things measured on the live channel that look related and are not. Recording them so
they are not mis-assigned:

- **`harness_drift_evidence.model_id` is NULL on all 64 rows**, so
  `harnesses/blocks.py::attribute_drift_evidence` returns
  `pause_release/unresolved_context` for every one and no executor block can ever be
  created from runtime drift. This is **pre-existing and deliberate**, not a consequence of
  zero resolvable targets: `harnesses/drift_emitter.py::DriftEmitter.evidence_fields` never
  populates `release_id`, `route_id`, or `model_id`, and says so — "Resolved launch context
  (release, route, model) is intentionally absent until S2f records it; the attribution
  policy pauses instead of creating blocks, which is the S2d.1 contract." Drift is still
  being observed: claude `transcript_record_shape_mismatch` at 07:22 today, codex
  `unknown_response_event` at 07:01.
- **9 open `model_rejected` rows in `run_live_status`.** Joining to `event.model` returns
  `<synthetic>` for all nine, so these are not provider rejections of a launched selector.
  Not evidence of launch-target damage.
