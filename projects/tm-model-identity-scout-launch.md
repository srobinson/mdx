---
title: Transport Matters model identity scout for launch and surfacing
type: projects
tags: [transport-matters, model-identity, harnesses, launch, control-plane]
summary: Source map and implementation plan for keeping launch selectors separate from observed wire identity
status: active
project: transport-matters
confidence: high
created: 2026-08-22
updated: 2026-08-22
---

# Transport Matters model identity scout for launch and surfacing

## Scope

This report covers the launch and surfacing side of model identity. It does not cover comparator behavior or baseline keying.

The source baseline is clean `main` at `03dc8d62b07f93e5462073fbfd2e45203c73f01e`. The scout performed no repository writes, branch operations, harness launches, provider calls, or tests.

The governing distinction is already present in `api/src/transport_matters/baseline_evidence.py :: BaselineCell`: `launch_model` is the selector passed to the harness, while `wire_model` is the identity observed in provider traffic. The launch path must keep using the selector. Resolved identity is display and reasoning evidence.

## Reuse Map

### Harness binaries own the observed launch catalog

Transport Matters reads the installed binaries directly.

- `api/src/transport_matters/harnesses/probes/claude.py :: MODEL_ENUMERATION_PROBE` runs `-p /model` and `-p /effort`. `_parse_model_enumeration` parses the result.
- `api/src/transport_matters/harnesses/probes/codex.py :: MODEL_ENUMERATION_PROBE` runs `debug models --bundled`. `_parse_model_enumeration` keeps models with `list` visibility.
- `api/src/transport_matters/harnesses/probes/grok.py :: COMBINED_REFRESH_PROBE` runs `models`. `_parse` returns authentication and model evidence together.
- `api/src/transport_matters/harnesses/probes/runner.py :: run_model_enumeration_probe` executes the installed binary and returns `tuple[EnumeratedModel, ...] | None`.
- `api/src/transport_matters/harnesses/probes/__init__.py :: EnumeratedModel` contains `model_id`, `effort_options`, and optional `default_effort`. Its docstring calls `model_id` a launch selector.

Claude and Codex cache the catalog in Postgres.

- `api/src/transport_matters/harnesses/state_refresh.py :: _refresh_target_snapshot` skips enumeration only when every cached row matches the exact harness version and probe revision and has complete, successful evidence.
- `api/src/transport_matters/harnesses/state_refresh.py :: _record_target_models` converts the result to `LocalTargetObservation` rows.
- `api/src/transport_matters/harnesses/connections_store.py :: ExecutorEvidenceStore.record_target_snapshot` writes an atomic snapshot scoped by executor and harness.
- `api/src/transport_matters/harnesses/connections_store.py :: ExecutorEvidenceStore.latest_target_observations` reads the cached snapshot.

A version change, probe revision change, incomplete row, or failed row causes Claude and Codex to enumerate again. An empty or failed enumeration keeps the last complete snapshot. Grok uses its combined probe on every refresh and keeps the prior model snapshot when parsing fails.

### Agent runtime metadata has a separate owner

Transport Matters also reads agent runtime artifacts, but they do not define the harness model catalog.

- `api/src/transport_matters/runtime_registry.py :: _list_runtime_templates_in_root` discovers `capabilities.json` and requires a sibling `runtime.toml` as a marker.
- `api/src/transport_matters/runtime_registry.py :: read_runtime_template_capabilities` parses `capabilities.json`.
- `api/src/transport_matters/runtime_registry.py :: _default_target` projects the generated `recommended_model` into agent catalog defaults.
- `api/src/transport_matters/runtime_templates.py :: RuntimeTemplateCapabilities` defines the generated artifact shape.

Transport Matters does not parse `runtime.toml` in this read path. The installed harness binary is authoritative for observed launch selectors and efforts. The compatibility release owns support, route, and lifecycle classification. `capabilities.json` owns agent template metadata and recommendations.

### Existing launch machinery already carries the selector

The controlled baseline path starts with an explicit selector.

- `api/src/transport_matters/baseline_harvest.py :: main` requires `--model` when a harness is selected.
- `api/src/transport_matters/baseline_harvest.py :: _select_model` requires an exact match in the enumerated launch view.
- `api/src/transport_matters/baseline_capture.py :: _run_probe` assigns the selected `EnumeratedModel.model_id` to `CapturedRunRequest.model`.
- `api/src/transport_matters/captured/invocations.py :: ClaudeInvocationBuilder.build`, `CodexInvocationBuilder.build`, and `GrokInvocationBuilder.build` pass the value to each harness invocation.
- `api/src/transport_matters/cli/launch_profile.py :: _model_argv` renders `--model <value>` without interpreting the value.
- `api/src/transport_matters/captured_turn.py :: run_captured_turn` launches the rendered child command.

The normal launch path preserves the same actuation contract.

- `api/src/transport_matters/controlplane/run_models.py :: LaunchRequest` receives raw requested intent.
- `api/src/transport_matters/controlplane/launch_service.py :: ControlPlaneLauncher._execute` sends that intent to the gateway.
- `api/src/transport_matters/api/v1/capture_rpc_routes.py :: _resolve_launch_target` validates or resolves the requested selector and effort.
- `api/src/transport_matters/harnesses/launch_target.py :: resolve_launch_target_advisory` passes an unknown explicit model to the harness with an advisory when the only problem is missing target observation.
- `packages/runtime/src/service/RunManager.ts :: RunManager.createNew` spawns the client command returned by Python without rebuilding the model argument.

The claim that Claude accepts only aliases is false. `api/src/transport_matters/harnesses/probes/claude.py :: _MODEL_LIST_PATTERN` parses native output that also advertises a full model ID. `_model_argv` accepts any string. The controlled baseline command is narrower because it accepts only an enumerated selector.

Resolved identity must not affect these launch facts:

- An explicit selector remains the value passed to `--model`.
- An omitted selector continues to omit the flag and lets the harness choose its default.
- `best` and `opusplan` remain valid launch policies even when neither has one fixed wire model.
- `api/src/transport_matters/controlplane/launch_service.py :: _intent_fingerprint` continues to hash raw requested intent.
- `api/src/transport_matters/controlplane/run_models.py :: LaunchResult.model` continues to describe requested intent until the field is renamed truthfully.

### Existing evidence can support identity without another capture system

Three existing owners contain the required facts.

- `api/src/transport_matters/baseline_evidence.py :: BaselineCell` stores both `launch_model` and `wire_model` with the exact harness version and the A/B/A evidence bundle.
- `api/src/transport_matters/baseline_store.py :: read_current_baselines` reads the current promoted bundles for one harness and provider.
- `api/src/transport_matters/wire_store_observer.py :: WireStoreObserver.on_outbound_request` sees and persists the normalized wire model before provider completion.

The live capture boundary lacks one fact. `api/src/transport_matters/shared_proxy/binding.py :: ProxyRunBinding` carries the harness and launch fields but does not carry the selected launch model or exact observed harness version. `WireStoreObserver._submit_exchange` therefore cannot relate `entry.model` to the selector without an unsafe join.

`api/src/transport_matters/harnesses/access_verification.py :: _verification_request` already spends one default model turn when exact version access evidence is missing. If that request carries the selected launch model, its outbound wire request can supply default identity evidence without another provider call.

### Existing refresh owners remove the need for a scheduler

- `api/src/transport_matters/main.py :: _start_session_backed_services` creates the shared `refresh_harness_state` callable over `ExecutorEvidenceStore`.
- `api/src/transport_matters/main.py :: lifespan` starts one guarded `run_startup_refresh` task.
- `api/src/transport_matters/harnesses/state_refresh.py :: run_startup_refresh` preserves the last evidence on failure.
- `api/src/transport_matters/api/v1/harnesses.py :: refresh_harnesses` invokes the same refresh owner on demand under a lock.
- `api/scripts/refresh_harness_state.py :: _refresh` invokes the same owner for an explicit channel and database.

The cache miss inside `_refresh_target_snapshot` is the exact version change seam. It can reset identity for the new version to unresolved and then accept evidence from current baselines or later captured traffic. No recurring scheduler is needed.

### Current launch and observation views collapse distinct meanings

The launch view follows this path:

`state_refresh.py :: _record_target_models`
to `resolver_snapshots.py :: resolver_snapshots_for_harness`
to `inventory.py :: _harness_item`
to `resolver.py :: launch_options`
to `harness_launch_view.py :: project_harness_launch_view`.

`api/src/transport_matters/harnesses/resolver.py :: launch_options` assigns `LaunchOption.model_id` from `LocalTargetObservation.native_model_id`. `api/src/transport_matters/api/v1/harness_launch_view.py :: _project_models` publishes that value as a model. The result contains the launch selector, with no wire identity, source, scope, or confidence.

The control plane launch response follows raw intent.

- `api/src/transport_matters/controlplane/run_models.py :: LaunchResult.model` echoes the requested value.
- `api/src/transport_matters/api/v1/capture_rpc_routes.py :: _resolve_launch_target` reduces `ResolvedTarget` to model and effort strings for actuation.
- `api/src/transport_matters/capture_rpc.py :: capture_spawn_spec_payload` does not return resolved identity.

The observer and director roster silently changes authority after the first turn.

- `packages/runtime/src/service/RunManager.ts :: RunManager.register` stores the raw requested model in launch facts.
- `api/src/transport_matters/controlplane/roster_projection.py :: project_roster` receives that value as `GatewayActivityRun.model`.
- `api/src/transport_matters/session/controlplane_statements.py :: GET_LAST_TURNS_FOR_RUNS_FOR_OWNER_SQL` reads the latest transcript `event.model`.
- `api/src/transport_matters/controlplane/roster_projection.py :: _accepted_model` returns the requested model before a primary turn and the transcript model after one.
- `api/src/transport_matters/controlplane/observe_models.py :: RosterItem.model` exposes both meanings through one field. `RosterItem.effort` always remains launch intent.

Observer and director grants receive the same read model. `SelfIdentityResult` contains no model. `WorkspaceSummaryResult` intentionally omits per run detail.

### One catalog relation exists and the resolver drops it

`api/src/transport_matters/harnesses/compatibility.py :: HarnessModelCompatibility` already has both `model_id` and `native_model_id`. The current embedded release data uses equal values for every target.

`api/src/transport_matters/harnesses/resolver.py :: _decorate_target` matches the compatibility edge by `native_model_id`, then discards the edge's `model_id`. `_find_offered_target`, `resolve_target`, and `launch_options` continue with the native selector. A future release with different values would lose the canonical identity before launch view projection.

This pair is underused. The implementation should preserve the existing relation and add policy aware evidence to it or to the existing target observation. It should not add a parallel alias catalog.

### No semantic alias mapping exists elsewhere

`api/src/transport_matters/model_ids.py :: normalise_model` and `denormalise_model` only add or remove provider prefixes. Anthropic, Codex, and Grok adapters use them. They contain no alias semantics, evidence, or confidence.

Outside baseline bundles, no first class record relates a selected alias to a captured wire model. The roster temporarily has both inputs, but `_accepted_model` returns one and discards the relation. `WireExchangeWrite.model` stores wire identity without the launch selector.

The negative searches were:

```text
rg -n -i "model[_ -]?identity|alias[_ -]?(resolution|mapping|observation)|wire[_ -]?model.*alias|alias.*wire[_ -]?model" api/src www/packages packages -g '*.py' -g '*.ts' -g '*.tsx'
rg -n -i --glob '!api/src/transport_matters/baseline*' --glob '!api/src/transport_matters/test_baseline*' "(run_)?model_(identity|evidence|source|confidence|resolution|provenance)|resolved_model|model_provenance|model_confidence|identity_confidence" api packages www shared docs
rg -n "launch_model|wire_model" api/src www/packages packages -g '*.py' -g '*.ts' -g '*.tsx'
rg "tomllib.*runtime\.toml|runtime\.toml.*tomllib|read_text\([^\n]*runtime\.toml" api/src/transport_matters --glob '*.py'
```

The first two searches found no production identity owner. The third confined the explicit launch to wire relation to baseline modules and tests. The fourth found no runtime manifest parser.

### `target_unavailable` is a stored snapshot outcome

`api/src/transport_matters/harnesses/state_refresh.py :: _refresh_harness` stores installation evidence, then returns before enumeration when no embedded release exists. A later release does not populate targets until another refresh.

With no target rows, `api/src/transport_matters/harnesses/resolver.py :: launch_options` returns no options. `api/src/transport_matters/api/v1/harness_launch_view.py :: _project_harness` creates `UnavailableHarnessView`. `_unavailable_reason` falls back to `target_unavailable` when compatibility supplies no earlier reason.

Resolved identity must remain optional so this path stays truthful. Missing resolution cannot make an enumerated launch selector unavailable.

## Quality Map

### The current type names hide the selector boundary

`EnumeratedModel.model_id` is a launch selector. `_record_target_models` writes it to `LocalTargetObservation.native_model_id`. `launch_options` publishes it as `LaunchOption.model_id`. These names imply a stable model identity even when the value is `best` or `opusplan`.

The same defect appears in the roster. `RosterItem.model` starts as launch intent and later becomes transcript evidence. A consumer cannot know which meaning it received.

### The repository cannot represent a policy alias

One wire model string plus a confidence label is insufficient. The data model needs explicit states for unresolved identity, identity observed under a named probe shape, and per turn resolution. An observed wire model must retain the exact harness version, source, observation time, and probe scope.

Three equal trivial turns support only this statement: the selector produced one wire model under that probe shape. They do not prove that the selector is fixed. Multiple observed wire models for one selector and version establish per turn behavior.

`opus` and `opus[1m]` must remain separate launch selectors even when they share one wire identity. Their equal request schemas do not prove equal context capability because path, query, and headers are outside the captured body. Effort has the same observability gap.

### The canonical compatibility identity is dormant

`HarnessModelCompatibility.model_id` participates in certification and target block keys, but `_decorate_target` drops it. Current equal values conceal the defect. A divergent pair can cause the launch view to show the selector, prevent canonical selection, and miss a target block keyed by the canonical model.

### The baseline command reconstructs a domain type from presentation data

`api/src/transport_matters/baseline_harvest.py :: _enumerated_models` rebuilds `EnumeratedModel` from the launch view instead of selecting from `HarnessInventoryItem.launch_options` or stored target observations. The uniform effort path drops per model default effort and ignores deviations. The command already loaded the full inventory, so the reconstruction duplicates an existing owner.

`baseline_harvest.py :: _select_model` also has an unreachable `requested is None` branch. `main` rejects a missing `--model`, and the only production call passes the required string.

### Startup catalog refresh must remain free of provider traffic

The current refresh pass observes installation, catalog, authentication, and stored evidence. Silently adding billed provider turns would cross the state observation and provider actuation boundary. Version changes should invalidate identity and accept later evidence. Exhaustive warming belongs to the existing explicit baseline harvest command.

### Sizing constrains placement

| File and symbol | Current size | Constraint |
| --- | ---: | --- |
| `api/src/transport_matters/harnesses/state_refresh.py :: _refresh_harness` | 441 line file, 141 line function | Keep identity work out of this function. It is close to the 150 line limit. |
| `api/src/transport_matters/main.py :: lifespan` | 645 line file, 121 line function | Reuse existing injection points. The file has 55 lines before the hard limit. |
| `api/src/transport_matters/baseline_capture.py :: harvest_controlled_baseline` | 404 line file, 125 line function | Keep identity observation separate from comparator assembly. |
| `api/src/transport_matters/captured/run.py :: prepare_captured_run` | 474 line file, 167 line function | Refactor before any change to this function. |
| `api/src/transport_matters/harnesses/resolver.py` | 668 lines | Move identity projection out before additions cross 700. |
| `api/src/transport_matters/harnesses/compatibility.py` | 638 lines | Extend narrowly or split target identity contracts first. |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py :: _resolved_domain_request` | 621 line file, 118 line function | Avoid adding display logic to this request boundary. |
| `api/src/transport_matters/controlplane/service.py` | 668 lines | Keep model projection in `roster_projection.py`. |
| `packages/runtime/src/service/RunManager.ts` | 685 lines | Do not add resolved identity machinery here. |
| `packages/runtime/src/server/runtimeRouter.ts :: registerRunRoutes` | 458 line file, 177 line function | Do not extend this function. Refactor first if a later requirement reaches it. |

Test files also constrain implementation. `api/src/transport_matters/test_captured_turn.py` has 692 lines. `api/src/transport_matters/test_wire_store_observer.py` has 670. Split either file before adding material coverage.

### Additional hygiene candidates

- `www/packages/core/src/types/harnessInventory.ts :: HarnessInventoryResponse` manually mirrors Python DTOs. `packages/AGENTS.md` assigns product to browser wire DTOs to `@tm/contract`. If this work changes the browser inventory contract, move the types to `@tm/contract` and delete the mirror in the same change.
- `packages/runtime/src/service/runManagerTypes.ts :: ManagedRunLaunchFacts` and `packages/activity/src/server/activityRouter.ts :: ActivityRuntimeLaunchFacts` duplicate a shape. The second may be a deliberate structural port. Do not merge them without checking the package boundary.
- `PrepareCaptureRequest.model`, `CapturedRunRequest.model`, and TypeScript launch inputs are unbranded strings. A broad branding migration would cross the assigned scope. Keep the new identity state typed and prevent it from reaching the existing launch argument.

## Cost of identity observation

`api/src/transport_matters/baseline_capture.py :: harvest_controlled_baseline` defines A1, B, and A2 and calls `_capture_probe` three times. `_capture_probe` creates a fresh isolated home. `_run_probe` launches one `run_captured_turn` with a unique delivery ID. The existing baseline cost for one selector is therefore three live provider turns.

A single outbound request is the cheaper evidence unit.

- `baseline_capture.py :: _build_probe_evidence` reads the wire identity from the parsed request.
- `wire_store_observer.py :: WireStoreObserver.on_outbound_request` persists that identity before provider completion.
- One `run_captured_turn` waits for a complete correlated turn and gives exact harness version evidence.

One outbound request can support "observed once under this launch shape." It cannot support "this selector is this model." A normal captured user turn costs no extra provider traffic and is the preferred passive source once the launch selector and version cross the proxy binding boundary.

## Plan

### 1. Make the existing target contract state the truth

Extend the existing target observation and compatibility contracts. Do not create a second catalog type or table.

- Give the launch selector a truthful field name in public contracts, such as `launch_model`.
- Preserve `HarnessModelCompatibility.model_id` when `_decorate_target` matches `native_model_id`.
- Represent identity as a discriminated state with these cases: unresolved, observed under a named scope, and resolves per turn.
- For an observed state, carry the wire model, exact harness version, source, observation time, probe scope, and observation count.
- For a per turn state, carry the observed wire models and the same provenance. Do not select one as the answer.
- Keep catalog support, lifecycle, and launchability separate from identity resolution. Missing identity must not produce `target_unavailable`.

Use the existing `harness_target_observation` row as the current cache. Add columns to that table only if the baseline and gate plan confirms that the compatibility release cannot carry the current evidence. Do not add a new table.

### 2. Populate identity from existing evidence owners

Use sources in this order:

1. Read exact version current bundles through `baseline_store.py :: read_current_baselines`. Convert the existing `BaselineCell` and its three probes into an observed under probe state.
2. Carry `launch_model` and exact harness version in `ProxyRunBinding`. Let `WireStoreObserver.on_outbound_request` add passive evidence to the existing target cache.
3. Reuse the already paid default request from `access_verification.py :: _verification_request` when it has complete selector provenance.

When the exact version cache misses, `_refresh_target_snapshot` must create current selector rows with unresolved identity. Later baseline or wire evidence fills them. A second wire model for the same selector and version changes the state to resolves per turn.

Do not run provider turns from `run_startup_refresh` or `POST /v1/harnesses/refresh`. Use the existing `baseline_harvest.py :: main` command when the operator explicitly requests exhaustive warming. Keep its three turn A/B/A confidence distinct from passive one request evidence.

### 3. Leave child actuation unchanged

- Resolve launchability against the launch selector.
- Return the launch selector from `resolve_launch_target_advisory` for `CapturedRunRequest.model`.
- Keep `_model_argv` unchanged.
- Keep omitted model behavior unchanged.
- Keep `best`, `opusplan`, and future router selectors invocable by selector.
- Keep full model ID pass through behavior and its advisory.
- Exclude resolved identity from `_intent_fingerprint`, idempotency keys, and child arguments.

No resolved identity field needs to cross Python `CapturedRunSpawnSpec`, TypeScript `CapturedRunSpawnSpec`, `runtimeRouter.ts`, or `RunManager.ts` for actuation. Avoiding those files also respects their size constraints.

### 4. Surface one identity contract through existing projections

Extend `api/src/transport_matters/harnesses/resolver.py :: LaunchOption` so it exposes the launch selector and the identity state separately. Extend `api/src/transport_matters/api/v1/harness_launch_view.py :: LaunchModelView` and use it for every listed selector. The current uniform string list cannot carry identity evidence.

The launch view wording must follow the state:

- Unresolved: show the selector only.
- Observed under a scope: show the wire model as an observation with source and confidence.
- Resolves per turn: show that phrase and any observed wire models as evidence, without choosing one.

Split `api/src/transport_matters/controlplane/observe_models.py :: RosterItem.model` into `launch_model` and structured observed identity. Delete `_accepted_model`. `project_roster` already receives raw launch intent and the latest transcript wire model, so it can populate both without changing launch behavior. Label `effort` as launch effort until wire effort becomes observable.

Keep `WorkspaceSummaryResult` compact. Add the same structured identity to `SelfIdentityResult` only if an agent must reason about its own current model. REST and MCP must return the same Python model.

If the browser inventory contract changes, move its DTOs to `@tm/contract` and delete the manual `@tm/core` mirror in the same change.

### 5. Remove the existing reconstruction and dead branch

Change `baseline_harvest.py :: main` to select from the already loaded `HarnessInventoryItem.launch_options` or stored target observations. Delete `_enumerated_models`. Change `_select_model` to require `str` and delete its unreachable default branch.

This keeps the baseline command on the authoritative catalog and prevents presentation compression from changing capture inputs.

### 6. Verify state, actuation, and policy behavior

Add focused tests for these facts:

- Three equal A/B/A wire models produce observed under probe, never fixed identity.
- Two wire models for one selector and exact version produce resolves per turn.
- `opus` and `opus[1m]` remain separate launch selectors when their observed wire model is equal.
- Missing effort, headers, path, and query do not produce inferred capability claims.
- Version change resets current identity to unresolved before new evidence arrives.
- Failed enumeration preserves the prior complete catalog without relabeling it as current identity.
- Missing identity leaves launchability and `target_unavailable` behavior unchanged.
- The child receives the launch selector byte for byte. Omitted selectors still omit `--model`.
- A full Claude model ID still passes through with the existing advisory behavior.
- Launch view, REST roster, and MCP roster expose the same identity state and provenance.
- The roster never substitutes observed wire identity into `launch_model`.

Split `test_captured_turn.py` and `test_wire_store_observer.py` before adding material cases. Run focused tests with `api/.venv/bin/python -m pytest`. Then run the repository `just check` and `just test-affected` gates.

## Required reuse constraints

The implementation must not add any of these owners:

- another harness catalog parser;
- another model argument builder;
- another capture runner;
- another baseline harvest command;
- another refresh endpoint or scheduler;
- another alias mapping table;
- another control plane projection inside `controlplane_mcp.py`.

Reuse `EnumeratedModel`, `run_model_enumeration_probe`, `ExecutorEvidenceStore`, `BaselineCell`, `read_current_baselines`, `run_captured_turn`, `WireStoreObserver`, `HarnessModelCompatibility`, `LaunchOption`, `LaunchModelView`, and `project_roster`.
