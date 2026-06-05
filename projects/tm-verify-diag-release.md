---
title: Transport Matters launch target resolution diagnostic
type: projects
tags: [transport-matters, harnesses, resolver, compatibility, launch-verification]
summary: Live preview diagnosis of release binding, unverified target selection, opt-in reachability, repair options, and blast radius
status: active
created: 2026-08-23
updated: 2026-08-23
project: transport-matters
confidence: high
---

# Transport Matters launch target resolution diagnostic

## Conclusion

### ESTABLISHED

The preview releases bind successfully. Target selection fails later because the active release catalogs produce zero `tested` targets. Every live option is `observed_unverified`: Claude 10 of 10, Codex 5 of 5, and Grok 2 of 2. Native default selection accepts only `tested`, `active`, locally healthy targets, so all three defaults reject with `target_unavailable`, reason `no_default_target`. Explicit selection rejects with `target_unverified_opt_in_required` unless the internal `ResolverRequest.allow_unverified_target` field is true. Evidence: `api/src/transport_matters/harnesses/resolver.py:_default_eligible`, `_select_edge`, `_validate_explicit_edge`; `api/src/transport_matters/harnesses/resolver_targets.py:decorate_target`; measurements M3 and M4 below.

The installed versions are above their blessed ceilings. That classification does not block release binding or launch compatibility. `match_release` deliberately returns `compatible` above the ceiling, and `resolve_compatibility_release_id` keeps the active release attribution for every version at or above the minimum. Evidence: `api/src/transport_matters/harnesses/compatibility.py:blessed_ceiling`, `range_position`, `match_release`; `api/src/transport_matters/harnesses/probes/targets.py:resolve_compatibility_release_id`; measurements M1 through M3.

The earlier `ResolverSnapshots.release is None` reading is incorrect for the current live preview state. A fresh read-only construction of the exact snapshots used by the resolver returned `claude-2.1.211-r2`, `codex-0.144.4-r2`, and `grok-1.0.4-r2`. Evidence: `api/src/transport_matters/harnesses/resolver_snapshots.py:resolver_snapshots_for_harness`; measurement M3.

## Scope and measurement method

Repository state was `main` at `d4ce12a5a398fe841c5e1ac64bac713320f01c4a`, with a clean tree. Live reads used preview database `postgresql://tm:tm@localhost:55432/transport_matters_preview`, executor `ef9cd166-7f7b-4ee0-9054-4d365393d509`, preview home `/Users/alphab/.transport-matters-preview`, and the already running backend on port 8798. No process was launched or restarted. No database or home write was made.

Measurements:

- **M1, embedded release classification.** A `uv run python -B` read called `embedded_channel_state`, `embedded_release_entry`, `blessed_ceiling`, and `range_position` for the three measured installed versions. Evidence owners: `api/src/transport_matters/harnesses/compatibility_store.py:embedded_channel_state`, `embedded_release_entry`; `api/src/transport_matters/harnesses/compatibility.py:blessed_ceiling`, `range_position`.
- **M2, stored evidence.** `psql` used `BEGIN TRANSACTION READ ONLY` and queried the latest rows in `harness_observation`, `harness_target_observation`, `harness_connection`, `harness_enablement`, and `harness_executor_block` for the named executor. Evidence reader owners: `api/src/transport_matters/harnesses/connections_store.py:ExecutorEvidenceStore`; `api/src/transport_matters/harnesses/blocks_store.py:ExecutorBlockStore`; `api/src/transport_matters/harnesses/enablement_store.py:HarnessEnablementStore`.
- **M3, live resolver snapshots.** A one-connection read-only pool called `resolver_snapshots_for_harness` with `ensure_native_connection=False`, followed by `launch_options` and `resolve_target`. The request variants were default, explicit, and explicit with `allow_unverified_target=True`. Evidence owners: `api/src/transport_matters/harnesses/resolver_snapshots.py:resolver_snapshots_for_harness`; `api/src/transport_matters/harnesses/resolver.py:launch_options`, `resolve_target`.
- **M4, live API inventory.** `GET http://127.0.0.1:8798/v1/harnesses` returned executor `ef9cd166-7f7b-4ee0-9054-4d365393d509`, channel `preview`, three `compatible` harnesses, 17 launchable options, and 17 `requires_unverified_opt_in` flags. Evidence owners: `api/src/transport_matters/api/v1/harnesses.py:get_harnesses`, `inventory_for_request`; `api/src/transport_matters/harnesses/inventory.py:harness_inventory`, `_harness_item`.
- **M5, run facts.** Existing preview `compatibility.json` files were read with `jq`. Claude run `e4ccd5ce-f3e3-4638-b071-232f5d228cee` recorded `claude-2.1.211-r2` at version `2.1.241`; Codex run `e5cfd0dd-caab-4e90-a412-4dc83166acc2` recorded `codex-0.144.4-r2` at version `0.149.0`; Grok run `b3ca2c7a-dc52-4078-ae57-077488017ad9` recorded `grok-1.0.4-r2` at version `1.0.5`. Evidence owners: `api/src/transport_matters/harnesses/compatibility_service.py:_gate`, `_record`; `api/src/transport_matters/harnesses/compatibility_facts.py:compatibility_fact_artifact`, `read_compatibility_facts`.
- **M6, opt-in surface search.** Repository-wide `rg` searches covered `allow_unverified_target`, `requires_unverified_opt_in`, `target_unverified_opt_in_required`, and every production `ResolverRequest` construction. Production constructions exist in `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolve_launch_target` and `api/src/transport_matters/harnesses/access_verification.py:_resolver_request`. Neither sets the target opt-in. `CapturedRunRequest` has no target opt-in field. Evidence: `api/src/transport_matters/captured/models.py:CapturedRunRequest`.

## 1. Release binding predicate

### ESTABLISHED

There are three related predicates.

1. **Snapshot release lookup.** `resolver_snapshots_for_harness` reads the embedded channel state for `(channel, harness_id)`, reads `embedded_release_entry(state.active_release_id)`, and assigns that entry directly to `ResolverSnapshots.release`. Installed version does not participate in this lookup. Evidence: `api/src/transport_matters/harnesses/resolver_snapshots.py:resolver_snapshots_for_harness`.
2. **Compatibility match.** `match_release` requires a present channel state and release, `state.status == "active"`, matching active release and harness IDs, and an unexpired state. A version below `minimum_version` yields `harness_update_required`. Active release, version, route, or target blocks can change the outcome. A version above the blessed ceiling remains `compatible`; only `range_position` records `above_ceiling`. Evidence: `api/src/transport_matters/harnesses/compatibility.py:match_release`.
3. **Target observation attribution.** `resolve_compatibility_release_id` requires a normalizable version, a present embedded channel state and entry, and a range position other than `below_minimum`. It intentionally attributes an above-ceiling observation to the active release. Evidence: `api/src/transport_matters/harnesses/probes/targets.py:resolve_compatibility_release_id`.

The blessed ceiling is `maximum_version` when declared, otherwise `baseline_version`. Evidence: `api/src/transport_matters/harnesses/compatibility.py:blessed_ceiling`.

| Harness | Active release | Installed | Minimum | Baseline | Maximum | Blessed ceiling | Range position | Live outcome | Latest targets attributed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| Claude | `claude-2.1.211-r2` | `2.1.241` | `2.1.211` | `2.1.211` | null | `2.1.211` | `above_ceiling` | `compatible` | 10 of 10 |
| Codex | `codex-0.144.4-r2` | `0.149.0` | `0.144.4` | `0.144.4` | null | `0.144.4` | `above_ceiling` | `compatible` | 5 of 5 |
| Grok | `grok-1.0.4-r2` | `1.0.5` | `1.0.4` | `1.0.4` | `1.0.4` | `1.0.4` | `above_ceiling` | `compatible` | 2 of 2 |

Values came from M1, M2, and M4. M2 also found one native connection per harness, no `harness_enablement` rows, and no active executor blocks. Missing enablement intent defaults to enabled in `resolver_snapshots_for_harness` through `user_enabled=True if intent is None else intent.enabled`.

`above_ceiling` currently changes inventory metadata and identifies comparison work. It does not clear `ResolverSnapshots.release`, clear target attribution, add a compatibility advisory, or reject resolution. Evidence: `api/src/transport_matters/harnesses/compatibility.py:match_release`; `api/src/transport_matters/harnesses/inventory.py:_harness_item`; M3 and M4.

## 2. Resolver snapshots and run compatibility facts

### ESTABLISHED

Both paths begin with the same embedded channel pointer and release entry.

- **Resolver path:** `resolver_snapshots_for_harness` loads the embedded channel state and entry, joins stored observations, connections, access evidence, target evidence, blocks, and enablement, then returns `ResolverSnapshots`. `resolve_target` consumes `snapshots.release`. Evidence: `api/src/transport_matters/harnesses/resolver_snapshots.py:resolver_snapshots_for_harness`; `api/src/transport_matters/harnesses/resolver.py:resolve_target`.
- **Run facts path:** `_gate` loads the embedded channel state and entry, probes the launched executable version, calls `match_release`, and passes the entry and observation to `_record`. `_record` writes `compatibility.json` whenever an entry and an installed, normalized, status `ok` observation exist. The write condition does not require an at-ceiling version. Evidence: `api/src/transport_matters/harnesses/compatibility_service.py:_gate`, `_record`; `api/src/transport_matters/harnesses/compatibility_facts.py:write_compatibility_facts`.

M3 read these non-null snapshot releases:

| Harness | `ResolverSnapshots.release.release.release_id` |
| --- | --- |
| Claude | `claude-2.1.211-r2` |
| Codex | `codex-0.144.4-r2` |
| Grok | `grok-1.0.4-r2` |

M5 read the same release IDs from existing run facts at the above-ceiling installed versions. The apparent split between a null resolver release and a named run release did not reproduce. The current source and live state show one active embedded release per harness in both paths.

## 3. Target selection and opt-in

### ESTABLISHED

The active manifest defines every target edge as `support_tier: "observed_unverified"`. Evidence: `api/src/transport_matters/harnesses/compatibility_releases_v1.json:releases[].targets[].support_tier`.

`decorate_target` joins a live observation to a release edge by exact `(route_id, native_model_id)`. A missing edge receives the fallback `observed_unverified`. Claude currently has no exact native selector match: the release names `claude-opus-4-8`, `claude-fable-5`, `claude-sonnet-5`, and `claude-haiku-4-5`, while live observations name `best`, `default`, `fable`, `fable[1m]`, `haiku`, `opus`, `opus[1m]`, `opusplan`, `sonnet`, and `sonnet[1m]`. Codex has one matching edge, `gpt-5.6-sol`, whose declared tier is still unverified. Grok has two matching edges, both declared unverified. Evidence: `api/src/transport_matters/harnesses/resolver_targets.py:decorate_target`; manifest target entries; M2.

`_default_eligible` requires `support_tier == "tested"`, lifecycle `active`, and local observation status `ok`. `_select_edge` returns `no_default_target` when the eligible set is empty. `_validate_explicit_edge` returns `target_unverified_opt_in_required` when the selected target is unverified and `ResolverRequest.allow_unverified_target` is false. Evidence: `api/src/transport_matters/harnesses/resolver.py:_default_eligible`, `_select_edge`, `_validate_explicit_edge`.

M3 produced the following exact results:

| Harness | Options | All options | Default | Explicit example | Explicit with internal opt-in |
| --- | ---: | --- | --- | --- | --- |
| Claude | 10 | `observed_unverified`, opt-in required | `target_unavailable:no_default_target` | `opus` rejected | `opus` resolved under `claude-2.1.211-r2` |
| Codex | 5 | `observed_unverified`, opt-in required | `target_unavailable:no_default_target` | `gpt-5.6-sol` rejected | `gpt-5.6-sol` resolved under `codex-0.144.4-r2` |
| Grok | 2 | `observed_unverified`, opt-in required | `target_unavailable:no_default_target` | `grok-4.6` rejected | `grok-4.6` resolved under `grok-1.0.4-r2` |

The rejection is reachable, and the predicate is satisfiable inside Python. There is no production operator opt-in surface. M6 found no setting, environment variable, enablement intent, CLI flag, control-plane action, API request field, or UI action that sets `ResolverRequest.allow_unverified_target`. `_resolve_launch_target` constructs the resolver request from harness, model, and effort only. `CapturedRunRequest` carries no target opt-in field. Evidence: `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolve_launch_target`; `api/src/transport_matters/captured/models.py:CapturedRunRequest`; M6.

`provider_access_approval="allow_unverified"` governs missing or unknown provider access evidence. `_resolve_launch_target` passes that value to `assess_provider_access` after target resolution and never maps it to `allow_unverified_target`. Evidence: `api/src/transport_matters/harnesses/access_policy.py:ProviderAccessApprovalRequest`, `assess_provider_access`; `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolve_launch_target`.

Operational opt-in result: **none found**. The internal field has no production ingress.

## 4. Concrete ways to resolve all three harnesses today

### ESTABLISHED constraints

Increasing `maximum_version` or moving `baseline_version` alone changes `range_position`. It leaves target support tiers unchanged, so native defaults still have zero eligible targets. Evidence: `api/src/transport_matters/harnesses/compatibility.py:range_position`, `match_release`; `api/src/transport_matters/harnesses/resolver.py:_default_eligible`.

Active embedded pointers require a digest-matched certification record. Each active release must have a complete record whose fixture and evidence digests validate against the release entry. Evidence: `api/src/transport_matters/harnesses/compatibility_store.py:_require_certified_active_pointers`; `api/src/transport_matters/harnesses/certification.py:validate_certification_for_release`.

### INFERRED options and cost

1. **Publish certification-backed current releases. High cost.** Author one new `CompatibilityReleaseEntry` per harness in `api/src/transport_matters/harnesses/compatibility_releases_v1.json`. Each entry needs current version coverage, current exact native target selectors, at least one `tested` and `active` target suitable as the unique native default, updated catalog or adapter revisions where the evidence demands them, recomputed release and target evidence digests, and a matching immutable record in `api/src/transport_matters/harnesses/certification_records_v1/`. Update the preview and intended stable channel pointers to the new release IDs. Runtime evidence collection, planned suites, fixture hashing, record minting, and package validation are owned by `api/src/transport_matters/harnesses/certification_minting.py:mint_outcome`, `successor_entry`, `write_record_once` and `api/src/transport_matters/harnesses/certification_evidence.py:CapturedRunEvidenceSource`. This option restores default resolution and removes the unverified opt-in requirement for the tested edges.
2. **Expose the existing internal target opt-in. Medium code and product-contract cost.** Add a request-scoped field to the public launch contract, thread it through the API or control-plane request, `CapturedRunRequest`, `_resolve_launch_target`, CLI and Canvas, and set `ResolverRequest.allow_unverified_target=True`. Require an explicit model because `_select_edge` never defaults to an unverified target. Add audit or durable intent coverage so the approval is attributable. M3 proves the existing resolver then resolves one explicit target per harness without changing releases. There is no configuration-only version of this option today.
3. **Change default selection policy. Small code surface, high policy cost.** Change `_default_eligible` and `_select_edge` to permit an unverified default, then define one deterministic default per harness. Merely admitting all unverified options would produce ambiguity because the live eligible sets have sizes 10, 5, and 2. This option weakens the launch contract rule documented and encoded by `api/src/transport_matters/harnesses/resolver.py:_default_eligible`; it also causes launch-triggered verification to run against an unverified target. Tests would need to cover the new default authority and ambiguity rule.

Fix option count: **3**.

## 5. Blast radius

### ESTABLISHED actual state

There are two direct readers of `TargetResolution.resolved`, both in `api/src/transport_matters/harnesses/launch_target.py`:

1. `launch_target_advisory` actuates the resolved native model and effort. With `target_unverified_opt_in_required`, it deliberately passes an explicit request through unchanged and adds an advisory. `_resolve_launch_target` calls it only when the caller supplied a model or effort. A default launch leaves model and effort unset and lets the harness choose. Evidence: `api/src/transport_matters/harnesses/launch_target.py:launch_target_advisory`, `_passes_to_harness`; `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolve_launch_target`.
2. `launch_verification_cell` returns `NoVerificationCell` for every rejection. `schedule_prepared_launch_verification` passes that cell to the coordinator, and `LaunchVerificationCoordinator.submit` logs `launch baseline verification skipped: no verification cell` and returns false. This is the silent degradation observed after #436. Evidence: `api/src/transport_matters/harnesses/launch_target.py:launch_verification_cell`; `api/src/transport_matters/api/v1/launch_verification_routes.py:schedule_prepared_launch_verification`; `api/src/transport_matters/launch_verification.py:LaunchVerificationCoordinator.submit`.

Other adjacent consumers continue to function in the measured state:

- Inventory uses `launch_options`, and M4 returned all three harnesses as compatible and launchable with 10, 5, and 2 visible options. Each option advertises `requires_unverified_opt_in`. Evidence: `api/src/transport_matters/harnesses/resolver.py:launch_options`; `api/src/transport_matters/api/v1/harness_launch_view.py:_project_harness`.
- Provider access verification uses `assess_provider_access` and its own approval policy. It does not consume `ResolvedTarget`. Evidence: `api/src/transport_matters/harnesses/access_verification.py:_verify_harness`; `api/src/transport_matters/harnesses/access_policy.py:assess_provider_access`.
- Run compatibility facts continue to record the active releases, proven by M5. Evidence: `api/src/transport_matters/harnesses/compatibility_service.py:_record`.

Actual silently degraded consumer count: **1**, launch-triggered baseline verification.

### ESTABLISHED counterfactual: a genuinely missing release

The requested `no release binds` counterfactual has three degraded product consumers:

1. **Launch inventory and picker:** `launch_options` returns an empty tuple when `snapshots.release is None`; `_project_harness` emits `UnavailableHarnessView`. Evidence: `api/src/transport_matters/harnesses/resolver.py:launch_options`; `api/src/transport_matters/api/v1/harness_launch_view.py:_project_harness`.
2. **Explicit captured launches:** `resolve_target` rejects with `target_unavailable`, reason `compatibility_catalog_unavailable`; `launch_target_advisory` treats this as a hard rejection; `_resolve_launch_target` returns HTTP 409. Evidence: `api/src/transport_matters/harnesses/resolver.py:resolve_target`; `api/src/transport_matters/harnesses/launch_target.py:launch_target_advisory`; `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolve_launch_target`, `_launch_target_rejection_status`.
3. **Launch-triggered verification:** default captured launches preserve the harness-chosen target behavior, but `launch_verification_cell` yields `NoVerificationCell(reason="target_unavailable")`, and the coordinator skips verification. Evidence: `api/src/transport_matters/harnesses/launch_target.py:launch_verification_cell`; `api/src/transport_matters/launch_verification.py:LaunchVerificationCoordinator.submit`.

Counterfactual `no release binds` degraded consumer count: **3**.

## Final answers

1. Releases bind from the active embedded channel pointer. Minimum version and blocks participate in compatibility; the blessed ceiling records `above_ceiling` and does not refuse. All three live harnesses are above ceiling and compatible.
2. `ResolverSnapshots.release` is non-null for all three harnesses. Run facts and resolver snapshots name the same active releases. The prior null reading was wrong.
3. The unverified-target predicate is reachable and internally satisfiable. No production opt-in ingress exists.
4. Three concrete options exist: publish certified tested releases, expose request-scoped target opt-in, or change default selection policy.
5. The actual state silently degrades one consumer, launch-triggered verification. A genuine missing-release state degrades three product consumers: inventory, explicit launch, and verification.
