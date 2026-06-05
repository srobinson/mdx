# PR #425 review — fix/preserve-canonical-model-identity

Reviewer: independent (did not build this PR). Baseline `main` at `153d0324`, head `9c8d443c`,
3 commits, +436/-194 across 8 files.

Method: read-only. The branch was never checked out. Blobs were read with
`git show 9c8d443c:<path>` and `git show main:<path>`; every behavioural claim below was produced
by running exported trees (`git archive 9c8d443c api` and `git archive 153d0324 api`) in a
scratchpad against the repo interpreter `api/.venv/bin/python` (3.14). The repo working tree was
pristine before this review and is pristine now.

## Verdict

**8 findings: 2 Major, 6 Minor. No Blocker.** The core fix is correct, and its fixture is
genuinely load-bearing. Both Majors come from the canonical fallback and the `None` canonical
value, not from the discard fix itself. Finding 1 is reachable with today's release data.

## Priority checks

**1. Actuation is unchanged in the resolved path. Clean, with one hole (Finding 4).**
`resolver.py:556` still sets `ResolvedTarget.model_id = target_evidence.native_model_id`, and
`launch_target.py:54`, the only production reader, hands that to the launch profile. No production
path reads `canonical_model_id` for actuation: the readers are `harness_launch_view.py` (display),
`certification_evidence.py:438` (edge-set comparison), and `resolver.py` itself. Executed against
a divergent fixture, the opt-in path returns `('opus', None, ())` — the native selector. The hole
is the pass-through rejection path, Finding 4.

**2. The fixture is genuine and load-bearing. Verified independently.**
`test_resolver_model_identity.py` uses `CANONICAL_MODEL="claude-opus-4-8-20260801"` against
`NATIVE_SELECTOR="opus"`, so the ids actually differ. I reinstated **only** the discard in the
exported tree (`decorate_target` -> `canonical_model_id=None`, one line, nothing else) and re-ran
`src/transport_matters/harnesses/`:

```
unmutated:            2 failed, 621 passed      (the 2 are export artifacts, see below)
discard reinstated:   8 failed, 615 passed
```

The six new failures: `test_canonical_request_resolves_to_native_selector_for_actuation`,
`test_native_request_matches_block_keyed_by_canonical_model`,
`test_launch_option_carries_selector_and_canonical_identity`,
`test_native_selector_match_precedes_canonical_fallback`,
`test_resolver.py::TestTargetSelection::test_target_block_is_advisory`, and
`test_resolver_launch_options.py::test_matching_edge_attaches_certification_metadata_and_advisory`.
The fixture reaches `decorate_target` and the discarded `edge.model_id` is load-bearing.

The two baseline failures (`test_inventory_vocabulary`, `test_registry`) fail on the *unmutated*
export too: they read fixture files outside `api/`, which `git archive api` does not carry. They
are an artifact of my sandbox, not of the PR.

**The chain does not reach the launch view.** That is Finding 8: with the discard reinstated, both
launch-view tests stay green (`3 passed`), because
`test_launch_projection_preserves_distinct_canonical_identity` hand-builds its `LaunchOption`.

**3. The third commit belongs. It is a correction inside this PR, not scope creep.**
`fea8d75a` introduced the canonical fallback as a **single** pass:
`model_id in (target.observation.native_model_id, target.canonical_model_id)`. That is order
dependent: a request naming a native selector could bind to an earlier target whose *canonical* id
equalled that string. `9c8d443c` replaces it with two ordered passes (`resolver_targets.py:51-60`),
native first, canonical only as fallback, and adds
`test_native_selector_match_precedes_canonical_fallback`, which builds exactly that collision
(A: native `opus` / canonical `claude-opus-4-8-20260801`; B: native `claude-opus-4-8-20260801` /
canonical `claude-opus-policy`) and asserts the request binds to B.

Against `main` it changes nothing any current input can produce: all nine targets in
`compatibility_releases_v1.json` have `model_id == native_model_id`, so the native pass always
matches first and the canonical pass is unreachable. The commit is necessary given the fallback
and it belongs here. What deserves scrutiny is the fallback itself, which arrived in `fea8d75a`
and was not in the brief: Findings 2 and 6.

**4. `target_unavailable` truthfulness. One Major.** Resolved identity is correctly optional, and
`test_unresolved_identity_keeps_enumerated_selector_launchable` proves a locally enumerated
selector with no release edge stays `launchable` with `canonical_model_id is None`. Missing
resolution does not make an enumerated selector unavailable. The defect is the other direction:
that same `None` now makes a target-scope block unreachable. Finding 1.

**5. The refactor is a move, not a rewrite. Clean.** `b58f8f26` is verbatim: `_OfferedTarget` ->
`OfferedTarget`, `_decorate_target` -> `decorate_target`, `_find_offered_target` ->
`find_offered_target`, bodies byte-identical to `main`. Promoting all three to public names is
required by `api/CLAUDE.md`'s module privacy rule and enforced by
`test_private_import_boundary.py`; `main`'s `test_resolver.py` referenced none of the privates, so
that commit needed no test change.

`resolver_targets.py` is a sensible owner, not a dumping ground: 60 lines, one frozen dataclass
and two pure functions, no I/O, importing only downward (`compatibility`, `connections`) and under
`TYPE_CHECKING`, which is correct because `OfferedTarget` is a plain dataclass rather than a
pydantic model whose annotations are evaluated at runtime.

The test split (`test_resolver.py` 729 -> 592, new `test_resolver_launch_options.py` 165) landed
in `fea8d75a` rather than the refactor commit, and it is a pure move: the concatenated test
function names of the two files are identical to `main`'s, in the same order. Worth noting only
because `main`'s `test_resolver.py` was **over the 700 hard limit** at 729, so mandatory
refactor-first work ended up bundled into a fix commit.

**6. No prohibited additions. Clean.** No alias catalog, no second catalog parser, no model
argument builder, no refresh endpoint or scheduler. The existing
`HarnessModelCompatibility.model_id` / `native_model_id` relation is read, never duplicated.

**7. Sizing. Clean.** `resolver.py` 668 -> **646**, as reported. `resolver_targets.py` 60,
`harness_launch_view.py` 242 -> 257, `certification_evidence.py` 669 (unchanged),
`test_resolver.py` 729 -> 592, `test_resolver_launch_options.py` 165,
`test_resolver_model_identity.py` 129, `test_controlplane_mcp_inventory.py` 352 -> 384. Nothing
over 700. Longest function in the touched production files is `resolve_target` at 92 lines;
`launch_options` 75, `_project_models` 29, `decorate_target` 22. Nothing near 150.

---

## Finding 1 — Major. Target-scope blocks are inert for any target with no release edge

**`api/src/transport_matters/harnesses/resolver.py:537` and `:626`**, from
**`resolver_targets.py:41`**

`_tuple_match` is now passed `target.canonical_model_id`, which `decorate_target` sets to `None`
whenever no release edge matches. `match_release` (`compatibility.py:633`) guards its target-block
loop with `and model_id is not None`, so for any `observed_unverified` target the block is skipped
by construction. There is no value an operator can put in `VersionBlock.model_id` to reach such a
target, because it has no canonical id at all. The control is unreachable, not merely re-keyed.

Unlike everything else here this is reachable with **today's** data: it needs only a locally
enumerated model absent from the release, which
`test_unresolved_identity_keeps_enumerated_selector_launchable` establishes is a supported,
launchable case.

Same fixture, same request, both trees:

```
target:  native_model_id="claude-enumerated-only", no release edge
block:   scope="target", route_id=ROUTE, model_id="claude-enumerated-only"
request: native, model_id="claude-enumerated-only", allow_unverified_target=True

main (153d0324):  resolved=True  advisories=('target_unavailable',)
PR   (9c8d443c):  resolved=True  advisories=()
```

Under the enforcing rollout posture that advisory is the refusal, so `main` refuses the blocked
target and the branch launches it.

The fix is the idiom this PR already uses one file away, at `certification_evidence.py:438`
(`option.canonical_model_id or option.model_id`): pass
`target.canonical_model_id or evidence.native_model_id` at both call sites. That keeps the
canonical keying the PR wants for certified targets and restores block reach for unattributed
ones. The inconsistency between the two files is itself the tell.

## Finding 2 — Major. The canonical fallback resolves silently and order-dependently

**`api/src/transport_matters/harnesses/resolver_targets.py:57`**

The canonical pass takes the first match with no ambiguity guard. Nothing forbids two edges
sharing one `model_id`: `CompatibilityReleaseEntry._validate_references` (`compatibility.py:403`)
checks route-id uniqueness and route references only. With edges `(opus -> CANON)` and
`(opus-latest -> CANON)`, an explicit request for `CANON`:

```
observations ('opus', 'opus-latest')  -> resolved model_id = opus
observations ('opus-latest', 'opus')  -> resolved model_id = opus-latest
```

`LAUNCH-CONTRACT.md` states the selection order and then "fail on ambiguity or absence", and
`_select_edge` returns `target_ambiguous` (`resolver.py:429`) for exactly this shape in the
default path. The new lookup path silently picks one instead, and the caller launches a different
model than they named with no advisory. `test_native_selector_match_precedes_canonical_fallback`
covers native-versus-canonical precedence but not this canonical-versus-canonical collision.

Either refuse the collision the way `_select_edge` does, or state that a canonical id is not an
accepted request selector at all (see Finding 6).

## Finding 3 — Minor. The block key for certified targets inverted, undocumented

**`api/src/transport_matters/harnesses/resolver.py:537`, `:626`**

For a certified target the same change inverts which identity a target-scope block must use:

```
divergent target: canonical="claude-opus-4-8-20260801", native="opus"

main (153d0324):  block keyed by NATIVE -> ('target_unavailable',)   CANONICAL -> ()
PR   (9c8d443c):  block keyed by NATIVE -> ()                        CANONICAL -> ('target_unavailable',)
```

Canonical is the correct key: `SCOPE_KEY_FIELDS["target"]` is `("route_id", "model_id")` and
`VersionBlock.model_id` pairs by name with `HarnessModelCompatibility.model_id`. The code is
right and `main` was wrong. The gap is that this is stated nowhere: `VersionBlock.model_id`
(`compatibility.py:323`) carries no docstring, `docs/HARNESS-COMPATIBILITY.md` never mentions
`model_id`, and no validator binds a block's `(route_id, model_id)` to an existing release target.
A block authored with the native selector becomes a silent no-op the moment a release ships
divergent ids. One sentence on the field, or a validator, closes it.

## Finding 4 — Minor. The pass-through still actuates on the caller's canonical id

**`api/src/transport_matters/harnesses/launch_target.py:60`**

On a pass-through rejection `resolve_launch_target_advisory` returns `request.model_id` verbatim.
For a divergent `observed_unverified` target without opt-in:

```
main (153d0324):  ('claude-opus-4-8-20260801', None, (target_unavailable {model_id: 'claude-opus-4-8-20260801', reason: 'not_observed'},))
PR   (9c8d443c):  ('claude-opus-4-8-20260801', None, (target_unverified_opt_in_required {model_id: 'opus'},))
PR, with opt-in:  ('opus', None, ())
```

**Not a regression**: `main` forwarded the same canonical id, and the pass-through is documented
("Unknown explicit models, invalid efforts, and unverified targets pass through as requested").
But the PR changes the situation: the resolver now *finds* the target, so it holds
`target.observation.native_model_id` at the moment it rejects, and discards it anyway. One return
value carries two contradictory identities — the launch model is the canonical id while the
advisory detail names `opus`. This is the same defect class the PR exists to fix, one layer up,
and the resolver is one line from closing it.

## Finding 5 — Minor. The launch view drops a conflicting canonical identity

**`api/src/transport_matters/api/v1/harness_launch_view.py:172`**

`model.canonical_model_id = model.canonical_model_id or option.canonical_model_id`

`_project_models` groups by `option.model_id`, the native selector, and `decorate_target` resolves
the edge per route, so two connections or routes can map one selector to different canonical
models. Every other field in this merge accumulates (`efforts.extend`,
`exclusion_reasons.extend`, `requires_unverified_opt_in |=`); this one keeps whichever option came
first and discards the other with no signal, so `_has_deviation` cannot flag what it never sees:

```
options: ("opus", canonical="claude-opus-4-8"), ("opus", canonical="claude-opus-policy")
models:      ['opus']
deviations:  [{'id': 'opus', 'canonical_model_id': 'claude-opus-4-8'}]
```

The mutation itself is fine and matches the file's pattern (`_ModelProjection` is a mutable
`@dataclass(slots=True)`); the defect is the silent conflict resolution.

## Finding 6 — Minor. The request contract widened without saying so

**`api/src/transport_matters/harnesses/resolver.py:56` and `:63`**

`fea8d75a` widened what `ResolverRequest.model_id` and `AgentTargetPreference.model_id` accept: a
request naming a canonical id now resolves where `main` returned `target_unavailable`. Both fields
are bare `model_id: str` with no docstring, and neither the class docstrings ("Caller intent for
one resolution: explicit fields are honored or rejected", "One agent supplied target preference")
nor `docs/LAUNCH-CONTRACT.md` records that two identity spaces are now accepted on one field.

That is the exact ambiguity this project is removing elsewhere: one field, two meanings, and a
caller cannot tell which it supplied. The widening may well be wanted, since an agent
recommendation plausibly carries a catalog id rather than a native selector. It should be stated
at the contract rather than inferred from a lookup helper — and Finding 2 is what that ambiguity
costs when two edges collide.

## Finding 7 — Minor. `exclude=True` inverts the lean and full view contract

**`api/src/transport_matters/harnesses/resolver.py:209`**

`canonical_model_id: str | None = Field(default=None, exclude=True)`

The MCP tool is documented as "List lean launch choices by default; pass `view=full` for
diagnostics" (`controlplane_mcp.py:411`), and the new test asserts `"canonical_model_id" not in
full_option`. So the diagnostics view is now strictly less informative than the lean view for the
one field this PR adds. It also means any round-trip of a `LaunchOption` through
`model_dump`/`model_validate` loses the identity silently. Keeping the hand-written TS in
`www/packages/core/src/types/harnessInventory.ts` unchanged is a reasonable motive; an optional
field there is cheap and removes the inversion.

## Finding 8 — Minor. No fixture-backed coverage through the launch view

**`api/src/transport_matters/api/v1/test_controlplane_mcp_inventory.py:257`**

`test_launch_option_carries_selector_and_canonical_identity` stops at `launch_options`, and
`test_launch_projection_preserves_distinct_canonical_identity` starts from a hand-built
`LaunchOption` with `canonical_model_id=` passed in directly. Verified: with the discard
reinstated in `decorate_target`, both launch-view tests still pass (`3 passed, 4 deselected`).
Each half of the seam is pinned, but nothing proves a canonical id travels from a release entry
through `decorate_target` and `launch_options` into `project_harness_launch_view`. One test
building its inventory from `launch_options(_divergent_snapshots())` closes it.

## Not findings, recorded

- `certification_evidence.py:438` is correct and complete. `release_edge_set`
  (`certification.py:485`) keys on `target.model_id`, the canonical id, so aligning `resolved`
  with it is the fix; the `or option.model_id` fallback preserves `main`'s behaviour for
  unattributed targets, which legitimately fail the edge-set comparison. I checked whether
  `allowed_models` (canonical) versus `entry.model` (the actuated wire model) was left
  inconsistent, and it is not: the embedded catalog ids are full model ids, not selectors, so the
  wire model is the canonical space.
- `resolver_targets.py` uses `from __future__ import annotations` while `resolver.py` does not.
  Both styles exist in this package; not worth a change.

## Baseline note

While this review was running, `main` advanced from the pinned `153d0324` to `a2401a29` (PR #424
merged). That commit touches only `baseline_evidence.py` and `test_baseline_comparison.py`,
neither of which appears in #425's diff or in any baseline citation above, so every citation and
every executed comparison in this document still holds against `153d0324`. #425 and #424 are
disjoint; #425 needs a rebase onto `a2401a29` but no conflict resolution.

---

# Delta round — `a2401a29..2633df16`

The branch was rebased onto `main` at `a2401a29` and force-pushed; head is now **2633df16**,
four commits, +656/-208 across 12 files. Every sha cited above has changed. Method unchanged:
read-only, branch never checked out, both trees exported with `git archive` and executed against
`api/.venv/bin/python`. Tree pristine before and after.

**Verdict: all eight findings closed. Nothing regressed. The validator approach is sound; I
endorse it.**

## Major 1 — closed, verified independently

`resolver.py:565` and `:654` now pass `target.canonical_model_id or <native>` at both sites. My
own fixture from the first round, unchanged, run against both heads:

```
                    resolve advisories        launch_option advisories
9c8d443c            ()                        ()
2633df16            ('target_unavailable',)   ('target_unavailable',)
```

The block reaches a locally enumerated target again on both paths. The regression is
`test_unresolved_identity_matches_block_keyed_by_native_selector`
(`test_resolver_model_identity.py:126`), and it is precise: reverting **only** the two `or`
fallbacks in the new tree fails that one test and nothing else (`1 failed, 9 passed`). It asserts
both `resolve_target` and `launch_options`.

`VersionBlock.model_id` (Finding 3) now carries a description naming canonical identity as the
key, with the native selector for edge-less targets — which is exactly the fallback behaviour, so
the doc and the code agree.

## Major 2 and the fourth instance — closed. The validator approach is right.

Major 2 proper is fixed with the existing vocabulary, not a second concept: `find_offered_target`
became `matching_offered_targets` returning a tuple, and both `_select_edge` and `_preference_edge`
route `len > 1` into the shared `_target_ambiguity` helper, which is now also used by the
pre-existing default-path ambiguity. Executed:

```
observations ('opus', 'opus-latest')  -> rejected target_ambiguous {'candidates': 'opus,opus-latest'}
observations ('opus-latest', 'opus')  -> rejected target_ambiguous {'candidates': 'opus,opus-latest'}
```

Order independent, and the candidate list is sorted so the message is stable.

**Adjudication of the fourth instance.** `_validate_references` (`compatibility.py:413-417`) now
rejects duplicate `(route_id, native_model_id)` per release, and `decorate_target` does a map
lookup. The concern was whether the validator runs on every construction path and what happens if
it does not. Checked directly:

- `CompatibilityReleaseEntry.model_config` is `{'frozen': True, 'extra': 'forbid'}`, so no
  instance can be mutated into an invalid state after construction.
- Production has exactly two sources: `CompatibilityManifest.model_validate(raw)`
  (`compatibility_store.py:122`, and the embedded loader), and the direct constructor at
  `certification_minting.py:465` and `:469`. Both run `mode="after"` validators, and pydantic
  validates the nested `releases` tuple. There is no `model_construct` and no `model_copy` of this
  model anywhere in production; `embedded_release_entry` only selects from the already-validated
  manifest.
- The shipped `compatibility_releases_v1.json` passes the new rule: 3 releases, 9 targets, no
  duplicate `(route, native)`, verified by loading it.
- The failure mode if the validator were ever bypassed is benign, because `decorate_target` uses
  `.get()`, not `[]`. Forced through `model_construct` with a duplicate, it returns the **last**
  edge rather than the scan's first; with an unknown native id it returns
  `canonical=None, tier=observed_unverified`, identical to the old scan's miss. No `KeyError`, no
  silent miss.

So the ambiguous state really is unrepresentable at the boundary, the boundary really is total,
and the degradation if it ever were not is deterministic rather than an exception. This is the
stronger of the two options and it is correctly executed. One cosmetic note, not a finding:
`decorate_target` rebuilds `edges_by_native_identity` on every call, once per observation, so the
dict is allocated where the scan allocated nothing. Same complexity, and it is called with a
handful of targets.

## Finding 8 — closed, and this is the one that mattered

`test_launch_projection_preserves_distinct_canonical_identity` was replaced by
`test_launch_projection_receives_canonical_identity_from_release`
(`test_controlplane_mcp_inventory.py:266`), which builds its inventory from
`launch_options(divergent_snapshots())` rather than a hand-built `LaunchOption`. Reinstating only
the discard now fails it:

```
FAILED api/v1/test_controlplane_mcp_inventory.py::test_launch_projection_receives_canonical_identity_from_release
```

alongside 6 resolver tests (11 failed total against 2 baseline export artifacts). The chain from
release entry through `decorate_target` and `launch_options` into `project_harness_launch_view` is
now covered end to end. The helper was promoted from `_divergent_snapshots` to
`divergent_snapshots` for the cross-module import, which respects the module privacy rule.

## The six Minors — all closed

- **3 (block key undocumented).** `VersionBlock.model_id` now has a description
  (`compatibility.py:323-329`) naming canonical identity as the key and the native selector as the
  edge-less fallback.
- **4 (pass-through actuated on the canonical id).** `launch_target.py:60` now returns
  `rejection.details.get("model_id", request.model_id)`, and `invalid_effort` gained
  `"model_id": evidence.native_model_id` (`resolver.py:497`). I checked all three pass-through
  codes: `invalid_effort` and `target_unverified_opt_in_required` carry the native selector,
  `target_unavailable/not_observed` carries the request verbatim, which is correct because no
  target was found. Executed: the no-opt-in canonical request now returns `('opus', ...)` where
  `9c8d443c` returned the canonical id, and the returned model finally agrees with the advisory
  detail.
- **5 (view merge dropped a conflict).** `_ModelProjection.canonical_model_ids` is now a `set`
  with a `canonical_model_id` property that returns `None` unless exactly one, and a conflict
  appends `target_ambiguous` to `exclusion_reasons` (`harness_launch_view.py:177-183`). Silent
  loss became a visible exclusion, again reusing the existing vocabulary.
- **6 (two identity spaces on one field).** Descriptions added to `ResolverRequest.model_id`
  (`resolver.py:56-62`) and `AgentTargetPreference.model_id` (`resolver.py:70-75`). **This
  genuinely resolves it rather than recording it, and the difference from #423 is the direction
  of the field.** `RosterItem.model` was an *output* whose two meanings were undecidable at the
  receiving end. These are *inputs*: the caller knows which identity it supplied, precedence is
  documented and deterministic, the canonical space now rejects rather than guesses when
  ambiguous, and the *result* separates the spaces into `ResolvedTarget.model_id` for actuation
  and `canonical_model_id` for evidence. Every input either resolves to exactly one target or is
  rejected by name. That is a total function with a documented rule, not a silent overwrite.
- **7 (`exclude=True` inverted lean and full).** Removed; `canonical_model_id: str | None = None`
  is now serialized, the docstring was corrected, and the TS DTO was extended in both
  `www/packages/core/src/types/harnessInventory.ts` and
  `harnessInventory.testSupport.ts`. The new test asserts
  `full_option["canonical_model_id"] == CANONICAL_MODEL`.
- **8** above.

## Nothing regressed

- **Actuation.** `ResolvedTarget.model_id` is still `target_evidence.native_model_id`, and every
  executed path returns the native selector: `('opus', None, ())` with opt-in, `('opus', ...)`
  without. No production path actuates on a canonical id.
- **`b36d383e` is still a behaviour-preserving move** after the rebase: `decorate_target`'s body
  is byte-identical to `a2401a29`'s `_decorate_target` apart from the three privacy renames.
- **Sizing.** `resolver.py` is **674**, not the 646 reported for the previous head — the fix round
  added `_target_ambiguity`, the field descriptions and the ambiguity branches. Still under 700,
  with 26 lines of headroom, so the next change to that file should expect to refactor first.
  `compatibility.py` 638 -> 649, `harness_launch_view.py` 242 -> 268, `resolver_targets.py` 52,
  `test_resolver.py` 729 -> 596, `test_resolver_model_identity.py` 255,
  `test_controlplane_mcp_inventory.py` 352 -> 416. Nothing over 700. Longest function anywhere in
  the touched production files is `resolve_target` at 92; `match_release` 89, `launch_options` 75,
  `_project_models` 34, `decorate_target` 18. Nothing near 150.
- **Gates.** `ruff check` and `ruff format --check` clean, `mypy` clean on the five changed
  modules, and 633 passed in `harnesses/` plus the inventory suite (2 failures and 92 errors are
  my sandbox: fixture files outside `api/` that `git archive api` does not carry, and tests that
  need a database URL).
