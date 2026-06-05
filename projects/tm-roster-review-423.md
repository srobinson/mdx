# Review: PR #423 — separate requested and observed roster models

Reviewer: transport-matters:general:1:3.3 (independent; no hand in this design)
Branch `fix/roster-model-authority` head `638470c5` against `main` `6a89ac85`.
Tree pristine at review time (`git status --porcelain` empty).
Scope reviewed: the 2-commit diff only, 6 files, +25/-16.

## Verdict

The central fix is correct: `model` is genuinely inert and the regression genuinely pins it.
Four findings, no Blocker: 2 Major, 2 Minor. Both Majors are contract-statement defects
rather than logic defects — the code stopped lying, and the documentation has not caught up.

## What I verified

**`model` is now inert (brief check 2). Confirmed.** `roster_projection.py:40` assigns
`model=item.model` with no conditional. `item` is `GatewayActivityRun`, whose `model` is set
at `packages/activity/src/server/activityRouter.ts:417` (`effectiveProjection`:
`model: launch?.model ?? null`) and serialised by `runToWire` at `:450`. Transcript evidence
reaches the projection only through `last_turns`, and after this PR the only consumer of that
mapping's `model` is `_observed_model`. The old three-argument `_accepted_model` is deleted,
not bypassed: its `launched_model` parameter is gone from the signature at
`roster_projection.py:59-62`. Branches checked: no turn (`last_turn is None` →
`observed_model=None`, `model` unchanged); sticky rejection (`roster_projection.py:63`,
suppressed to `None`, `model` unchanged); a transcript model the launch never requested
(`test_service.py:214-218`, launch `requested-fable` against turn `claude-fable-5`, reported
in separate fields).

**Consumer completeness (brief check 3). Clean on the Python side.** The only readers of
`project_roster` output are `controlplane/service.py:617` (`_roster_snapshot`),
`service.py:168-195` (`roster` — filters on `state`/`tier`, sorts on `last_turn_at`, never
touches `model`) and `service.py:619` (`_summary_text`, counts `state` only).
`api/v1/controlplane_routes.py:121` and `api/v1/controlplane_mcp.py:416` serialise
`RosterResult` unaltered. The only `RosterItem` construction sites are
`roster_projection.py:34` and the skins-test fake, so the new no-default field cannot be
silently omitted anywhere. `SelfIdentityResult` carries no model; `controlplane/models.py`
grant vocabulary carries no model. No reader treats `model` as observed evidence.

**Regression asserts the observable end state (brief check 4). Confirmed, and it is the
with-turn case.** `test_service.py:178-215` already carried launch model `requested-fable`
against turn model `claude-fable-5` on `main`, where the assertion read
`"model": "claude-fable-5"`. The PR flips it to `"model": "requested-fable"` plus
`"observed_model": "claude-fable-5"`, so it fails against `6a89ac85` on the `model` key
alone — and therefore also fails a hybrid that added the new field while leaving
`_accepted_model` in place. `test_service.py:288-324` additionally pins the rejection
suppression with a real last turn present (`model="<synthetic>"`), which a no-turn fixture
could not have proved.

**Scope (brief check 6). Clean.** No effort change, no `HarnessModelCompatibility.model_id`,
no `classify_aba`, no source, confidence, probe scope, or per-turn resolution state.

**Gates.** `ruff check` and `mypy` clean on the changed modules;
`pytest src/transport_matters/controlplane/test_service.py
src/transport_matters/api/v1/test_controlplane_skins.py` → 40 passed.

## Findings

### 1. Major — `model` does not "always" carry the requested launch selector

`docs/CONTROLPLANE.md:64`, `docs/LAUNCH-CONTRACT.md:159`, behaviour at
`api/src/transport_matters/controlplane/roster_projection.py:40`

The new doc sentence is "`model` always carries the requested launch selector." Traced to its
source, that is not what the code delivers:

- `packages/activity/src/projections/workspaceActivity.ts:30-50` — `RunActivityProjection`
  has **no `model` field**. The durable Activity projection never carries a model, so
  `effectiveProjection` (`activityRouter.ts:413-418`) has exactly one source for it.
- `packages/gateway/src/main.ts:158` wires that source to `RunManager`.
- `packages/runtime/src/service/RunManager.ts:131` — `private readonly runs = new Map<...>()`.
  Process-lifetime memory. `launchFacts` is written once at spawn (`:482`,
  `model: input.model ?? null`) and read at `:293`. There is no `rehydrate`, `restore`,
  `adopt`, or `reattach` symbol in that file; `lookup` returning null yields
  `launchFacts → null`, hence `model → null`.

So `RosterItem.model` is null in three ordinary situations: a launch that pinned no model
(`LaunchRequest.model` is optional and defaulting is the common case), any run whose
`RunManager` entry is gone after a backend restart, and any run not created by this
`RunManager`. In all three, `main` filled the field from the observed turn via
`_accepted_model`; this PR correctly stops doing that, and the truth survives in
`observed_model`.

The defect is the contract statement. An agent holding `{"model": null}` and this doc will
conclude "no selector was requested". Two materially different facts are collapsed there —
"launched with the harness default" and "the requested selector is no longer known" — and
unlike the `observed_model` case there is no sibling field that separates them. This is the
same class of ambiguity the PR was written to remove, one field over.

Fix, smallest first: state the real lifetime in both docs ("`model` carries the requested
launch selector for as long as the gateway holds the run's launch facts; it is null when no
selector was requested and after those facts are lost") and carry the same sentence in the
field description from finding 2. If the owner wants `model` to be genuinely always-present,
that is a durable-launch-facts change and belongs in the wider identity model, not here.

### 2. Major — the disambiguating contract is not on the wire

`api/src/transport_matters/controlplane/observe_models.py:47-48`

```python
    model: str | None
    observed_model: str | None
```

Neither field carries a `Field(description=...)` or a docstring. `RosterItem` is an MCP tool
output schema and a REST body; its consumers are agents, and the generated schema is the only
documentation they receive. Everything that makes this PR meaningful — that `model` is the
requested selector, that it is never overwritten, that `opusplan` is a per-turn policy rather
than an alias, that null in `observed_model` means "no evidence yet" — lives only in
`docs/CONTROLPLANE.md:62-66`, which is not delivered with the payload.

An agent reading `{"model": "opusplan", "observed_model": "claude-opus-4-6"}` with no
documentation sees one unqualified field beside one explicitly qualified field. The
unqualified name is the one that reads as authoritative, so the natural misreading is
"`model` is what it is running, `observed_model` is a diagnostic detail" — exactly inverted,
and exactly the misreading this PR exists to prevent.

The repo already solves this identical ambiguity in-band, three ways:

- `controlplane/run_models.py:42-45` — `LaunchResult.model` carries
  `Field(description="Raw requested model. Capture resolves and actuates the target separately.")`.
- `observe_models.py:61` — `RosterResult.total`, in this same file, carries a docstring for a
  far less ambiguous field.
- `docs/LAUNCH-CONTRACT.md:133-134` states the rule outright: results name requested values
  explicitly "so they cannot be mistaken for capture-resolved or native-observed facts".

This also resolves brief check 7 (naming). Keeping `model` unqualified for symmetry with
`RosterItem.effort` is defensible, but only if the field says what it is. Without
descriptions the asymmetric pair is not self-explaining, and renaming to `requested_model` —
for which `controlplane/action_builders.py:60` is the existing precedent — becomes the better
option.

Suggested, folding in finding 1:

```python
    model: str | None = Field(
        description=(
            "Requested launch selector, never overwritten by turn evidence. A policy "
            "selector such as opusplan, or a per-account selector such as best, may resolve "
            "to a different model on each turn. Null when no selector was requested and "
            "after the gateway loses the run's launch facts."
        ),
    )
    observed_model: str | None = Field(
        description=(
            "Model on the most recent primary turn that carried one. Null until such a turn "
            "is observed and while needs_you.kind=model_rejected."
        ),
    )
```

### 3. Minor — an existing assertion was deleted rather than extended

`api/src/transport_matters/api/v1/test_controlplane_skins.py:311-312`

The REST hunk keeps its identity assertion and adds the new one:

```python
    rest_roster = roster.json()["items"][0]
    assert rest_roster["run_id"] == "run-peer"
    assert (rest_roster["model"], rest_roster["observed_model"]) == ("gpt-5", "gpt-5-codex")
```

The MCP hunk replaces it:

```python
    mcp_roster = roster.structuredContent["result"]["items"][0]
    assert (mcp_roster["model"], mcp_roster["observed_model"]) == ("gpt-5", "gpt-5-codex")
```

`git show main:...:307` confirms
`assert roster.structuredContent["result"]["items"][0]["run_id"] == "run-peer"` was there. In
a test named `test_mcp_observe_tools_delegate_principal_and_arguments`, the MCP skin no longer
proves the roster item's identity survives the structured-content round trip. A regression
that mismapped run ids in the MCP projection would now be caught on the REST path only.
Coverage unrelated to this PR was dropped silently; restore the assertion so the two skins
stay symmetric.

### 4. Minor — the doc states two of the three ways `observed_model` is null

`docs/CONTROLPLANE.md:64-66` says `observed_model` "is null before an accepted provider turn
and while `needs_you.kind=model_rejected`". The code produces a third case:

`session/controlplane_statements.py:48-51` selects the model as
`(array_agg(e.model ORDER BY e.ts DESC ...) FILTER (WHERE e.model IS NOT NULL))[1]`, so a
`RunLastTurnRow` exists for any primary turn but its `model` is null when no turn carried one.
`roster_projection.py:65` then returns `None` for a run that has taken turns.

A consumer separates that from "no turn yet" only by cross-reading `last_turn_at`, which is
non-null exactly when the row exists. The inference holds, but it is unstated, and this is a
read model whose purpose is to need no inference.

Related precision point in the same sentence: "accepted provider turn" is inherited from the
old `_accepted_model` wording. The query filters on `kind='turn' AND is_sidechain=false` only;
the sole acceptance test in the code is the `model_rejected` suppression. "Most recent primary
turn that carried a model" describes what is implemented, and the rename to `_observed_model`
was made for exactly that reason.

## Not flagged, per brief

PEP 758 (none present in this diff); absent TypeScript changes; `RunManager.ts` launch facts
storing raw requested intent (flagged only for its *lifetime*, in finding 1, not its content);
the wider identity model.

## Not a finding, recorded

`api/v1/test_controlplane_skins.py` is 699 LOC after this PR, 695 before — one line under the
repo's 700 hard guardrail. Not a violation. The next change to that file refactors first.

---

# Delta round: `638470c5..2a16bb96`

One commit, `2a16bb96 fix(controlplane): clarify roster model contract`, +42/-18 across 4
files. Tree pristine. All four findings closed; nothing regressed.

**Major 1 — closed, and the new wording is exhaustive.** `docs/CONTROLPLANE.md:64-68` now
reads "`model` carries the requested launch selector while the gateway retains its
process-lifetime launch facts. It is null when no selector was requested or those facts are
unavailable." Checked against the source: `launchFacts` is written exactly once, at
`RunManager.ts:482` (`model: input.model ?? null`), and read at `:293` as a spread copy;
those are the only two occurrences in the file, so nothing mutates it after spawn.
`RunActivityProjection` (`workspaceActivity.ts:30-50`) still has no `model` field, so
`effectiveProjection` has one source. `model` is therefore null in exactly three situations —
no selector requested, `RunManager` entry gone after a restart, run not created by this
`RunManager` — and the last two are both "those facts are unavailable". No case remains
unstated, and there is no case where `model` is non-null but is not the requested selector.
`gateway/src/main.ts:151-159` (`launchFacts: activity.launchFacts ?? runManager`) is an
injection seam; `resolveActivityDeps` supplies no override, so `runManager` is the production
source. `docs/LAUNCH-CONTRACT.md:159-161` carries the same correction.

**Major 2 — closed, judged from the payload.** Verified against the live MCP tool rather than
the source: listing tools on the skins app returns `roster.outputSchema` with

- `model` → "Requested launch selector from the gateway's in-memory launch facts. Never
  replaced by turn evidence. A selector can resolve per turn or per account. Null when no
  selector was requested or the launch facts are unavailable."
- `observed_model` → "Model on the most recent primary turn that carried one. Null when no
  primary turn has carried a model or while needs_you.kind is model_rejected."
- `required` includes both, so null is always an explicit value and never an omission.

As a consumer with nothing else: "requested" plus "never replaced by turn evidence" plus "can
resolve per turn or per account" is enough to stop me reading `model` as the running model,
and a non-null `observed_model` equal to `model` is agreement while null is absence. No
guessing left on either axis.

**Minor 3 — closed.** `test_controlplane_skins.py:312` restores
`assert mcp_roster["run_id"] == "run-peer"`; the MCP and REST assertions are symmetric again.

**Minor 4 — closed.** `docs/CONTROLPLANE.md:66-68` states the third null case and its
disambiguator ("When it is null, `last_turn_at` distinguishes no primary turn from primary
turns without a model"), and "accepted provider turn" is replaced by "the most recent primary
turn that carried a model", which matches what `controlplane_statements.py:48-58` filters on.

**Original fix intact.** `roster_projection.py` and `test_service.py` are byte-identical to
`638470c5` (empty diffs). `model=item.model` at `:40` is still unconditional, and the
with-turn regression at `test_service.py:214-218` still asserts `"model": "requested-fable"`
against turn model `claude-fable-5`, so it still fails against `6a89ac85`, where
`_accepted_model` returned the turn model.

**Gates.** `ruff check` and `mypy` clean; the two affected test modules → 40 passed.

**Observed, not raised** (below the Blocker/Major bar set for this round): the
`observed_model` field description does not itself name `last_turn_at` as the disambiguator
between its two null causes, though `docs/CONTROLPLANE.md` does. Absence-versus-agreement,
which is what the field exists to answer, is fully covered without it.
