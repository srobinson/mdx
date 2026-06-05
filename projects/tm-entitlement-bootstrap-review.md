# TM PR #449 review: recover baseline publication from stale evidence

Target: `fix/baseline-entitlement-reference` at `630c4cb6`, against main `0acb2418`.
Merge base is exactly `0acb2418`, one commit ahead, 11 files, 403/191.
Tree confirmed pristine (`git status --porcelain` empty) before and after review. Read only.
No provider turns spent.

Verdict: **0 major, 3 minor. Merge.**
An unrecognised refusal **cannot** permanently exclude a model.

Gates run independently: `cd api && just check` clean (ruff, mypy 841 files),
`just test` 4198 passed in 44.15s.

---

## 1. Fail toward transient (the property that matters most)

**Holds.** `baseline_attempts.classify_provider_refusal` replaced two loose
`re.search` patterns with a table of `(provider, status, pattern, reason)` tuples
matched by `pattern.fullmatch` against the whitespace-normalized message. Three
independent conditions must all hold: exact provider string, exact status, and the
whole message equal to the known sentence. The old `_TRANSIENT_REFUSAL_MARKERS`
denylist is gone, which is the right direction: a denylist of transient words has to
anticipate every transient phrasing, while a fullmatch allowlist has to anticipate
only the permanent ones and defaults everything else to transient.

Characterized empirically against the live matcher:

| message | classification |
| --- | --- |
| exact live message (`The 'gpt-5.2' model is not supported when using Codex with a ChatGPT account.`) | EXCLUDE |
| double quotes / no quotes / curly quotes around the model | EXCLUDE |
| no trailing period | transient |
| `Error: ` prefixed | transient |
| suffixed with `Pick another.` | transient |
| reworded (`ChatGPT Plus account`) | transient |
| same sentence at HTTP 403 | transient |
| same sentence, provider `openai` | transient |
| unrelated 400 (`Rate limit exceeded`) | transient |
| old broad phrasing (`The model is not available for this account.`) | transient |

The only over-match found is a contrived doubled sentence, which is semantically the
same refusal. The pattern is brittle, and brittle in the safe direction: every
rewording costs one redundant turn per publish run and never hides a launchable
model. The inline comment at `_PROVIDER_REFUSAL_PATTERNS` states that tradeoff
explicitly, and it is the right one.

Two further defences worth recording:

- `account_entitlement_excluded_models` no longer trusts stored evidence. It
  re-runs `classify_provider_refusal` over each attempt's recorded
  `provider_status` / `provider_message`, so the pattern table is authoritative at
  read time, not write time. Deleting a pattern later retroactively un-excludes
  every target it wrongly excluded, with no state edit. Covered by
  `test_baseline_attempts.test_a_structured_exclusion_is_revalidated_against_current_provider_policy`.
- Because `fullmatch` only ever accepts a ~90 character sentence, the
  `provider_message[:2048]` truncation can never break that re-classification
  round trip.

Provider vocabulary verified against the live store rather than assumed:
`storage.base.transport_refusal` keys codex refusals on `transport.provider == "codex"`,
and `harnesses.resolver_snapshots` derives the same string from
`get_harness_descriptor(harness_id).wire_provider`. Live: claude→`anthropic`,
codex→`codex`, grok→`grok`. The table's `"codex"` key is correct.

## 2. The bootstrap is exactly once

**Holds, proven live and by test.** Three links:

1. `baseline_capture._comparison_reference` returns `None` only when
   `reference.cell.runtime_template != template_identity`, printing the superseded
   and current identities to stderr.
2. `harvest_controlled_baseline` writes the new bundle with
   `cell.runtime_template = template_identity` (the *current* template) and, with no
   reference, leaves `reference_bundle_id`, `reference_outcome`,
   `reference_content_report` null. It does not fabricate `EXACT`.
3. `baseline_store.promotes_baseline` returns `True` when `reference_outcome is None`,
   so `write_baseline_bundle` advances the current pointer to the bootstrap bundle.

The next capture therefore reads a reference whose template matches and compares
normally. `test_baseline_capture.test_harvest_bootstraps_once_when_the_capture_template_changes`
asserts exactly this: first call bootstraps (3 probes, null reference, stderr
message), second call yields `reference_bundle_id == first.bundle_id`,
`reference_outcome == "exact"`, 6 probes total, and no bootstrap message.

Live state confirms the brief's premise. Of 16 current cells, exactly three carry
the superseded template `269afd` and are correctly `reusable=NO`:

    claude/opus        v2.1.241  tpl=269afd  reusable=NO
    codex /gpt-5.6-sol v0.149.0  tpl=269afd  reusable=NO
    grok  /grok-4.6    v1.0.5    tpl=269afd  reusable=NO

The other 13 carry the current `6db698` and are reusable, so they cost nothing.
All three harnesses resolve to the same current template
(`generated_from 5982f4…`, `content_digest 6db698…`).

## 3. The guard still guards

**Holds, and the relaxation is narrow.** `_comparison_reference` still raises
`ValueError("baseline cell coordinates or capture plan do not match the reference")`
for any mismatch in harness, provider, launch_model, effort, `no_system_prompt`,
`bypass_permissions` or `isolated_home`. Only `runtime_template` was lifted out of
the compared dict into its own branch. `test_baseline_capture.test_harvest_refuses_a_same_template_coordinate_mismatch_before_launch`
pins this: same template, `no_system_prompt=False`, raises, and `prepared == []`,
so it still refuses **before** spending a turn.

## 4. Un-exclude works without editing state

**Holds.** `read_baseline_attempts` collapses to the latest attempt per
`(harness, provider, launch_model)` ordered by `(started_at, harness_version)`, so a
newer attempt supersedes an older excluded one regardless of version. Nothing in
`baseline_harvest.harvest_baseline` consults the exclusion set, so a direct harvest
of an excluded model always re-attempts.

Operator procedure, exactly: run `baseline_harvest` for that harness and model
(`--force` only needed if a bundle already exists for the installed version). A
success writes a `SUCCEEDED` attempt that becomes the latest, and the model drops
out of `account_entitlement_excluded_models` on the next read, for both the launch
view and publication planning. A continued refusal simply re-records the exclusion.
Covered by `test_baseline_harvest.test_manual_harvest_can_retry_and_clear_an_account_exclusion`
and `test_baseline_attempts.test_exclusion_survives_a_version_bump_until_a_new_attempt_clears_it`.

Second, independent lever: because exclusions are re-derived from the pattern table
at read time (section 1), removing a pattern un-excludes retroactively.

Note: an interrupted forced harvest leaves `IN_PROGRESS` as the latest attempt,
which is not `FAILED` and so un-excludes the model until the next run re-records it.
Self correcting, costs at most one turn.

## 5. Exclusion does not block publication; an empty harness still refuses

**Holds, in both directions.**

- Plan time: `build_baseline_publish_plan` raises
  `ValueError(f"{descriptor.id}: launch view has no publishable models")` when every
  model of a harness is excluded. This fires before any spend.
- Run time: `publish_baselines.publish` diffs `planned.harnesses` against
  `_without_account_exclusions(planned).harnesses` and raises
  `"publication has no account reachable baseline cells for …"` for any harness that
  lost all of its cells to an exclusion discovered during the run.

A harness that keeps reachable targets publishes normally with the excluded cell
dropped. `BaselinePublishPlan` carries only `cells`; `harnesses`, `missing_cells`
and `provider_turns` are derived properties, so rebuilding the plan from filtered
cells is lossless.

## 6. Spend safety

**Unchanged and intact.**

- Cannot spend without confirmation: the plan is built and printed before
  `execute_baseline_publish_plan(confirm_spend=…)`, and `prepare_publication`
  (`require_clean_worktree`) runs before the prompt.
- Cannot spend more than printed: `_without_account_exclusions` runs inside the
  `publish` callback, after all captures. It only ever removes cells.
- Cannot mint claiming more than captured: `publish_planned_baselines` returns 2 and
  prints `planned baseline missing after capture: …` for any planned cell with no
  stored bundle, before `publish_release_catalog` runs.

This last one also contains the only coupling hazard I found.
`baseline_harvest._capture_selected_baseline` returns **0** for an excluded cell that
produced no evidence, and correctness then depends on `_without_account_exclusions`
independently re-deriving the same exclusion so the cell is dropped from the plan.
The two paths agree because both call `classify_provider_refusal`, and if they ever
diverged `publish_planned_baselines` refuses rather than minting a false reference.
Fails safe, so I am not raising it as a defect.

## 7. Everything else in the delta

`resolver_snapshots.resolver_snapshots_for_harness` dropped the
`observation is None or observation.normalized_version is None` guard, so exclusions
now apply whenever a provider is known. That is required for Defect A: the exclusion
must outlive the version it was observed at. Verified live by reproducing the exact
call site expression against `~/.transport-matters-preview/baselines`:

    claude: wire_provider='anthropic'  account_excluded_models=[]
    codex : wire_provider='codex'      account_excluded_models=['gpt-5.2']
    grok  : wire_provider='grok'       account_excluded_models=[]

The launch surface therefore suppresses exactly `gpt-5.2` and nothing else. The
vocabularies line up: `BaselineAttemptRecorder` records `launch_model` from
`EnumeratedModel.model_id`, and `harnesses.state_refresh` / `reference_minting` set
`native_model_id` from the same `model_id`, which is what
`harnesses.resolver` compares against `snapshots.account_excluded_models`. Aliases
are distinct keys (`opus` and `opus[1m]` are separate), so an exclusion cannot spill
onto a sibling alias.

No www or contract files are touched by this PR. The
`account_entitlement_unavailable` union member and `exclusion_reasons` field shipped
in #447 and are already on main, so old-frontend-against-new-backend is not a
question this delta reopens.

`baseline_publish.build_baseline_publish_plan` calls `resolve_capture_baseline_template`
unguarded, but `publish_baselines` wraps plan construction in `try/except Exception`
and prints `could not plan baseline publication: …` with exit 2, so a missing
template still fails cleanly without a traceback.

---

## Minors

**m1. The resolver-snapshot test now stubs the function whose call site changed.**
`harnesses/test_resolver_snapshots.py::test_resolver_snapshots_pin_provider_access_and_account_exclusions`
replaced real attempt evidence with
`monkeypatch.setattr(resolver_snapshots, "account_entitlement_excluded_models", …)`.
The delta's only change in `resolver_snapshots.py` is inside that expression, so the
one test named for it no longer exercises
`read_baseline_attempts(output=baseline_output, harness=harness_id)`. A wrong store
path or harness key would return an empty frozenset, silently re-offer an excluded
model in the launch view and palette, and no test would fail. The test already
monkeypatches `default_storage_root` to `tmp_path`, so restoring real evidence is
cheap: write one failed attempt under `tmp_path/baselines` carrying the codex
sentence and assert it surfaces in `account_excluded_models`. I verified the wiring
is correct live (section 7), so this is a coverage gap rather than a defect, but it
is the gap over the exact line that changed.

**m2. The deleted test took the rationale for `content_digest` with it.**
`test_harvest_refuses_a_reference_taken_from_an_edited_template` carried the only
prose explaining why the content digest belongs in the template identity: a hand
edited control home is a new cell, not harness drift, and without the digest the
edit's effect on the wire would be compared against the old reference and
misattributed to the harness. The replacement docstring on
`baseline_capture.capture_template_identity` now says only what happens ("Any
identity change forces one comparison free bootstrap"). The bootstrap still rules
out that misattribution, by skipping the comparison instead of refusing it, which is
precisely why the relaxation is safe. That reasoning is worth keeping. Fold the
deleted paragraph into `capture_template_identity`'s docstring.

**m3. Manual harvest and publication disagree about what "current" means.**
`baseline_store.read_reusable_baseline_for_version` now takes
`planned_template_identity` and rejects a stale-template bundle, but the
manual path in `baseline_harvest.harvest_baseline` still uses
`has_baseline_bundle_for_version`, which is template blind. Concretely, today:
`baseline-publish-all` plans a capture for `claude/opus` because its bundle carries
the superseded template, while a manual harvest of the same cell without `--force`
prints `current: claude/opus harness_version=2.1.241` and does nothing. Before this
PR both paths agreed, because neither knew about templates. Nothing is incorrect,
publication drives the real flow and `--force` overrides, but an operator checking a
cell by hand is told the opposite of what the publisher believes. Give
`has_baseline_bundle_for_version` the same template awareness, or route the manual
currency check through `read_reusable_baseline_for_version`.

## Observation, owner's call

A bootstrap bundle is indistinguishable from a first ever capture in the durable
evidence: both carry `reference_bundle_id = None` and `reference_outcome = None`.
The only record that a drift chain was deliberately reset is a stderr line during
the run. It is reconstructible, since the superseded bundle is still on disk with
the old template, but it is not stated. Recording the superseded template identity
on the bundle would close it, at the cost of a
`BASELINE_ARTIFACT_SCHEMA_VERSION` bump, which is a bigger change than the gap
warrants unless drift provenance is going to be audited later. Flagging, not
prescribing.
