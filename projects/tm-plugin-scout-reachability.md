---
title: Transport Matters baseline reachability scout and plan
type: scout
tags:
  - transport-matters
  - baselines
  - production-entry
  - code-hygiene
summary: Source grounded recommendation and implementation plan for production baseline harvest and comparison entry points.
status: complete
created: 2026-08-22
updated: 2026-08-22
project: transport-matters
confidence: high
---

# Transport Matters baseline reachability scout and plan

## Verdict

Use different homes for the two operations.

| Operation | Recommended production home | Public shape | Reason |
| --- | --- | --- | --- |
| Harvest | API Justfile | `just api baseline-harvest ...` | Harvest is a source checkout certification procedure. It requires a clean Git commit, consumes provider turns, writes accepted evidence, and needs a controlled workspace. The API Justfile already owns opt in, source only operational jobs. |
| Compare | Installed Transport Matters CLI | `transport-matters baseline compare --channel <channel> --harness <harness>` | Comparison is a safe channel scoped read. The installed CLI is the existing operator surface and can expose consistent help, channel selection, exit codes, and structured output. |

Do not place either operation in the control plane, Desktop, or Canvas in this pass. Those surfaces add remote authority, asynchronous job lifecycle, API contracts, UI state, and duplicated presentation. They do not improve the current operator workflow.

The strongest counterargument is a single `transport-matters baseline` command family containing both operations. That would improve discovery. Current harvest provenance makes that surface misleading because a wheel installation cannot identify its running source with `Path(__file__).resolve().parents[3]`. A Justfile recipe states the real precondition: run from the checked out source being certified. Move harvest into the installed CLI only after package provenance replaces the checkout assumption.

## Scope and evidence boundary

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Branch: `main`
- Pinned commit: `10db3ca7f664fb2068f1c7246041705cee93ceb1`
- Initial state: clean
- Review boundary: current source only
- Exclusions: history, pull request diffs, provider turns, repository writes, store writes

The harvest and comparator currently have no registered production caller. Their reachable interface is direct Python module execution. The installed console entry is `transport-matters.cli`, `main`, registered by `api/pyproject.toml` as `transport-matters`.

## Reuse map

### Baseline behavior owners

| Concern | Current owner | Reuse decision |
| --- | --- | --- |
| Controlled A, B, A capture | `api/src/transport_matters/baseline_capture.py`, `harvest_controlled_baseline` | Keep as the capture owner. Preserve prompt suppression, event assembly, three turn sequencing, validation, and promotion as one lifecycle. |
| Baseline persistence | `api/src/transport_matters/baseline_store.py`, `BaselineStore` and `accept_degraded_baseline` | Reuse. Expose acceptance as a distinct operation because it is an approval and write boundary. |
| Cohort reading | `api/src/transport_matters/baseline_comparison.py`, `read_current_baselines` | Reuse directly. |
| Pair comparison | `api/src/transport_matters/baseline_comparison.py`, `compare_model_pair` | Reuse. It already compares both directions. |
| Cohort comparison | `api/src/transport_matters/baseline_comparison.py`, `compare_model_cohort` | Reuse. |
| Equivalence classes | `api/src/transport_matters/baseline_comparison.py`, `fold_model_equivalence_classes` | Reuse. |
| Diagnostics | `api/src/transport_matters/baseline_comparison.py`, `comparison_diagnostics` | Reuse. Keep actual model, bundle, direction, and outlier values in diagnostics. |
| Channel home | `api/src/transport_matters/storage_roots.py`, `default_storage_root` | Use after channel resolution. Default baseline storage remains `<channel home>/baselines`. |
| Launch inventory | `api/src/transport_matters/harnesses/inventory.py`, `harness_inventory` | Reuse after harvest activates the selected channel. |
| Source provenance | `api/src/transport_matters/harnesses/certification_minting.py`, `require_clean_worktree` | Reuse from the source operation. Add the required post capture check before publication. |

### House entry patterns

| Pattern | Current owner | Application |
| --- | --- | --- |
| Installed command family | `api/src/transport_matters/cli/db_cmd.py`, `db_app` and `api/src/transport_matters/cli/__init__.py`, `main` | Use a small `baseline_app` module for compare. Keep only registration in the 600 line CLI root. |
| Read only channel selection | `api/src/transport_matters/cli/channel_options.py`, `resolve_channel_or_exit` and `api/src/transport_matters/cli/tail_cmd.py`, `run_tail` | Compare resolves the channel, derives its home explicitly, and avoids process environment mutation. |
| Stateful channel selection | `api/src/transport_matters/cli/channel_options.py`, `activate_channel_or_exit` | Any future installed harvest adapter must activate before settings, inventory, executor identity, pool, or path resolution. |
| CLI option contract | `api/src/transport_matters/cli/launch_options.py`, `ChannelOption` | Reuse `--channel` and its environment fallback. Do not reuse `StorageDirOption`; it addresses per run exchange storage. |
| Source only operational recipe | `api/justfile`, `shared-proxy-load-test` | Add a forwarding `baseline-harvest *args` recipe. The root `api *args` recipe already delegates, so a second root alias would duplicate routing. |
| Status and error rendering | `api/src/transport_matters/cli/db_cmd.py`, command callbacks | Use explicit stderr messages and `typer.Exit`. Do not return legacy integer statuses from a Typer callback. |
| Text and JSON listing | `api/src/transport_matters/cli/instances.py`, command rendering | Reuse the presentation convention for comparator output. Avoid its stale manifest cleanup because compare is read only. |

### High risk analogue

`api/justfile`, `shared-proxy-load-test` is the closest operational analogue for harvest. It is explicit, opt in, source checkout scoped, and absent from routine startup. Harvest adds stronger controls because it consumes billed provider turns and can publish accepted evidence:

1. Validate the checkout, channel, inventory, model, template, authentication, output root, and workspace before the first provider request.
2. Print the resolved channel, executor, harness, model, output root, workspace, and source commit before capture.
3. Require an explicit harness and model for capture. Keep inventory as a separate read operation.
4. Recheck the clean source commit immediately before publication.
5. Return a nonzero status for degraded, breaking, invalid, or interrupted runs.

## Surface assessment

| Candidate | Harvest | Compare | Integration cost | Decision |
| --- | --- | --- | --- | --- |
| Installed CLI | Provenance is false for ordinary wheel installs under the current contract. A thin wrapper also risks losing integer exit statuses. | Strong fit. Read only, channel scoped, and useful to local operators and automation. | One command module, one registration, static help, output contract, and CLI tests. | Compare only. |
| API module | Current implementation home, with no discovery or supported invocation contract. | Current implementation home, with no discovery or supported invocation contract. | Low code cost and no reachability gain. | Keep command neutral behavior here. |
| API Justfile | Strong fit for a checkout bound, billed certification operation. | Usable, but hidden from installed operators and redundant with the CLI. | One forwarding recipe plus harvest contract grooming. | Harvest only. |
| Control plane | Requires privileged mutation authority, job progress, cancellation, timeout ownership, and audit semantics. | Possible, but duplicates a local read and requires REST and MCP twins. | High. `ControlPlaneService` is already 668 lines. | Reject for this pass. |
| Desktop and Canvas | Requires API transport, typed commands, progress and cancellation state, results UI, and safe confirmation. | Requires the same stack for a report already suited to the CLI. Developer command rows are development only. | High. Desktop and Canvas owners are near size or function limits. | Reject for this pass. |

## Quality map

Twenty findings should be resolved or explicitly deferred during implementation.

### Q01. No supported production entry

`baseline_harvest.py`, `main` and `baseline_compare.py`, `main` are parallel argparse adapters. Tests call those adapters directly, so they do not prove the installed console surface. Extract command neutral operations, then test the real recipe and CLI boundary.

### Q02. Installed harvest cannot prove its declared source commit

Harvest derives a repository root from `Path(__file__).resolve().parents[3]`. A wheel resolves that path inside its environment rather than a Git checkout. The resulting Git failure is reported as a generic capture failure. Keep harvest checkout scoped until provenance is package based.

### Q03. Source provenance is checked only before capture

The source commit is read once before the multi turn A, B, A sequence. Later source, addon, or runtime template changes can be published under the earlier commit. Run the second clean worktree check required by the certification helper immediately before promotion.

### Q04. The default harvest workspace is neither created nor isolated

The default is a fixed path under the system temporary directory. Harvest does not create it, while launch validation requires an existing directory. A fresh machine can fail before capture. A surviving directory can contribute stale files or instructions that are absent from provenance. Create a unique controlled workspace or require an explicit validated empty directory.

### Q05. Channel selection is absent from both adapters

Each adapter derives its default output from the active environment. Harvest also reads channel scoped settings, database rows, and executor identity. Add explicit channel handling. Harvest must activate before any dependent resolution. Compare can resolve the channel and pass its home directly.

### Q06. Explicit output can mix channel evidence

`--output` is independent from the selected channel database and executor home. Harvest can read one channel and write another channel's baseline directory. Compare can read arbitrary artifacts without identifying that divergence. Keep the override for tests and deliberate offline stores, but print and persist the resolved channel and explicit root relationship.

### Q07. Lower capture code imports CLI template ownership

`baseline_capture.py`, `_template_identity` imports digest helpers from `cli/home_seed.py`, which reexports from `cli/home_overlay.py`. Move the pure runtime template identity calculation below the command layer and update both consumers.

### Q08. Captured dependency assembly reaches into Typer and duplicates CLI wiring

`captured/dependencies.py`, `default_claude_run_dependencies` lazily imports Typer and several CLI modules. The CLI root separately assembles the same dependencies and packaged addon failure. Move concrete construction to one neutral composition owner or inject `CapturedRunDependencies` at the command boundary. Rename the factory because it serves more than Claude.

### Q09. Harvest imports a server presentation module

`baseline_harvest.py` imports the launch projection from `api/v1/harness_launch_view.py`. The projection is pure, but its home creates a command to server layer reach. Move the projection to a neutral harness application module and let MCP and harvest share it.

### Q10. Pure evidence imports the session layer

`baseline_evidence.py` imports `mask_cross_launch_body` from `session/wire_normalization.py`. Move the pure masking function below both evidence and session normalization. Keep one implementation.

### Q11. Harvest combines inventory, capture, and acceptance

`baseline_harvest.py`, `main` selects three operational modes from argument combinations. Either acceptance flag bypasses inventory and ignores capture arguments. The implicit model branch in `_select_model` is unreachable because `main` rejects a missing model first. Expose inventory, capture, and acceptance as distinct command neutral operations and source recipes.

### Q12. Broad capture handling changes setup failures into exit 1

The capture block catches every `Exception`. Packaged addon resolution raises `typer.Exit(2)`, which the handler reclassifies as a capture failure. Catch domain failures at their owner and translate them once at the entry boundary.

### Q13. A thin Typer wrapper would silently lose legacy exit codes

Typer ignores ordinary callback return values for process status. Returning the integer from either current `main` would make degraded harvests and invalid comparisons exit 0. Command neutral operations should return typed outcomes. The CLI callback must raise `typer.Exit` with the mapped status.

### Q14. Comparator success does not define structural success

Every completed report returns 0, including breaking pairs. This may be correct for an informational report. A production command needs an explicit policy: retain report semantics by default and add a named strict mode for gating, or make breaking comparisons nonzero. Tests must pin the choice.

### Q15. Static CLI help can drift from registration

`cli/help.py`, `_ROOT_HELP` and `_SUBCOMMAND_HELP` are maintained separately from Typer registration. The registered `db` family is already absent from root help. Add baseline help in the same change and either derive the registry from one owner or add a discovery test that compares help with registrations.

### Q16. Inventory listing can mutate a fresh channel home

The no harness path calls inventory, which calls `local_executor_id`. First use mints `executor-id`. Name this operation accurately and preflight home writability, or provide a genuinely read only inventory query with an explicit executor ID.

### Q17. Launch view selection assumes an unguarded invariant

After selecting a launch view item, harvest uses `next(...)` to locate the matching inventory row. A projection mismatch raises uncaught `StopIteration`. Replace it with a checked lookup and a domain error even though both collections currently share an origin.

### Q18. Production output has no structured contract

Harvest and compare emit line oriented text that resembles machine records but has no escaping or JSON schema. Add `--json` for automation and retain concise text for humans. Diagnostics must keep the actual model, bundle, direction, and values.

### Q19. Production must not reuse the CLI test helper module

`cli/_helpers.py` imports `pytest`, exposes private helpers, and is used only by tests. It is likely included in the wheel because its name does not match the wheel's test exclusions. Keep production imports away from it. Rename or relocate it under tests during nearby packaging cleanup.

### Q20. Candidate surface owners have no room for embedded implementations

The CLI root is about 600 lines, `ControlPlaneService` about 668, and Desktop `main.ts` about 674. `run_doctor`, `useCommandCenter`, and the command center component also exceed or approach the 150 line function threshold. Add only small registration points to these owners. New behavior belongs in focused modules.

## Implementation plan

### Phase 1. Establish command neutral contracts

1. Introduce typed request and outcome contracts for inventory, harvest, acceptance, and comparison in the baseline application layer.
2. Separate parsing, rendering, and process exit translation from baseline behavior.
3. Keep `baseline_comparison.py` as the sole comparison owner. Do not reproduce pair traversal, severity folding, equivalence classes, or diagnostics.
4. Move template identity, cross launch masking, and launch view projection to neutral owners. Consolidate captured dependency construction.
5. Delete the superseded argparse adapter path when each caller has migrated. The project has no compatibility obligation.

### Phase 2. Harden harvest before exposing the recipe

1. Separate inventory, capture, and acceptance operations.
2. Give capture an explicit harness and model. Resolve and activate the channel before output, settings, pool, executor, or dependency access.
3. Replace the fixed temporary directory with a unique controlled workspace, or require an explicit validated empty directory.
4. Preflight every local condition before the first provider request.
5. Check the clean source commit before capture and immediately before publication. Reject a changed commit or dirty tree.
6. Add `baseline-harvest *args` to `api/justfile`. Add a separate acceptance recipe if approval remains a supported operation. Rely on the existing root `api *args` delegation.
7. Print the fully resolved execution identity before capture and return stable exit codes 0, 1, and 2.

### Phase 3. Add the installed comparison command

1. Create a focused `cli/baseline_cmd.py` with `baseline_app` and a thin `compare` callback.
2. Register the group in `cli/__init__.py` without adding command bodies there.
3. Reuse `ChannelOption`, call `resolve_channel_or_exit`, and pass `default_storage_root(spec.id) / "baselines"` explicitly.
4. Preserve human diagnostics and add a stable JSON result.
5. Pin report versus gate exit semantics. A strict flag is the least disruptive way to support both uses.
6. Update static help and add a registration to help consistency test.

### Phase 4. Prove the real surfaces

1. Move baseline behavior tests from private adapter helpers to the command neutral API.
2. Add installed CLI tests for discovery, help, unknown channel exit 2, stable and preview roots, explicit output, empty and incomparable cohorts, both comparison directions, mixed source commits, JSON, and strict breaking status.
3. Add harvest boundary tests with fake dependencies for exit 0, 1, and 2, acceptance failures, fresh workspace creation, channel database and executor selection, and the guarantee that preflight failures make zero provider requests.
4. Mutate the checkout between probes in a test and prove the second provenance check blocks publication.
5. Prove the Codex baseline path still suppresses the managed AGENTS identity block through `no_system_prompt=True`.
6. Build and install the wheel in an isolated environment. Prove comparison works without pytest and without importing the CLI test helper module.
7. Run focused baseline and CLI tests, the full API gate, static dependency cycle analysis, and the repository gate. Do not use a live provider for automated verification.

## Acceptance criteria

- `just api baseline-harvest` is discoverable, checkout scoped, explicit about provider spend, and completes preflight before any provider request.
- Harvest records the same clean commit before capture and before publication.
- Capture, inventory, and acceptance have distinct entry contracts.
- `transport-matters baseline compare` is present in installed help and reads the selected channel home.
- Comparison retains bidirectional pair analysis, worst structural severity, equivalence classes, and outlier specific diagnostics.
- Human and JSON outputs are stable, and exit semantics are documented and tested.
- No new production code imports `cli/_helpers.py`, Typer from the captured layer, CLI template helpers from baseline capture, server routes from harvest, or session normalization from pure evidence.
- No touched file exceeds 700 lines and no new or extended function exceeds about 150 lines.
- Focused tests, package installation proof, dependency cycle analysis, the full API gate, and the repository gate pass without a live provider turn.

## Deferred surfaces

Control plane and Canvas exposure should wait for an explicit product requirement. A future remote harvest design needs a privileged grant, durable job identity, progress events, cancellation, timeout recovery, audit history, and clear billing confirmation. A future Canvas comparison view should consume a stable API result rather than reimplement baseline reading or diagnostics in TypeScript.
