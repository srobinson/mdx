# Review: blessed range position (slice/version-comparison)

Diff: `main` (2181a80b)..`444cb57d`, single commit, 17 files.
Reviewer: independent, worktree `.claude/worktrees/version-compare`. Gates not run (orchestrator owns them).
Behavioural claims below were checked by executing `match_release` against the real test fixtures, not by reading alone.

Counts: **0 Blocker, 1 Major, 5 Minor, 7 Note.**

Hypothesis 1 (always launch) confirmed, advisory and enforcing. Hypothesis 2 (test honesty) **refuted**, the test is honest. Hypothesis 5 (certification parity) **refuted**, behaviour did change; the version is named. Hypotheses 3, 4, 6, 7 confirmed with the qualifications below. Hypothesis 8 found the one Major.

---

## Findings, ranked by value

### 1. Major. The new Support fact reads `range_position` alone, so a refused harness renders a green "Current"

`www/packages/canvas/src/firstrun/harnessCards.ts::supportFact` switches on `compatibility.range_position` and never consults `compatibility.outcome`, `block_reason_code`, or `recommended_pin_version`. The two questions the backend deliberately split are then re-conflated in the wrong direction: the card shows the range answer and discards the launch answer.

Failure scenario, executed against the real fixtures:

```
version-scope block on the baseline, observed version == baseline
match_release -> outcome="harness_version_blocked"  range_position="at_ceiling"
                 block_reason_code="wire_contract_drift"  recommended_pin_version set
card renders  -> Support / "Current" / status "good", no detail
```

The enumerated block is the one remaining way to refuse a version, and it is the exact case the card paints green. Under `COMPATIBILITY_ROLLOUT="enforcing"` the launch is refused while the only support surface on the screen says the harness is current.

Second shape, same root cause. A paused or revoked channel pointer, or an active release-scope block, returns early from `match_release` with `outcome="compatibility_release_unavailable"` and `range_position="unknown"`, while `inventory._harness_item` still emits a non-null `channel`. The card takes the non-null-channel limb and renders "Not yet known" / pending with the detail "The blessed range could not be resolved for this version." That detail is false: the range resolves fine, the release pointer is paused. Verified: `match_release` on a paused state returns `compatibility_release_unavailable | unknown | None`.

Smallest correct fix: handle the refusing outcomes in `supportFact` before the `range_position` switch. `harness_version_blocked` becomes "Blocked" / caution carrying `block_reason_code` (the file already has the `Partial<Record<string, string>>` humanizer idiom for reason codes, see `PROBE_FAILURE_DETAILS`), and `compatibility_release_unavailable` becomes "Release paused" / neutral. The range switch then runs only for outcomes that do not refuse, which is what the fact's own docstring already claims it does.

### 2. Minor. `blessed_ceiling`'s stated rationale contradicts the value it returns when a maximum is declared

`api/src/transport_matters/harnesses/compatibility.py::blessed_ceiling` argues the fallback from the docstring premise "certification proves the contract AT `baseline_version`, and nothing above the certified baseline was ever observed". The same function returns `maximum_version` whenever it is declared, and `HarnessCompatibilityRelease._validate_version_range` permits `baseline < maximum`. By the function's own premise, a release declaring `maximum > baseline` blesses versions certification never observed. Both readings cannot be true.

Nothing breaks today, because the only shipped release with a declared maximum is `grok-1.0.4-r2` where `minimum == baseline == maximum == 1.0.4`. So `maximum_version` currently earns its keep in exactly zero places: it is either absent (claude, codex) or redundant with the baseline (grok).

Smallest fix, and the cleaner shape: tighten `_validate_version_range` to reject `maximum > baseline`, at which point `maximum_version` is provably always equal to `blessed_ceiling(release)` and the field can be deleted from `HarnessCompatibilityRelease`, from `HarnessChannelInfo`, and from the TS mirror. `blessed_ceiling` then reduces to `release.baseline_version` and the second ceiling on the payload (finding 6) disappears with it. If deleting the field is out of scope for this slice, the minimum action is rewriting the docstring so it stops arguing a premise the code does not hold.

### 3. Minor. Certification did not keep today's behaviour; it narrowed for claude and codex

The brief asked which versions changed status. Naming them:

- Before: `certification_evidence.CapturedRunEvidenceSource._check_version` refused iff `match.outcome != "compatible"`. For a release with no declared maximum, every version at or above `minimum_version` was `compatible`, including versions above the baseline, so the mint succeeded.
- After: the same versions are `above_ceiling` and refuse.

Concrete: minting `codex-0.144.4-r2` from a run captured on codex `0.150.0` succeeded on `main` and refuses on this branch with "compatible (above_ceiling)". Same for `claude-2.1.211-r2` from any run above `2.1.211`, which is every current Claude Code install. `grok-1.0.4-r2` above `1.0.4` is the only case genuinely unchanged: it refused before through `harness_version_blocked` and refuses now through the position guard.

No version moved in the other direction: nothing that previously refused now mints.

The narrowing is defensible and arguably correct, since the mint always evaluates `self._entry.release`, which is the release being minted, so its baseline is the version the run proved. But the commit message presents the guard as preserving the refusal, and it does more than that. Smallest fix: no code change, state the narrowed mint window (`[minimum_version, baseline_version]`) in the commit message and in the `docs/HARNESS-COMPATIBILITY.md` paragraph, which currently says only "an above-ceiling run mints nothing" without noting that this is newly true for claude and codex.

One cosmetic consequence worth folding in: the refusal message interpolates `{match.outcome} ({match.range_position})`, so the above-ceiling refusal reads "cannot certify ...: compatible (above_ceiling)". Legible, but the word "compatible" inside a refusal is avoidable.

### 4. Minor. The field's own contract docstring still describes the deleted rule

The diff rewrote the "outside every certified range" sentence in the `probes/targets.py` module docstring and in `resolve_compatibility_release_id`, and missed the model that owns the field. `api/src/transport_matters/harnesses/connections.py::LocalTargetObservation` still says:

> `compatibility_release_id` is null while observing a version outside every certified range; an in range observation carries the active release id.

After the diff it is null only below the floor, or when no pointer or entry resolves. This is the docstring a reader reaches first when asking what the field means, and it now states the rule the diff deleted.

Two more stale claims in the same neighbourhood, both about `match_release` being uncalled, both false since S2f shipped (`compatibility_service` documents itself as "the first production `match_release` caller"):

- `probes/targets.py` module docstring: "`match_release` (uncalled until S2f wires launch gating)". The diff edited the following sentence of this very docstring.
- `harnesses/blocks.py` module docstring: "`match_release` stays uncalled". Not touched by the diff.

Smallest fix: correct the `LocalTargetObservation` docstring to say "below the release floor", and delete the two parentheticals.

### 5. Minor. The floor comparison is now expressed twice

The ceiling comparison is expressed exactly once, in `compatibility._range_position`, and `blessed_ceiling` has exactly one caller (verified repo-wide). That half of hypothesis 7 is confirmed. The floor is not: `_range_position` computes `below_minimum`, and `probes/targets.py::resolve_compatibility_release_id` independently computes `compare_versions(normalized_version, entry.release.minimum_version) < 0`.

The diff created `_range_position` as the one place the range is judged, then edited the exact function holding the duplicate copy and left it. Given the repo's zero-tolerance DRY rule, this is the moment to collapse it.

Smallest fix: make the range classifier public (`range_position(...)`) and have `resolve_compatibility_release_id` return `None` when it yields `"below_minimum"`. `match_release` cannot be reused wholesale there, because attribution deliberately ignores channel status and blocks, so the classifier is the right seam.

### 6. Minor. Both new payload fields are pure pass-throughs with no test at either surface

`compatibility_service._gate` threads `range_position` and `blessed_ceiling_version` into `CompatibilityGateDecision`, and `inventory._harness_item` threads them into `HarnessCompatibilityInfo`. Delete either assignment and every gate still passes: `test_compatibility_service.py` and `test_inventory.py` gained nothing in this diff, and the vitest tests construct the payload by hand through `makeInventoryItem`, so the hand-written TS mirror is never checked against what the backend actually emits.

The vocabulary fixture pins union members, not payload shape, so it cannot catch a dropped field either. Surfacing the range is the deliverable of this slice, and it is the one part of the slice nothing proves.

Smallest fix: one assertion in `test_inventory.py` on the claude item (it already has a channel and an observed version) asserting `compatibility.range_position` and `compatibility.blessed_ceiling_version`, and one on the decision returned by the existing gate test. Both are additive to tests that already build the state.

---

## Notes

### N1. Hypothesis 1 confirmed. No remaining refusal path for an above-ceiling version, under either posture

Traced end to end, with the executed result at each hop for a clean above-ceiling observation:

- `compatibility.match_release` returns `outcome="compatible"`, `range_position="above_ceiling"`, `blessed_ceiling_version="2.1.211"`. Executed, not inferred.
- `resolver._compatibility_disposition` returns `None` for `compatible` **before** it consults `compatibility_enforcing()`, so `_apply_compatibility` produces no `ResolutionRejection` and `_collect_compatibility` appends no exclusion code, identically under `advisory` and `enforcing`.
- `resolver._offered_targets` was the real hazard, and the diff correctly identified it: `accepts_unattributed` is limited to `harness_update_required` and `harness_version_unknown`, so a `compatible` above-ceiling version needs its target evidence attributed or the whole native catalog is filtered out. `resolve_compatibility_release_id` now attributes it.
- `compatibility_service._gate` raises only on `compatibility_enforcing() and decision.outcome != "compatible"`, so enforcing does not refuse either. Its recording path is also clean: `compatibility_facts.compatibility_fact_artifact` performs no range validation, so the enforcing fail-closed `except Exception` handler in `gate_launch_preparation` cannot be tripped into a `compatibility_release_unavailable` refusal by an above-ceiling version.
- Connection evidence was never version-bounded: `state_refresh` stamps authentication and access observations with `entry.release.release_id` unconditionally, so `connections.connection_evidence_matches_scope` was already unaffected by the ceiling.

Only `certification_evidence` refuses, by design (finding 3).

One operational caveat: for an already-stored target observation recorded while the old code nulled its attribution, the fix takes effect on the next target enumeration, which `state_refresh` runs at startup. No migration is needed, but a machine that does not refresh keeps the old rows and the old symptom.

### N2. Hypothesis 2 refuted. The regression test pins the observable end state

`test_resolver.py::TestEvidenceCurrency::test_version_above_the_blessed_ceiling_still_offers_its_targets` asserts `assert options` (non-empty), `all(option.launchable ...)`, and `resolve_target(native_request(), snapshots).rejection is None`. Those are the end state a user experiences.

It fails for the right reason on revert. `make_produced_target_evidence` really calls `build_target_observation`, and it is constructed after the two `monkeypatch.setattr` calls on `targets_module`, so the production attribution path runs against the synthesized closed-ceiling release. Revert `probes/targets.py` alone and the evidence carries `compatibility_release_id=None`, `_offered_targets` filters it out, `launch_options` returns `()`, and `assert options` is the first assertion to fail. The trailing `assert evidence.compatibility_release_id == ...` is an intermediate, but it is last and not load-bearing.

Placement nit only: the test sits in `TestEvidenceCurrency`, which is about evidence staleness rather than version range, and it has to override the class's shared `make_snapshots` target observation to do its work.

### N3. Hypotheses 3 and 4. No live disagreement between the two ceilings, and no frontend misuse

`blessed_ceiling` has exactly one caller (`match_release`), verified repo-wide. `_validate_version_range` reads `maximum_version` raw and the fallback never reaches it. `resolve_compatibility_release_id` no longer reads any ceiling. `certification_evidence` reads the position, not the ceiling. So the only place the two readings coexist is the inventory payload, where `channel.maximum_version` is the raw value and `compatibility.blessed_ceiling_version` is the effective one.

On the frontend: `HarnessChannelInfo` has **zero** readers in `www` today. A grep across `www/packages` and `www/apps` finds the interface declaration, the `makeChannel` test fixture, and nothing else. `supportFact` reads the effective ceiling and says so in its docstring, and `harnessInventory.ts` documents the divergence on the interface. So the trap is latent rather than sprung. It is also removable rather than documentable, which is what finding 2 proposes.

### N4. The enumerated block mechanism is intact, and the dead literal is genuinely gone

Executed: a version-scope block at the baseline returns `harness_version_blocked` with `recommended_pin_version` and `reason_code` preserved, and a version-scope block above the ceiling also returns `harness_version_blocked` with `range_position="above_ceiling"`. Blocks still refuse specific versions, including new ones. The block ordering in `match_release` (release, then version, then route, then target) is unchanged; only the return construction was factored into the `matched` closure.

`harness_version_unsupported` has zero occurrences anywhere in the worktree, including docs, the shared vocabulary fixture, and the TS mirror. Removal is complete.

### N5. Nothing claims a comparison ran

The only strings the above-ceiling card emits are "Newer than blessed" and "blessed to `<version>` · wire comparison due". "blessed to" is a manifest fact. "due" states a pending obligation, which is true of the model. No text asserts a comparison happened, and no text asserts a stored baseline exists. The known-context constraint is respected.

Residual, offered for judgement rather than as a defect: "due" implies something will run it, and nothing will, since the comparator is not wired outside the baseline harvester and no baseline exists on this machine. If the operator has no action to take, "not compared yet" is the more honest phrasing.

Related and worth stating plainly: the only durable record that a harness is above the ceiling is the `range_position` value in the `harness_compatibility_gate` audit detail, which nothing reads. That is consistent with a slice that only builds the state machine, so long as nobody mistakes the card text for a queued job.

### N6. Vocabulary pin, house rules, and one identity-digest side effect

Vocabulary pin (hypothesis 6) is complete on all three planes. `shared/harness_inventory_vocabulary_v1.json` gained `blessed_range_position`; `test_inventory_vocabulary._VOCABULARIES` maps it to the Python alias; `harnessInventory.test.ts` gained the `EXPECTED` member list, the `Equal<BlessedRangePosition, ...>` entry, **and** the matching thirteenth `true` in the value literal, so the tuple length change is satisfied on both the type and the value side and tsc will actually enforce it. `expect(fixture).toEqual(EXPECTED)` is key-order insensitive, so the JSON placement does not matter.

House rules: `compatibility.py` is 635 lines, `resolver.py` 668, `harnessCards.ts` 429, all under 700. `match_release` is roughly 90 lines including the nested `matched` helper, under 150. No em dash appears on any added line in any file, and the commit message is clean. The `·` separator in the new card detail is the file's existing `joinDetail` idiom, not a new one. `supportFact` follows the degrade-on-unknown-member switch idiom used by `authenticatedFact` and `accessFact` rather than the exhaustive no-default idiom used by `installedFact`, which is the correct choice of the two for a backend-sourced union.

Side effect worth knowing about: `compatibility_service.gate_dispatch_identity` digests the entire `CompatibilityGateDecision`, so the two added fields change the dispatch id for otherwise identical outcomes. A retry of a run first recorded by a pre-branch build will insert a new audit row instead of deduping onto the old one. This repo carries no backward-compatibility obligation, so it is informational, and `test_identical_outcomes_share_a_dispatch_id` still holds within a single build.

### N7. The doc reconciliation is one sentence short

`docs/HARNESS-COMPATIBILITY.md` gained an accurate paragraph, but the sentence two lines above it in the "Identity and release" section still reads "It pins baseline and minimum versions ... The range ceiling is open under runtime drift detection." A reader now meets "the ceiling is open" and "the blessed ceiling is `maximum_version` or `baseline_version`" within four lines. Both are true under different senses of "open", which is exactly the ambiguity the new paragraph exists to remove. Fold the older sentence into the new paragraph, or reword it to "the ceiling never refuses".
