# Adversarial review: release request schema binding (#444)

Branch `feat/reference-schema-binding` at `fc69ed08`, against `main` `96ef6f39`.
53 files, 2941 insertions. Read only.

## Verdict

**2 major, 3 minor. Do not merge yet. NOT safe for the owner to run as it stands.**

Not because it is dangerous. The spend gate is sound, it cannot spend more than it printed,
and it refuses loudly rather than blessing what it did not capture. It is unsafe because it
would **bill him for a codex cohort that structurally cannot be minted**, and it re-buys two
cells he already owns.

Of the 48 provider turns the plan actually asks for on his machine, roughly **21 are wasted**:
15 on codex evidence no mint can consume, and 6 re-capturing cells he has. Fix M1, decide M2,
and it becomes safe.

Every one of the owner's four decisions is genuinely implemented. The failures are in the
economics, not the contract.

## Inspection boundary

Tree pristine at `fc69ed08`, `git status --porcelain` empty at start and finish. No writes,
no checkout, no stash. Full suite `4180 passed in 53.34s`.

I built the real publication plan against his live preview store and exercised the mint path
against his three real bundles, both read only. I spent no provider turns and made no launch.

## The owner's four decisions

### 1. Release owns the range; a local verdict reports only. Implemented.

No local path writes a range. `minimum_version`, `maximum_version` and `blessed_ceiling`
appear nowhere in `support_verdict_store`, `harnesses/reference_minting` or
`launch_verification`. The only writer of release data is
`api/scripts/mint_harness_certification_record.py`, which is repo side and already gated by
`require_clean_worktree`.

The one place a range moves is `certification_minting.successor_entry`, and it moves the
right way:

    if reference_material.references:
        release_fields.update(baseline_version=baseline_version, maximum_version=baseline_version)

A reference release **collapses the ceiling onto the baseline**. It cannot extend a blessing;
it narrows it to the version a capture actually proved. That is the contract in
`docs/HARNESS-COMPATIBILITY.md` implemented literally.

The local verdict path is `launch_verification` writing through
`support_verdict_store.write_support_verdict_for_capture` into
`<channel home>/baselines/`, read back by `resolver_snapshots_for_harness` into
`ResolverSnapshots.support_verdicts`, surfaced by `resolver.launch_options` as
`LaunchOption.support_state`. Report only, end to end.

### 2. Per model, effort recorded not keyed, captured at low. Implemented, haiku included.

`ReleaseRequestSchemaReference.key` is `(route_id, launch_model_id)`; `effort` is a recorded
field outside the key. `baseline_publish._baseline_effort` returns `"low"` when advertised,
`None` when the model advertises no efforts, and raises during planning when a model
advertises efforts but not `low`, which fails before any spend.

Verified on his real inventory rather than by reading. The actual plan:

    claude  haiku      effort=None
    claude  opus       effort=low     (and the other eight claude aliases)
    codex   gpt-5.6-*  effort=low
    grok    grok-4.5   effort=None
    grok    grok-4.6   effort=None

**Haiku is planned at `None` and is not refused.** `_baseline_effort` returns `None` for it
because the launch view advertises no efforts (`claude_launch_effort_options` returns `()` for
haiku), and the capture path never consults the resolver, so no `invalid_effort` rejection can
arise mid-cohort. `harvest_baseline` then resolves `capture_effort` to the launch view's
`default_effort`, which `claude_launch_effort` pins to `None` for haiku. Plan and capture
agree.

`reference_minting._validate_cohort` enforces the low rule at mint time and permits `None`,
so the haiku exception survives into the cohort validator rather than tripping it.

Grok cells carry `effort=None` because grok enumerates no efforts at all, which I confirmed
last round against `harness_target_observation`.

### 3. Advisory permanently. Confirmed; `degraded` cannot gate.

`resolver.launch_options` builds `launchable=not exclusions`, and `support_state` is never
appended to `exclusions`. It is a sibling field on `LaunchOption`, projected into
`LaunchModelDeviation.support_state` for display.

`below_minimum` maps to `SupportState.DEGRADED` in `launch_options`, which matches the
contract that `degraded` carries one meaning everywhere including an unsupported old version,
and it still does not exclude.

One presentational note rather than a gate: `harness_launch_view._has_deviation` now returns
true when `support_state is not None`, so a **blessed** model also renders as a deviation.
That is a display choice, not a block, but it means the deviation list stops meaning "something
is off".

### 4. Spend authorized for all three harnesses. Plan covers all three.

`_selected_descriptors` with `--all` returns claude, codex and grok. The plan is 17 cells and
48 provider turns, slightly above the roughly 45 he authorized.

## Hunt A: can it spend without confirmation? No.

This is the question that mattered most and it is clean.

`execute_baseline_publish_plan` gates on

    if plan.provider_turns and not confirm_spend and not _confirm_spend_interactively(plan):

Three independent conditions, and every one fails closed:

- `confirm_spend` comes only from argparse `--confirm-spend`. There is no environment
  fallback, no config, no default true. Nothing else in the module reads it.
- `_confirm_spend_interactively` returns `False` immediately when `not sys.stdin.isatty()`,
  so CI, a pipe, a cron and a background process all refuse. When it is a tty it requires the
  literal word `publish`; any other input, including a bare Enter, refuses.
- Neither recipe passes `--confirm-spend`. `just baseline-publish <harness>` takes exactly one
  argument and forwards it through `{{quote(harness)}}`; `just baseline-publish-all` takes
  none. There is no `*args` passthrough on either, so the flag cannot be smuggled in from the
  recipe surface.

A plan with `provider_turns == 0` skips the gate, which is correct: with nothing to capture
the loop body never runs.

I could not construct any path, flag, environment variable or CI context that spends without
a deliberate human `publish` or an explicitly typed `--confirm-spend` on the module.

## Hunt B: can it spend more than it printed? No.

`provider_turns` is `3 if needs_capture else 0`, and `harvest_controlled_baseline` runs
exactly three probes (A1, B, A2). Actual spend is bounded by the printed figure, per cell and
in total:

- No retry anywhere. `execute_baseline_publish_plan` catches a failed capture, prints, sets
  `failed`, and moves to the next cell. A failed cell never re-attempts.
- No double capture. Inside `harvest_baseline` the `exclusive_file_lock` is taken and the
  evidence check is repeated before capture, so a cell captured concurrently by the automatic
  launch coordinator is found and skipped.
- A version change between planning and capture is caught rather than paid for.
  `expected_harness_version` makes `harvest_baseline` refuse with "installed version changed
  after publication planning" and return 2 **before** the capture, so an auto-update mid-run
  costs nothing.
- A cell that fails partway through A/B/A spends fewer than three turns, never more.

The consent the plan prints is honoured. The problem is not that it spends more than it says;
it is what the printed plan claims about the cells, which is M2.

## Hunt D: can it mint a release that claims more than it captured? No.

The strongest part of the change. `reference_minting.assemble_reference_material` refuses on
five independent grounds before anything is sealed:

- `_validate_target_coverage` requires the covered set to equal the release target catalog
  **exactly**, reporting both `missing` and `unexpected`. A partial cohort cannot mint.
- `_validate_cohort` requires one harness, provider, version, source identity and runtime
  template across the cohort, rejects any recorded effort other than `low`, and rejects a
  repeated launch model.
- `_canonical_model_for_projection` requires exactly one canonical target match.
- `_route_for_provider` requires exactly one certified route.
- `ReferenceMaterial.__post_init__` requires references and evidence to agree key for key on
  canonical model, effort, version and schema digest.

Proven live rather than read. I bound each of his three real bundles against its embedded
release entry:

    claude-2.1.211-r2: REFUSED -> launched model 'opus' and wire model 'anthropic/claude-opus-5' resolve to 0 canonical targets
    codex-0.144.4-r2:  REFUSED -> provider 'codex' resolves to 0 certified routes
    grok-1.0.4-r2:     REFUSED -> reference cohort does not cover the release target catalog; missing=[('grok.grok_com.account', 'grok-4.5')]

Three different refusals, all loud, none silent. The grok one is the coverage guard working
exactly as designed: I bound one of two cells and it refused. The other two are findings, M1
and m1 below.

`ReleaseRequestSchemaReference` also self validates its own digest, and
`BaselineBundleBinding` rejects absolute paths and `..` components, so a binding cannot point
outside the store.

## Hunt E: immutability and certification. Holds, and is tightened.

`validate_certification_for_release(record, sealed)` still runs at the end of `mint_outcome`.
`_require_certified_active_pointers` is untouched. Additions:

- `MintPlan` rejects a repeated baseline bundle binding.
- `mint_outcome` requires `bool(plan.baseline_bindings) == bool(reference_material.references)`
  and requires the two bundle id sets to match exactly, so assembled material cannot drift
  from the plan.
- A new guard rejects runtime evidence that does not observe `plan.baseline_version`.
- A new baseline version is only accepted when immutable baseline bindings accompany it.
- `CertificationRecordV1.schema_version` moves 1 to 2 carrying `reference_evidence`, and the
  three embedded records plus the manifest move to v2 with recomputed digests.

The "immutable mint bindings" claim is real. `request_schema.RequestSchemaNode` was also made
deeply immutable via `MappingProxyType` with an explicit `model_serializer`, which matters
because the schema is now digested inside a signed release; a mutable mapping there would let
a digest and its content diverge.

## Hunt F: local evidence never mutates the global tested catalog. Holds.

The verdict store writes only under `<channel home>/baselines/`. `decorate_target`'s new
fallback reads `release.references` and `release.targets`, both from the signed embedded
entry; the only local input is `observation.native_model_id`. Nothing local writes
`compatibility_releases_v1.json`.

## Hunt G: the recipes. Correct, with one rough edge.

Arguments are forwarded with `{{quote(harness)}}` at both levels, both recipes carry
`[no-exit-message]`, and the root delegates by `cd` into `api_dir`. Channel selection works:
`default_storage_root()` honours `TRANSPORT_MATTERS_CHANNEL`, which I confirmed resolves to
`~/.transport-matters-preview`, `~/.transport-matters` and `~/.transport-matters-dev` for
`preview`, `stable` and `dev`. The default is `preview`, which is the channel Canvas runs and
where his three cells live. That is the right default.

The rough edge is m1.

## Hunt H: scope. Everything is in slice.

| group | verdict |
| --- | --- |
| `baseline_publish`, `baseline_harvest`, `justfile`, `api/justfile` | the publication surface, in slice |
| `release_reference`, `reference_minting`, `certification_reference`, `certification_minting`, `certification.py`, the three certification records, `compatibility_releases_v1.json` | the release binding, in slice |
| `support_verdict`, `support_verdict_store`, `support_state`, `resolver`, `resolver_snapshots`, `resolver_targets`, `harness_launch_view` | the advisory verdict path, in slice |
| `shared/harness_inventory_vocabulary_v1.json`, `www/packages/core` types and tests, `harnessInventory.testSupport.ts` | the pinned cross language contract must move with the Python side, in slice |
| `request_schema.py` | deep immutability and an explicit serializer for a schema that now lives inside a signed digest, in slice and a genuine hardening |
| `launch_verification_paths.py` | extraction of the path helpers, needed once `resolver_snapshots` imports the verdict store, in slice |

Nothing here is outside the slice.

## Major

### M1. Codex references can never be assembled, so 15 codex turns are unmintable

`reference_minting._route_for_provider` selects the route by matching the captured cell's
provider against `route.provider_id`:

    route_ids = tuple(route.route_id for route in entry.routes if route.provider_id == provider)
    if len(route_ids) != 1:
        raise ValueError(f"provider {provider!r} resolves to {len(route_ids)} certified routes")

`BaselineCell.provider` is `descriptor.wire_provider`. Those are two different vocabularies and
they only coincide by accident:

| harness | `wire_provider` (cell) | route `provider_id` | match |
| --- | --- | --- | --- |
| claude | `anthropic` | `anthropic` | yes |
| grok | `grok` | `grok` | yes |
| **codex** | **`codex`** | **`openai`** | **no** |

Confirmed live: binding his real `gpt-5.6-sol` bundle refuses with "provider 'codex' resolves
to 0 certified routes". This is not a stale catalog and not fixable by minting a newer release:
the route's `provider_id` is the vendor and should stay `openai`, while the cell's provider is
the wire provider and should stay `codex`.

Consequence for the spend: the five codex cells cost 15 of the 48 turns, produce bundles and
projections, and then no codex reference cohort can ever be assembled from them. That is the
orchestrator's stated worst case, an unusable release, paid for in advance.

The test suite misses it because `harnesses/test_reference_minting.py` exercises only
claude cells (`opus`, `opus[1m]`) on the anthropic route, the one harness where the two
vocabularies happen to agree. Codex and grok never appear in it.

Fix: resolve the route from the harness rather than from the wire provider string, or map the
descriptor's wire provider to the route's provider id explicitly. Each release carries exactly
one route today, so `_route_for_provider` could take the entry's single route and validate the
harness instead. Add a codex case to `test_reference_minting.py` either way; that one fixture
would have caught this.

### M2. Resume re-captures cells he already owns, and prints them as `missing`

`_planned_baseline_exists` calls `read_latest_baseline_for_version`, which matches on

    and (effort is _ANY_EFFORT or bundle.cell.effort == effort)

The plan passes a concrete effort, and his stored bundles are artifact version 8, which
`read_baseline_bundle` normalizes to `effort=None`. `None == "low"` is false, so a cell he has
is judged missing.

The real plan on his machine:

    claude  opus         effort=low   v=2.1.241  needs_capture=True   turns=3
    codex   gpt-5.6-sol  effort=low   v=0.149.0  needs_capture=True   turns=3
    grok    grok-4.6     effort=None  v=1.0.5    needs_capture=False  turns=0

Only grok resumes, and only because its planned effort is `None`, which happens to equal the
legacy value. He pays 6 turns for evidence he already has.

There is a defensible argument for re-capturing: a legacy bundle cannot prove it was taken at
low, and `_validate_cohort` would then admit a cohort mixing a known-low capture with an
unknown-effort one. If that is the intent, it is a reasonable call.

What is not defensible is the plan output. It prints `status=missing` with no indication that
a bundle exists at an unknown effort. The printed plan is the operator's consent, and here it
tells him he has no opus baseline when he has one. Whichever way the owner decides, the plan
must distinguish "no evidence" from "evidence at an unknown effort" before he authorizes.

If the decision is to reuse, compare with `effort is None or bundle.cell.effort == effort`
for legacy artifacts, or plan with `_ANY_EFFORT` and record what was found.

## Minor

### m1. His captured claude cohort cannot mint against the current entry

Binding his real `opus` bundle refuses with "launched model 'opus' and wire model
'anthropic/claude-opus-5' resolve to 0 canonical targets".

This is a catalog vintage problem rather than a code defect. The embedded entry is
`claude-2.1.211-r2` whose targets are `claude-opus-4-8`, `claude-fable-5`, `claude-sonnet-5`
and `claude-haiku-4-5`, while the installed 2.1.241 puts `claude-opus-5` on the wire.
`_canonical_model_for_projection` correctly refuses to guess. Haiku has the same shape:
the wire says `claude-haiku-4-5-20251001`, the catalog says `claude-haiku-4-5`.

The operational consequence is a sequencing requirement nobody has stated: the 48 turns
produce projections and mint bindings, but minting also needs a release entry whose targets
match the observed wire models for the installed version. He should know that before he spends,
because the capture is only half the path to a release.

### m2. A set but empty `TRANSPORT_MATTERS_CHANNEL` gives a raw traceback

`api/justfile` uses `env_var_or_default("TRANSPORT_MATTERS_CHANNEL", "preview")`, which returns
the empty string when the variable is exported but empty, and the recipe then passes it
through. `default_storage_root()` raises `ValueError: invalid channel id ''`, and because it is
evaluated in the argparse `default=` expression in `baseline_publish.main` it lands outside the
`try` in `publish_baselines`. The operator gets a traceback instead of a message.

Fail closed, so no spend, but hunt G asks whether it fails comprehensibly and here it does not.
Resolve the storage root inside the guarded path, or treat an empty value as unset in the
recipe.

### m3. After the first mint, aliases inherit a canonical target's tier

`resolver_targets.decorate_target` gains a fallback: when an observation has no direct target
edge, it looks for a single reference binding that launch model to a canonical id and adopts
that canonical target's edge, including `support_tier` and `lifecycle`.

Inert today, since all three embedded releases ship `"references": []`, and I confirmed that.
It activates on the first minted reference release, and then every alias bound by a reference
inherits its canonical target's tier. If a release ever marks a target `tested`, all ten claude
aliases pointing at it become `_default_eligible` simultaneously, and `_select_edge` returns
`target_ambiguous` when more than one is eligible.

Everything today is `observed_unverified` so nothing changes yet, and the palette path resolves
an explicit configured model rather than the default branch. Worth knowing before the first
mint rather than discovering it from a `target_ambiguous` on a launch.

## What would make it safe to run

1. Fix M1. Without it, a third of the spend produces evidence no mint can consume.
2. Decide M2 and make the plan say which it chose. Either is acceptable; silently printing
   `missing` for a cell that exists is not.
3. Optionally state m1's sequencing in the recipe output or the docs, so he knows the capture
   is not the last step before a release.

None of these touch the spend gate, the turn accounting, or the mint's refusal to over-claim,
which are the three things that would have made this genuinely dangerous. Those are right.

---

# Delta re-review cff0d6a6

`git diff fc69ed08 cff0d6a6`, one commit "fix(harnesses): correct reference publication
economics", 9 files, 352 insertions.

**0 major, 1 minor. MERGE. Safe for the owner to run.**

**Position on the explicit non-low recapture rule: it is not justified on schema grounds, it
is incoherent with its own legacy fallback, and it should go once the claude effort probe
lands. Keeping it today costs nothing and is a defensible hedge.**

Tree pristine at `cff0d6a6`. Read only, no provider turns, no launch. Full suite
`4187 passed in 48.99s`.

## 1. Major 1 is fixed, and the test matrix is real

`_route_for_provider` is gone. `_route_for_harness` now validates the descriptor's wire
provider against the captured cell's provider and then takes the entry's single certified
route, so the vendor-versus-wire-provider vocabulary collision cannot recur.

Confirmed live by re-running the exact binding that failed before, against his real bundles
and the embedded entries:

| harness | before | after |
| --- | --- | --- |
| codex | `provider 'codex' resolves to 0 certified routes` | `reference cohort does not cover the release target catalog; missing=[gpt-5-codex, gpt-5.4-mini]` |
| claude | `'opus' and 'anthropic/claude-opus-5' resolve to 0 canonical targets` | unchanged |
| grok | `does not cover the release target catalog; missing=[grok-4.5]` | unchanged |

Codex's refusal moved from a structural impossibility to the ordinary coverage guard doing
its job on a one-cell binding, which means the route resolved and
`_canonical_model_for_projection` matched `gpt-5.6-sol`. Claude and grok are unchanged and
still refuse for their own correct reasons, so nothing regressed.

**The test matrix is genuinely three harnesses.**
`test_assembly_resolves_the_certified_route_for_every_harness` is parametrized over claude
(`anthropic`/`anthropic`), **codex (`codex`/`openai`)** and grok (`grok`/`grok`), asserting
both the resolved `route_id` and the canonical model. The codex row is exactly the pair that
made the original defect invisible. This is a matrix, not one addition.

## 2. Major 2 is fixed live, and the plan now tells the truth

All three of his cells resume. The real printed plan on his store:

    claude  opus         status=current  recorded_effort=unrecorded  provider_turns=0
    codex   gpt-5.6-sol  status=current  recorded_effort=unrecorded  provider_turns=0
    grok    grok-4.6     status=current  recorded_effort=none        provider_turns=0

`read_reusable_baseline_for_version` prefers an exact effort match and falls back to
unrecorded-effort evidence only for a planned low cell. The new `recorded_effort` column is
the part that fixes my actual complaint: the plan previously said `missing` for a cell that
existed, and now distinguishes `absent`, `unrecorded` and `none` explicitly.

`publish_planned_baselines` was moved to the same reader, so a resumed legacy cell is also
found at publish time and emits its binding instead of reporting "planned baseline missing
after capture". Plan and publish now agree, which they did not before.

### Judging the rule

The straight answer the orchestrator asked for.

**The legacy half is clearly right.** Unrecorded effort satisfying a low cell is correct
because effort is content and keys nothing, which I proved for codex and grok and hold at high
confidence for claude.

**The explicit non-low half is not justified on schema grounds.** A bundle captured at high
produces a byte-identical `RequestSchema` to one captured at low. Re-capturing it spends three
turns to re-derive something already proven equal.

**It is also incoherent with the fallback beside it.** The rule accepts a legacy bundle of
*unknown* effort and rejects one of *known* high effort. His opus bundle is almost certainly a
high-effort capture, since `~/.claude/settings.json` sets `effortLevel: high`; it is admitted
only because nothing recorded that. The rule rewards ignorance and punishes recorded
knowledge, on an axis where the recorded value provably does not matter.

**Where it does earn its keep** is as a hedge on the one thing still open. If the claude probe
came back the other way and effort turned out to be structural for claude, a cohort mixing low
and high references would be an unreproducible blessing. Low-only guarantees that anyone can
reproduce the reference by capturing at low. `reference_minting._validate_cohort` already
demands low-or-none, so the planner and the cohort validator are at least consistent with each
other: resuming a high bundle would produce a cohort refused at mint time, after the operator
believed he was finished. Given that, the current rule is the safe pairing.

**The cost is real but deferred, and it interacts with what just shipped.** It bites nothing
today, since all three of his bundles are legacy. It bites after the next harness upgrade:
#443's automatic palette verification captures at the *configured* effort, which is `high` for
claude, so the first launch after a version bump writes explicit high evidence for that cell,
and the next publish run refuses to reuse it and pays three turns. One cell per model he
happens to launch before publishing.

**Recommendation:** settle the two-turn claude probe, then drop the non-low restriction in
both places, accept any recorded effort for a low cell, and record the actual effort on the
reference. Until the probe lands, keep it, and describe the legacy fallback honestly as the
same hedge failing open rather than as a separate rule.

Not a blocker either way. It costs zero turns on this run.

## 3. The printed plan is true

Bound against his real store and printed exactly what he will see:

    publish plan: harnesses=claude,codex,grok planned_cells=17 missing_cells=14 provider_turns=42

**17 cells, 14 missing, 42 provider turns**, matching the builder's report to the cell. Three
cells resume, fourteen at three turns each is 42. The arithmetic and the store agree.

I ran it with a `capture` and a `publish` that raise on call. Neither fired, and the run
returned 2.

## 4. Minors: two fixed, one untouched

**m1, the catalog mismatch, is fixed harder than I asked.** I asked for the sequencing to be
stated; it is now a hard preflight that refuses before authorization:

    publication preflight refused: claude 2.1.241 has no embedded compatibility release at the
    installed version; add its release entry and target catalog before authorizing provider spend

`_reference_release_preflight_refusals` requires an embedded release whose `baseline_version`
equals the installed version, per harness. All three refuse today, which is correct: the
embedded releases are 2.1.211, 0.144.4 and 1.0.4 against installed 2.1.241, 0.149.0 and 1.0.5.

**This is the operationally important fact of this review: the tool is safe and currently
inert.** He cannot spend anything until release entries exist for the installed versions. That
is the right order, and it is now enforced rather than documented.

One property worth naming: with `--all`, any single harness missing its release refuses the
whole run rather than proceeding with the others. All-or-nothing suits a fleet publish, and it
fails closed, so I am not raising it.

**m2, the empty channel traceback, is fixed.** `--output`'s default no longer evaluates
`default_storage_root()` at parser construction, and the resolution moved inside the guarded
block. `TRANSPORT_MATTERS_CHANNEL="" python -m transport_matters.baseline_publish --harness
claude` now prints `could not plan baseline publication: invalid channel id ''; expected
^[a-z][a-z0-9_]*$` with no traceback.

### The one minor: m3 was not addressed

`harnesses/resolver_targets.py` is untouched by this delta and no comment or document mentions
the behaviour. The builder's report that all three minors are fixed is wrong on this one.

`decorate_target` still adopts a canonical target's edge, including `support_tier` and
`lifecycle`, for any observation a single reference binds. It stays inert while every embedded
release ships `references: []`, and it was informational rather than a defect, so it is not a
merge blocker. It should be recorded somewhere before the first minted reference release,
because that is when every alias bound by a reference starts inheriting its canonical target's
tier, and `_select_edge` returns `target_ambiguous` when more than one becomes default
eligible.

## 5. No regression in the cleared safety properties

Re-checked, since the delta landed in exactly the files that carry them.

- **Spend without confirmation.** The gate is byte-identical, and the new preflight sits
  *before* it and returns 2, so it cannot prompt and then refuse, nor confirm and then refuse.
  Neither recipe passes `--confirm-spend`, and `_confirm_spend_interactively` still refuses on
  a non-tty. My live run with raising stubs proved capture was never reached.
- **Spend more than printed.** `provider_turns` is still `3 if needs_capture else 0`, with no
  retry and no second capture path. `harvest_baseline`'s in-lock recheck moved to the same
  reusable reader as the planner, so the two now agree on what counts as existing evidence,
  which removes a way the plan and the capture could have disagreed.
- **Mint claiming more than captured.** `_validate_cohort`, `_validate_target_coverage`,
  `_canonical_model_for_projection` and `ReferenceMaterial.__post_init__` are unchanged except
  for the route fix, and I re-exercised all three harnesses live: three refusals, none silent.

## 6. The document is accurate

`docs/HARNESS-COMPATIBILITY.md` now states the sequencing before the publisher flow and
updates the diagram to `prepare installed-version release catalog -> capture reference cohort
-> detect -> ...`. It describes the preflight behaviour exactly as I observed it, including
that the refusal comes before authorization. It contradicts nothing in the blessing and range
contract; it is additive publisher-side sequencing.

## Verdict

**MERGE, and yes, it is safe for the owner to run.**

Both majors are fixed and I verified each against his real store rather than against a
fixture. The plan he will see is true to the cell. The spend gate, the turn accounting and the
mint's refusal to over-claim are all intact.

He should know two things before he starts. It will refuse all three harnesses today until
release entries exist for the installed versions, which is the tool protecting him rather than
failing. And when it does run, 42 turns is the whole authorization; there is no path by which
it becomes more.

---

# Final check bf23c5b4

`git diff cff0d6a6 bf23c5b4`, one commit "fix(harnesses): reuse baselines across efforts",
7 files, 31 insertions, 43 deletions.

**0 major, 0 minor. MERGE. Safe for the owner to run.**
**The plan number is unchanged: 17 cells, 14 missing, 42 provider turns.**

Tree pristine at `bf23c5b4`. Read only, no provider turns, no launch. `4187 passed in 48.39s`.

The probe settled the one thing my effort-axis report left open, and it landed where the
evidence pointed: `/output_config/effort` carries `high` against `low` as a **value at a path
present in both runs**, with 430 path-and-type pairs identical and none exclusive to either.
Claude joins codex and grok. Removing the rule on the strength of that is right, and it
removes the hedge rather than the reasoning behind it.

## 1. The rule is gone from both places, and the actual effort is what gets recorded

**Publication resume.** `baseline_store.read_reusable_baseline_for_version` collapses to one
lookup:

    effort=_ANY_EFFORT if planned_effort == "low" else planned_effort

A planned low cell now reuses evidence at any recorded effort, unrecorded included. The
preference ordering, the legacy special case and the non-low rejection are all deleted, and the
docstring now states the reason rather than the rule: "Effort changes request content without
changing request structure."

A planned `None` cell still requires evidence recorded without effort. That is correct rather
than a leftover: haiku and grok have no effort axis at all, so a bundle carrying one would be a
different actuation, not the same cell at another setting. It cannot arise today either, since
`claude_launch_effort_options` returns `()` for haiku and grok enumerates no efforts.

**Cohort validation.** The `nonbaseline_efforts` block is gone from
`reference_minting._validate_cohort`. What remains is the set that actually protects the
release: one harness, provider, version, source identity and runtime template; no repeated
launch model; exact target coverage; single canonical resolution; digest agreement between
reference and evidence.

**Actual effort, not an asserted one.** `assemble_reference_material` builds both the reference
and its evidence with `effort=projection.cell.effort`, read from the bundle. That was always
the source, but until this commit the cohort validator constrained what could reach it. Now the
recorded value is genuinely whatever the capture did, and a cohort may legitimately be
heterogeneous in effort. Since effort is proven content on all three harnesses, the structural
claim the release blesses is identical either way, so the heterogeneity costs the blessing
nothing.

## 2. The plan number: unchanged at 17 / 14 / 42

Re-bound against his live preview store:

    publish plan: harnesses=claude,codex,grok planned_cells=17 missing_cells=14 provider_turns=42

Same three cells resume, with the same `recorded_effort` values:

    claude  opus         status=current  recorded_effort=unrecorded
    codex   gpt-5.6-sol  status=current  recorded_effort=unrecorded
    grok    grok-4.6     status=current  recorded_effort=none

Removing the rule made resume strictly more permissive, and nothing moved, for a good reason:
all three of his bundles are legacy with unrecorded effort, which the previous rule already
admitted for a low cell. The relaxation matters for evidence that does not exist yet, which is
exactly the future case I flagged. **42 remains the number he authorizes.**

## 3. No regression in the safety properties

- **Spend without confirmation.** `execute_baseline_publish_plan` is untouched. The preflight
  still precedes the spend gate and returns 2, neither recipe passes `--confirm-spend`, and
  `_confirm_spend_interactively` still refuses on a non-tty. I re-ran the real plan with
  `capture` and `publish` stubs that raise on call; neither fired, and the run returned 2.
- **Spend more than printed.** `provider_turns` is still `3 if needs_capture else 0` with no
  retry. The planner and `harvest_baseline`'s in-lock recheck call the same
  `read_reusable_baseline_for_version`, so relaxing it moved both together and they cannot
  disagree about what counts as existing evidence.
- **Mint claiming more than captured.** `_validate_target_coverage` is untouched, and it is the
  guard that carries this property. What was removed constrained the *effort* of a covered
  cell, never *which* cells were covered. Re-exercised live against all three harnesses: three
  refusals, none silent.

## 4. m3 is addressed, documented and covered

Three ways, which is more than I asked for.

`resolver_targets.decorate_target` carries a comment stating the intent: a signed reference
declares the alias to be another surface for the canonical target, so it inherits that target's
full support policy rather than fabricating a second policy edge.

`docs/HARNESS-COMPATIBILITY.md` states the consequence including the part I flagged: the alias
inherits tier, lifecycle and launch adapter revision, and "multiple tested aliases remain
distinct native choices, so default resolution refuses `target_ambiguous` until the caller
selects one identity explicitly". That is precisely the behaviour I warned would surprise
someone after the first mint, written down before it can.

`test_release_reference.test_reference_alias_intentionally_inherits_the_canonical_target_policy`
covers it, asserting the inherited `canonical_model_id`, `support_tier="tested"` and
`lifecycle="deprecated"` together. The name states the intent, so a future reader cannot mistake
it for an accident.

## 5. The preflight fact, confirmed precisely, with two additions

The orchestrator's statement is **exactly right on every clause**:

- **Refuses until entries exist at the installed versions.**
  `_reference_release_preflight_refusals` requires an embedded release whose
  `release.baseline_version` equals the freshly probed installed version, per harness. All three
  refuse today: embedded 2.1.211, 0.144.4 and 1.0.4 against installed 2.1.241, 0.149.0 and
  1.0.5. Verified live.
- **Digest valid.** `compatibility_store._require_digest_integrity` recomputes every entry's
  digest at manifest load and raises on mismatch, so a hand authored entry with a stale
  `release_digest` fails loudly at first read rather than at spend time.
- **Inactive.** `_require_certified_active_pointers` iterates `channel_states` and skips
  anything whose status is not `active`. A release entry that no active pointer names needs no
  certification record. So the new entries must be authored inactive, leaving the channel
  pointer on the current release; making one active before minting would fail the manifest load
  outright.
- **Correct routes.** `_route_for_harness` requires exactly one route on the entry and requires
  its harness descriptor's wire provider to match the captured cell's provider.
- **Zero provider turns.** Authoring a release entry touches only
  `compatibility_releases_v1.json`. Nothing in the preflight, the manifest load or the digest
  recomputation contacts a provider.

**Two requirements the builder did not name**, both of which will stop him after he has paid if
he gets them wrong:

**a. The target catalog must name the canonical models by their observed wire identity, not by
the previous release's names.** `_canonical_model_for_projection` matches a capture against
`entry.targets` on `{wire_model, unqualified wire model, launch_model}`. The current claude
catalog says `claude-opus-4-8` and `claude-haiku-4-5`, while the wire says `claude-opus-5` and
`claude-haiku-4-5-20251001`. That mismatch is exactly why binding his real `opus` bundle still
refuses with "resolve to 0 canonical targets". The new entry's targets must carry the wire
names.

**b. The target catalog must be exactly the set of canonical models the cohort will produce,
with no extras.** `_validate_target_coverage` demands set equality, so any target he lists that
no captured cell resolves to makes the cohort permanently unmintable. This is not hypothetical:
the current codex catalog lists `gpt-5-codex` and `gpt-5.4-mini`, neither of which the codex
launch view offers today, and that is precisely the `missing=[gpt-5-codex, gpt-5.4-mini]`
refusal I reproduced.

Concretely, the ten claude aliases collapse onto four distinct canonical models, so his claude
target catalog should be those four rather than ten. From the captured wire models: `best`,
`opus` and `opus[1m]` resolve to `claude-opus-5`; `default`, `opusplan`, `sonnet` and
`sonnet[1m]` to `claude-sonnet-5`; `fable` and `fable[1m]` to `claude-fable-5`; `haiku` to
`claude-haiku-4-5-20251001`. Those mappings come from his stored bundles, one at 2.1.241 and
the rest at 2.1.238, so he should confirm the 2.1.241 wire identity for the aliases he has not
recaptured before sealing the catalog.

## Verdict

**MERGE, and yes, safe to run.** Nothing in this delta touches the spend gate, the turn
accounting or the coverage guard. The rule I objected to is gone from both places on the
strength of a probe that proved the objection, the recorded effort is now the captured one, and
the number he consents to is still 42.
