# Does effort change the raw request schema?

Investigation and report only. No code, no repo writes, no provider turns spent.

## Verdict

**No, for every harness I can measure. Effort is content, not structure.**

| harness | where effort sits on the wire | key set varies with effort? | verdict |
| --- | --- | --- | --- |
| codex | `/reasoning/effort`, a leaf scalar | no, measured on the same model at `low` and `high` | **content** |
| grok | `/reasoning/effort`, a leaf scalar | no, measured on the same model at `high` and `xhigh` | **content** |
| claude | nowhere. `thinking` is `{type}` and carries no budget | key set invariant across 77 captures | **content, one gap** |

**Disk settled codex and grok outright.** Claude is settled to the limit of what exists on
disk and has one narrow residual gap that one cheap probe pair would close. I did not run it.

**m6 as built is wrong, and the challenge is correct.** Effort should be **recorded** on the
cell and should **not be a key**. That is a subtraction from `#443`, not a revert: keep
`BaselineCell.effort` and artifact version 10, drop every path, pointer, attempt, lock and
cohort fork. It deletes most of the 122 lines in `baseline_store.py`, and it removes d2 and
d3 entirely rather than living with them.

I wrote the review that cleared m6. It was cleared as correctly implemented, which it is.
Nobody, including me, asked whether the axis should exist. The owner is right to ask.

## Inspection boundary

Tree pristine, `git status --porcelain` empty, branch `fix/palette-verification-trigger`.
Read only throughout. Nothing was written to either baseline store, and no launch was made.

Sources: the three v8 bundles in `~/.transport-matters-preview/baselines`, sixteen older
bundles the operator moved to `~/.Trash/baselines 13-25-39-440` (artifact version 5), **136
`request.raw` files** under `~/.transport-matters*/workspaces`, the `transport_matters` and
`transport_matters_preview` databases, and cm entries `01a023c9` and `01a023d6`.

Correction to the brief: the stable home has no `baselines` directory at all. The "roughly 16
cells from earlier work" are the sixteen in the Trash. I read them there without restoring
them.

## The mechanical half, settled with certainty from the code

Before asking what each harness sends, it matters what `compare_request_schema` counts.

`mint_request_schema` builds nodes from paths and value *types*, never from scalar values.
`request_array_branch` is the only place a value becomes structure, and it discriminates on
`type` or `role` **inside array items only**. `thinking` and `reasoning` are root objects, so
no value inside them can ever become a branch.

Executed to confirm, on synthetic bodies differing in exactly one way:

    responses: effort VALUE low -> xhigh              -> exact     0 findings
    anthropic: thinking adaptive -> enabled+budget    -> degraded  1 finding  (/thinking/budget_tokens added)
    anthropic: budget_tokens VALUE 31999 -> 60000     -> exact     0 findings

So the whole question reduces to one thing: **does changing effort change a key set?** A
changed effort value never can. Only effort switching a property in or out of existence can.

## Codex: content. Measured twice, independently.

cm `01a023c9` recorded it on 2026-08-21 and I reproduced it from the Trash bundles with the
production comparator:

    codex effort LOW (sol) vs MEDIUM (luna)   -> exact     0 findings
    codex MEDIUM (luna) vs MEDIUM (terra)     -> exact     0 findings
    codex 5.6-low vs 5.5-medium               -> breaking  4 findings

The orchestrator's summary of `01a023c9` is accurate. Its own words: "luna and sol differ in
the static node values `/model` and `/reasoning/effort`, yet structure is EXACT and content
changes are 0."

The alias pair crosses `/model` as well as effort, so I checked the same model too. Among the
136 captured `request.raw` files there are `gpt-5.6-sol` requests at **both `low` and
`high`**, and the `reasoning` key set is `{context, effort, summary}` in both.

The key set does vary within codex, and it is worth being precise about why it is not effort:
six `gpt-5.6-sol` captures carry `{context, effort}` with no `summary`, and all six are at
`effort: low`, the same effort as nineteen captures that do carry `summary`. **The `summary`
property varies while effort is held constant, so it is not a function of effort.**

## Grok: content, and the axis is already dead there anyway

Captured `grok-4.6` requests exist at **`high` and `xhigh`**, both with the identical
`reasoning` key set `{effort, summary}` and the same 27-tool catalog. Three further captures
carry `{summary}` with no `effort` at all, and those have a 1-tool catalog: a different
request kind, not a different effort setting.

Separately, and decisively for the design question: **`harness_target_observation` records
`native_efforts = []` for every grok model.** TM enumerates no grok efforts, so the resolver's
per-model effort gate rejects any effort and a grok verification cell always carries
`effort=None`. Meanwhile grok's wire body genuinely carries `effort: "xhigh"` from
`~/.grok/config.toml`. The coordinate is permanently `None` for a third of the fleet, while
the thing it claims to record is varying on the wire. A key that cannot see its own subject is
not a key.

## Claude: content on all available evidence, with one narrow gap

Claude is the one the orchestrator most expected to differ. It does not, on anything on disk.

Across all 136 captures there are **77 `claude-opus-5` requests**. Grouped by `thinking`:

| shape | count | what these are |
| --- | --- | --- |
| `{"type": "adaptive"}` | 56 | real turns: 22 to 30 tools, 3 system parts, `max_tokens` 64000, streaming |
| `{"type": "disabled"}` | 7 | auxiliary calls: **0 tools**, 1 message, still 3 system parts |
| no `thinking` key | 14 | reachability probes: **`max_tokens: 1`**, 0 tools, 0 system, not streaming |

**Every real chat request has the same `thinking` key set, `{type}`.** The only structural
variation, `thinking` being absent, belongs to a `max_tokens: 1` connectivity ping that is not
a chat request and would never be a first-turn baseline probe. `adaptive` versus `disabled` is
a value change at a fixed path, which the comparator scores `exact`.

`budget_tokens` appears exactly once in the whole corpus, on
`anthropic/claude-haiku-4-5-20251001`, and `harnesses/claude_effort.claude_model_supports_effort`
excludes haiku from effort entirely. So the one model that emits a different `thinking` shape
is the one model that takes no effort. cm `01a023d6` attributes that same difference to the
generation boundary across 45 claude pairs, with every Claude 5 pair EXACT.

The mechanism argues the same way. `{"type": "adaptive"}` means the server chooses the budget.
While claude sends `adaptive`, **there is no field in the body that could carry an effort
level**, so effort cannot be in the schema.

### The gap, stated honestly

I cannot recover the launched effort from the stored artifacts. `transport.json` carries
transport metadata, `event.raw` and `event.ir` are transcript records, and `wire_blob` holds
decomposed IR components, none of which carry sampling parameters. So I cannot prove those 56
`adaptive` captures span more than one effort setting.

The residual risk is precisely one thing: that some effort value switches claude-5 from
`{type: "adaptive"}` to `{type: "enabled", budget_tokens: N}`. That would be `degraded`, per
the synthetic test above.

Worth flagging while here: `docs/LAUNCH-CONTRACT.md` states "Claude has no separate effort
actuation argument; explicit Claude effort is preserved as requested metadata with an
`effort_not_actuated` advisory", and `capture_rpc_routes._resolve_launch_target` emits that
advisory. But `cli/launch_profile._claude_effort_argv` does emit `--effort` for any non-haiku
model. Those two cannot both be current. If the document is right, claude effort never reaches
the process at all and the question is closed by construction. That contradiction should be
resolved regardless of this decision.

## 3. The single probe that would close it

Only claude needs one, and only at the extremes.

**One cell: `claude` / `opus`, captured at `effort=low` and at `effort=max`.** If `thinking`
is `{type: "adaptive"}` at both ends of the vocabulary (`low, medium, high, xhigh, max`), it
holds throughout and claude joins codex and grok.

Cost: **two provider turns** if run as two single first-turn exchanges, since the request body
is emitted before any response matters and the trivial `Reply with exactly ALPHA.` prompt is
enough. **Six turns** if run as two full A/B/A captures through
`harvest_controlled_baseline`, which is the only path that exists today.

I have not run it. The owner decides.

## 4. The design call

### Should effort be a coordinate at all? Recorded yes, keyed no.

Read cm `01a023c9`'s argument again, because it is the real case for m6 and it is not a schema
argument: "**Effort is not pinned in the cell and is not in any content group.** If a harness
changed its default effort for a model, two harvests of the same cell would compare EXACT
while the request genuinely differed."

That is an **attribution** concern. It is answered completely by recording effort on the cell,
which makes the stored evidence say what produced it. It says nothing about keying, and keying
is where every cost lives.

Keying on effort costs, in `#443` as built: a pointer schema bump to 6 with a legacy fallback,
an attempt path fork, a lock and workspace fork, a cohort partition, `rglob` enumeration, 122
lines in a persistence file, plus d2 and d3 from my own review. It buys the ability to hold two
baselines that, on all present evidence, can never differ.

It is also actively wrong in two places. For grok the coordinate is always `None` while the
wire effort is `xhigh`, so it records a falsehood. And `_require_comparable_capture_plan` now
refuses a reference whose effort differs, which turns a comparable pair into a hard failure on
an axis that does not affect comparability.

The principle the project already holds settles it: **structure gates, content never gates.**
Effort is content. Content is recorded and reported, never made a key and never made a refusal.

### Should capture pin the cheapest effort? Yes, after the claude probe.

`baseline_capture.harvest_controlled_baseline` passes `model.default_effort` at every call
site, so the operator's three live cells were captured at `high`, `high` and `xhigh`. If
effort is not schema relevant, `low` produces identical evidence for fewer reasoning tokens
and a faster turn, three times per capture.

The tension the brief raises dissolves rather than trading off. "Pinning one effort means we
only ever verify one of them" is only a cost if the others could differ. They cannot, so
pinning `low` verifies all of them.

Sequence it: settle claude first, then pin `low`. Pinning before the probe would bake in the
one assumption still unproven, and at `low` claude is least likely to reach for a budget.

## 5. What `#443` should become

**Re-scope m6 to record without keying. Do not merge as is, and do not revert m6.**

Keep, unchanged:

- `BaselineCell.effort`, `BaselineArtifactSchemaVersion` 10, and
  `LEGACY_BASELINE_ARTIFACT_SCHEMA_VERSIONS = {8, 9}` with the legacy read that sets
  `cell["effort"] = None`. This is the recorded coordinate and it is the part that answers cm.
- `BaselineCaptureAttempt.effort` as a recorded field.
- `harvest_controlled_baseline` and `LaunchVerificationCoordinator` passing the cell's effort
  through, so what is recorded is what ran.

Remove:

- The effort fork in `baseline_store._current_path`, and with it
  `BaselinePointerSchemaVersion` 6, `PREVIOUS_BASELINE_POINTER_SCHEMA_VERSION`, the legacy
  fallback in `read_current_baseline_ref`, the `_read_pointer` upgrade, and the `rglob`. The
  pointer stays at version 5 and never moves. **This alone removes d2 and d3.**
- The effort directory in `baseline_attempts.baseline_attempt_path`, and effort from the
  identity tuple in `read_baseline_attempt`. Keep the field on the record.
- The effort segment in `launch_verification_lock_root` and `launch_verification_workspace`,
  restoring the docstring that this branch replaced. Its original wording was right: effort
  "does not name a separate current pointer, so it must not create a second lock for the same
  write target."
- `effort` from `baseline_comparison._ModelCohortCoordinates`. Two cells at different efforts
  are comparable, so effort must not partition the cohort.
- The effort branch in `baseline_store.has_baseline_bundle_for_version`, including the legacy
  exemption it needed.

Change:

- `baseline_capture._require_comparable_capture_plan` should stop raising on an effort
  mismatch and record the difference instead. Refusing to compare across efforts is the one
  place the axis would actively block correct work.

Net effect: the artifact gains a field and a version, and nothing gains a key. Most of the
122 lines in `baseline_store.py` go away, the branch keeps the guard fix and the other five
minors, and the two minors I raised against it stop existing rather than being accepted.

If the owner would rather not re-scope on a green branch, the ranked alternatives are: merge
as is and un-key in a follow-up, which costs a second artifact migration to undo a key that
should not have been added; or revert m6 entirely, which is cheaper than that but throws away
the recorded coordinate that cm legitimately asked for. Re-scoping now is the smallest total
change.

## Open, and worth a separate look

1. The `LAUNCH-CONTRACT.md` versus `_claude_effort_argv` contradiction above. If claude effort
   is genuinely never actuated, the claude gap closes with no probe at all.
2. Grok's empty `native_efforts` means TM models no grok effort while grok's wire body carries
   one. Whatever is decided here, the grok effort vocabulary is unobserved and the cell cannot
   describe the request.
3. Neither `compare_content` group covers `/reasoning/effort` or `/thinking`. If the owner
   wants a silent effort change to be *visible* rather than merely recorded, adding those
   pointers to a content group is the proportionate mechanism, and it gates nothing.

## Postscript: the branch moved while this was written

Head is now `bb4dcf5d` ("fix: finalize verification cell migration"), one commit past the
`0543ec77` I re-reviewed. Tree still pristine. It answers my d2 and d3 by **accepting and
managing** them rather than removing them:

- d3 gains a shadowing rule in `read_current_baseline_refs`: a version 5 effort-less pointer
  stops being a cohort member once any effort specific pointer exists for that model. Roughly
  20 lines of set building and path part inspection.
- d2 gains a docstring on `read_current_baseline` and a paragraph in the version 10 comment
  block, recording the one time comparison loss per effort as intended behaviour.

Both are well written and both are correct given the key. Neither would need to exist without
it. That is another 35 lines in `baseline_store.py`, on top of the 122, spent entirely on
consequences of a coordinate that the evidence above says cannot change the schema. It
strengthens the recommendation rather than weakening it: the key keeps generating work.

The re-scope described in section 5 applies unchanged to `bb4dcf5d`, and now also deletes the
shadowing rule.

---

# Re-scope review ef54874b

`git diff bb4dcf5d ef54874b`, one commit "fix: record baseline effort without partitioning",
25 files, 186 insertions and 278 deletions, net -92.

**0 major, 3 minor. MERGE.**
**The key is genuinely gone, in all six places. d2 and d3 are deleted, not relocated.**
**Probe recommendation: run it. High confidence it confirms content, and 2 turns is the
right price for what it now protects.**

Tree pristine at `ef54874b`. Read only. Full suite `4143 passed in 46.79s`.

## 1. The key is gone, all six

| where | state |
| --- | --- |
| pointer path | `_current_path` back to `<model>.json`, no fork. `BaselinePointerSchemaVersion` back to `Literal[5]`, `PREVIOUS_BASELINE_POINTER_SCHEMA_VERSION` deleted, `_CurrentBundlePointer.effort` and `CurrentBaselineRef.effort` deleted |
| attempt path | `baseline_attempt_path` back to one directory chain, effort out of `read_baseline_attempt`'s identity tuple and out of `read_baseline_attempts`' dedupe key |
| lock domain | effort segment removed from `launch_verification_lock_root`, and the original docstring restored word for word: effort "does not name a separate current pointer, so it must not create a second lock for the same write target" |
| workspace | effort segment removed from `launch_verification_workspace` |
| cohort partition | `effort` removed from `baseline_comparison._ModelCohortCoordinates` and from `_model_cohort_coordinates` |
| comparison reference | **confirmed**: `baseline_capture._require_comparable_capture_plan` no longer takes or compares `effort`. A reference captured at a different effort is comparable again |

`has_baseline_bundle_for_version` also lost both the effort branch and the legacy exemption
that branch needed, and `assess_baseline_staleness` and `read_current_baseline` lost the
parameter. Nothing is half removed.

The clearest evidence is the net against `main`: `baseline_store.py` is now +47/-32 rather
than the +157 it carried at `bb4dcf5d`, and every remaining line is either the
`LEGACY_BASELINE_ARTIFACT_SCHEMA_VERSIONS` rename or effort recording. `glob` replaced
`rglob`. The store's addressing is byte-for-byte the shape it had before this branch.

## 2. What was kept is exactly the specification

- `BaselineCell.effort: str | None` with `min_length=1`, recorded and never keyed.
- `BaselineArtifactSchemaVersion = Literal[10]`, `BASELINE_ARTIFACT_SCHEMA_VERSION = 10`.
- `LEGACY_BASELINE_ARTIFACT_SCHEMA_VERSIONS = frozenset({8, 9})`, accepted by
  `read_baseline_bundle`, `has_baseline_bundle_for_version` and `_parse_baseline_attempt`,
  each normalizing the legacy cell to `effort = None`.
- `BaselineCaptureAttempt.effort` kept as a recorded field, still populated by both
  `BaselineAttemptRecorder` construction sites.
- The version 10 comment now reads "records the launch effort as capture attribution ...
  Effort is request content and does not address current pointers or partition structural
  comparisons", which is the finding rather than a restatement of the key.

`test_effort_is_recorded_without_partitioning_attempt_identity` pins it precisely: two
attempts at different efforts, one file on disk, the effort recorded and the count
incremented. `test_model_cohort_allows_effort_differences` pins the cohort side.

## 3. d2 and d3 are deleted, and no cell loses a reference

The 35 lines that managed the consequences are gone rather than rewritten. The shadowing set
comprehension in `read_current_baseline_refs`, the `read_current_baseline` docstring about
never falling back, the paragraph in the version 10 comment recording a one time comparison
loss, the legacy fallback and version upgrade inside `_read_pointer`: all removed.
`_read_pointer` is back to `model_validate_json` catching `ValidationError`.

Proven live rather than read. Against the operator's real store, where every artifact is a
version 8 bundle or attempt and every pointer is version 5:

    claude opus         staleness=current  evidence=True  ref=HIT  full=HIT  attempt=succeeded
    codex  gpt-5.6-sol  staleness=current  evidence=True  ref=HIT  full=HIT  attempt=succeeded
    grok   grok-4.6     staleness=current  evidence=True  ref=HIT  full=HIT  attempt=succeeded

Two things to read off that. `full=HIT` where it was `MISS` at `0543ec77`: the two readers
agree again, so **no cell loses a reference comparison**, which is d2 gone at the level of
observable behaviour rather than documentation. And `attempt=succeeded` where the effort keyed
identity tuple previously hid the legacy record.

The claude cohort enumerates exactly `[('opus', None)]`. One entry, no phantom sibling. d3
gone.

## 4. Nothing re-captures and nothing became unreadable

Covered by the table above: all three cells `current` with durable evidence present, read
through the same paths `main` uses. The legacy `{8, 9}` tolerance is what carries the v8
bundles, and it is the only compatibility machinery left.

## 5. Dead code

`ruff` is clean across the five touched modules, so no import was stranded.
`claude_launch_effort` survives with one caller, `claude_launch_effort_evidence`, which is
correct: advertised options must still exclude haiku even though actuation no longer does.
`BaselineCaptureAttempt.effort` is still written by both recorders.

The one genuine residue is e2 below.

## 6. The doc fix is on the correct side, verified against the binary

`claude --help` on the installed 2.1.241:

    --effort <level>    Effort level for the current session (low, medium, high, xhigh, max)

So claude actuates effort, `LAUNCH-CONTRACT.md` was wrong, and changing the document rather
than the code is right. Deleting the `effort_not_actuated` advisory from
`capture_rpc_routes._resolve_launch_target` follows, since it asserted something false.

The haiku half is a real behaviour change and worth naming as such rather than as a doc fix.
`_claude_effort_argv` and `effort_policy.launch_effort_value` both dropped their `model_id`
parameter, so an explicit effort now reaches argv for haiku where `claude_launch_effort`
previously swallowed it. The corrected document describes this accurately: "Models without
advertised effort support may still receive an explicit value as passthrough, with the
resolver advisory preserved for attribution."

It is coherent with the existing contract. `claude_launch_effort_options` still returns `()`
for haiku, so `native_efforts` is empty, so an explicit effort resolves to `invalid_effort`,
which `launch_target._passes_to_harness` already lists as a rejection that passes through to
the harness with an advisory. The advisory the document means is that one, not the deleted
claude specific lie.

Risk is low rather than zero: `--help` documents `--effort` as a session flag with no model
qualifier, so haiku should accept or ignore the value rather than fail to parse. I did not
launch haiku to confirm, since that would spend a turn.

## Minor

### e1. The `low` capture pin landed ahead of the probe it depends on

`baseline_harvest.harvest_baseline` now does

    capture_effort = "low" if "low" in selected.effort_options else selected.default_effort

pinned by `test_main_defaults_supported_baseline_capture_to_low`. That is my section 4
recommendation, but I attached a sequence to it that did not survive: settle claude first,
then pin. Pinning first is what converts the open claude question from an unknown into a
risk.

The exposure is narrow and worth stating precisely. It applies to the CLI harvest only; the
automatic path builds `EnumeratedModel(default_effort=cell.effort)` from the launch's real
effort and is unaffected. But `tm baseline` is how the operator harvests deliberately, and
if claude's `thinking` shape is effort sensitive, every future CLI captured claude baseline
would be taken at `low` while the operator's launches run at `high`, making the stored
reference describe a cell nobody exercises.

Either run the probe in item 7, or drop the pin until it is run. Following `default_effort`
costs a little more per capture and keeps the capture aligned with the launch, which makes
the unanswered question harmless.

### e2. `require_persisted_baseline_for_version` still threads a tautological effort assertion

It keeps `effort: str | None = None` and

    if bundle.cell.effort != effort:
        raise ValueError("controlled capture recorded a different effort: ...")

Neither caller can trip it. `harvest_controlled_baseline` sets `cell.effort =
model.default_effort`; the coordinator builds `EnumeratedModel(default_effort=cell.effort)`
and passes `effort=cell.effort`; the CLI builds it from `capture_effort` and passes
`effort=model.default_effort`. Both sides of the comparison come from one value routed
through one object, so unlike the `harness_version` check directly above it, which compares a
prepared value against an observed one, this one cannot fail.

It is the last place the removed coordinate still threads through the persistence API. Either
delete the parameter, since the caller already owns both sides, or keep it and say in the
docstring that it guards a caller invariant rather than an observation.

### e3. Cosmetic churn left where the parameter was removed

`_current_path` and the `read_current_baseline_ref` call site were widened to multi line
signatures to hold `effort`, and both kept that shape after it was removed;
`_current_path` also gained a `directory` local it no longer needs, and
`read_current_baseline_ref`'s two guards were merged into one. Behaviour is identical to
`main` and the tests confirm it, but the diff against `main` shows changed lines that changed
nothing. Restoring the original formatting would make `baseline_store.py`'s net diff read as
exactly what it is.

## 7. The probe: run it

**Recommendation: spend the two turns. Confidence the result confirms content: high, call it
85 to 90 percent.**

The evidence for content is strong and I would not weaken it: 77 `claude-opus-5` captures
with the `thinking` key set invariably `{type}`, `budget_tokens` present only on
`claude-haiku-4-5` which claude's own capability gate excludes from effort, cm `01a023d6`
finding every Claude 5 pair EXACT across 45 pairs and three wire models, and the mechanical
point that `{type: "adaptive"}` hands the budget to the server so no field exists to carry a
level.

Three things stop that being enough.

The failure mode is observed, not hypothetical. `{"type": "enabled", "budget_tokens": N}` is
in claude's own wire vocabulary in this very corpus. The question is only whether a model
class or an effort level selects it, and I have variation on one of those axes and none on
the other.

I cannot show the 77 span more than one effort. The operator's `settings.json` pins
`effortLevel: high` and TM's canvas launches send no `--effort`, so the honest reading is that
they may all sit at one point. Seventy-seven observations of one condition is one observation.

And this delta raised the stakes rather than leaving them flat. Before e1, an effort sensitive
claude was merely unrecorded. With captures pinned to `low` while launches run at `high`, it
becomes a reference schema that is systematically wrong for the whole claude fleet.

Two turns against that is not a close call. Ask for `opus` at `low` and at `max`: the extremes,
because if `adaptive` holds at both ends of `low, medium, high, xhigh, max` it holds
throughout.

### What changes if it comes back the other way

If `--effort max` yields `{"type": "enabled", "budget_tokens": N}` on opus:

- Effort becomes structural **for claude only**. Codex and grok stay content; both are proven
  on same model pairs and neither result depends on this.
- e1 inverts from a minor into a defect: drop the `low` pin immediately, because capturing at
  an effort the operator never launches would be the actively wrong choice.
- The coordinate does not simply come back. The discriminator would be the `thinking` shape,
  which `compare_request_schema` already detects as `degraded` without help, so the gate would
  be working rather than blind. What would need deciding is narrower: whether a claude cell
  captured at one effort may serve as the reference for a launch at another, which is a
  comparison eligibility question, not a storage key question. The re-scope in this commit
  would still stand for the store.

So even the adverse outcome does not undo this merge. It changes one default and reopens one
narrower question. That asymmetry is the whole argument for spending the two turns now.

## Coherence of the final state

41 files and 1103 insertions against `main`, and the shape reads as one idea per layer.
`configured_launch_model` reads the model the launch home will consume,
`launch/environment.resolve_launch_content_home` owns which home that is,
`harnesses/launch_target` replays it to name a cell without touching actuation, and the
baseline store records what ran without letting it address anything. Effort enters as
attribution at the one place it is observed and stops there.

The seams I would have expected to leak do not. Actuation still passes `model=None` for a
palette launch, the strict resolution is still the sole launch authority, and the store is
addressed exactly as it was before the branch. The two artifact facts a reader must hold are
small and stated where they live: bundles are version 10 with versions 8 and 9 readable, and
pointers never moved off version 5.
