---
title: Transport Matters Verification Surfacing Spec
type: projects
tags: [transport-matters, harnesses, baseline, verification, inventory, launch-readiness, canvas, spec]
summary: What the operator sees about baseline verification per harness and per cell, where it lives, how a failed capture is re-run, and what the canvas shows
status: active
project: transport-matters
confidence: high
created: 2026-08-23
updated: 2026-08-23
---

# Transport Matters Verification Surfacing Spec

Spec only. Companion to `~/.mdx/projects/tm-reference-schema-spec.md`, which still stands and
whose four open decisions are with the owner. That spec answers what a release ships and who
consumes `SupportState`. This one answers what the operator can see today, with no release
reference in existence.

## Inspection boundary

Read at `c6914269b9667271f339f833e7e9d75a25e35b7d` on `main`, clean tree. Codex owns the working
tree; this pass wrote nothing to the repository, no store, no home, and made no provider call.
The live preview store was read, not modified.

### Live state, measured

The preview home now holds **three** captured cells, not two. Grok landed at 12:57, after the
brief was written:

| cell | version | ceiling | attempt | bundle bytes |
| --- | --- | --- | --- | ---: |
| `claude/anthropic/opus` | 2.1.241 | 2.1.211 | succeeded, count 1 | 671,266 |
| `codex/codex/gpt-5.6-sol` | 0.149.0 | 0.144.4 | succeeded, count 1 | 300,539 |
| `grok/grok/grok-4.6` | 1.0.5 | 1.0.4 | succeeded, count 1 | 189,470 |

All three installed versions are above their release's blessed ceiling, so all three remain
captures under codex's new economics. Every `current` pointer carries `accepted_by: null`.

Stable and dev homes still have no `baselines` directory.

**The whole read this spec proposes costs 1,755 bytes**: three `current` pointers at 253, 255
and 248 bytes, three `attempts` records at 334, 336 and 329 bytes. That is the entire surface,
for every harness, against 1.16 MB of bundles it never opens. It is the same economy
`baseline_staleness` documents about itself.

## 1. What the operator sees

Per harness, and within it per cell, five facts. Nothing here requires a new verdict.

| fact | answered by | today |
| --- | --- | --- |
| has a baseline, and at which version | `baseline_staleness.assess_baseline_staleness` | exists, no caller |
| does it match the installed harness | same, `verdict` of `current`/`stale`/`unknown` | exists, no caller |
| where the version sits in the blessed range | `HarnessCompatibilityInfo.range_position` | already served |
| blessed or degraded | `support_state.SupportState` | exists, no input, no caller |
| if nothing was captured, why | nothing. `LaunchVerificationCoordinator._capture_is_due` decides it and writes it to the log | invisible |

The four states the brief names map cleanly onto two existing fields plus one absence:

- **unblessed below floor** is `range_position == "below_minimum"`. It is not a baseline state at
  all, and its remediation is upgrading the harness, never capturing evidence. Reading it off the
  compatibility field it already lives in keeps that distinction intact.
- **blessed** and **degraded** are `SupportState`, and are unreachable until a release ships a
  reference schema. The field must be present and `null`, never absent, so the operator can tell
  "not compared" from "compared and fine". `SupportState`'s own docstring already settles this:
  a version that has not been compared has no state, which is the absence of a verdict rather
  than a member.
- **unknown** is `assess_baseline_staleness`'s third verdict, which its docstring already refuses
  to treat as a synonym for either other answer.

### Why no capture: one owner, two readers

`_capture_is_due` already computes every reason a cell has no evidence, and emits each as a
`logger.info` line: evidence already exists, cell lock held, retry cooling. Codex is adding two
more (below floor, inside range) and deleting one (retry cooling). Surfacing must not
re-derive those branches in the inventory, or the explanation and the decision drift apart the
first time one of them changes.

**Extract the decision, do not copy it.** A pure `assess_capture_decision` returning a typed
reason, called by the coordinator to act and by the inventory to explain. It belongs at the
package root beside `baseline_staleness`, `verification_cell` and `support_state`, for the reason
all three state in their own docstrings: it belongs to neither layer that touches it.

This is not a third verdict. It is a reason code in the shape of
`resolver_contracts.ResolutionRejectionCode` and `captured.readiness.LaunchReadinessFailureCode`,
and it replaces log lines rather than adding a parallel judgment. The vocabulary:

```text
captured | in_progress | failed | not_due_inside_range | not_due_below_floor
| lock_held | target_not_launchable | harness_not_installed | never_launched
```

`never_launched` is the state all three stable and dev cells are in right now, and the state the
operator currently cannot distinguish from a silent failure.

### `effort_policy_unverified` misleads, and should be renamed

`effort_policy.HarnessAdvisory` is a single member literal, `effort_policy_unverified`, emitted
only for claude and only when `claude_effort.claude_effort_policy_verified` returns false. That
function compares against `CLAUDE_EFFORT_POLICY_VERIFIED_THROUGH`, currently `"2.1.239"`.

The operator's claude is **2.1.241**. The advisory is firing on his machine right now, while the
baseline captured at 2.1.241 succeeded on the first attempt. Adding a baseline surface beside an
advisory that reads "unverified" and means something else entirely is how an operator learns to
distrust both.

Scoping does not fix it. The collision is the word, and the vocabulary already carries three
unrelated senses of it:

1. `effort_policy_unverified`: claude's effort vocabulary is unconfirmed above 2.1.239.
2. `compatibility.SupportTier` value `observed_unverified`: this target edge has no tested
   certification.
3. baseline verification: no controlled capture exists for this cell.

**Rename to `effort_vocabulary_unconfirmed`.** The cost is one single member Python literal and
its hand mirrored TypeScript union in `www/packages/core/src/types/harnessInventory.ts`, which
carries an `// api:` comment naming its Python owner. Both are one line. Renaming the third sense
is out of scope; renaming the one that will sit next to the new field is the cheap cut.

## 2. Where it lives

**`/v1/harnesses`, on `harnesses.inventory.HarnessInventoryItem`, built by
`harnesses.inventory._harness_item` under `harnesses.inventory.harness_inventory`.** That is the
symbol `api/v1/harnesses.get_harnesses` returns unchanged, and the projection every other
per-harness fact already flows through.

### The chosen verdict: `assess_baseline_staleness`

Item 2 asks which of the two inert verdicts becomes the answer, or why a third is justified.
**`baseline_staleness.assess_baseline_staleness` is the answer, and no third is added.**

`SupportState` cannot be the answer today. `assess_support_state` requires a reference
`RequestSchema`, no release ships one, and both live bundles record `reference_outcome: null` for
exactly that reason. Making it the surface's primary field would ship a column that is `null` for
every cell on every machine until the reference schema work lands. `assess_baseline_staleness`
needs nothing that does not already exist on disk: it reads one `current` pointer per cell and
compares its `harness_version` against a fresh probe.

So the shape carries both, with `SupportState` present and nullable from day one. When a release
ships a reference, `support` starts being populated by the write site named in the reference
schema spec, and no field is renamed, added, or moved on either side of the API.

The one hazard to respect: `assess_baseline_staleness` requires a **freshly probed** installed
version, and its docstring names the exact defect otherwise, four codex cells reading `current`
against a stored row that had drifted. `_harness_item` already holds
`observation.normalized_version` from the stored row. That is the wrong input. The inventory must
pass what `compatibility_service._observe` observed, or pass `None` and accept `unknown`, and
never pass the stored row silently.

### Response shape

```python
class BaselineAttemptInfo(_InventoryModel):
    status: BaselineAttemptStatus          # in_progress | failed | succeeded
    attempt_count: int
    started_at: str
    completed_at: str | None

class BaselineCellInfo(_InventoryModel):
    provider: str
    launch_model: str
    verdict: StalenessVerdict              # current | stale | unknown
    baseline_version: str | None
    installed_version: str | None
    bundle_id: str | None
    accepted_by: str | None
    support: SupportState | None = None    # null until a release ships a reference
    capture: BaselineCaptureDecision       # why there is or is not evidence
    attempt: BaselineAttemptInfo | None = None
```

`HarnessInventoryItem` gains `baselines: tuple[BaselineCellInfo, ...]`, named and shaped after
its existing neighbour `target_observations: tuple[TargetObservationInfo, ...]`.

`accepted_by` is surfaced because the affordance already exists and is invisible:
`baseline_store.accept_degraded_baseline`, reachable only through
`baseline_harvest --accept-degraded --accepted-by`. All three live pointers read `null`, and no
surface would ever show that a human vouched for a degraded baseline.

### One wrinkle, named rather than hidden

`harness_inventory` is documented as "async reads only, over the caller's pool". The baseline
store is the filesystem. Three pointer reads and three attempt reads totalling 1,755 bytes on the
request path is not worth a thread hop, and `_capture_is_due` already does the same reads
synchronously inside the verification path. Do it inline, and revisit if a cohort ever reaches
the scale where it matters: a full claude cohort is ten aliases, so roughly 6 KB.

The TypeScript mirror in `www/packages/core/src/types/harnessInventory.ts` is hand maintained
with `// api:` provenance comments and must be updated in the same change.

## 3. Manual re-run

**The affordance already exists and is wrong for this job.**
`baseline_harvest` (`python -m transport_matters.baseline_harvest --harness <id> --model <id>`)
captures a controlled baseline through the real launch path. It imports no `baseline_attempts`,
takes no `WorkspaceLock`, and consults no quota. A successful manual harvest therefore writes a
bundle and a pointer while leaving a `failed` attempt record untouched. Under the surface
specified above, the operator would fix the cell and keep being told it is broken.

So the manual re-run is not a new capture path. It is the existing coordinator, invoked
explicitly:

**`LaunchVerificationCoordinator.submit(..., force=True)`.** Force bypasses two gates and neither
of the two that matter: it overrides the recorded attempt state and the already-have-evidence
check, and it never bypasses the cell `WorkspaceLock` or the quota decision. A forced run writes
a new attempt record like any other, so the surface converges.

**Both affordances, one function behind them.**

- **CLI**, for the operator at a terminal: a `baseline` sub-typer registered beside the existing
  `db_app` and `channel_app` in `cli/__init__.py`. `baseline status` prints the same projection
  the API serves. `baseline verify --harness claude --model opus` runs one cell and requires
  `--yes`, following `doctor --reap-orphans --yes`, which is the existing precedent for an
  explicit and costly action.
- **Route**, because the canvas cannot shell out:
  `POST /v1/harnesses/{harness}/baselines/{model}/verify`, modelled on the existing
  `POST /harnesses/refresh` in `api/v1/harnesses`, which already serializes an operator triggered
  action against a startup task under an app-state lock.

**What it costs, stated at the point of invocation:** three provider turns against the operator's
own quota, one per A/B/A probe, on the operator's own account. Measured wall clock from the three
live attempts: 19s, 34s, 30s. The confirmation prompt should say the turn count, not "this may
take a while".

**What it does not do:** it does not delete a bundle, does not move a `current` pointer backwards,
and does not clear a `failed` record without launching. A record only changes because a run
happened.

## 4. The canvas surface

### Minimum viable: a launch readiness check

The palette does not read `/v1/harnesses`. `launcher/useLauncherData` composes
`firstrun/useLaunchReadiness`, which fetches `/v1/launch-readiness` and renders
`captured.readiness.LaunchReadiness`. That model is already exactly the right shape:

```python
class LaunchReadinessCheck(BaseModel):
    id: str
    label: str
    ready: bool
    code: LaunchReadinessFailureCode | None
    detail: str
    harness_id: HarnessId | None
    remediation: str | None
```

**Add one check per installed harness in `captured.readiness._harness_checks`**, beside the
existing enablement, client binary and credential checks. `ready` is false only when a capture
actually failed. `detail` names the cell and version. `remediation` names the re-run command.

Zero new endpoints, zero new components, zero new frontend types. The palette already renders
checks with remediation strings, and the operator already looks there when a launch is blocked.

A cell that was simply never launched must not make the harness unready. It is the normal state
of every cell on a fresh machine, and a permanently amber palette teaches the operator to ignore
it.

### Later: per model in the picker

Once a release ships a reference and `support` stops being `null`, the per model badge belongs on
the launch picker rows, carried on `resolver.LaunchOption` and projected through
`api/v1/harness_launch_view.LaunchModelView`. That is the read site the reference schema spec
already specifies, and it should not be built twice. Building it now would ship a badge that says
nothing for every model on every machine.

### Not in either tier

A capture progress indicator. Verification is fire and proceed by design and completes in about
30 seconds; a spinner for an operation the operator did not start and does not wait for is an
interruption, not information. `in_progress` appears in the inventory and that is enough.

## 5. Deliberately out of scope

- **Making `SupportState` populated.** That needs the release reference, specified separately.
  This slice ships the field as nullable and nothing more.
- **Reviving `accept_degraded_baseline` as a UI action.** The value is surfaced read only. An
  acceptance workflow needs a decision about who may vouch and on what evidence, and there is
  nothing to accept until degraded verdicts exist.
- **Any Postgres representation.** The baseline store is the filesystem and stays the authority.
  `harness_drift_evidence` cannot express blessed with no finding.
- **Retry policy.** Codex owns it on the concurrent branch. This spec surfaces whatever policy
  lands and takes no position beyond the conflicts named below.
- **A per cell history view.** One `current` pointer and one attempt per version is the state;
  bundles accumulate but reading them costs 1.16 MB against 1,755 bytes.
- **Renaming `observed_unverified`.** The third sense of the word. Real, and a separate change
  with a much larger blast radius through the release catalog.
- **Stable and dev channel parity.** Both homes are empty because the operator launches preview.
  The surface reads the resolved channel's home and says `never_launched` for the others, which
  is the truth.

## Conflicts with codex's concurrent change

Four, in descending order of cost.

**1. Deleting `retry_after` blanks the operator's only evidence, silently.**
`baseline_attempts.BaselineCaptureAttempt.retry_after` is required, validated
(`retry_after < started_at` raises), and present in all three live records on disk. Removing
auto-retry either leaves it as a vestigial required field or changes the model shape, and a shape
change means bumping `BASELINE_ARTIFACT_SCHEMA_VERSION` from 8 to 9. `read_baseline_attempt`
then returns `None` for every existing record: *"Older evidence schemas invalidate it."*

That behaviour was correct while the file held disposable retry state. It stops being correct the
moment the same file is the only record that a capture succeeded or failed, which is exactly what
this spec makes it. The three successful attempts from 12:49 and 12:57 would vanish from the
surface on the first backend start after the bump, with no error anywhere.

Either keep the shape and stop writing `retry_after` meaningfully, or bump and accept that the
operator's first view of the new surface shows three cells with bundles and no attempt history.
The second is survivable only because bundles and pointers carry their own versions (5 for
pointers, 8 for attempts) and are read independently. It should be a decision, not a side effect.

**2. "Capture only above the ceiling" makes the reference schema uncapturable.**
The reference schema authoring flow requires a controlled capture at **exactly** the blessed
ceiling, and `CompatibilityReleaseEntry` validation is specified to reject a reference whose
`observed_harness_version != blessed_ceiling(release)`. Under the new economics a version at the
ceiling is inside the range and skips with zero spend. Launch verification would then be
structurally incapable of producing the evidence a release needs.

That is fine if authoring always goes through `baseline_harvest`, which ignores the economics
gate entirely. It should be stated as the intent rather than discovered later. The gate belongs
on the automatic path only, never on the explicit one, and the same applies to the forced re-run
in item 3.

**3. No retry plus no surface is a permanent silent hole, and the ordering matters.**
The brief already names this. The consequence for sequencing: if the retry deletion lands first,
every failure between the two merges is invisible and unrecoverable without the operator finding
the attempt file by hand. **Land surfacing first, or land both together.** The surface has no
dependency on the economics change; the economics change has a real dependency on the surface.

**4. `_capture_is_due` is being rewritten by codex and extracted by this spec.**
Both changes touch the same method: codex adds the ceiling gate and removes the cooldown branch,
this spec lifts the whole decision into a pure typed owner both the coordinator and the inventory
read. Doing them in either order is fine; doing them concurrently produces a conflict in the one
function whose branches are the reason vocabulary. Whoever goes second should extract, so the
reasons and the decision cannot drift.

One non-conflict worth recording: `minimum_version == baseline_version` for a new harness makes
`below_minimum` reachable, which yields `harness_update_required`, which
`launch_target._passes_to_harness` does not whitelist. So a downgraded harness both refuses to
launch and never captures. That is consistent, and item 1 surfaces it as unblessed below floor
with an upgrade remediation rather than a verification one.

## Open decisions for the owner

**1. Does a failed capture make the harness unready in the palette?**
With auto-retry gone, a red check clears only when the operator runs the explicit re-run. A check
that stays red teaches him to ignore the palette; a check that is never red hides the failure the
whole slice exists to expose.
*Recommendation:* not ready, but only after a failure, never for a cell that was simply never
launched. `never_launched` is the normal state of most cells forever.

**2. Is the manual re-run per cell or per harness cohort?**
Per cell is three turns. A claude cohort is ten aliases, thirty turns.
*Recommendation:* per cell only. Cohort capture is a release authoring act and belongs to
`baseline_harvest`, where the operator is already deliberate about spend.

**3. Rename `effort_policy_unverified`?**
It is a published vocabulary in two hand synchronised places, and it is currently firing on the
operator's machine for an unrelated reason while a baseline surface is about to appear beside it.
*Recommendation:* rename to `effort_vocabulary_unconfirmed` in the same change that adds the
baseline field, so the two never ship adjacent under the same misleading word.

## Verification of the claims in this spec

Measured rather than read:

- Three live cells in `~/.transport-matters-preview/baselines`, all `succeeded` at
  `attempt_count: 1`, bundles of 671,266 / 300,539 / 189,470 bytes.
- Surface read cost: six files, 1,755 bytes total.
- Attempt durations from `started_at` to `completed_at`: 19s, 34s, 30s.
- All three `current` pointers carry `artifact_schema_version: 5` and `accepted_by: null`; all
  three attempt records carry `artifact_schema_version: 8`.
- `~/.transport-matters` and `~/.transport-matters-dev` contain no `baselines` directory.
- Installed claude is 2.1.241 against `CLAUDE_EFFORT_POLICY_VERIFIED_THROUGH = "2.1.239"`, so
  `effort_policy_unverified` is active now.

Read at the SHA above: `assess_baseline_staleness` and `SupportState` each have zero non-test,
non-docstring references under `api/`. `baseline_harvest` imports neither `baseline_attempts` nor
`WorkspaceLock`. `read_baseline_attempt` returns `None` on any `artifact_schema_version`
mismatch.
