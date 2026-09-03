# Portfolio reconciliation

Independent whole-backlog audit of the 43 open issues. Source SHA `53511834`. 18 comments read in
full. Five Luna auditors cover code-specific areas; this report covers reconciliation across the
whole set: ordering, duplication and nesting, contradictions, stale decisions, and the policy
questions nobody has ruled on.

Machine-readable companion: `portfolio.json` (43 issues, 11 packages, 10 decision conflicts).

---

## 1. Highest-value ordering

Two lines of work can start today in parallel and never touch each other.

| # | Package | Issues | Why here |
| --- | --- | --- | --- |
| 1 | Restore runnability | 631, 632, 470 | The stated product premise is broken in production right now |
| 2 | Orchestration observability | 574, 515, 573, 624, 555 | Fully independent, four of five are small, every one found by an agent hitting the wall |
| 3 | Override correctness | 592, 368, 611 | Independent; #592 is live corruption of the operator's own prompt |
| 4 | Every first launch has a state | 633, 477 | Completes package 1's premise; blocked on one ruling and one unticketed run |
| 5 | See the wire, take the token lever | 456, 457, 458, 460, 459 | Largest measured lever; #456 is startable now |
| 6 | Per-runtime authority | 595, 596, 597, 598, 599, 600 | Well planned, strictly ordered; also caps MCP token cost |
| 7 | Browser integrity, then ergonomics | 565, 603, 504 | #603's diagnosability half is immediate; the rest needs a trust model |
| 8 | Operator facts leave the disposable home | 472, 471, 482 | #482 is the most implementation-ready issue in the backlog |
| 9 | Certification hygiene and corpus | 446, 523, 383, 384, 381, 448 + parents | Enabling; pull the certify run forward |
| 10 | Recall that answers honestly | 498, 496 | Real value, large scope, no dependant. Split before scheduling |
| 11 | Deferred on a recorded trigger | 413, 602 (+504, 459) | The value is in not spending on them |

### Immediate independent slices

Each of these is landable now with no unresolved decision and no blocker:

**#456** read-only wire-class viewer · **#611** purpose fixtures · **#592** override anchors ·
**#515** `watch_status` · **#574** `pane` verb · **#624** error vocabulary · **#471** log
destination · **#472** toggle persistence · **#446** baseline CLI boundary · **#603's
diagnosability half** (named refusal reason, separate mint verb).

#456 is the single best first move outside package 1: read-only, runs on data already shipped, no
proxy changes, and it is the declared acceptance surface for every later overlay slice.

### Strategic sequence

Package 1 restores the premise. Package 4 completes it, but is gated on a ruling (DC-1) and on a
certify run that has no issue number — start the ruling immediately and open the run as an issue.
Packages 2 and 3 are free parallelism from day one. Package 5 waits on nothing except its own first
slice, and its later slices should be sequenced with package 6, because the two clusters interact in
a way neither issue records.

---

## 2. Strongest contradictions

Ten are recorded in `portfolio.json` under `decision_conflicts`. The five that change what gets
built:

### DC-1 · Provisional degraded versus "absence of evidence is not a verdict"

**#633** starts an uncovered model at `degraded / verification_pending` and keeps `degraded` for
missing references, failed capture, provider refusal and derivation failure.

**#384's ratified owner comment** (2026-08-20) says the opposite: when the comparator cannot run,
*the status does not change, and there is no new status for it. Absence of evidence is a trigger to
retry, not a verdict.* CLAUDE.md agrees on both counts: `SupportState` is *unknown before
comparison*, and `degraded` *means overlay fidelity is compromised. It carries that one meaning
everywhere.*

Writing `degraded` before any comparison asserts a fidelity fact no evidence supports, and #633
specifies no retraction path for a degraded row a later successful comparison should replace.
Leaving it unknown breaks Stuart's premise that a model is always blessed or degraded.

**Recommended reconciliation** (owner ruling required, do not implement either reading first):
separate the stored verdict from the presented posture, a distinction the codebase already makes
(state versus findings; `DriftOutcome` versus `SupportState`). Store `unknown` with phase
`verification_pending` or reason `no_compatible_reference`; project it as "degraded, verification
pending" in the launch view and #477's status bar. That gives #633 its outcome, keeps #384's rule,
preserves retry-on-absence, and needs no retraction path.

### DC-2 · An approved decision whose premise was later measured false

Chronology matters here.

- 2026-09-04, conversation msg 60: Stuart **APPROVE**s removing `account_entitlement_unavailable`
  from launch resolution, keeping it in certification and publishing. The stated premise: *the
  refreshed catalog is already account-aware, so entitlement filtering comes from the vendor.*
- #632's body is written to that approval.
- 2026-09-05, comments on **#632** and **#470**: *entitlement filtering does not arrive from the
  source.* Keep the read in launch resolution; move storage to the session store; #632 should
  depend on #470 rather than delete the read.

This is a re-decision, not a clarification: it deletes and retains the same code path. Two things
need saying before anyone implements it.

**The reversal's evidence does not actually falsify the premise.** The comment measures the
*bundled* catalog (`the bundled catalog enumerates gpt-5.2 with visibility: list`). The approval's
premise was about the *refreshed* catalog, which conversation msg 50 reported as **omitting**
gpt-5.2 for this account. No refreshed-catalog measurement of gpt-5.2 at 0.153.2 is recorded
anywhere. One command settles it: `codex debug models` on this account. Record the result on #470.

**The storage move is right regardless**, and for a reason the comment states well: a release cannot
know which account will run it, so an account fact in signed release data is wrong by construction.

**One correction to the comment.** It calls the retained exclusion *an enumerated block in the #384
sense*. #384's `blocked_versions` are publisher-declared release data with a `block_reason_code`;
an account entitlement is per-operator runtime evidence learned from a 400. Borrowing that name
imports authority from a mechanism it does not use. Call it a runtime provider-refusal exclusion.

### DC-3 · Account identity is not provider identity

**#470** says *the natural key is the provider account, not the executor id*, then specifies *keyed
by provider and model*. Provider is not an account. Under the stated key, switching from a
subscription to an API key, or two accounts on one machine, inherits a refusal that does not apply,
with no way to clear it. The issue's acceptance criteria do not cover an account change. Decide the
identity before implementing, and add the criterion.

### DC-6 · Two tool authorities that neither cluster knows about

**#455–458** control what the *harness* puts on the wire (builtin schemas, system prompt), declared
in agent-runtimes `[tools]`. **#593–600** control what *TM's MCP* exposes to the run, declared as
runtime MCP capabilities and filtered at `tools/list`. These are not duplicates — different
mechanism, different owner, different failure mode (fail-open byte splice versus authoritative
call-time authz). But there are two real couplings, recorded in neither cluster:

1. **They cancel out on claude.** #455's own measurement: `--tools ""` alone made the request
   *bigger* (123,737 versus 114,619 bytes), because `ToolSearch` and `DeferredToolPlaceholder` are
   themselves builtins, so disabling builtins un-defers all 86 MCP tool schemas. #457 shipped
   without #597 is a token regression on claude.
2. **Two things called "capabilities" in one `runtime.toml`.** #457 keys `[tools]` on capability
   names (`shell`, not `bash`); #596 defines capability identifiers for MCP tools. #597's guardrail
   already forbids inferring policy from names — it just does not know `[tools]` is coming.

One naming decision and one sequencing rule (#597 with or before #457's claude arm), recorded on
#455 and #593.

### DC-5 · Byte splicing: two open issues hold opposite rulings

**#455/#457**: *application is byte splicing, never decode-and-reserialize*, because every writer in
the codebase sorts keys. **#523 retained decisions**: *Do not introduce a byte splicer.* #457 cannot
meet its own byte-diff acceptance criterion without the mechanism #523 forbids. #523's ruling
predates #455's measurement and its own body has since cancelled the raw executor that motivated it.
Rule for #455 and strike the line, or state the exception. Owner decision.

---

## 3. Stale decisions overtaken by shipped code

### #384's `maximum_version` blocker is resolved

The comment files it as a blocker: *`maximum_version` means the opposite of blessed MAX ... Above
MAX refuses to launch today.* Verified at `53511834`, all three parts of the proposed resolution are
implemented:

- `compatibility.py:565` `blessed_ceiling()` returns `maximum_version or baseline_version`
- `compatibility.py:581` `range_position()` is the comparator trigger
- `compatibility.py:686` `harness_version_blocked` is now raised **only** by an enumerated
  `blocked_versions` entry of scope `version` — the one-concept-per-mechanism split the comment asked
  for

The comment's live release table is also stale. Current manifest: `claude-2.1.250-r2` (max 2.1.250),
`codex-0.149.1-r2` (max 0.150.1), `grok-1.0.5-r2` (max 1.0.5) — not the "no ceiling at all" state
described. Installed codex 0.153.2 and claude 2.1.261 are both **above ceiling today**, so the
comparator path is hot, which is exactly why #633 matters now.

What still stands: `COMPATIBILITY_ROLLOUT = "advisory"` (`compatibility_service.py:101`), so
below-MIN does not block, as comment 3 ratified.

**#384 also contradicts itself**: comment 1 says below-MIN blocking is already shipped; comment 3
corrects it to not shipped and rules no change. A reader stopping at comment 1 gets the opposite
answer.

### #573's third scope item shipped six hours before the snapshot

HEAD `53511834` is `fix(delivery): reconcile prompts without active waiters (#629)`, adding
`delivery_resident.py` (213 lines) and `delivery_events.py` and moving reconciliation off
`DeliveryWaiter`. That is #573's item 3 ("lazy correlation"), done.

Items 1 and 2 are untouched: `delivery_binding.py:33-47` still writes **one** binding object per run
and overwrites unconditionally, and no merged-queue matching exists. Strike item 3, and **raise the
priority** — the reconcile-on-wait behaviour was the accidental mitigation, and a stranded row is
now a row that will never correlate rather than one waiting on a `wait_for_reply`.

### #368's mechanism is stale, its outcome is not

#368 predates both the request-purpose classifier (#557 / PR #559, now guarded by #611) and #592.
Its "detection ships as data, not code" ruling would build a second detector for a question #611's
classifier answers, and its second stated harm — a positional edit authored on an aux shape
clobbering the main turn — is #592's defect class and is fixed there for *every* shape, not just aux.
Rewrite #368 as a consumer of the existing classification at the breakpoint pause branch, keep its
acceptance criteria verbatim, cite the clobber to #592.

---

## 4. Duplicates, subsets, parents

**No pair in this backlog is a duplicate outcome.** Shared code was not treated as duplication
(#470 and #632 both touch `resolver_snapshots.py`; #574 and #616 share one snapshot capture).

**The one merge:** #459 into #460. #459 is self-declared *back pocket, not scheduled*, and its entire
"open work before this is more than a note" section is #460's scope. Its just-bash benchmark table
and codex transplant checklist must survive verbatim as #460's reference section — that table is
currently duplicated across #455, #459 and #460.

**Correct subsets, keep separate:** #611 out of #523 (explicitly split, sequenced ahead);
#477's advisory half into #632 (they overlap on the same rejection path, and #632 deletes a code
#477 is built on); #496 as a two-part split with only part 1 ready.

**Parents carrying zero implementation weight:** #630, #381, #455, #593 — and #384 in practice.
Counting them as work overstates the backlog by roughly 12%.

**Two structural gaps:**

1. **#455's children are prose-only.** `manifest.json` shows `sub_issues: []` for #455, while #456,
   #457, #458, #459 and #460 each declare `Parent: #455` in text. Create the real links so the epic
   stops reading as work.
2. **The lifecycle has two parents.** #384 (release compatibility lifecycle) and #630 (discovery and
   first-launch verdict) both own it, and #630 is not linked under #381/#384. Recommend #630 becomes
   the live parent; #384's lifecycle table moves to `docs/HARNESS-COMPATIBILITY.md`, leaving #384
   holding only the older-harness support policy and the upgrade button.

**Unticketed work blocking two packages:** the `certify --all` publication run. Verified at
`53511834`: the shipped manifest carries **26 references, all `first-turn`, zero `envelope_schema`**.
#633's two-shape acceptance and #523 items 2–4 both depend on it. Open it, and sequence #446's
boundary decision immediately before it so an operator has one entry point during the run.

---

## 5. Priority: original versus recommended

| Issue | Original | Recommended | Reason |
| --- | --- | --- | --- |
| 633 | P2 | **P1** | Without it, #631/#632 make astra discoverable and verdictless — the exact gap Stuart named |
| 470 | unlabelled bug | **P1** | Promoted onto the critical path by #632's comment; it now owns the storage move #632 depends on |
| 624 | P3 | **P2** | Agent orchestration is the primary usage mode; three conditions collapse onto `invalid_request` |
| 573 | P5 | **P3** | Half shipped; the remaining half is the actual stranding cause and its mitigation is gone |
| 592 | unlabelled | **P2** | Live corruption: the operator's own prompt replaced by prior instruction text |
| 456, 457 | unlabelled | **P2** | Largest measured lever; tools are 91% of addressable mass on an Opus baseline |
| 574, 565, 611 | unlabelled | **P2** | Release-day blindness; the last open integrity boundary; the cheapest durable guard |
| 603 | P1 | **P2** | Diagnosability half is P1-cheap; the window change is gated on #565 (DC-4) |
| 598, 599, 600 | P2 | **P3** | Unstartable until their blockers land; #599/#600 reference artifacts that do not exist |
| 504, 413, 602, 459 | unlabelled | **P5** | Trigger-gated, owner-deferred, undecided, or merged |

Full per-issue dispositions, evidence, dependencies and confidence: `portfolio.json`.

---

## 6. Verification boundaries

Findings are from source at `53511834` and the supplied corpus. No runtime, database or provider
probe was run. GitHub state beyond `manifest.json` (#385, #386, #398, #557, PR #559, PR #564) was not
independently fetched. The 34-tool count was corroborated by decorator counts across three modules
(8 + 13 + 13), not by executing `tools/list`.

**Unknowns left open, deliberately:** whether `codex debug models` lists gpt-5.2 on this account at
0.153.2 (settles DC-2); whether any test exercises a conversation long enough for `feed` and
`summary` to differ (#496); how grok-4.5 reports its model id (#555); whether a provider accepts a
`tool_use` for an undeclared tool (#455, #459).

---

## Completion

Assigned issues: **43**. Reported: **43**, each exactly once. Comments read: **18**.
Source SHA: **53511834**. Git evidence: HEAD commit `53511834` (#629) diffstat and full body.

Source files checked: `probes/codex.py`, `harnesses/resolver.py`, `resolver_snapshots.py`,
`resolver_contracts.py`, `launch_target.py`, `harnesses/compatibility.py`, `compatibility_service.py`,
`compatibility_store.py`, `compatibility_releases_v1.json`, `support_verdict_store.py`,
`launch_verification.py`, `launch_verification_support.py`, `baseline_store.py`, `baseline_publish.py`,
`baseline_publish_plan.py`, `baseline_attempts.py`, `cli/baseline_cmd.py`, `cli/home_constants.py`,
`model_ids.py`, `controlplane/roster_projection.py`, `controlplane/delivery_binding.py`,
`controlplane/delivery_wait.py`, `api/v1/controlplane_gateway_reads.py`, `api/v1/controlplane_mcp.py`,
`api/v1/space_mcp.py`, `api/v1/browsing_mcp.py`, `session/session_statements.py`, `addon_handlers.py`,
`overrides/`, `packages/activity/src/projections/conversation.ts`,
`packages/browsing/src/server/browsingRouter.ts`, `www/packages/canvas/src/model/capturedRunStore.ts`,
`docs/HARNESS-COMPATIBILITY.md`.
