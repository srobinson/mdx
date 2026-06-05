# TM PR #451 review: publish compatible harness ranges

Target: `fix/baseline-range-publication` at `bcfc43ff`. Tree pristine, read only, no
provider turns spent. Gates run independently: `cd api && just check` clean (ruff, mypy
843 files), `just test` 4213 passed.

Verdict: **0 major, 3 minor. Merge.**
A drifted version **cannot** silently widen the range.

## Correction to the brief

The brief says "against main db6131c3" and "#450 is CLOSED unmerged". Neither holds.
`#450` is **merged** as `d96b0bf6` ("Mint a new revision when the cohort changes (#450)")
and is in `main`; `main` is now `d96b0bf6`, and the merge base of this branch is
`d96b0bf6`, not `db6131c3`. The quoted 1082/332 line counts are for `d96b0bf6..bcfc43ff`,
so the delta reviewed is right and only the stated base was wrong. This PR therefore sits
*on top of* #450 and removes the revision-chain machinery that shipped in it.

Worth noting, since it bears on the judgement below: two of my three #450 minors were
fixed before that merge. `describe_release_changes` now names what moved (m2), and
`baseline_store.read_latest_baseline_for_version` now selects on the bundle's recorded
`generated_at` with `bundle_id` as tiebreak instead of filesystem mtime (m3). The third,
`maximum_version` being silently reverted, is superseded by this PR's range model.

## The load-bearing judgement: dropping revision chains

**I agree with the reasoning, and the facts behind it check out.**

- `RejectAllSignatureVerifier` is the only concrete `SignatureVerifier` in the tree, and
  every derived signature is `stub:embedded:{release_id}`. Nothing verifies anything.
- `compatibility_releases_v1.json` appears in exactly one production module,
  `harnesses/compatibility_store.py`. There is no fetch, download, or retrieval path.
- It is force-included in the wheel by `api/pyproject.toml`. It ships as package data.

So the manifest is source, distributed inside the build, never fetched and never verified.
Git is its revision history, and an in-manifest revision chain buys nothing a commit does
not already provide. Immutable revisions start earning their keep when #448 gives the
manifest a delivery channel that can fetch and verify it.

The immutability that *does* matter today is preserved rather than dropped.
`compatibility_store.update_release_catalog_entries` refuses to replace any id that is not
an `-r1` catalog candidate, so certified `r2+` content cannot change, and
`certification_minting.mint_outcome` now requires `plan.baseline_version` to equal the
target release's baseline, pushing baseline establishment into source publication where it
belongs. The mutable surface is exactly the uncertified candidate, which is exactly source.

## 1. References do not move on a widen

**Holds.** `release_publication.widen_release_range` rebuilds only the release row and
passes `entry.routes`, `entry.targets` and `entry.references` through unchanged. Verified
live against the real `claude-2.1.241-r1`:

    references identical: True
    targets identical   : True
    routes identical    : True
    release fields changed: maximum_version '2.1.241' -> '2.1.256',
                            published_at, release_digest
    observed_harness_version on refs still: ['2.1.241']

So a widened entry still points at evidence captured at its baseline, and the only
recomputed field is the digest, which `seal_release_entry` must recompute for the changed
payload. The candidate cohort assembled for the comparison is discarded;
`reference_minting.assemble_reference_catalog` is pure (it reads projections and builds
values, writing nothing), so running it for the EXACT test has no side effect.

Widening is also monotonic: `widen_release_range` raises unless the new maximum is strictly
above `blessed_ceiling`. Live, both `2.1.241` (equal) and `2.1.200` (lower) are refused.

## 2. The no-op, at every depth

**Holds.** Verified live against his store and manifest, with the writer stubbed:

    run 1: release catalog updated=claude-2.1.241-r1
           changes=ref opus: effort None -> 'low'; target opus: evidence_digest
    run 2: release catalog unchanged=claude-2.1.241-r1 action=no-op   (0 writes)
    run 3: release catalog unchanged=claude-2.1.241-r1 action=no-op   (0 writes)

The same-baseline cohort change updates `claude-2.1.241-r1` **in place**, keeping its id,
and the following runs write nothing. `update_release_catalog_entries` adds a second
backstop: it compares the rebuilt document against the parsed original and skips both the
write and the cache clear when `updated == raw`.

After a widen the no-op is reached by a different branch: `exact` plus
`compare_versions(observed, ceiling) == 0` short-circuits to `existing_ids` before any
entry is built. `test_baseline_publish_revisions.test_exact_newer_cohort_widens_only_the_maximum_once`
covers that path.

## 3. Drift cannot silently widen

**Holds, and I tried hard to break it.** `reference_cohort_is_exact` requires the stored
and candidate reference sets to have identical `(route_id, launch_model_id)` keys, equal
`canonical_model_id` per key, and `compare_request_schema(...).outcome is DriftOutcome.EXACT`
for every cell, with a `ValueError` from the comparator failing closed to `False`. EXACT
means zero gating findings, since `report_outcome` returns EXACT only when no finding is
BREAKING or DEGRADED.

Characterized against the owner's real 10-cell claude cohort:

| candidate cohort | verdict |
| --- | --- |
| identical | widen |
| only `observed_harness_version` differs | widen |
| only `effort` differs | widen |
| `canonical_model_id` changed on one cell | new baseline |
| one property removed from one cell's schema | new baseline |
| one property added (always present) | new baseline |
| one property added intermittently (1 of 3 observations) | new baseline |
| one property's kinds widened (`string` -> `string\|null`) | new baseline |
| one model missing from the cohort | new baseline |
| one extra model in the cohort | new baseline |

Nothing a new version *adds, changes, or removes* gets through. The two things that widen
are the two that must: the version being blessed, and effort, which the capture design
already established changes content without changing structure.

Two boundaries are deliberate rather than defects, and both are the documented contract
("structure gates, content never gates"):

- Opaque content is not merely skipped at comparison time, it is never recorded. In the
  live reference, `tools[*].description` and `tools[*].input_schema` are stored as
  `{"opaque": true, "properties": null}`. There is nothing to diff, so a version that
  changes only system text, tool descriptions or tool schemas widens. `_compare_nodes`
  additionally raises if the two sides disagree about where the opaque boundary sits, so
  the boundary itself cannot drift unnoticed.
- Negative evidence does not gate. See m3.

## 4. The deliberate assumption is documented

**Holds.** `docs/HARNESS-COMPATIBILITY.md` states it in the range section, where a reader
meets `blessed_ceiling`, not buried in a publisher runbook: source publication captures
only the latest installed version, "Intermediate versions are assumed compatible and are
deliberately unproven", the repair is the operator raising `minimum_version` to the
earliest retained known good version, "Both bounds remain operator owned", and "Automatic
widening changes only `maximum_version` and never narrows either bound".

It does not contradict the rest of the contract. The older paragraph calling a release an
immutable signed snapshot is amended in place to "Once certified", with the `r1` candidate
named as replaceable until certification produces its successor. The publisher flow diagram
was updated to match the new order.

Passing remark, not a finding: the edited immutability paragraph left one line noticeably
longer than the surrounding wrap.

## 5. Edge cases

**All three refuse comprehensibly, before any capture.** `preflight_release_catalog` runs
inside `prepare()`, which `execute_baseline_publish_plan` calls before the spend
confirmation and before the capture loop, reporting `publication preparation refused: …`
and returning 2. Live:

    MISSING   gemini: no embedded release exists; source publication needs a baseline
    DUPLICATE claude: latest baseline '2.1.241' is ambiguous across releases
                      ['claude-2.1.241-r1', 'claude-2.1.241-rX']
    DOWNGRADE claude: observed harness version '2.1.240' is a downgrade from published
                      ceiling '2.1.241'; source publication never narrows a range

A downgrade never narrows: it refuses before reaching any code that could write. There is
also a neat guard against equivalent-but-differently-spelled versions comparing equal while
differing as strings.

The downgrade rule has a false-positive case; see m1.

## 6. The bounds stay operator owned

**Holds.** `derive_inactive_release_entry` carries `minimum_version` and `maximum_version`
forward from the predecessor when the baseline is unchanged, and pins both to the baseline
only for a genuinely new one. Live, the in-place update of `claude-2.1.241-r1` left
`2.1.241 / 2.1.241` untouched. `widen_release_range` writes `maximum_version` only.
Nothing on either path writes `minimum_version` or lowers a bound. This closes the defect I
raised against #450.

## 7. Outside the range model

The `certification_minting` change is in scope rather than stray: `mint_outcome` now always
requires the plan's baseline to match the target release, dropping the branch that let
certification establish a new baseline from immutable bindings, and `successor_entry` loses
its `baseline_version` override so a successor inherits the operator's range instead of
resetting it. `next_release_id` survives for certification; `initial_release_id` moved to
`release_publication` beside its only caller and `release_revision` is gone with the chain.
`release_identity.is_catalog_candidate_release_id` is a shared one-line vocabulary used by
both the store and the publisher. Nothing unrelated rides along.

---

## Minors

**m1. A version inside a blessed range is refused as a "downgrade", and it aborts the whole
`--all` run.** `baseline_publish._source_predecessor` refuses whenever
`compare_versions(observed, blessed_ceiling) < 0`. Once a range has been widened, every
version the release *already blesses* trips it. Verified live with baseline 2.1.241 and
ceiling 2.1.256:

    observed 2.1.250 -> claude: observed harness version '2.1.250' is a downgrade from
    published ceiling '2.1.256'; source publication never narrows a range

2.1.250 is not a downgrade from anything; it is covered by the range. The right answer is a
no-op naming the covering release and its bounds. The blast radius is what makes this worth
fixing now rather than later: the check runs in `preflight_release_catalog` inside
`prepare()`, so one harness sitting mid-range aborts publication for **every** harness in an
`--all` run, before capture, and the `--all is atomic; publish one harness independently`
hint does not print because that hint lives on the publish-result path, not the prepare
path. Harness auto-update makes this ordinary rather than exotic; codex moved 0.149.0 to
0.149.1 on its own in #449. Suggested rule: `observed` within `[minimum_version,
maximum_version]` is a no-op; only `observed < minimum_version` is a genuine downgrade;
`observed > maximum_version` compares and widens. `docs/HARNESS-COMPATIBILITY.md` states the
same conflation ("An observed version below the published ceiling is treated as a
downgrade"), so code and doc move together.

**m2. Replacing a release that a channel state points at is unguarded.**
`compatibility_store.update_release_catalog_entries` refuses to replace non-`r1` ids, and
refuses to **add** an entry whose id is already active, but it computes that second check
from `added_ids = {entry ids} - set(current_ids)`. A *replacement* of an already-present id
is therefore never tested against `active_ids`. Nothing else closes the gap:
`compatibility.py` requires only that `active_release_id` resolve to some release, with no
constraint that it be certified or `-r2`, and `is_catalog_candidate_release_id` is a bare
`endswith("-r1")`. So if an operator ever activates an r1 candidate, the next publication
silently rewrites the content under a live channel pointer, which is the one thing the
activation guard exists to prevent. Compute `activated` over all entry ids that appear in
`active_ids`, replacements included.

**m3. A widen throws away the comparator's findings, including evidence that the new version
stopped exercising the blessed shape.** `reference_cohort_is_exact` reads
`compare_request_schema(...).outcome` and discards `.findings`. Removal of a JSON kind is
emitted with `outcome=None`, and `report_outcome` folds `None` to EXACT; `present_in` and
`observation_count` are not compared at all. Both verified:

    reference string|null -> candidate string    : exact, findings=[(None, MISSING)]
    reference string      -> candidate string|null: degraded
    property present_in 3 -> 2 (became intermittent): widen

The stance is defensible, and I would not change it: three probes are weak negative
evidence, and treating "this capture happened not to exercise it" as drift would make
widening nearly impossible. What is not defensible is that the operator never hears about
it. The widen prints only `maximum_version 'X' -> 'Y'`, so a version that quietly stopped
sending a nullable field, or started sending a field only sometimes, extends the blessed
range with no trace. The findings are already computed and thrown away. Collect the MISSING
ones and print them on the widen line, so the operator sees what the widen did not prove.
