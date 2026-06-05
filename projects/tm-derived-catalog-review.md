# Adversarial review: publish-derived release catalog (#447)

Branch `feat/publish-derived-release-catalog` at `a45461f9`, against `main` `a150064a`.
11 files, 738 insertions. Read only.

## Verdict

**1 major, 2 minor. MERGE the code. The spend is safe, but it does not end where he thinks.**

**Manual steps between spending and an active release: six per harness, eighteen in total.**

The code is right. The owner's premise change is right, and it dissolves both failure modes I
found before: the derived catalog cannot say `claude-opus-4-8` when the wire says
`claude-opus-5`, and it cannot carry stale extras, because targets are now emitted from the
captured cells themselves.

The finding is not in the code. It is that after the 42 turns he holds **inactive draft
entries**, and reaching an active release needs a certification mint that requires a fresh
captured run at exactly the installed version, a hand-authored plan with no template, and two
hand-edits of a tracked JSON file, none of which has a recipe. He asked for this before he
spends, so here it is.

Tree pristine at `a45461f9`, `git status --porcelain` empty at start and finish. No writes, no
checkout, no stash. Full suite `4191 passed in 48.21s`, matching the builder's count.

## 1. The activation sequence, walked

I traced every step from "42 turns spent" to "active release" and checked what tooling exists.

### What the recipe gives him

`just baseline-publish-all` captures the 14 missing cells, publishes gate projections, and
calls `release_publication.derive_inactive_release_entry` per harness, which
`compatibility_store.append_inactive_release_entries` writes into the tracked manifest. It
prints `status=inactive activation=certify-then-update-channel-states`.

That is the end of the automation. Everything below is manual.

### What is still required, per harness

**Step 1. A fresh captured run at exactly the installed version.** This is mandatory, not
optional, and it is the step most likely to surprise him.
`certification.CERTIFICATION_FACETS` requires all seven facets present, and a required facet
raises "cites no runtime evidence" without a `runtime_ref`. Runtime evidence comes from
`plan.scenario_ids` through `mint_outcome`'s `runtime_source.collect`, and
`certification_minting.RealRuntimeEvidencePending.collect` raises unconditionally unless the
plan supplies `scenario_bindings`. Since #444, `mint_outcome` also rejects any run whose
`observed_harness_version != plan.baseline_version`. The three existing records observed
2.1.214, 0.144.4 and 1.0.4, so none can be reused for 2.1.241, 0.149.0 and 1.0.5. He needs a
new captured session per harness, at the exact installed version, and its `run_dir`.

**Step 2. Hand-author a `MintPlan` JSON.** `certification_minting.MintPlan` requires
`release_id`, `harness_id`, `baseline_version`, `suites`, `scenario_ids`, `facets`,
`fixture_patterns`, plus `scenario_bindings` and optionally `baseline_bindings`. There is no
template, no generator and no example in the repo. The only file matching a plan shape is
`harnesses/test_mint_plans.py`, a test module. A real record carries seven facets, five fixture
files, one suite result and one runtime run, so the plan is a substantial artifact.

**Step 3. Run the mint.** `uv run python scripts/mint_harness_certification_record.py --plan
plan.json`. No recipe exists for this; `api/justfile` and the root `justfile` have nothing
between `baseline-publish-all` and unrelated release tagging. It requires a clean worktree.

**Step 4. Hand-edit the manifest to replace the draft.** The script's own output says it:
"Replace the release in compatibility_releases_v1.json with the successor entry below, point
the channel states at it, and run --verify-activation before the flip." It prints the successor
entry as JSON on stdout for copy and paste.

**Step 5. Hand-edit `channel_states`.** I grepped for any writer and there is none: no script,
no module function, no recipe touches `channel_states`. `reseal_compatibility_manifest.py`'s
own docstring confirms the expected workflow is "After editing
``compatibility_releases_v1.json`` by hand".

**Step 6. Verify before the flip.** `--verify-activation <release_id>`.

A conditional seventh: `scripts/reseal_compatibility_manifest.py` if the hand edits disturb a
digest.

### The plain answer

**Six manual steps per harness, eighteen across the three**, of which three per harness are
hand-editing a tracked JSON file, one is authoring an artifact with no template, and one
requires provider work the 42 turns do not include.

**Is every step possible today?** Yes, technically. Nothing is missing that would make it
impossible. But nothing is scripted, and the sequence is documented only across a script
docstring, a stdout message, and this review.

**Would he be stranded?** Not permanently. The captured evidence is durable, immutable, and
independent of activation: bundles, projections and the derived entries all survive, and the
resume logic means none of it is ever re-bought. But he would hold paid-for evidence and
discover that "run one recipe and have a working release" is off by an entire certification
project, including another round of provider work.

That is worth knowing before the 42 turns rather than after, which is exactly why this was
asked.

## 2. Derivation correctness

Targets come from the wire model each captured cell actually reported.
`reference_minting._wire_model_id` is
`projection.cell.wire_model.split("/", 1)[-1]`, so `anthropic/claude-opus-5` becomes
`claude-opus-5`, and `assemble_reference_catalog` builds each target with
`model_id=canonical_model_id` (the wire model) and `native_model_id=launch.model_id` (the
alias). The alias to canonical mapping the owner refused to maintain is derived, per capture,
from what the harness actually sent.

Every derived target carries `support_tier="observed_unverified"` and `lifecycle="active"`.
That is the right tier and it also settles a concern I raised at #444: since no derived target
is `tested`, the `decorate_target` reference fallback cannot make a set of aliases default
eligible, so the `target_ambiguous` risk stays inert.

**The grok question: what happens to a cell whose wire identity is not yet known.** It refuses.
Derivation runs after capture, and `assemble_reference_catalog` compares the captured cohort
against the launch view before deriving anything:

    captured_models != set(launch_by_id)
      -> "captured reference cohort does not exactly match the launch view; missing=... unexpected=..."

Exercised live against his real store, binding only his stored `grok-4.6` while the launch view
offers both grok models:

    REFUSED -> captured reference cohort does not exactly match the launch view; missing=['grok-4.5']

and with a cohort that matches:

    DERIVED [('grok-4.6', 'grok-4.6', 'observed_unverified')]

So a partial cohort produces no catalog at all rather than a catalog missing a model. If any
of the 14 captures fails, the harness gets no entry and the failure is loud. That is the right
direction and it is the answer to the derived-after-capture concern.

The eight distinct wire models you list are consistent with what derivation will produce, with
one caveat worth stating: only `claude-opus-5`, `gpt-5.6-sol` and `grok-4.6` are observed at
the *installed* versions in his current store. The rest come from bundles captured at 2.1.238
and from ad hoc `request.raw` traffic. Derivation does not care, because it reads each cell's
own capture rather than a table, but it means the final catalog's exact contents are not
predictable from today's evidence, and grok-4.5's wire identity genuinely is unknown until it
is captured.

## 3. `_validate_target_coverage` is gone, and the property holds by construction

Confirmed removed: no reference to `_validate_target_coverage` survives anywhere in `api/src`.

**The property still holds, and here is the proof.** The claim a release makes about a schema
is a `ReleaseRequestSchemaReference`. In both surviving paths, every reference is built inside
`for projection in projections`, where `projections` comes from `_bound_projections(bindings,
...)`, which reads an immutable bundle off disk per binding. A reference therefore cannot exist
without a captured bundle behind it. `CompatibilityReleaseEntry._validate_cross_references`
additionally requires every reference's `observed_harness_version` to equal the release's
`baseline_version`, so a reference cannot claim a version it did not observe.

In the publish path the guarantee is stronger still, because the targets are emitted from the
same loop: there is no separate catalog to disagree with. That is why the coverage check became
tautological, and removing it was correct.

What was lost is the *converse*, and it is minor 1 below.

## 4. Version semantics

`derive_inactive_release_entry` sets `baseline_version = minimum_version = maximum_version =
installed`. Exercised through the real functions on a derived grok entry:

    baseline/min/max = 1.0.5 1.0.5 1.0.5 | blessed_ceiling = 1.0.5

    installed 1.0.4: below_minimum
    installed 1.0.5: at_ceiling
    installed 1.0.6: above_ceiling

Exactly the owner's ongoing workflow. A later harness version reads `above_ceiling`, and
`LaunchVerificationCoordinator.submit`'s gate admits `above_ceiling` and `unknown`, so it stays
capture eligible: new version, run the recipe, bump the maximum. Anything older reads
`below_minimum`, which `launch_options` maps to `SupportState.DEGRADED` without excluding it.

One property worth naming because it is easy to misread: while the entry is inactive, every
installed version reads `unknown` against it, since `match_release` attributes only through the
active pointer. `unknown` is also capture eligible, so there is no dead zone between publishing
and activating.

## 5. The source write

- **Reuses the existing gate.** `baseline_publish` imports `require_clean_worktree` from
  `harnesses.certification_minting`. One implementation, no second copy.
- **Checked twice.** Once before any capture through the `prepare` callback, and again in
  `publish_release_catalog` immediately before the write, which additionally refuses if HEAD
  moved: "HEAD moved while baselines were captured; release output would name the wrong
  source".
- **Refuses comprehensibly.** A dirty tree surfaces as `publication preparation refused: ...`
  with exit 2 and no capture attempted.
- **The diff is reviewable.** `append_inactive_release_entries` preserves the rest of the
  document (`{**raw, "releases": [*raw["releases"], *new]}`) and writes through
  `write_atomic_json`. I verified the current file round-trips byte for byte through
  `json.dumps(..., indent=2) + "\n"`: 16877 bytes in, 16877 identical bytes out. So the diff is
  the appended entries and nothing else, not a whole-file reformat.
- **Validated before writing.** `_validate_embedded_manifest(updated)` runs the full schema,
  digest, reference, channel and adapter validation over the merged manifest, and the write
  explicitly refuses if a new release id is already active: "new releases must remain
  inactive".

## 6. Spend safety unchanged

- **Cannot spend without confirmation.** The gate in `execute_baseline_publish_plan` is
  unchanged and still first, before `prepare` and before the capture loop. Verified live: with
  `prepare`, `capture` and `publish` stubs that raise on call, the real plan printed and
  returned 2 with none of them fired.
- **Cannot spend more than printed.** `provider_turns` is still `3 if needs_capture else 0`,
  no retry, and the planner and `harvest_baseline`'s in-lock recheck share
  `read_reusable_baseline_for_version`.
- **Cannot mint claiming more than captured.** Section 3.

The live plan is unchanged and matches the builder's report exactly:

    publish plan: harnesses=claude,codex,grok planned_cells=17 missing_cells=14 provider_turns=42
    provider spend refused: confirm interactively or rerun with --confirm-spend

The catalog preflight is gone, as intended, and the spend refusal is now the only gate before
capture.

## 7. The stale entries

They coexist safely. `append_inactive_release_entries` appends and never rewrites existing
entries, `_require_certified_active_pointers` only validates entries an active pointer names,
and the stale releases keep their existing certification records and their active pointers
until step 5 moves them. `publish_release_catalog` also detects an existing entry at the same
version and verifies the captured cohort matches it rather than appending a duplicate,
printing `release catalog current=...`, so re-running the recipe is idempotent.

## Major

### M1. The 42 turns do not produce an active release, and the gap is unscoped

Detailed in section 1. Six manual steps per harness, eighteen total; three hand-edits of a
tracked JSON per harness; a `MintPlan` with no template; and one step that needs provider work
the 42 turns do not cover.

This is not a code defect and nothing here needs changing to merge. It is an expectation gap,
and it is exactly what he asked to know before spending. My recommendation is that he is told
the number before he types `publish`, and that the activation path gets its own slice with at
least a plan generator and a channel-activation command, since hand-editing `channel_states`
in a digest-sealed manifest is the step most likely to go wrong quietly.

## Minor

### m1. Nothing requires a minted release's references to cover its targets

`CompatibilityReleaseEntry._validate_cross_references` enforces references ⊆ targets: every
reference must name a known target. It does not enforce the converse, and with
`_validate_target_coverage` removed from `assemble_reference_material` too, nothing does.

In the publish path this cannot bite, because both come from one loop. In the **mint** path it
can: `certification_minting.successor_entry` copies `entry.targets` unchanged while references
come from the plan's `baseline_bindings`. A hand-authored plan binding a subset yields a sealed
release whose catalog lists models with no schema evidence.

Not an over-claim, since those targets stay `observed_unverified` and claim nothing a launch
view does not already observe. But it is a silent incompleteness the operator can cause by
hand, in exactly the artifact he has to hand-author, and it would show up later as models with
no comparison baseline rather than as an error. A completeness check at seal time would close
it.

### m2. The spend prompt is asked before the worktree check

`execute_baseline_publish_plan` runs the confirmation gate first and `prepare()` second, so a
dirty tree lets him type `publish` to authorize 42 turns and only then refuses with
"publication preparation refused". Fails closed with zero spend, so it is an ordering nit
rather than a risk, but the check costs nothing and belongs before the question.

## Is it safe for the owner to run?

**Yes, the spend is safe.** Nothing can spend without his typed confirmation, nothing can
exceed 42 turns, a partial run cannot produce a catalog, and every captured bundle is durable
and resumable, so no turn is ever bought twice.

**But it does not end where he expects.** If his decision to spend assumes one recipe yields a
working release, the answer he needs is eighteen manual steps, and he should decide with that
number in hand.
