# 632: resolution: retained targets must survive a harness version change and never gate launchability

URL: https://github.com/littleorgans/transport-matters/issues/632
State: open
Labels: bug, P1
Updated: 2026-09-05T03:11:03Z

Sub issue of the harness and model discovery epic.

Target observations are treated as version locked permission records, so a harness patch release erases every retained target and the harness disappears from the launch view. Runs continue to launch throughout, because actuation is fail open.

## Observed

```
target 2.1.260 / installed 2.1.260   10 launch options
target 2.1.260 / installed 2.1.261    0 launch options
```

`harnesses/connections_store.py:276` already reads every target row by `(executor_id, harness_id)`, so storage is correct. `harnesses/resolver.py:342-376` then removes rows whose observed harness version does not exactly equal the installed version. Zero options makes `api/v1/harness_launch_view.py:153-161` emit `launchable: false`, and `_unavailable_reason` at `:278` falls through to `target_unavailable`.

`harnesses/resolver.py:547` copies the target observation's older version into `ResolvedTarget`, so deleting the equality alone is not sufficient. No runtime consumer reads `ResolvedTarget.harness_version`: the constructor and `test_resolver.py:350` are the only direct references. First launch verification already reads the actual version from prepared run facts at `launch_verification.py:215-246`.

`harnesses/launch_target.py:185-196` passes an explicit unobserved selector through to the harness, which is why claude runs kept working while the picker offered nothing.

## Scope

- `harnesses/resolver.py`: simplify `_offered_targets` to decorate every row already scoped to the executor and harness. Remove the installed version equality, active release attribution filtering, observation status filtering, account entitlement filtering, and the enumeration derived unverified opt in. The compatibility release continues to supply canonical identity, lifecycle and launch adapter metadata through `decorate_target`. Net deletion keeps this 692 line file under the 700 line limit.
- Separate the two version authorities:

```python
class TargetObservationProvenance(_ResolverModel):
    compatibility_release_id: str | None
    harness_version: str
    observed_at: str
    observation_revision: str
    observation_adapter_revision: str

class ResolvedTarget(_ResolverModel):
    ...
    installed_harness_version: str
    target_observation: TargetObservationProvenance
```

  `installed_harness_version` comes from the current `LocalHarnessObservation`, normalized where available. Nesting is preferred over flat fields so the two authorities cannot be confused by name.
- Remove `allow_unverified_target`, `target_unverified_opt_in_required` and `requires_unverified_opt_in`. `observed` and `declared` describe provenance; requiring an opt in turns enumeration into permission. Touches `harnesses/resolver_contracts.py`, `www/packages/core/src/types/harnessInventory.ts` and the shared `LaunchOption` fixture.
- Remove `account_entitlement_unavailable` from launch resolution and `harnesses/resolver_snapshots.py`. Keep it in certification and publishing, where it prevents known futile provider spending. The vendor's refreshed catalog is account aware, so entitlement filtering arrives from the source.
- `api/v1/harness_launch_view.py`: an installed, enabled, launch capable harness with zero options returns `launchable: true` with `models: []`, `efforts: []`, authentication `unknown` and access `missing`. Probe absence, stale evidence and probe failure must never reach the unavailable branch. Keep the unavailable projection for a missing executable, a disabled harness, a retired target and an explicit authored block.
- `harnesses/launch_target.py`: convert a `target_unavailable` rejection carrying `reason=not_observed` into a `VerificationCell` using the requested harness, model and effort, so enumeration failure never prevents first launch assessment. Apply the same rule to a configured native model discovered from the launch home.
- Docs: replace the target authority table at `docs/HARNESS-COMPATIBILITY.md:168-189`, whose freshness and opt in rules this overturns. Update `docs/LAUNCH-CONTRACT.md:91-99,113-128` and remove the obsolete rejection from `docs/plans/LOGGING-PLAN.md:237-242`.

No lifecycle field is added to `harness_target_observation`. Lifecycle remains compatibility metadata applied by `harnesses/resolver_targets.py:26`.

## Verification

The integrated regression belongs in `test_state_refresh.py`:

1. Record ten successful target observations at `2.1.260`.
2. Change the installed harness observation to `2.1.261`.
3. Return a structured enumeration timeout.
4. Assert all ten prior rows remain stored with `2.1.260` and their original timestamp.
5. Assert all ten launch options remain offered.
6. Resolve one option and assert `installed_harness_version == "2.1.261"`.
7. Assert its target provenance still says `2.1.260`.
8. Assert support is unknown for the unassessed installed version.
9. Assert `resolve_launch_target_views` produces a `VerificationCell`.

Also update `test_resolver.py`, `test_resolver_launch_options.py`, `test_resolver_snapshots.py`, `test_resolver_model_identity.py`, `test_resolver_support.py`, `test_launch_target.py`, `test_capture_rpc_verification_cell.py` (the unknown explicit model case changes from `NoVerificationCell` to `VerificationCell`), `test_controlplane_mcp_inventory.py` and `harnessInventory.test.ts`.

## Outcome

A harness patch release never removes a harness from the launch view. Absent, stale or failed enumeration leaves every retained target offered and verifiable.


## Comment by srobinson at 2026-09-05T03:11:03Z (updated 2026-09-05T03:11:03Z)

https://github.com/littleorgans/transport-matters/issues/632#issuecomment-5548958695

## Entitlement filtering does not arrive from the source

One scope bullet needs correcting before implementation: "Remove `account_entitlement_unavailable` from launch resolution ... The vendor's refreshed catalog is account aware, so entitlement filtering arrives from the source."

Verified against codex 0.153.2: the bundled catalog enumerates `gpt-5.2` with `visibility: list`, and the provider answers 400 `The 'gpt-5.2' model is not supported when using Codex with a ChatGPT account`. The catalog is not account aware for this case. The refusal is learned only from a provider turn, which is exactly what #470 records.

Certification and publishing cannot own it either. A release cannot know which account will run it, so an account fact in signed release data is wrong by construction.

Boundary, as recorded on #470:

- Entitlement exclusions are runtime evidence in the session store, keyed by provider and model, beside the existing quota decisions.
- They are the one sanctioned refusal at launch, an enumerated block in the #384 sense. Everything else in this issue stands: version equality, release attribution, observation status and the unverified opt in all stop gating.

So the bullet becomes: move the entitlement read from the on disk baseline attempts to the store, and keep it in launch resolution. #470 carries the storage change; this issue should depend on it rather than delete the read.


## Sub issues
[]
