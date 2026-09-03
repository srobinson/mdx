# Independent review of the grooming proposal

Reviewed: `proposed-grooming.json` (1221 lines, 43 dispositions, 25 packages, 2 close candidates, 10 owner
decisions), with `github-edit-drafts.md` and `consolidation.md`. Snapshot `53511834`; repository HEAD at review
time is `56cd5755`. Read-only throughout: no source, no GitHub, no runtime, no provider probe.

## Verdict

**Approved with five material corrections.** The proposal's evidence base, package structure and per-issue scope
work are sound and I kept them. Four of the brief's ten review points were already answered correctly by the
proposal (#459 transfer preconditions, #633 not blocked on `certify --all`, #384 retaining real work, #573
separating shipped from open). Five needed correction, below. Corrected artifacts: `final-grooming.json`,
`final-grooming.md`, `final-github-edit-drafts.md`, `verify-final-grooming.py`. The proposed originals are intact.

Closure count changes from "1 unconditional + 1 conditional" to **1 unconditional, 0 conditional**: 43 open issues
become 42.

## Material corrections

### 1. #381 is retained, not closed into #630

The proposal made #381 a conditional close into #630 behind three preconditions. Reversed.

`issue-630.md` states its own outcome as "a model or harness version released today is discoverable, launchable,
captured, and classified blessed or degraded on its first launch", with sub-issues #631/#632/#633. That is a
three-defect P1 regression epic. `issue-381.md` is a product arc with three ordered capabilities and its own
parent acceptance, and its Goal 3 (inspect, fork, edit, save named versions, compare token impact, restore, return
to the TM-managed overlay) has no other home in the 43. The proposal's own remedy proves the mismatch: it had to
move Goal 3 into #384 and reparent #383 and #384 under a bug epic to make the closure legal. That broadens a
narrow bug parent to buy one closure, which is exactly what the brief forbids and what the rubric means by an
umbrella contributing no duplicate effort.

Retaining costs nothing. #381 already carries zero implementation weight in WP-25 and already holds #383 and #384
as real sub-issues. The correction is a cross-link between the two parents, not a reparenting. Recorded as
closable later if the owner promotes Goal 3 to its own issue.

### 2. OD-1: pending verification is presented as pending

The proposal recommended storing `unknown` while displaying "degraded, verification pending". Rejected.

Verified at HEAD, `support_state.py:63-73`: two members, `BLESSED` and `DEGRADED`, with the docstring "A version
that has not been compared yet has no state at all, which is the absence of a `SupportVerdict` rather than a member
here", and "`degraded` carries this one meaning everywhere". The display is the only place an operator meets the
word. Storing one thing and showing another gives `degraded` a second meaning at exactly the surface the invariant
exists to protect, and it also produces a label that must later be retracted for every model that comes out
blessed.

Corrected recommendation: store no verdict until a comparator runs, and present an explicit verification phase with
a reason ("verification pending"). #633's actual outcome, that a first launch is never silently verdictless, is
satisfied by a pending phase, because a phase with a reason is a state. What survives as a genuine owner question
is the posture, whether the launch view treats pending as a caution or as neutral information. My recommendation is
neutral, since nothing is ever blocked and the comparison completes on that same launch.

### 3. Owner decisions cut from ten to three

Seven were ordinary engineering judgments and are resolved on the issues that own them:

| was | subject | resolution |
| --- | --- | --- |
| OD-3 | #597 as a dependency of #457 | sequencing on the claude arm only; recorded as #457 acceptance |
| OD-5 | #482 credential placement | auth home outside the disposable channel home, or detect and tell the operator |
| OD-6 | #446 fold harvest CLI or document | document the boundary; `baseline_publish` already calls `harvest_baseline`, so the fold removes no duplication |
| OD-7 | #596 literal tool count | assert the catalog invariant, let counts fall out |
| OD-8 | #603 attach window before #565 | gated; widening a window over a forgeable binding is a security regression |
| OD-9 | which issue is the lifecycle parent | dissolved by correction 1; cross-link, do not reparent |
| OD-10 | `certify --all` ownership | a new issue outside this snapshot; stays in `unresolved` |

Three genuine product-policy conflicts remain, each a case where two ratified positions disagree and engineering
cannot pick a winner without inventing a product decision:

- **OD-1** pending presentation (#633 vs #384 comment 3 and `support_state.py`).
- **OD-2** the entitlement gate (#632's 2026-09-05 comment reverses its body and the 2026-09-04 approved removal),
  plus the account identity that scopes it.
- **OD-3** #523's retained byte-splicing prohibition against #455/#457/#458's byte-diff acceptance.

### 4. WP-11 no longer hard-depends on WP-10

The proposal wrote `WP-11 -> WP-10` (that is, #457/#458 behind #597) while its own OD-3 said the constraint applies
to the claude arm only. The graph contradicted the prose. Dependency reduced to WP-08; the claude-arm constraint is
now an acceptance criterion on WP-11 and on #457: either #597 lands first, or the claude arm reports the
un-deferred MCP tool schemas inside its own token measurement and states the regression rather than hiding it. The
rank order is unchanged, so nothing is scheduled earlier than it was.

### 5. Line limits and record shape

`final-grooming.json` is 99 lines with one compact record per line, against the proposal's 1221. Schema is
unchanged except for an added `review` object recording these corrections and an `id` on each owner decision.

## Checked and left standing

- **#459 into #460.** Preconditions and the transfer list are correct and complete, and the closing comment already
  ends with "No implementation and no experiment result is declared complete by this closure." Kept verbatim.
- **#633 and `certify --all`.** WP-05 depends on WP-01 only; nothing sequences it behind a publication run. The
  missing-shape rule from #604 means first-turn-only references compare without refusing the shape they lack.
- **#384.** Correctly held as real work, not parent overhead. Its six unbuilt acceptance criteria (automatic
  overlay selection and application, provider-bound proof, inspectability, safe passthrough on drift and preimage
  failure, older-harness policy, the executing upgrade button) are preserved verbatim in the C4 draft, with only
  the genuinely resolved `maximum_version` blocker struck.
- **#573.** Item 3's shipped half is correctly attributed to #629 and the open half is correctly kept. The claim
  rests on source reading, and I confirmed the two facts it turns on: `prompt_delivery.py:128` is the only
  `tracker.track` call, and `startup_passes.py` registers `RECONCILIATION_LABEL` lifecycle reconciliation only. No
  restart was performed, so the runtime boundary stays declared, not proven.
- **#470/#632.** Provider is not an account. Kept, and promoted into OD-2 alongside the entitlement reversal.
- **#456 and PRs #463/#464.** Correctly described as open and unmerged with no closure credit. Their diffs were not
  reviewed here either, so the unknown stands.
- **Package structure.** 25 packages, 44 issue references, #611 deliberately in two (owner WP-07, prerequisite
  WP-17). No cycles, ranks contiguous, no package precedes a dependency, no double-counted effort: the four
  tracking parents sit together in WP-25 at zero weight and appear nowhere else.

## Uncertainty

- The #381 retention is a scope judgement about product coherence. If the owner reads Goal 3 as already dead, the
  proposal's closure becomes defensible and the open count drops to 41.
- OD-2's recommendation does not depend on measuring whether the refreshed codex catalog omits `gpt-5.2` for this
  account, but that measurement is still unmade. One read-only `codex debug models` settles it.
- Effort labels are estimates. No test suite, runtime launch, database read or provider probe was run in this
  review; the only new observations are two greps and one `git show --stat`, all read-only.
- Two audit agents never wrote their report files. Their corrections reached the proposal through transcripts, and
  I re-verified only the ones that changed a disposition here.

## Verification

`verify-final-grooming.py` extends `verify-proposal.py` with survivor/precondition consistency, ledger-to-candidate
agreement, rank contiguity, self-dependency, owner-decision identity and the brief's line limits. Result: PASS,
43/43 covered exactly once.
