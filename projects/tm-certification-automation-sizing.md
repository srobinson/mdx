# Transport Matters certification automation sizing

## Scope and result

Read only sizing against clean HEAD `a45461f9837fbf3079fbcf7f27d2bd1ced9d2348` on `feat/publish-derived-release-catalog`. No provider turns, tests, or repository writes were performed.

Planning number for the full owner workflow, one recipe per new harness version:

| Step | Production LOC | Test LOC | Character |
| --- | ---: | ---: | --- |
| 1. Capture one fresh exact version certification run | 230 | 350 | Largest slice, with release attribution and capture policy decisions |
| 2. Generate the `MintPlan` | 130 | 185 | Moderate, mostly derivation with a harness template decision |
| 3. Run the mint | 20 | 30 | Small, existing production owner is reusable |
| 4. Install the record and replace the draft with the sealed successor | 60 | 100 | Moderate, requires safe idempotent manifest mutation |
| 5. Advance selected `channel_states` | 45 | 85 | Small JSON mechanics, real activation and signing policy decision |
| 6. Verify activation | 15 | 30 | Small and collapsible into the manifest transaction |
| **Total** | **500** | **780** | Excludes generated JSON and documentation lines |

The planning confidence is about plus or minus 25 percent. The largest variable is how preactivation evidence is attributed to the candidate release without weakening the existing identity checks.

## A. MintPlan generator

The cheap generator premise is partly correct. A per harness seed is stable enough to reuse. The claim that only the version and bindings change is broader than the evidence supports.

Evidence:

- `api/src/transport_matters/harnesses/certification_minting.py:MintPlan` separates release identity, baseline version, suite definitions, fixture patterns, scenario IDs, facet references, scenario bindings, and baseline bindings.
- Current HEAD has two plan examples, `api/plans/claude-2.1.211-r2.json` and `api/plans/codex-0.144.4-r2.json`. Grok has an embedded certification record but no plan. `api/src/transport_matters/harnesses/test_mint_plans.py:_PLAN_RUNS` explicitly fixes the plan set to Claude and Codex.
- The historical Codex r2 and r3 plans at commit `1ce9cc06` are structurally identical after removing release identity and bindings. That proves reuse for an evidence successor at the same harness version. There is no same harness, cross version plan pair in the repository.
- `api/src/transport_matters/harnesses/certification.py:release_edge_set`, `_validate_edge_coverage`, and `api/src/transport_matters/harnesses/test_mint_plans.py:TestShippedMintPlans.test_edge_refs_cover_the_release_catalog_exactly` require the launch facet to cite the current release edge set exactly.
- `api/src/transport_matters/harnesses/release_publication.py:derive_inactive_release_entry` derives targets and references from the new captured cohort. The generator must therefore regenerate `launch_profile_resolved.edge_refs` from the candidate release.
- Fixture ownership is harness specific and can be version specific. The Codex plan cites `codex_response_create_certified_0144.json`; the Grok record cites version named fixtures. `TestShippedMintPlans.test_suite_selectors_and_fixture_patterns_resolve` proves present coherence without declaring cross version stability.

The safe inheritance rule is:

- Reuse by default: suites, fixture patterns, scenario IDs, facet applicability, fixture refs, and runtime refs.
- Replace: release ID, baseline version, scenario bindings, and baseline bindings.
- Derive: launch facet edge refs from the new candidate release.
- Revalidate: suite selectors, fixture patterns, fixture refs, predicates, and scenarios whenever adapter revisions or certification policy change.

The seed must come from a previous plan or an explicit harness template. A release entry cannot be the sole source because it carries no suite selectors, fixture globs, scenario vocabulary, or facet fixture refs. Grok needs a seed template before the generator is generic across all three harnesses.

Implementation placement matters. `certification_minting.py` is 655 lines and `compatibility.py` is 692 lines. The generator and recipe orchestration belong in a new focused module to preserve the 700 line project limit.

## B. Fresh certification capture and provider cost

There is no production certification capture command today.

Existing owners:

- `api/scripts/mint_harness_certification_record.py:_mint` consumes an existing `ScenarioRunBinding`. It does no capture.
- `api/src/transport_matters/captured_turn.py:run_captured_turn` is the production proven owner for one headless captured provider request.
- `api/src/transport_matters/baseline_harvest.py:observe_baseline_harness_version` provides the exact version preflight needed before provider spend.
- `api/src/transport_matters/harnesses/certification_evidence.py:CapturedRunEvidenceSource.collect` derives all seven certification predicates from one owned run, stored executor snapshots, raw exchanges, transcript copies, compatibility facts, and session facts.
- `api/src/transport_matters/harnesses/certification_run_reader.py:read_captured_run_index` requires at least one completed exchange. It does not require multiple exchanges.

The minimum certification cost is one provider turn per harness. Claude, Codex, and Grok therefore cost three certification turns in total. One run is sufficient because `CapturedRunEvidenceSource._check_launch_profile` proves the complete resolver edge set from stored state, while every live exchange present only needs to use an allowed edge.

This cost is separate from the baseline publication plan:

- `api/src/transport_matters/baseline_publish.py:BaselinePublishCell.provider_turns` assigns three turns to each missing model cell.
- `api/src/transport_matters/baseline_capture.py:harvest_controlled_baseline` performs the A, B, A capture.
- The printed 42 is 14 missing baseline cells times three turns.
- A complete fresh run across all three harnesses is 42 baseline turns plus 3 certification turns, 45 total.

A backend startup can also spend up to one access verification turn per harness when current provider access evidence is absent. That owner is `api/src/transport_matters/harnesses/access_verification.py:verify_provider_access`. The certification recipe should call the bounded capture owner directly and budget access verification separately, so startup behavior cannot hide extra spend.

The current path has three design seams:

1. Exact version enforcement happens after capture in `CapturedRunEvidenceSource._check_version` and `certification_minting.py:mint_outcome`. The recipe must call `observe_baseline_harness_version` before spawning.
2. `CapturedRunEvidenceSource._read_facts` requires the captured release ID to equal the mint target. Normal launch facts name the current active release. `compatibility_store.py:append_inactive_release_entries` deliberately leaves the new exact version release inactive.
3. `CapturedRunEvidenceSource._check_authentication` also requires stored authentication evidence attributed to the target release ID. A normal preactivation run remains attributed to the active predecessor.

The safest design carries two explicit identities through certification: the active predecessor that actually governed capture, and the candidate release being evaluated as if active. The evaluator should prove their derivation relationship and preserve all route, adapter, version, and evidence checks. Relaxing the release identity checks without an explicit lineage contract would weaken certification.

The existing baseline capture internally receives a `CapturedTurn` with a run directory and run ID, then discards that binding from the published interface. A deeper integration could retain one A1 run and reuse it for certification, reducing the normal new version path to zero extra certification turns. Current artifacts do not expose the required run directory and executor ID, and the predecessor attribution issue still needs resolution. The production cost statement therefore remains one extra turn per harness today.

## C. Channel state writing

The JSON mutation is small. Activation policy and signing scope require an explicit decision.

Evidence:

- `api/src/transport_matters/harnesses/compatibility.py:CompatibilityChannelState` requires a positive sequence and validates block ownership.
- `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` enforces a sequence strictly greater than the held value for each `(channel, harness_id)` and verifies channel signatures for mutable updates.
- Embedded loading through `_validate_embedded_manifest` has no prior sequence history and relies on package integrity. Current stable and preview states use sequence `1` and stub signatures.
- `api/src/transport_matters/harnesses/compatibility.py:channel_state_signature_payload` covers every channel field except the signature. A real signature must be produced after the release ID, sequence, activation time, status, expiry, minimum product version, and blocks are final.
- `api/src/transport_matters/harnesses/compatibility_store.py:_require_certified_active_pointers` requires a digest matched certification record behind every active embedded pointer.

For the current committed embedded manifest workflow, the recipe can:

1. Require an explicit activation channel.
2. Find exactly one state by `(channel, harness_id)`.
3. Set the new release ID, `sequence + 1`, activation timestamp, and active status.
4. Preserve blocks, expiry, and minimum product version unless explicit policy changes them.
5. Follow the current stub signature convention.
6. Validate and reload the complete embedded manifest.

Stable and preview must remain independent. A recipe that silently advances both removes the current promotion boundary. The evidence channel also needs to remain separate from the activation channel because current evidence commonly lives in preview while the resulting release may later promote to stable.

Real cryptographic signing and key management are outside the 500 production and 780 test line estimate. If this recipe must publish signed mutable channel payloads rather than prepare a package embedded diff, signing becomes a separate credential and architecture slice.

## D. Steps that disappear inside one recipe

The six operator steps should not remain six implementation phases.

The safe recipe order is:

1. Start from a clean tracked tree and pin HEAD.
2. Plan the baseline spend and exact installed version.
3. Capture the baseline cohort and one certification scenario without writing tracked files.
4. Derive the exact version candidate release in memory.
5. Generate the typed plan in memory, including current baseline bindings and derived edge refs.
6. Mint the record and sealed successor through `certification_minting.py:mint_outcome`.
7. Validate the exact record and release pair through `certification.py:validate_certification_for_release`.
8. Recheck the same clean HEAD.
9. Install the immutable record idempotently.
10. Replace the draft in the candidate manifest, advance the explicitly selected channel state, validate the full manifest, and write it atomically.
11. Clear the embedded manifest cache and reload the result as the final proof.

This ordering removes the standalone plan authoring, mint subprocess, stdout copy, manual reseal, manual channel edit, and separate activation command. `successor_entry` already seals the release digest, so `api/scripts/reseal_compatibility_manifest.py:reseal` should not participate in the recipe.

`write_record_once` rejects every existing path. The recipe needs a small idempotent installer that accepts a byte identical record on retry and rejects conflicting content. Writing the record before the active manifest is safe because a later manifest failure leaves an inert orphan record. A retry can complete the manifest write.

The current publisher writes the inactive release before minting, while `api/scripts/mint_harness_certification_record.py:_mint` requires a clean tree. A one recipe implementation must extract pure candidate derivation from `baseline_publish.py:publish_release_catalog` and defer tracked writes until certification and the clean HEAD recheck finish. An intermediate commit would violate the requested reviewable single diff workflow.

Range policy also belongs in the final release derivation. `derive_inactive_release_entry` currently makes baseline, minimum, and maximum exact at the new version. `certification_minting.py:successor_entry` can preserve the predecessor minimum while advancing baseline and maximum. The owner must choose whether each new certification widens the existing range or replaces it with a new exact range. The stated workflow, updates the min and max range, points toward preserving the certified floor and advancing the ceiling.

## Smallest cheaper path

The smallest safe change from already valid captured evidence to a blessed committed diff is one `certification-finalize` command, approximately **260 production LOC and 450 test LOC**.

Inputs:

- Harness ID.
- Exact scenario run directory.
- Executor ID.
- Evidence channel.
- Activation channel.
- Existing current baseline cohort or explicit immutable baseline bindings.
- Harness plan template, with a new Grok seed required for generic three harness support.

The command would generate the plan in memory, call the existing mint owner, install the record, replace the candidate release, advance one channel state, validate the pair and full manifest, and leave the tracked diff for review.

Tradeoff: the owner must still create the exact version certification run manually and provide its binding. That costs one provider turn per harness and preserves the most failure prone manual step. It also assumes the supplied evidence already satisfies the candidate release attribution contract. This path removes the repeated JSON ceremony but does not reach the requested one recipe per new harness version workflow.

## Recommendation

Build the full recipe as one new orchestration owner rather than adding six wrappers. Reuse `run_captured_turn`, `observe_baseline_harness_version`, `derive_inactive_release_entry`, `mint_outcome`, `validate_certification_for_release`, and the atomic manifest writer. Keep harness plan templates declarative. Require explicit evidence and activation channels. Resolve predecessor to candidate evidence attribution as a typed lineage contract before implementation.
