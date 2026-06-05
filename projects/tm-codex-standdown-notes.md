# Certification activation standdown notes

## Circularity finding

Capture attribution and certification target selection are separate lookups.

`compatibility_service._gate()` reads the current channel state, loads `state.active_release_id`, and passes that release to `compatibility_fact_artifact()`. The artifact copies `release.release_id` into the captured run facts. Current stable and preview Claude channel states point to `claude-2.1.211-r2`, so a fresh capture under the current manifest records `claude-2.1.211-r2` even when the installed harness version is `2.1.241`.

`CapturedRunEvidenceSource._read_facts()` enforces exact equality between the captured facts release id and the MintPlan target release id. `_check_authentication()` separately requires an authenticated observation bound to the target release id. The evaluator's as if active channel copy only affects resolver evaluation. It does not relabel the captured facts or authentication row.

The current flow is therefore circular while the channel pointer must remain on `claude-2.1.211-r2`. A new turn alone cannot produce evidence for `claude-2.1.241-r1`.

The supported cycle break visible in the code is:

1. Point preview at source candidate `claude-2.1.241-r1` with channel status `paused`.
2. Refresh harness state so authentication evidence binds to r1.
3. Capture the certification exchange. The advisory compatibility gate records facts for the paused pointer and permits the launch.
4. Mint the r1 plan at baseline `2.1.241`.
5. Because r1 has no sealed prior record, `mint_outcome()` derives the sealed `claude-2.1.241-r2` successor.
6. Embed the r2 record and successor release, point the channel at r2 while paused, verify r2, then activate it.

Minting from a run attributed to the predecessor does not break the cycle under current checks. Targeting r1 fails `_read_facts()` on release identity. Targeting the old r2 fails because `mint_outcome()` requires the runtime observed version to equal the plan and entry baseline, which remains `2.1.211`.

## Harness keyed recipe finding

The owner is correct that recipe input should be a harness. Target selection can stay independent of the channel pointer:

1. Resolve the registered harness executable.
2. Probe and normalize the installed version through the same `observe_baseline_harness_version()` owner used by baseline publication.
3. Reuse `select_source_release()` against the embedded catalog and require disposition `baseline`.
4. Print `harness`, installed version, and selected release id.
5. Refuse an absent executable, unparseable version, absent or ambiguous latest catalog baseline, or an installed version that does not equal the selected catalog baseline.
6. Mint from `plans/<selected-release-id>.json`, or verify the embedded record for the selected release.

With the current catalog, this selection resolves installed Claude `2.1.241` to `claude-2.1.241-r1`, while capture attribution still resolves through the channel pointer to `claude-2.1.211-r2`. That distinction is the circularity.

## Workspace state at standdown

Codex had begun the harness keyed recipe correction before the standdown arrived. The shared worktree contains uncommitted modifications in:

- `api/scripts/mint_harness_certification_record.py`
- `api/src/transport_matters/harnesses/release_publication.py`
- `api/src/transport_matters/harnesses/test_release_publication.py`
- `api/src/transport_matters/harnesses/test_mint_plans.py`
- `api/justfile`
- `justfile`

Focused tests had passed before the last small input validation edit: 25 tests across `test_release_publication.py` and `test_mint_plans.py`. A live provider free verify probe printed `resolved claude installed version 2.1.241 to claude-2.1.241-r1`, then correctly failed because no embedded r1 certification record exists. No provider turn ran. No commit or push was made for these follow up edits.
