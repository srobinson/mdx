# Proposed grooming: final synthesis

Snapshot `535118346ca5d0584a7a4a3da28a55be532dc3bd`. 43 open issues, 18 comments. Verified against GitHub at synthesis time:
all 43 are still open, no new issues appeared, and PRs #463 and #464 are still open and unmerged.

Machine-readable companion: `proposed-grooming.json`. Local edit drafts: `github-edit-drafts.md`.
Coverage check: `python3 verify-proposal.py` (43/43 issues once, every package reference and dependency resolves, no cycles).

---

## 1. What actually closes

One unconditional closure survives the evidence. The consolidation auditor found the same one, and I did not find a second
that holds up. Everything else that looks like a duplicate is either a parent with pending children or two issues sharing a
code path, and shared code is not a duplicate outcome.

### Closure 1, unconditional: #459 into #460

| | |
| --- | --- |
| Closes | #459 Research: portable exec kernel as a standard builtin surface |
| Survivor | **#460** Experiment: just-agent, one bash tool, our system prompt, A/B |
| Why | #459's own header says *Back pocket, not scheduled*, its comment points at #460, and every item under *Open work before this is more than a note* is #460's measurement plan. |
| Nothing shipped | The survivor still owes the just-bash MCP server and the A/B run. This closure declares no result. |

Acceptance that must move first (drafted in `github-edit-drafts.md`):

- The just-bash benchmark table and its reproduction script, including that sed, find, grep and wc matched native output while rg was the outlier.
- The codex execution-kernel checklist: sandbox and approval policy, known cwd and explicit workdir, shell and PATH guarantees, process lifecycle, output limits and truncation, structured patching, safety enforcement below the model, verification guidance.
- The isolation tradeoffs: OverlayFs, ReadWriteFs cost, Vercel Sandbox, and the absence of process lifecycle and hard VM isolation in just-bash.
- The open questions: whether a provider accepts a tool_use for an undeclared tool, and whether a companion mechanism is needed for PTY or long-running work.
- The decision not to document rg in the kernel contract until the implementation gap is resolved.

The benchmark table is currently duplicated across #455, #459 and #460. After the transfer it lives once, on #460.

### Closure 2, conditional on an owner ruling: #381 into #630

#381's three implementation children (#370, #382, #392) are closed; its two open children are #383 and #384, both tracked
elsewhere. It is a wrapper with one unique line left. It is **not** completed and must not be closed as though it were.
The restructure is: reparent #383 and #384 under #630, move the power-user overlay deferral onto #384, then close #381.
Owner decision **OD-9** rules on it. Until then #381 stays open.

### Scope subtractions: the other half of consolidation

These remove real work from the backlog without closing an issue. They matter more than a closure count.

| Issue | Struck | Evidence |
| --- | --- | --- |
| #384 | The `maximum_version` blocker and the settled lifecycle table | `blessed_ceiling()` `compatibility.py:565`, `range_position()` `:581`, `harness_version_blocked` `:686` are all shipped; the doctrine belongs in `docs/HARNESS-COMPATIBILITY.md` |
| #573 | Item 3's in-process half only | HEAD `53511834` is #629; `delivery_resident.py` gives evidence-driven reconciliation. Its `track()` runs only at delivery creation, so the restart clause **stays** |
| #477 | *Every resolver rejection becomes advisory* | Conflicts with #470's sanctioned exclusion and with enablement and infrastructure gates |
| #632 | The entitlement-removal bullet | Replaced per its own 2026-09-05 comment: keep the read, move the storage |
| #368 | *Detection ships as data, not code*, and the clobber half | #611 already pins the classifier; #592 fixes the clobber for every shape |
| #599 | The transport-setting relocation | #600 assigns itself exactly the same work |
| #598 | The hard #597 dependency | The consent UI does not consume the filtered catalog |
| #470 | *An enumerated block in the #384 sense* | #384 blocks are publisher-declared release data with a `block_reason_code`; this is per-operator runtime evidence from a 400 |

Net: 43 open today. 42 after closure 1. 41 if OD-9 rules for the restructure. Plus eight scope subtractions and
four parents that stop counting as work.

---

## 2. Four portfolio conclusions I do not adopt

**#633 does not wait for a new `certify --all` run.** The portfolio lists the publication as a blocking dependency of
PKG-2. #633's own cost table says otherwise: *Today's codex release carries first turn references only, so astra costs 3*.
`CLAUDE.md` states the rule #604 set, that the gate compares what a release carries without refusing the shape it lacks.
The run improves coverage; it does not unlock the first-turn path. WP-05 is sequenced behind WP-01 only.

**#384 is not zero implementation.** No `overlays` package exists at this SHA; `overrides/` is the operator-authored path
and `cli/home_overlay.py` is filesystem seeding. Six of #384's seven acceptance criteria are overlay application and
degradation behaviour, not doctrine. Calling it a parent that carries no weight would delete the unbuilt half of Autopilot.
It is WP-18, effort L.

**#457 does not strictly depend on #597.** The codex and grok arms are independent. The coupling is real but narrow and
one-directional: on claude, disabling builtins un-defers the MCP tool schemas, so #457 alone is a measured regression there
(123,737 versus 114,619 bytes). That is shared sequencing for one arm, ruled in OD-3.

**Projecting unknown as degraded is not automatically safe.** The portfolio's own recommendation is the right one, but the
distinction has to be kept where the codebase already keeps it. `SupportState` carries one meaning for `degraded`
everywhere, including an unsupported old version. Store `unknown` with a verification phase; present *degraded, verification
pending*. Writing `degraded` to the store before a comparator has run asserts a fidelity fact no evidence supports and needs
a retraction path #633 does not specify. OD-1.

---

## 3. The backlog, in order

Ranked by concrete harm to the core promise first, then breadth, then work unlocked, then cost. Effort is S/M/L estimate,
not duration. Parents carry no effort. Full acceptance per package is in `proposed-grooming.json`.

| # | Package | Issues | Effort | Depends on |
| ---: | --- | --- | :---: | --- |
| 1 | **WP-01** Restore runnability: discover, resolve and remember | #631, #632, #470 | L | - |
| 2 | **WP-02** Overrides apply to the block they were authored on | #592 | M | - |
| 3 | **WP-03** Orchestration a director can see and branch on | #574, #515, #624 | M | - |
| 4 | **WP-04** A queued nudge correlates, and survives a restart | #573 | M | - |
| 5 | **WP-05** Every first launch has a state | #633 | L | WP-01 |
| 6 | **WP-06** The verdict reaches the run | #477 | M | WP-01, WP-05 |
| 7 | **WP-07** Purpose classification has a source of truth, and the breakpoint uses it | #611, #368 | S | WP-02 |
| 8 | **WP-08** See exactly what each harness puts on the wire | #456 | M | - |
| 9 | **WP-09** Effective authority and a catalog that cannot drift | #595, #596 | M | - |
| 10 | **WP-10** A run discovers only the tools its policy permits | #597 | M | WP-09 |
| 11 | **WP-11** Take the token lever: declared tool surface and regenerated prose | #457, #458 | L | WP-08, WP-10 |
| 12 | **WP-12** Operator facts stop dying with the home | #472, #471 | S | - |
| 13 | **WP-13** Log a harness in from inside the app | #482 | L | WP-12 |
| 14 | **WP-14** Only a genuine presenter wins, and a refusal says why | #565, #603 | L | - |
| 15 | **WP-15** Canvas shows the authority a run will actually get | #598 | M | WP-09, WP-12 |
| 16 | **WP-16** Current protocol, one transport owner, proven against real clients | #599, #600 | L | WP-10 |
| 17 | **WP-17** One publishing entry point and a corpus that can be audited | #446, #523, #611 | L | WP-07 |
| 18 | **WP-18** The owned overlay actually applies, and old harnesses have a policy | #384 | L | WP-01, WP-05 |
| 19 | **WP-19** Explain the first request to a new operator | #383 | M | WP-08 |
| 20 | **WP-20** Compatibility updates arrive signed | #448 | L | WP-17 |
| 21 | **WP-21** Recall answers, or says what it searched | #498, #496 | L | - |
| 22 | **WP-22** A model id the roster can look up | #555 | S | - |
| 23 | **WP-23** Does a small owned surface do the work | #460, #459 | M | WP-08 |
| 24 | **WP-24** Deferred on a recorded trigger | #413, #602, #504 | S | - |
| 25 | **WP-25** Tracking parents carry no implementation weight | #630, #381, #455, #593 | S | - |

### Start now, in parallel, nothing blocking

**WP-01** (#631, #632, #470), **WP-02** (#592), **WP-03** (#574, #515, #624), **WP-04** (#573), **WP-08** (#456),
**WP-09** (#595, #596), **WP-12** (#472, #471), **WP-14**'s #603 diagnosability half.

If only one thing starts: **WP-01**. The product promise is that a model released today stays runnable, and it is broken
in production now. If a second track runs beside it, **WP-02**: an operator's own prompt is being replaced by prior
instruction text on Codex continuations, and it touches nothing WP-01 touches.

### Why each package sits where it does

**WP-01 · Restore runnability: discover, resolve and remember** — The central product promise is broken in production now: gpt-6-astra and gpt-5.3-codex-spark are undiscoverable and a version bump withdraws offered targets. Everything else in the compatibility area is worth less until this holds.

**WP-02 · Overrides apply to the block they were authored on** — Live corruption of the operator's own prompt on Codex continuation requests, independent of every compatibility change, and small enough to land beside WP-01.

**WP-03 · Orchestration a director can see and branch on** — Three small independent fixes, each found by an agent hitting the wall during this very audit. Free parallelism from day one and no unresolved decision.

**WP-04 · A queued nudge correlates, and survives a restart** — #629 removed the accidental mitigation: a stranded row used to correlate on the next wait, and now a row nobody waits on and no in-process tracker holds will never correlate.

**WP-05 · Every first launch has a state** — Completes WP-01's premise. Without it, WP-01 makes astra discoverable and verdictless, which is the exact gap named. It is startable against today's first-turn-only references and does not wait on a new publication run.

**WP-06 · The verdict reaches the run** — The only surface where blessed, degraded or pending reaches a human. Cheap once WP-05 has defined the matrix, and meaningless before it.

**WP-07 · Purpose classification has a source of truth, and the breakpoint uses it** — #611 is the cheapest durable guard in the backlog and #368 stops being a second detector once it consumes the existing classifier. #368's dangerous half is removed by WP-02.

**WP-08 · See exactly what each harness puts on the wire** — The declared acceptance surface for every later overlay slice, read-only, and running on data already shipped. Two open PRs already carry part of it.

**WP-09 · Effective authority and a catalog that cannot drift** — The current runtime request is transported but does not constrain the grant actually minted, so both overgrant and undergrant are reachable today. Both slices are independent of each other and of WP-01.

**WP-10 · A run discovers only the tools its policy permits** — Caps MCP token cost per run and is the prerequisite that makes WP-11's claude arm a reduction rather than a regression.

**WP-11 · Take the token lever: declared tool surface and regenerated prose** — The largest measured lever in the backlog, and it becomes measurable only once WP-08 can show the diff and WP-10 has bounded the MCP catalog on claude.

**WP-12 · Operator facts stop dying with the home** — Two small independent fixes; #472 must precede #598's consent persistence claim.

**WP-13 · Log a harness in from inside the app** — The most implementation-ready issue in the backlog with an approved six-slice plan, and first-run blocking for a new operator.

**WP-14 · Only a genuine presenter wins, and a refusal says why** — The last open integrity boundary on the browser surface. #603's diagnosability half is cheap and ships first; the window relaxation waits on the binding.

**WP-15 · Canvas shows the authority a run will actually get** — Completes the authority program's user-facing half once the resolver exists; the #597 dependency is sequencing only.

**WP-16 · Current protocol, one transport owner, proven against real clients** — Infrastructure that is not a prerequisite for authority correctness; scheduled after the filter so the port carries the final adapter shape.

**WP-17 · One publishing entry point and a corpus that can be audited** — Enabling work. #446 is a small decision that should be recorded before the next publication run; #523's later items improve as reference coverage grows.

**WP-18 · The owned overlay actually applies, and old harnesses have a policy** — This is the unbuilt half of the Autopilot promise and it is not doctrine. No overlays package exists at this SHA; the settled lifecycle rules move to docs so the issue holds only the work.

**WP-19 · Explain the first request to a new operator** — First-turn education is the remaining child of the Autopilot umbrella and reuses the projection WP-08 builds.

**WP-20 · Compatibility updates arrive signed** — Strategic supply-chain work with a real fail-closed requirement. Deferred behind the certification boundary and an owner decision on the trust root.

**WP-21 · Recall answers, or says what it searched** — Real value with no dependant. Both issues must be split before scheduling; only #496 part 1 and #498 item 1 are ready as written.

**WP-22 · A model id the roster can look up** — Small and self-contained; low urgency because no operator action currently depends on it and grok-4.5 behaviour is unverified.

**WP-23 · Does a small owned surface do the work** — Investment experiment, not a defect. It decides which controls #457 needs, so it is worth running once the wire viewer can measure the arms.

**WP-24 · Deferred on a recorded trigger** — The value is in not spending on them now. They are listed so the deferral is a decision rather than a gap.

**WP-25 · Tracking parents carry no implementation weight** — Counting these as work overstates the backlog. #455's children are prose-only today and #383/#384 have two competing parents.

---

## 4. Owner decisions

Ten. The first two block implementation; the rest change scope or sequence.

### OD-1 · Does an uncovered model store degraded before any comparison runs, or store unknown with a verification phase and present it as degraded pending?

Affects #633, #384, #477, #630.

**Recommendation.** Store unknown with an explicit verification phase and reason; project it as 'degraded, verification pending' in the launch view and the run status bar. This gives #633 its 'never verdictless' outcome, keeps #384's ratified rule that absence of evidence is a retry trigger, keeps CLAUDE.md's single meaning for degraded, and needs no retraction path when the comparison later completes. Do not write degraded as a stored fidelity fact before a comparator has run.

- issue-633.md: 'An uncovered model begins at degraded with reason verification_pending'
- issue-384.md comment 3: comparator failure leaves the status unchanged; absence of evidence is a trigger to retry, not a verdict
- CLAUDE.md: SupportState is unknown before comparison, and degraded means overlay fidelity is compromised, carrying that one meaning everywhere
- catalog.md: support_state.py:63-73 has only blessed and degraded, with no state before comparison
- portfolio.md DC-1 recommends the same separation of stored verdict from presented posture

### OD-2 · What identity key scopes a runtime provider-refusal exclusion?

Affects #470, #632.

**Recommendation.** Key it on a provider account identity derived from the credential or route in use, not on provider+model alone and not on the executor id. If no stable account identity is available, record explicitly in #470 that switching accounts requires an operator clear, and add that as an acceptance criterion. Provider+model alone leaks one account's 400 onto another account on the same machine.

- issue-470.md: 'the natural key is the provider account, not the executor id' followed by 'keyed by provider and model'
- portfolio.md DC-3
- catalog.md: 'Provider plus model alone is unsafe if two provider accounts share a machine; executor id alone loses the intended cross-home survival'

### OD-3 · Is #597 a hard dependency of #457, or shared sequencing?

Affects #457, #597, #455, #593, #596.

**Recommendation.** Shared sequencing, with one hard constraint. #457's codex and grok arms are independent of #597. On claude, disabling builtins un-defers the MCP tool schemas, so #457 shipped alone is a measured token regression there. Either land #597 before #457's claude arm, or land #457's claude arm with the un-deferred schemas explicitly measured and stated. Also settle the two meanings of 'capability' in runtime.toml before either lands.

- portfolio.md DC-6: --tools "" alone made the claude request bigger, 123,737 vs 114,619 bytes, because ToolSearch and DeferredToolPlaceholder are themselves builtins
- portfolio.md DC-6: #457 keys [tools] on capability names while #596 defines capability identifiers for MCP tools
- authority.md: #597 filters tools/list from the frozen capability tuple

### OD-4 · Byte splicing: #455/#457 require it, #523's retained decisions forbid it.

Affects #455, #457, #458, #523.

**Recommendation.** Rule for #455/#457 and strike or qualify #523's line. #457 cannot meet its own byte-diff acceptance without the mechanism, #523's ruling predates #455's measurement, and #523's own body has since cancelled the raw executor that motivated it. If the ban stands instead, #457 and #458 need new acceptance criteria before they are scheduled.

- portfolio.md DC-5
- CLAUDE.md: prepare_outbound_request already returns the original IR and original bytes on any serialization failure, so an unchanged request keeps its original bytes today

### OD-5 · Where do harness credentials live so a channel home wipe does not invalidate a login?

Affects #482, #472, #470.

**Recommendation.** Place the harness auth home outside the disposable channel home, or surface the invalidation to the operator on the next launch. #482 currently assumes the credential predicate is the verdict without saying what happens when the home that holds it is wiped, which is the same failure class as #470 and #472.

- recovered runtime msg5: current readiness deliberately leaves credential minting in the launch attempt
- issue-470.md: 'Most of the home regenerates for free' - credentials are the counterexample alongside entitlement exclusions

### OD-6 · #446: fold the harvest CLI into publish, or document the boundary?

Affects #446, #523.

**Recommendation.** Document the boundary (the issue's option 2). The implementation duplication the fold would remove is already absent: baseline_publish imports harvest_baseline and passes each planned cell to it. Folding adds migration risk for no DRY gain. Portfolio recommends option 1; this recommendation is the cheaper of two defensible answers and the decision is the deliverable either way.

- catalog.md: baseline_publish.py:16-18 already imports harvest_baseline
- catalog.md: 'Folding the CLI would add risk without removing the shared implementation duplication, which is already absent'
- portfolio.md PKG-10 acceptance recommends option 1

### OD-7 · Should #596 assert a literal tool count?

Affects #596, #597.

**Recommendation.** No. Assert the catalog invariant (every registered tool appears exactly once, in order, with one capability and one minimum grant) and let the count fall out. A number in prose goes stale on the next tool.

- portfolio.md DC-9
- authority.md: 13 + 13 + 8 decorators counted at this SHA, not executed

### OD-8 · Can the CDP attach window be relaxed before presenter registration is authenticated?

Affects #603, #565.

**Recommendation.** No. Ship #603's diagnosability half now (named refusal cause, separate mint verb) and gate the window relaxation on #565, because the relaxation rests on a binding #565 says is forgeable by any same-host process.

- portfolio.md DC-4
- recovered runtime msg4: the registration endpoint is loopback only, yet reachable by any same-host process without authentication

### OD-9 · Which issue is the live lifecycle parent, #384 or #630?

Affects #381, #384, #630, #383.

**Recommendation.** #630. Reparent #383 and #384 under it, leave #384 holding the owned-overlay application work, the older-harness policy and the upgrade button, and move the settled lifecycle table to docs/HARNESS-COMPATIBILITY.md. #381 then becomes closable as a superseded umbrella. Do not close #381 before the reparenting lands.

- portfolio.md s4: 'the lifecycle has two parents'
- manifest.json: #630's children are #631/#632/#633; #381's are #383/#384 with three closed
- consolidation.md advises retaining both parents for now, so this is a change from that recommendation and needs an owner ruling

### OD-10 · Who owns and when does the certify --all publication run happen?

Affects #523, #633, #446.

**Recommendation.** Open it as its own issue and schedule it after WP-17's #446 boundary decision so an operator has one entry point during the run. It is coverage improvement, not a blocker: #633 states first-turn capture costs 3 requests per model against today's references, and the gate compares what a release carries without refusing the shape it lacks. Do not sequence WP-05 behind it.

- issue-633.md: 'Today's codex release carries first turn references only, so astra costs 3 and spark costs 3'
- CLAUDE.md: a release published before the dimension existed carries first-turn references only, and the launch gate compares what that release carries without refusing the shape it lacks
- recovered autopilot msg7: 26 embedded reference cells, all first-turn, zero envelope
- recovered reconciliation-check msg4: the stronger dependency claim needs narrowing

---

## 5. Disposition ledger, all 43

Every open issue exactly once. `survivor` names where the work lives after grooming; it equals the issue itself unless
the issue merges or restructures away.

| Issue | Action | Survivor | Package | Conf | Remaining scope |
| --- | --- | :---: | :---: | :---: | --- |
| **#368** | keep, rewrite | - | WP-07 | high | Rewrite as a CONSUMER of the existing request-purpose classification at the breakpoint pause branch. Keep the acceptance verbatim (aux turn and quota probe cross un-paused, user turn pauses, passthrough recorded not silent, pinning test from run 163c35b4). Drop the 'detection ships as data, not code' ruling and cite #592 for the clobber half. |
| **#381** | umbrella, restructure | #630 | WP-25 | medium | Tracking only, zero implementation. CONDITIONAL closure: recommend closing as a superseded umbrella once #383 and #384 are reparented under #630 and its one unique line (power-user overlay editing and version management are future work) is transferred to #384. It stays OPEN until those preconditions are met; the survivor named here is where its tracking role goes, not a statement that it is already closed. |
| **#383** | keep | - | WP-19 | high | Optional, skippable, reopenable first-turn HTML report: role and provenance totals, per-leaf pointers and digests, observed facts separated from inferred classifications. Shares the request projection with #456 but is a different audience and surface. |
| **#384** | keep, rewrite | - | WP-18 | high | NOT zero work. Retains: automatic selection and application of the TM-owned overlay for a certified release, provider-bound capture proving the transformation, inspectability of original/overlay/bound request/audit/response, safe passthrough on drift or preimage failure, the older-harness support policy decided and tested at its boundary, and the upgrade button. STRIKE the resolved maximum_version blocker and correct comment 1's below-MIN claim. MOVE the settled lifecycle table to docs/HARNESS-COMPATIBILITY.md. |
| **#413** | defer | - | WP-24 | medium | Deferred by owner decision with a recorded trigger. The real question is the specialist Codex skills/ write-through asymmetry and a stated rule per family, not a generic name-set cleanup. |
| **#446** | keep, rewrite | - | WP-17 | high | One recorded boundary decision plus help text. Recommend the issue's option 2 (document harvest as debug-only single-cell evidence that never changes a release, publish is the normal workflow) over folding the CLI. |
| **#448** | defer | - | WP-20 | medium | Signed retrieval, real SignatureVerifier with key distribution and rotation, staged rollout through channel_states, remote kill switch over blocked_versions, two distinct nudges. Deferred behind the certification boundary work; trigger is a decided trust root. |
| **#455** | umbrella | - | WP-25 | high | Tracking only. Zero implementation. Create the real sub-issue links to #456, #457, #458, #460 (currently prose-only) and preserve its measured token and mechanism record. |
| **#456** | keep | - | WP-08 | high | Read-only wire-class viewer with region breakdowns, per-tool costs, addressable targets. Strongest independent slice. PRs #463 and #464 are OPEN and unmerged: partial in-flight work, no closure credit. |
| **#457** | keep | - | WP-11 | medium | Harness builtin subtraction driven by a capability library and agent-runtimes [tools], byte-diffed and token-measured per harness. Sequencing constraint on the claude arm only (see OD-3), not a strict dependency for codex and grok. |
| **#458** | keep | - | WP-11 | high | Regenerate the prose that teaches tools after a tool decision, verified on the wire, platform-aware for at least two profiles, with forward-original-bytes on a mismatch. Distinct correctness requirement from tool subtraction. |
| **#459** | close, merge | #460 | WP-23 | high | No standalone work survives. The just-bash benchmark table, the codex execution-kernel checklist, the isolation/process-lifecycle gaps and the open questions transfer into #460 as a reference section before closing. |
| **#460** | keep | - | WP-23 | high | Survivor of #459. Build the just-bash MCP server and run the unattended same-task A/B on a frontier model, measuring request bytes and end-to-end tokens separately, with failures classified and the result reported whichever way it falls. Absorbs #459's research record. |
| **#470** | keep, rewrite | - | WP-01 | high | Move provider-refusal evidence to the session store with an atomic upsert and a resolver read path; prove survival of a home wipe. REWRITE two things: define the account identity key explicitly, and rename the retained exclusion a runtime provider-refusal exclusion rather than 'an enumerated block in the #384 sense'. |
| **#471** | keep | - | WP-12 | high | Env-configurable log destination that can live outside the channel home, a readable log file for foreground runs, and tail resolving the same configured path with an unchanged default. |
| **#472** | keep | - | WP-12 | high | Canvas launch toggles survive a channel home wipe. Precedes #598's consent persistence claim. |
| **#477** | keep, reduce scope | - | WP-06 | high | Per-run status bar carrying range position, verification phase/state and advisories into the activity projection. STRIKE the blanket 'every resolver rejection becomes advisory' clause; it conflicts with #470's sanctioned exclusion and with enablement/infrastructure gates. |
| **#482** | keep | - | WP-13 | high | All six approved slices with their verbatim gates: exit is the trigger and the credential predicate is the verdict; harness-keyed public identity with start-twice rejoining; no home path, argv, env or PTY types on any public surface. Reconcile credential placement against the disposable-home risk. |
| **#496** | keep, split | - | WP-21 | high | Split at two outcomes: part 1 (summary selection counts turns not messages, elision reported) is ready now; part 2 (tool-parts projection with include:[], per-part truncation budgets and cursor contiguity) needs a design pass first. |
| **#498** | keep, split | - | WP-21 | high | Split at four independently deliverable outcomes: (1) fix the search_text writer and backfill, or report coverage; (2) GET /v1/sessions/search over content_tsv with ts_headline snippets; (3) explicit scope in every list response plus harness/provider/session filters; (4) a separate investigation into why the #492/#493/#495 implementation sessions were never captured. |
| **#504** | defer | - | WP-24 | high | Deferred until a second presenter exists. Trigger recorded: when a second presenter appears, the Gateway owns entries[] and index, can_go_back/can_go_forward are derived, and the pushState question is answered. |
| **#515** | keep | - | WP-03 | high | watch_status() over every subscription the run holds and watch_status(target) for one, each carrying target, events, registered_at, last_event_at, deliveries, target_state and shadowed_by, with empty distinguishable from error. Additive read over existing state. |
| **#523** | umbrella | - | WP-17 | high | Request class vocabulary, native-control matrix per harness, runtime-overlay and interactive-direction profiles, public corpus export. #611 already split out. Items 2-4 improve when the release carries both shapes but do not require it to start. |
| **#555** | keep | - | WP-22 | medium | Normalize the grok observed_model suffix so the roster reports a model id a harness can answer for, keep the raw response value on the event, and pin declared-to-observed resolution per harness with a regression. grok-4.5 behaviour unverified. |
| **#565** | keep | - | WP-14 | high | Authenticate Canvas presenter registration and bind it to a genuine Electron instance: a rogue loopback process registering first cannot become the selected composited presenter or publish a devtools origin under a genuine identity. |
| **#573** | keep, reduce scope | - | WP-04 | high | Items 1 and 2 stand in full: LivePromptDeliveryBindings must hold every pending binding claimed by its own digest, and a Codex merged user message must match a delivery whose prompt text is one line of it with the per-delivery outcome ruled. Item 3 is PARTIALLY shipped: #629 gives evidence-driven reconciliation for deliveries created in this process. The startup/restart sweep clause REMAINS OPEN and must be restated, not struck. |
| **#574** | keep | - | WP-03 | high | pane(run_id, max_chars?) returning the snapshot under the server cap, satisfied by an observer grant, resolving the gateway that actually owns the terminal, with the post-exit read decision recorded. |
| **#592** | keep | - | WP-02 | high | Content-anchored overrides: anchor required for the four positional kinds and rejected at the store boundary without one, resolution by anchor with index as hint, a miss producing applied:false with reason anchor_miss and rewriting nothing. |
| **#593** | umbrella | - | WP-25 | high | Tracking only. Zero implementation. Acceptance aggregation across #595-#600. #2 and #594 shipped (PR #615 / 0ee82d2b) but do not complete the program. |
| **#595** | keep | - | WP-09 | high | One pure resolver over requested / limiting / override / effective, omitted distinguished from explicit none, the frozen decision persisted and used for identity, bearer minting and home seeding. |
| **#596** | keep | - | WP-09 | high | A validated ordered catalog of the current tool set with one capability and one minimum grant per entry, encoding the 14 observer / 20 director split, validated before first registration, with registrar-drift tests. No behaviour change. |
| **#597** | keep | - | WP-10 | high | Run-scoped tools/list filtering from the frozen capability tuple plus effective role, rejecting hidden calls before dispatch. Existing call-time authorization stays as the backstop. |
| **#598** | keep, rewrite | - | WP-15 | high | Preview of requested grant, Canvas ceiling, override state, effective grant and requested capabilities on the selected row; future-launch-only semantics; existing runs frozen. DOWNGRADE the #597 dependency from hard to sequencing unless the UI is changed to consume a server-filtered catalog. |
| **#599** | keep, reduce scope | - | WP-16 | high | Mechanical SDK port: mcp>=2.1,<3, lock regeneration, MCPServer, snake-case internals, HTTPX 2 client support, unchanged wire/auth/catalog behaviour. STRIKE the transport-setting relocation; #600 owns it. |
| **#600** | keep | - | WP-16 | high | Sole owner of the transport settings move, the exact /mcp mount, explicit server version, the 4194304/4194305 boundary, legacy and modern client proof, seeded homes and one real bounded captured run. |
| **#602** | defer | - | WP-24 | medium | Deferred as a design note with a recorded trigger. Unique undecided product content: the SHA is the unit of handoff, gate evidence attaches to a SHA, the loop terminates only when both agents bless the same SHA, and one round trip's token cost is measured before tuning. |
| **#603** | keep, split | - | WP-14 | high | Split: the diagnosability half (a refusal that names its cause, a separate mint verb) ships independently and immediately. The attach-window relaxation is gated on #565 because it rests on a binding #565 says is forgeable. |
| **#611** | keep | - | WP-07/WP-17 | high | Derived request-purpose fixtures at harness/version/model/profile/class with a check mode that fails on a changed projection and names what changed. Explicit split out of #523, sequenced ahead of it. |
| **#624** | keep | - | WP-03 | high | Preserve the code and message the gateway actually wrote so an idempotency conflict is distinguishable from a generic invalid_request; unknown codes still map from status. Decide launch_failed explicitly. |
| **#630** | umbrella | - | WP-25 | high | Tracking only. Zero implementation. Becomes the live lifecycle parent; keep #631/#632/#633 links and add the settled-doctrine pointer to docs/HARNESS-COMPATIBILITY.md. |
| **#631** | keep | - | WP-01 | high | Refreshed codex enumeration as primary with bundled fallback, all visibility values admitted, separate enumeration timeout, typed sanitized failures, additive merge that retains a model absent from a successful result. |
| **#632** | keep, rewrite | - | WP-01 | high | Version-independent target offering, installed version separated from observation provenance, deletion of allow_unverified_target/opt-in vocabulary, VerificationCell instead of a target_unavailable rejection. REWRITE the entitlement bullet: keep account_entitlement_unavailable in launch resolution, move only its evidence source to #470's store. |
| **#633** | keep, split | - | WP-05 | high | Split into four landable slices: (a) reference selection policy with exact precedence and sibling alternatives, (b) verification phase/state contract, (c) durable deduplicated queue with restart recovery, (d) retention plus the read-only support-verdicts route. NOT blocked on a certify --all run. |

Titles are in `manifest.json`; per-issue evidence strings are in `proposed-grooming.json` under `issue_dispositions[].evidence`.

---

## 6. Unresolved, and what this synthesis could not verify

- The certify --all publication run has no issue number and is not part of this 43-issue snapshot. It belongs in a new issue rather than silently inside #523 or #633 (OD-10).
- Whether the refreshed codex catalog (0.153.2, not the bundled one) omits gpt-5.2 for this account is unmeasured. The 2026-09-05 comment measures the BUNDLED catalog, so it does not falsify the 2026-09-04 approval's premise. One read-only `codex debug models` settles it. The recommendation to keep the entitlement read does not depend on the answer: a 400 has already been observed, and #631's additive-retention rule means a model the refreshed catalog drops keeps its previous row and stays offered anyway.
- #573 item 3's remaining half is asserted from source reading, not from a restart experiment: delivery_resident.track() is called only at delivery creation (prompt_delivery.py:128) and startup_passes.py registers only lifecycle reconciliation. No restart was performed.
- PRs #463 and #464 were read as open at synthesis time; their diffs were not reviewed, so how much of #456 they actually deliver is unknown.
- grok-4.5's observed model id is unverified, so #555's normalization rule cannot be fixed yet.
- Whether any existing test exercises a conversation long enough for feed and summary to diverge (#496 part 1) is unknown.
- Whether a provider accepts a tool_use for an undeclared tool (#455, #459, #460) is unanswered and gates the kernel decision.
- #385, #386, #398, #557 and PR #559 are referenced by issue bodies but sit outside this manifest; their state was not independently fetched.
- Effort labels are S/M/L estimates from scope and blast radius, not measured durations. No provider probe, runtime launch, database read or full test suite was run for this synthesis.
- Two audit agents (reconciliation-check and portfolio's adversarial follow-up) never wrote their report files; their corrections survive only as conversation transcripts and were re-verified here against source where they changed a disposition.

### Confidence

High-confidence dispositions rest on a cited symbol, a cited line, or the issue's own text. Medium-confidence ones
(#381, #413, #448, #457, #555, #602) rest on judgement about value or on an unmeasured premise, and each says which.

Three claims were re-verified against source during this synthesis rather than taken from the upstream reports:

- `delivery_resident.track()` is called only from `prompt_delivery.py:128`, and `startup_passes.py` registers lifecycle
  reconciliation only. #573's restart clause is therefore open, and the earlier *item 3 is done* reading is too strong.
- No `overlays` package exists under `api/src/transport_matters`, so #384's application contract is unbuilt.
- All 43 issues are still open on GitHub and #463/#464 are still unmerged.

Not run: any provider probe, runtime launch, database read, restart experiment, or test suite. The two open PRs' diffs
were not reviewed. No GitHub mutation and no source change was made.

