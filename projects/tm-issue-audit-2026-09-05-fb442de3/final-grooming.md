# Final grooming: 43 open issues, reconciled

Snapshot `535118346ca5d0584a7a4a3da28a55be532dc3bd`. Independent review of `proposed-grooming.json`; corrections and their
evidence are in `grooming-review.md`, exact edit text in `final-github-edit-drafts.md`, machine-checkable
record in `final-grooming.json`, verified by `verify-final-grooming.py`. Nothing has been applied to GitHub.

## 1. Consolidation and closures

### Open-count impact

| | issues |
| --- | --- |
| open at snapshot | 43 |
| closed by consolidation (unconditional) | 1 ([#459](https://github.com/littleorgans/transport-matters/issues/459)) |
| **open after consolidation** | **42** |
| conditional on an owner ruling | 0 |
| closable later if Goal 3 is promoted to its own issue | 1 ([#381](https://github.com/littleorgans/transport-matters/issues/381), not recommended now) |

The honest closure count is one. The proposal offered a second, closing [#381](https://github.com/littleorgans/transport-matters/issues/381) into [#630](https://github.com/littleorgans/transport-matters/issues/630),
and this review reverses it: [#630](https://github.com/littleorgans/transport-matters/issues/630) is a three-defect P1 regression epic, [#381](https://github.com/littleorgans/transport-matters/issues/381) is the
Autopilot product arc whose Goal 3 (inspect, fork, edit, version, compare, restore overlays) has no other home.
Closing it required reparenting [#383](https://github.com/littleorgans/transport-matters/issues/383) and [#384](https://github.com/littleorgans/transport-matters/issues/384) under a bug parent, which broadens a narrow
epic to buy a closure. Retaining costs nothing: it already carries zero implementation weight.

### The closure

**[#459](https://github.com/littleorgans/transport-matters/issues/459) closes into [#460](https://github.com/littleorgans/transport-matters/issues/460).** Self-declared back-pocket research note with no standalone schedule; its entire 'open work before this is more than a note' section is #460's measurement plan, and its comment already points at #460.

Transfer before closing:

- The just-bash benchmark table and its reproduction script, including that sed, find, grep and wc matched native output while rg was the outlier.
- The codex execution-kernel checklist: sandbox and approval policy, known cwd and explicit workdir, shell and PATH guarantees, process lifecycle, output limits and truncation, structured patching, safety enforcement below the model, verification guidance.
- The isolation tradeoffs: OverlayFs, ReadWriteFs cost, Vercel Sandbox, and the absence of process lifecycle and hard VM isolation in just-bash.
- The open questions: whether a provider accepts a tool_use for an undeclared tool, and whether a companion mechanism is needed for PTY or long-running work.
- The decision not to document rg in the kernel contract until the implementation gap is resolved.

Preconditions:

- #460's body carries the transferred reference section before #459 is closed.
- The #455 parent relationship is retained on #460.
- The closing comment does not imply any experiment result exists or any implementation shipped.

### Duplicate effort removed without a closure

Six scope corrections remove work that was counted twice or was already shipped. They matter as much as the
closure and are cheaper to apply.

| issue | removed | now owned by |
| --- | --- | --- |
| [#573](https://github.com/littleorgans/transport-matters/issues/573) | item 3's resident reconciliation half | shipped in #629 at `53511834` |
| [#384](https://github.com/littleorgans/transport-matters/issues/384) | the `maximum_version` blocker in comment 2 | shipped: `compatibility.py:565,581,686` |
| [#599](https://github.com/littleorgans/transport-matters/issues/599) | the transport-settings relocation | [#600](https://github.com/littleorgans/transport-matters/issues/600), which already assigns itself the same work |
| [#368](https://github.com/littleorgans/transport-matters/issues/368) | 'detection ships as data, not code', a second purpose detector | the existing classifier, pinned by [#611](https://github.com/littleorgans/transport-matters/issues/611) |
| [#368](https://github.com/littleorgans/transport-matters/issues/368) | the positional-edit clobber harm | [#592](https://github.com/littleorgans/transport-matters/issues/592), fixed there for every request shape |
| [#477](https://github.com/littleorgans/transport-matters/issues/477) | 'every resolver rejection becomes advisory' | [#632](https://github.com/littleorgans/transport-matters/issues/632) owns which rejections stop gating |

### Structural corrections, no closure

- [#611](https://github.com/littleorgans/transport-matters/issues/611) is already split out of [#523](https://github.com/littleorgans/transport-matters/issues/523) and is sequenced ahead of it; it is the one issue deliberately
  referenced by two packages (owner WP-07, prerequisite WP-17) and is not double-counted effort.
- [#455](https://github.com/littleorgans/transport-matters/issues/455) records five children in prose with no real sub-issue links. Link [#456](https://github.com/littleorgans/transport-matters/issues/456), [#457](https://github.com/littleorgans/transport-matters/issues/457), [#458](https://github.com/littleorgans/transport-matters/issues/458)
  and [#460](https://github.com/littleorgans/transport-matters/issues/460).
- [#633](https://github.com/littleorgans/transport-matters/issues/633), [#498](https://github.com/littleorgans/transport-matters/issues/498), [#496](https://github.com/littleorgans/transport-matters/issues/496) and [#603](https://github.com/littleorgans/transport-matters/issues/603) are split at independently deliverable outcomes, not at files.
- Four tracking parents ([#630](https://github.com/littleorgans/transport-matters/issues/630), [#381](https://github.com/littleorgans/transport-matters/issues/381), [#455](https://github.com/littleorgans/transport-matters/issues/455), [#593](https://github.com/littleorgans/transport-matters/issues/593)) sit together in WP-25 at zero weight.
- PRs #463 and #464 are open and unmerged. [#456](https://github.com/littleorgans/transport-matters/issues/456) takes no closure credit for them.

## 2. Ranked work

Ranked by broken core promise first, then breadth, then work unlocked, then cost and risk. Effort is an S/M/L
estimate. Dependencies are hard unless the acceptance says otherwise.

| rank | package | issues | effort | depends on |
| --- | --- | --- | --- | --- |
| 1 | **WP-01** Restore runnability: discover, resolve and remember | [#631](https://github.com/littleorgans/transport-matters/issues/631), [#632](https://github.com/littleorgans/transport-matters/issues/632), [#470](https://github.com/littleorgans/transport-matters/issues/470) | L | - |
| 2 | **WP-02** Overrides apply to the block they were authored on | [#592](https://github.com/littleorgans/transport-matters/issues/592) | M | - |
| 3 | **WP-03** Orchestration a director can see and branch on | [#574](https://github.com/littleorgans/transport-matters/issues/574), [#515](https://github.com/littleorgans/transport-matters/issues/515), [#624](https://github.com/littleorgans/transport-matters/issues/624) | M | - |
| 4 | **WP-04** A queued nudge correlates, and survives a restart | [#573](https://github.com/littleorgans/transport-matters/issues/573) | M | - |
| 5 | **WP-05** Every first launch has a state | [#633](https://github.com/littleorgans/transport-matters/issues/633) | L | WP-01 |
| 6 | **WP-06** The verdict reaches the run | [#477](https://github.com/littleorgans/transport-matters/issues/477) | M | WP-01, WP-05 |
| 7 | **WP-07** Purpose classification has a source of truth, and the breakpoint uses it | [#611](https://github.com/littleorgans/transport-matters/issues/611), [#368](https://github.com/littleorgans/transport-matters/issues/368) | S | WP-02 |
| 8 | **WP-08** See exactly what each harness puts on the wire | [#456](https://github.com/littleorgans/transport-matters/issues/456) | M | - |
| 9 | **WP-09** Effective authority and a catalog that cannot drift | [#595](https://github.com/littleorgans/transport-matters/issues/595), [#596](https://github.com/littleorgans/transport-matters/issues/596) | M | - |
| 10 | **WP-10** A run discovers only the tools its policy permits | [#597](https://github.com/littleorgans/transport-matters/issues/597) | M | WP-09 |
| 11 | **WP-11** Take the token lever: declared tool surface and regenerated prose | [#457](https://github.com/littleorgans/transport-matters/issues/457), [#458](https://github.com/littleorgans/transport-matters/issues/458) | L | WP-08 |
| 12 | **WP-12** Operator facts stop dying with the home | [#472](https://github.com/littleorgans/transport-matters/issues/472), [#471](https://github.com/littleorgans/transport-matters/issues/471) | S | - |
| 13 | **WP-13** Log a harness in from inside the app | [#482](https://github.com/littleorgans/transport-matters/issues/482) | L | WP-12 |
| 14 | **WP-14** Only a genuine presenter wins, and a refusal says why | [#565](https://github.com/littleorgans/transport-matters/issues/565), [#603](https://github.com/littleorgans/transport-matters/issues/603) | L | - |
| 15 | **WP-15** Canvas shows the authority a run will actually get | [#598](https://github.com/littleorgans/transport-matters/issues/598) | M | WP-09, WP-12 |
| 16 | **WP-16** Current protocol, one transport owner, proven against real clients | [#599](https://github.com/littleorgans/transport-matters/issues/599), [#600](https://github.com/littleorgans/transport-matters/issues/600) | L | WP-10 |
| 17 | **WP-17** One publishing entry point and a corpus that can be audited | [#446](https://github.com/littleorgans/transport-matters/issues/446), [#523](https://github.com/littleorgans/transport-matters/issues/523), [#611](https://github.com/littleorgans/transport-matters/issues/611) | L | WP-07 |
| 18 | **WP-18** The owned overlay actually applies, and old harnesses have a policy | [#384](https://github.com/littleorgans/transport-matters/issues/384) | L | WP-01, WP-05 |
| 19 | **WP-19** Explain the first request to a new operator | [#383](https://github.com/littleorgans/transport-matters/issues/383) | M | WP-08 |
| 20 | **WP-20** Compatibility updates arrive signed | [#448](https://github.com/littleorgans/transport-matters/issues/448) | L | WP-17 |
| 21 | **WP-21** Recall answers, or says what it searched | [#498](https://github.com/littleorgans/transport-matters/issues/498), [#496](https://github.com/littleorgans/transport-matters/issues/496) | L | - |
| 22 | **WP-22** A model id the roster can look up | [#555](https://github.com/littleorgans/transport-matters/issues/555) | S | - |
| 23 | **WP-23** Does a small owned surface do the work | [#460](https://github.com/littleorgans/transport-matters/issues/460), [#459](https://github.com/littleorgans/transport-matters/issues/459) | M | WP-08 |
| 24 | **WP-24** Deferred on a recorded trigger | [#413](https://github.com/littleorgans/transport-matters/issues/413), [#602](https://github.com/littleorgans/transport-matters/issues/602), [#504](https://github.com/littleorgans/transport-matters/issues/504) | S | - |
| 25 | **WP-25** Tracking parents carry no implementation weight | [#630](https://github.com/littleorgans/transport-matters/issues/630), [#381](https://github.com/littleorgans/transport-matters/issues/381), [#455](https://github.com/littleorgans/transport-matters/issues/455), [#593](https://github.com/littleorgans/transport-matters/issues/593) | S | - |

### First work

**WP-01.** The central product promise is broken in production right now: `gpt-6-astra` and
`gpt-5.3-codex-spark` are undiscoverable, and a harness patch release empties the picker. Everything in the
compatibility area is worth less until this holds. WP-02 and WP-03 are independent and can run beside it.

#### WP-01 (rank 1) Restore runnability: discover, resolve and remember

Issues: [#631](https://github.com/littleorgans/transport-matters/issues/631), [#632](https://github.com/littleorgans/transport-matters/issues/632), [#470](https://github.com/littleorgans/transport-matters/issues/470) | effort L | depends on nothing

*Outcome.* A model or harness version released today is enumerated, offered and launchable; a harness patch release never empties the picker; the one surviving refusal is a provider entitlement refusal read from the session store and surviving a home wipe.

*Value.* The central product promise is broken in production now: gpt-6-astra and gpt-5.3-codex-spark are undiscoverable and a version bump withdraws offered targets. Everything else in the compatibility area is worth less until this holds.

*Acceptance.*

- #631: refreshed catalog primary with bundled fallback; list/hide/none parse identically; probe revision r2; typed enumeration success and failure with a closed vocabulary and no raw stderr; enumeration timeout distinct from the auth timeout; additive merge so a model absent from a successful result retains its row; both attempts failing changes no rows; refresh reruns on an unchanged CLI version.
- #632: ten target observations at 2.1.260 survive a move to 2.1.261 with all ten still offered; a resolved option reports installed 2.1.261 with target provenance 2.1.260; an installed enabled harness with zero options is launchable:true with empty models; allow_unverified_target, target_unverified_opt_in_required and requires_unverified_opt_in deleted; a target_unavailable rejection becomes a VerificationCell; HARNESS-COMPATIBILITY.md:168-189, LAUNCH-CONTRACT.md and LOGGING-PLAN.md reconciled.
- #632 rewritten: account_entitlement_unavailable stays in launch resolution and reads from the store; only the baseline-attempt read is removed from resolver snapshots.
- #470: wipe the channel home, restart, gpt-5.2 is still excluded with no new provider turn; a test covers record, discard, still enforced.
- #470 new: the exclusion key distinguishes two provider accounts on one machine, or the issue records that an account change requires an operator clear (OD-2).
- resolver.py and baseline_store.py are extracted below the 700-line rule before expansion.

#### WP-02 (rank 2) Overrides apply to the block they were authored on

Issues: [#592](https://github.com/littleorgans/transport-matters/issues/592) | effort M | depends on nothing

*Outcome.* A saved override applies to its anchored block or misses audibly; no override ever rewrites a different block on a later request.

*Value.* Live corruption of the operator's own prompt on Codex continuation requests, independent of every compatibility change, and small enough to land beside WP-01.

*Acceptance.*

- Anchor required for the four positional kinds and rejected at the store boundary without one.
- block_anchor and blockAnchor pinned equal by a shared fixture tested on both sides.
- Resolution by anchor with index as hint and tie breaker.
- A miss produces applied:false with reason anchor_miss and rewrites nothing.
- The run dda34ad8 replay applies both overrides on 69b93589 and neither on the continuation.

#### WP-03 (rank 3) Orchestration a director can see and branch on

Issues: [#574](https://github.com/littleorgans/transport-matters/issues/574), [#515](https://github.com/littleorgans/transport-matters/issues/515), [#624](https://github.com/littleorgans/transport-matters/issues/624) | effort M | depends on nothing

*Outcome.* An agent driving the control plane can read a blocked run's screen, enumerate its own subscriptions, and branch on the failure the server actually named.

*Value.* Three small independent fixes, each found by an agent hitting the wall during this very audit. Free parallelism from day one and no unresolved decision.

*Acceptance.*

- #574: pane(run_id, max_chars?) returns the snapshot with the server cap applied; an observer grant suffices; the verb resolves the gateway that owns the terminal; the post-exit read decision is recorded, including whether the last screen is retained at teardown.
- #515: watch_status() returns every subscription the run holds and watch_status(target) returns one, each with target, events, registered_at, last_event_at, deliveries, target_state and shadowed_by; empty is distinguishable from error.
- #624: an idempotency conflict returns its own code and the message RunManager wrote; an unknown gateway code still returns the status-derived code and generic message; the REST status map still exhausts the vocabulary; launch_failed is decided explicitly.

#### WP-04 (rank 4) A queued nudge correlates, and survives a restart

Issues: [#573](https://github.com/littleorgans/transport-matters/issues/573) | effort M | depends on nothing

*Outcome.* Two nudges queued in one turn both correlate on Claude and on Codex, and a delivery row pending across a gateway restart still reconciles.

*Value.* #629 removed the accidental mitigation: a stranded row used to correlate on the next wait, and now a row nobody waits on and no in-process tracker holds will never correlate.

*Acceptance.*

- #573 item 1: LivePromptDeliveryBindings holds every pending binding and claims each by its own digest, proven by arming two and claiming both.
- #573 item 2: a Codex merged user message matches a delivery whose prompt text is one line of it, with the per-delivery outcome ruled explicitly (both completed on the same range, or the earlier superseded).
- #573 item 3 remainder: a startup sweep registers or reconciles delivery rows left pending by a previous process, proven by a test that restarts with an open row and reaches a terminal state without a wait. The in-process resident path from #629 is not re-implemented.

#### WP-05 (rank 5) Every first launch has a state

Issues: [#633](https://github.com/littleorgans/transport-matters/issues/633) | effort L | depends on WP-01

*Outcome.* A model the shipped release does not reference comes out of its first launch blessed or degraded, with the reason and phase recorded and the work durably queued.

*Value.* Completes WP-01's premise. Without it, WP-01 makes astra discoverable and verdictless, which is the exact gap named. It is startable against today's first-turn-only references and does not wait on a new publication run.

*Acceptance.*

- Reference selection: exact precedence, then eligible sibling contracts with the shipped reference always on the left; bless on at least one complete comparison; body and envelope from the same reference; candidate identity preserved and reference identities recorded as provenance only; runtime-blessed newcomers never enter another candidate's reference set.
- A release carrying only first-turn references compares that shape and declines to answer for the shape it lacks, per the rule #604 set. First-turn capture costs 3 provider requests per new model; sibling count adds none; evidence reconciliation precedes the quota check.
- Verification phase is stored separately from SupportState (OD-1): queued, running, no_compatible_reference, capture_failed and derivation_failed are phases or reasons, and none of them manufactures a missing-property finding.
- A durable deduplicated queue keeps the two-worker execution limit; three simultaneous new models all drain and none is dropped; capture deadlines start at execution; restart discovers pending work; queue admission does not increment attempt_count.
- Retention: removing a model from a complete refreshed catalog preserves its verdict without restoring its picker entry; reappearance at the same coordinates reuses it, changed coordinates do not.
- A read-only GET /v1/harnesses/{harness_id}/support-verdicts with model, route, version and release filters.

#### WP-06 (rank 6) The verdict reaches the run

Issues: [#477](https://github.com/littleorgans/transport-matters/issues/477) | effort M | depends on WP-01, WP-05

*Outcome.* Range position, verification phase and state, and launch advisories appear on the run itself rather than only in a store.

*Value.* The only surface where blessed, degraded or pending reaches a human. Cheap once WP-05 has defined the matrix, and meaningless before it.

*Acceptance.*

- Range position, verification phase/state and advisories reach RunVitalsStrip per run through the activity projection.
- Advisory target recognition is displayed distinctly from a hard launch prerequisite; the blanket 'every rejection becomes advisory' requirement is removed from the issue.
- Pending, blessed, degraded, no reference and provider refusal each render truthfully and differently.

#### WP-07 (rank 7) Purpose classification has a source of truth, and the breakpoint uses it

Issues: [#611](https://github.com/littleorgans/transport-matters/issues/611), [#368](https://github.com/littleorgans/transport-matters/issues/368) | effort S | depends on WP-02

*Outcome.* Request-purpose classification is pinned by fixtures that fail a check when a harness changes its traffic, and an armed breakpoint stops pausing harness machinery turns.

*Value.* #611 is the cheapest durable guard in the backlog and #368 stops being a second detector once it consumes the existing classifier. #368's dangerous half is removed by WP-02.

*Acceptance.*

- #611: a capture produces a fixture at harness, exact version, model, capture profile and request class; check mode fails on a changed projection and names what changed; replay asserts primary True, housekeeping False, and no prompt-collision class resting on None; synthetic fixtures remain.
- #368: with a breakpoint armed, a title-generation turn and the quota probe cross un-paused while the user-composed turn pauses; aux passthrough is recorded in the exchange record, not silent; pinning test derived from run 163c35b4's three captured shapes.
- #368 introduces no second purpose detector; it reads the classification #611 pins.

#### WP-08 (rank 8) See exactly what each harness puts on the wire

Issues: [#456](https://github.com/littleorgans/transport-matters/issues/456) | effort M | depends on nothing

*Outcome.* An operator can read every wire class per region, with per-tool costs and addressable targets marked.

*Value.* The declared acceptance surface for every later overlay slice, read-only, and running on data already shipped. Two open PRs already carry part of it.

*Acceptance.*

- All five current wire classes render with region breakdowns cross-checked against the certified figures.
- Claude's section outline and codex's runtime blocks are visible without raw JSON.
- Per-tool costs are sortable and sum to the measured tool region; addressable targets are marked.
- A class with no captured exchange lists its targets and says so.
- PRs #463 and #464 are reviewed and merged or superseded; neither is treated as shipped until it merges.

#### WP-09 (rank 9) Effective authority and a catalog that cannot drift

Issues: [#595](https://github.com/littleorgans/transport-matters/issues/595), [#596](https://github.com/littleorgans/transport-matters/issues/596) | effort M | depends on nothing

*Outcome.* One effective grant is resolved and frozen per run, and the MCP tool set is a validated ordered catalog rather than decorator order.

*Value.* The current runtime request is transported but does not constrain the grant actually minted, so both overgrant and undergrant are reachable today. Both slices are independent of each other and of WP-01.

*Acceptance.*

- #595: one pure resolver over min(requested, limiting, optional override); omitted and explicit none are distinct; CMDK and MCP use the same resolver; the decision is persisted with provenance and used for identity, bearer minting and home seeding; effective none creates no bearer and no MCP client; restart and replay preserve the frozen decision.
- #596: every registered tool appears exactly once in a deterministic order with one capability and one minimum grant; the observer/director split is declared in one source of truth; schemas and outputs are byte-equivalent where ordering permits; contract tests fail on registrar drift.
- #596 asserts the catalog invariant, not a literal tool count in prose (OD-7).

#### WP-10 (rank 10) A run discovers only the tools its policy permits

Issues: [#597](https://github.com/littleorgans/transport-matters/issues/597) | effort M | depends on WP-09

*Outcome.* tools/list is filtered by the frozen capability tuple and effective role, and a guessed call to a hidden tool fails before side effects.

*Value.* Caps MCP token cost per run and is the prerequisite that makes WP-11's claude arm a reduction rather than a regression.

*Acceptance.*

- Observer runs list only observer tools within their runtime capabilities; director runs list director plus observer.
- Two bearers with different capabilities receive different deterministic catalogs.
- A guessed call to a hidden director tool fails before any side effect; an expired or revoked bearer receives no usable catalog.
- Filtering does not fork domain authorization; existing call-time checks remain.

#### WP-11 (rank 11) Take the token lever: declared tool surface and regenerated prose

Issues: [#457](https://github.com/littleorgans/transport-matters/issues/457), [#458](https://github.com/littleorgans/transport-matters/issues/458) | effort L | depends on WP-08

*Outcome.* A runtime declares its builtin tool surface once and gets it applied across three harnesses, and the prose that teaches those tools is regenerated to match.

*Value.* The largest measured lever in the backlog, and it becomes measurable only once WP-08 can show the diff and WP-10 has bounded the MCP catalog on claude.

*Acceptance.*

- #457: a runtime declaring a reduced [tools] set launches with only those tools on the wire, byte-diffed against the same launch without the overlay with changes confined to the tool region; measured token reduction per harness against the certified baseline; one capability declaration resolves on all three harnesses; a stale library entry whose tool schema digest moved is reported.
- #457 claude arm is measured with WP-10 in place, or the measurement explicitly records the un-deferred MCP schemas (OD-3).
- #458: disabling a tool re-renders the prose referencing it, verified on the wire; a render whose assumed tool set does not match the live request forwards original bytes and reports; rendering is platform-aware for at least two profiles; changes confined to prompt and tool regions; operator acceptance through the #456 viewer.
- The byte-splicing mechanism is ruled once for #457, #458 and #523 (OD-4).
- Sequencing, not a dependency: the codex and grok arms may land without #597 (WP-10). The claude arm either follows #597 or reports the un-deferred MCP tool schemas in its own token measurement, stated as a known regression rather than hidden by it.

#### WP-12 (rank 12) Operator facts stop dying with the home

Issues: [#472](https://github.com/littleorgans/transport-matters/issues/472), [#471](https://github.com/littleorgans/transport-matters/issues/471) | effort S | depends on nothing

*Outcome.* Launch toggles survive a channel home wipe, and a run's log is readable at a destination the operator chose.

*Value.* Two small independent fixes; #472 must precede #598's consent persistence claim.

*Acceptance.*

- #472: set both toggles, wipe the channel home, relaunch, settings unchanged.
- #471: a foreground run produces a readable log file; a destination outside the channel home survives a home wipe; tail resolves the same configured path; the default is unchanged.

#### WP-13 (rank 13) Log a harness in from inside the app

Issues: [#482](https://github.com/littleorgans/transport-matters/issues/482) | effort L | depends on WP-12

*Outcome.* A user completes harness login in the app, with the exit as trigger and the credential predicate as verdict.

*Value.* The most implementation-ready issue in the backlog with an approved six-slice plan, and first-run blocking for a new operator.

*Acceptance.*

- All six approved slices with their verbatim gates.
- Exit is the trigger and the credential predicate is the verdict, with outcomes succeeded, failed, cancelled, spawn_failed and lost.
- Harness-keyed public identity with start-twice rejoining and no attempt id; no home path, argv, env or PTY types on any public surface.
- The fallback URL is read from a bounded output_tail with nothing parsing it.
- New: the harness auth home is placed so a channel home wipe does not invalidate a login, or the invalidation is surfaced to the operator (OD-5).

#### WP-14 (rank 14) Only a genuine presenter wins, and a refusal says why

Issues: [#565](https://github.com/littleorgans/transport-matters/issues/565), [#603](https://github.com/littleorgans/transport-matters/issues/603) | effort L | depends on nothing

*Outcome.* Canvas presenter registration is authenticated and bound to a genuine Electron instance, and an attach either succeeds or refuses with a named cause.

*Value.* The last open integrity boundary on the browser surface. #603's diagnosability half is cheap and ships first; the window relaxation waits on the binding.

*Acceptance.*

- #565: a rogue loopback process registering first cannot become the selected composited presenter and cannot publish a devtools origin or pane observation under a genuine identity; a packaged desktop registers and resumes after renderer reload; a hosted desktop joins an already-live runtime; multiple genuine Canvas windows stay independently addressable.
- #603 first half: a refused attach names its cause and a separate mint verb exists; this half ships without #565.
- #603 second half: list panes, wait past the current window, attach, and re-attach after a dropped socket without a fresh browser_panes call, or the issue records why it must. Gated on #565 (OD-8).

#### WP-15 (rank 15) Canvas shows the authority a run will actually get

Issues: [#598](https://github.com/littleorgans/transport-matters/issues/598) | effort M | depends on WP-09, WP-12

*Outcome.* Requested grant, Canvas ceiling, override state, effective grant and requested capabilities are visible before launch, and existing runs stay frozen.

*Value.* Completes the authority program's user-facing half once the resolver exists; the #597 dependency is sequencing only.

*Acceptance.*

- Requested and effective grants are visible before launch; a director request is visibly limited when the gate is none or observer.
- Changing the gate persists through reload and does not silently change existing runs.
- One browser test proves the consent flow and payload.

#### WP-16 (rank 16) Current protocol, one transport owner, proven against real clients

Issues: [#599](https://github.com/littleorgans/transport-matters/issues/599), [#600](https://github.com/littleorgans/transport-matters/issues/600) | effort L | depends on WP-10

*Outcome.* The MCP server runs on a current SDK with one owner of the mounted transport policy, proven against a legacy and a modern client.

*Value.* Infrastructure that is not a prerequisite for authority correctness; scheduled after the filter so the port carries the final adapter shape.

*Acceptance.*

- #599: no FastMCP import and no SDK camel-case access remains; mcp>=2.1,<3 with a regenerated lock; resolution succeeds on Python 3.14; wire, auth and catalog behaviour unchanged. The transport-setting relocation is not in this issue.
- #600: one mounted app owner and the exact /mcp path; explicit server version; the three transport settings move here; 4194304 bytes returns 200 and 4194305 returns 413; legacy and modern client paths both list and call; seeded claude, codex and grok homes remain compatible; one real captured run lists its bounded catalog and completes a call.

#### WP-17 (rank 17) One publishing entry point and a corpus that can be audited

Issues: [#446](https://github.com/littleorgans/transport-matters/issues/446), [#523](https://github.com/littleorgans/transport-matters/issues/523), [#611](https://github.com/littleorgans/transport-matters/issues/611) | effort L | depends on WP-07

*Outcome.* An operator has one documented entry point for publication, and the captured corpus supports the request-class vocabulary and the native-control matrix.

*Value.* Enabling work. #446 is a small decision that should be recorded before the next publication run; #523's later items improve as reference coverage grows.

*Acceptance.*

- #446: one recorded decision. Recommended option 2 - harvest is documented as debug-only single-cell evidence that never changes a release, publish is the normal workflow, and help text states the boundary. harvest_baseline stays the shared capture function either way (OD-6).
- #523: the request class vocabulary first; then the native-control matrix per harness with the flag lists as written and grok's headless-only limitation recorded; then the runtime-overlay and interactive-direction profiles; then the public corpus export.
- #611 acceptance is delivered in WP-07 and is not re-implemented here; it appears in this package only as the corpus prerequisite it is.

#### WP-18 (rank 18) The owned overlay actually applies, and old harnesses have a policy

Issues: [#384](https://github.com/littleorgans/transport-matters/issues/384) | effort L | depends on WP-01, WP-05

*Outcome.* A certified release selects and applies the TM-owned overlay automatically, a provider-bound capture proves the transformation, and every failure path degrades to exact passthrough with a truthful notice.

*Value.* This is the unbuilt half of the Autopilot promise and it is not doctrine. No overlays package exists at this SHA; the settled lifecycle rules move to docs so the issue holds only the work.

*Acceptance.*

- A known certified release selects and applies the expected TM overlay automatically.
- A provider-bound capture proves the actual outbound request contains the expected transformation.
- The original request, overlay version, provider-bound request, audit and response are inspectable.
- No-drift and compatible-drift release fixtures continue safely; a breaking-drift fixture produces exact unoptimized passthrough and a truthful notice; application or preimage failure produces exact unoptimized passthrough.
- The older-harness support policy is decided, documented and tested at its boundary; the upgrade button is specified, executes rather than displays, and knows whether a captured run is in flight.
- The resolved maximum_version material and the settled lifecycle table are removed from the issue and live in docs/HARNESS-COMPATIBILITY.md.

#### WP-19 (rank 19) Explain the first request to a new operator

Issues: [#383](https://github.com/littleorgans/transport-matters/issues/383) | effort M | depends on WP-08

*Outcome.* An optional, skippable, reopenable HTML report explains the first full provider request.

*Value.* First-turn education is the remaining child of the Autopilot umbrella and reuses the projection WP-08 builds.

*Acceptance.*

- An optional skippable reopenable first-turn HTML report with role and provenance totals, per-leaf pointers and digests.
- Observed facts are separated from inferred classifications.
- The request projection is shared with #456 rather than duplicated.

#### WP-20 (rank 20) Compatibility updates arrive signed

Issues: [#448](https://github.com/littleorgans/transport-matters/issues/448) | effort L | depends on WP-17

*Outcome.* Compatibility data reaches an installed TM through a verified channel with rotation, staged rollout and a kill switch.

*Value.* Strategic supply-chain work with a real fail-closed requirement. Deferred behind the certification boundary and an owner decision on the trust root.

*Acceptance.*

- Retrieval with a surviving last-verified cache.
- A real SignatureVerifier with key distribution and rotation, replacing RejectAllSignatureVerifier.
- Staged rollout through channel_states and a remote kill switch over blocked_versions.
- Two distinct nudges, compatibility update and product release, never conflated.
- Trust root, transport and preview policy are decided and removed from the open-decisions list in docs/HARNESS-COMPATIBILITY.md.

#### WP-21 (rank 21) Recall answers, or says what it searched

Issues: [#498](https://github.com/littleorgans/transport-matters/issues/498), [#496](https://github.com/littleorgans/transport-matters/issues/496) | effort L | depends on nothing

*Outcome.* A recall question over the transcript store returns results or states its scope and coverage, and a conversation read stops presenting a summary as the whole conversation.

*Value.* Real value with no dependant. Both issues must be split before scheduling; only #496 part 1 and #498 item 1 are ready as written.

*Acceptance.*

- #498 item 1: backfill search_text across kinds and fix the writer, or have the endpoint report the coverage it searched.
- #498 item 2: GET /v1/sessions/search over content_tsv returning session_id, seq, ts and headline with ts_headline snippets.
- #498 item 3: scope is explicit in every list response so empty is distinguishable from elsewhere, with harness, provider and session filters.
- #498 item 4, separate: why the sessions implementing #492/#493/#495 were never captured, scoped to those implementation sessions.
- #496 part 1: the summary tail counts turns rather than messages, the elision is reported, and the count is named or exposed.
- #496 part 2, after a design pass: include:["text","tool_use",...] with per-part truncation budgets, cursor semantics keeping conversation_scan contiguity, and reuse of the inspector's part projection.

#### WP-22 (rank 22) A model id the roster can look up

Issues: [#555](https://github.com/littleorgans/transport-matters/issues/555) | effort S | depends on nothing

*Outcome.* The grok observed model resolves to an id a harness can answer for, with the raw response value retained on the event.

*Value.* Small and self-contained; low urgency because no operator action currently depends on it and grok-4.5 behaviour is unverified.

*Acceptance.*

- A regression pins declared-to-observed resolution per harness so an unresolvable id fails a test rather than reaching the roster.
- grok observed_model resolves to something harnesses can answer for; the event keeps the raw response value.
- grok-4.5 behaviour is measured before the normalization rule is fixed.

#### WP-23 (rank 23) Does a small owned surface do the work

Issues: [#460](https://github.com/littleorgans/transport-matters/issues/460), [#459](https://github.com/littleorgans/transport-matters/issues/459) | effort M | depends on WP-08

*Outcome.* An honest A/B says whether one bash tool plus our system prompt matches an untouched agent, with the kernel research recorded in one place.

*Value.* Investment experiment, not a defect. It decides which controls #457 needs, so it is worth running once the wire viewer can measure the arms.

*Acceptance.*

- Both arms run the same pre-chosen task set unattended and produce request bytes, total tokens, turns, wall clock, success rate and failures by category.
- The result is reported whichever way it falls, with the prompt iteration count; the A/B runs on a frontier model, not a small one.
- Absorbed from #459: the just-bash benchmark table and its reproduction script, the codex execution-kernel checklist (sandbox and approval policy, known cwd, PATH, process lifecycle, output limits, structured patching, safety below the model), and the OverlayFs / ReadWriteFs / Vercel Sandbox tradeoffs including the absent process lifecycle and hard VM isolation.
- Answered: whether a provider accepts a tool_use for an undeclared tool, and whether a companion mechanism is needed for PTY or long-running work.
- rg is not documented in the tool contract until the benchmark gap is resolved.

#### WP-24 (rank 24) Deferred on a recorded trigger

Issues: [#413](https://github.com/littleorgans/transport-matters/issues/413), [#602](https://github.com/littleorgans/transport-matters/issues/602), [#504](https://github.com/littleorgans/transport-matters/issues/504) | effort S | depends on nothing

*Outcome.* Nothing is scheduled. Each carries a trigger and an evidence base so the next person does not re-derive it.

*Value.* The value is in not spending on them now. They are listed so the deferral is a decision rather than a gap.

*Acceptance.*

- #413 trigger: a stated rule per family, provably inert sets deleted rather than trimmed, and the specialist-versus-control asymmetry resolved explicitly, with no new constraint imposed on agent-runtimes.
- #602 trigger: the SHA is the unit of handoff, gate evidence attaches to a SHA, the loop terminates only when both agents bless the same SHA, and one round trip's token cost is instrumented before tuning.
- #504 trigger: a second presenter exists. Then the Gateway owns entries[] and index, can_go_back and can_go_forward are derived, and the pushState question is answered.

#### WP-25 (rank 25) Tracking parents carry no implementation weight

Issues: [#630](https://github.com/littleorgans/transport-matters/issues/630), [#381](https://github.com/littleorgans/transport-matters/issues/381), [#455](https://github.com/littleorgans/transport-matters/issues/455), [#593](https://github.com/littleorgans/transport-matters/issues/593) | effort S | depends on nothing

*Outcome.* Four umbrellas track their children and add zero effort. Link hygiene only.

*Value.* Counting these as work overstates the backlog. #455's children are prose-only today and #383/#384 have two competing parents.

*Acceptance.*

- #455 gains real sub-issue links to #456, #457, #458 and #460, replacing the prose 'Parent: #455' lines.
- #630 becomes the live lifecycle parent and #383/#384 are reparented under it; #381 is then closable as a superseded umbrella once its power-user overlay deferral moves to #384 (OD-9).
- #593 keeps #595-#600 and duplicates none of their acceptance criteria.
- No parent's acceptance restates a child's implementation criterion.

## 3. The 43-issue ledger

Every open issue exactly once. `survivor` is the issue that carries the outcome forward.

| issue | action | survivor | package | remaining scope |
| --- | --- | --- | --- | --- |
| [#368](https://github.com/littleorgans/transport-matters/issues/368) | `keep_rewrite` | - | WP-07 | Rewrite as a CONSUMER of the existing request-purpose classification at the breakpoint pause branch. Keep the acceptance verbatim (aux turn and quota probe cross un-paused, user turn pauses, passthrough recorded not silent, pinning test from run 163c35b4). Drop the 'detection ships as data, not code' ruling and cite #592 for the clobbe... |
| [#381](https://github.com/littleorgans/transport-matters/issues/381) | `umbrella_keep` | - | WP-25 | RETAIN OPEN. Tracking only, zero implementation. Reviewer reverses the proposed conditional close into #630: #630 is a narrow P1 regression epic over three discovery/resolution/verification defects, while #381 owns the broader Autopilot product arc (first-turn education, owned-overlay authority, and the Goal 3 power-user overlay inspec... |
| [#383](https://github.com/littleorgans/transport-matters/issues/383) | `keep` | - | WP-19 | Optional, skippable, reopenable first-turn HTML report: role and provenance totals, per-leaf pointers and digests, observed facts separated from inferred classifications. Shares the request projection with #456 but is a different audience and surface. |
| [#384](https://github.com/littleorgans/transport-matters/issues/384) | `keep_rewrite` | - | WP-18 | NOT zero work. Retains: automatic selection and application of the TM-owned overlay for a certified release, provider-bound capture proving the transformation, inspectability of original/overlay/bound request/audit/response, safe passthrough on drift or preimage failure, the older-harness support policy decided and tested at its bounda... |
| [#413](https://github.com/littleorgans/transport-matters/issues/413) | `defer` | - | WP-24 | Deferred by owner decision with a recorded trigger. The real question is the specialist Codex skills/ write-through asymmetry and a stated rule per family, not a generic name-set cleanup. |
| [#446](https://github.com/littleorgans/transport-matters/issues/446) | `keep_rewrite` | - | WP-17 | One recorded boundary decision plus help text. Engineering resolution (was OD-6): take the issue's option 2. Document harvest as debug-only single-cell evidence that never changes a release, with publish as the normal workflow. baseline_publish already imports harvest_baseline and passes each planned cell to it, so folding the CLI remo... |
| [#448](https://github.com/littleorgans/transport-matters/issues/448) | `defer` | - | WP-20 | Signed retrieval, real SignatureVerifier with key distribution and rotation, staged rollout through channel_states, remote kill switch over blocked_versions, two distinct nudges. Deferred behind the certification boundary work; trigger is a decided trust root. |
| [#455](https://github.com/littleorgans/transport-matters/issues/455) | `umbrella_keep` | - | WP-25 | Tracking only. Zero implementation. Create the real sub-issue links to #456, #457, #458, #460 (currently prose-only) and preserve its measured token and mechanism record. |
| [#456](https://github.com/littleorgans/transport-matters/issues/456) | `keep` | - | WP-08 | Read-only wire-class viewer with region breakdowns, per-tool costs, addressable targets. Strongest independent slice. PRs #463 and #464 are OPEN and unmerged: partial in-flight work, no closure credit. |
| [#457](https://github.com/littleorgans/transport-matters/issues/457) | `keep` | - | WP-11 | Harness builtin subtraction driven by a capability library and agent-runtimes [tools], byte-diffed and token-measured per harness. Engineering resolution (was OD-3): #597 is NOT a dependency. The codex and grok arms are independent of it. On the claude arm only, disabling builtins un-defers the MCP tool schemas, so either #597 lands fi... |
| [#458](https://github.com/littleorgans/transport-matters/issues/458) | `keep` | - | WP-11 | Regenerate the prose that teaches tools after a tool decision, verified on the wire, platform-aware for at least two profiles, with forward-original-bytes on a mismatch. Distinct correctness requirement from tool subtraction. |
| [#459](https://github.com/littleorgans/transport-matters/issues/459) | `close_merge` | [#460](https://github.com/littleorgans/transport-matters/issues/460) | WP-23 | No standalone work survives. The just-bash benchmark table, the codex execution-kernel checklist, the isolation/process-lifecycle gaps and the open questions transfer into #460 as a reference section before closing. |
| [#460](https://github.com/littleorgans/transport-matters/issues/460) | `keep` | - | WP-23 | Survivor of #459. Build the just-bash MCP server and run the unattended same-task A/B on a frontier model, measuring request bytes and end-to-end tokens separately, with failures classified and the result reported whichever way it falls. Absorbs #459's research record. |
| [#470](https://github.com/littleorgans/transport-matters/issues/470) | `keep_rewrite` | - | WP-01 | Move provider-refusal evidence to the session store with an atomic upsert and a resolver read path; prove survival of a home wipe. REWRITE two things: define the account identity key explicitly, and rename the retained exclusion a runtime provider-refusal exclusion rather than 'an enumerated block in the #384 sense'. |
| [#471](https://github.com/littleorgans/transport-matters/issues/471) | `keep` | - | WP-12 | Env-configurable log destination that can live outside the channel home, a readable log file for foreground runs, and tail resolving the same configured path with an unchanged default. |
| [#472](https://github.com/littleorgans/transport-matters/issues/472) | `keep` | - | WP-12 | Canvas launch toggles survive a channel home wipe. Precedes #598's consent persistence claim. |
| [#477](https://github.com/littleorgans/transport-matters/issues/477) | `keep_scope_reduce` | - | WP-06 | Per-run status bar carrying range position, verification phase/state and advisories into the activity projection. STRIKE the blanket 'every resolver rejection becomes advisory' clause; it conflicts with #470's sanctioned exclusion and with enablement/infrastructure gates. The status bar must render pending verification as pending, not... |
| [#482](https://github.com/littleorgans/transport-matters/issues/482) | `keep` | - | WP-13 | All six approved slices with their verbatim gates: exit is the trigger and the credential predicate is the verdict; harness-keyed public identity with start-twice rejoining; no home path, argv, env or PTY types on any public surface. Reconcile credential placement against the disposable-home risk. Engineering resolution (was OD-5): the... |
| [#496](https://github.com/littleorgans/transport-matters/issues/496) | `keep_split` | - | WP-21 | Split at two outcomes: part 1 (summary selection counts turns not messages, elision reported) is ready now; part 2 (tool-parts projection with include:[], per-part truncation budgets and cursor contiguity) needs a design pass first. |
| [#498](https://github.com/littleorgans/transport-matters/issues/498) | `keep_split` | - | WP-21 | Split at four independently deliverable outcomes: (1) fix the search_text writer and backfill, or report coverage; (2) GET /v1/sessions/search over content_tsv with ts_headline snippets; (3) explicit scope in every list response plus harness/provider/session filters; (4) a separate investigation into why the #492/#493/#495 implementati... |
| [#504](https://github.com/littleorgans/transport-matters/issues/504) | `defer` | - | WP-24 | Deferred until a second presenter exists. Trigger recorded: when a second presenter appears, the Gateway owns entries[] and index, can_go_back/can_go_forward are derived, and the pushState question is answered. |
| [#515](https://github.com/littleorgans/transport-matters/issues/515) | `keep` | - | WP-03 | watch_status() over every subscription the run holds and watch_status(target) for one, each carrying target, events, registered_at, last_event_at, deliveries, target_state and shadowed_by, with empty distinguishable from error. Additive read over existing state. |
| [#523](https://github.com/littleorgans/transport-matters/issues/523) | `umbrella_keep` | - | WP-17 | Request class vocabulary, native-control matrix per harness, runtime-overlay and interactive-direction profiles, public corpus export. #611 already split out. Items 2-4 improve when the release carries both shapes but do not require it to start. The byte-splicing prohibition retained in this body conflicts with #455/#457's byte-diff ac... |
| [#555](https://github.com/littleorgans/transport-matters/issues/555) | `keep` | - | WP-22 | Normalize the grok observed_model suffix so the roster reports a model id a harness can answer for, keep the raw response value on the event, and pin declared-to-observed resolution per harness with a regression. grok-4.5 behaviour unverified. |
| [#565](https://github.com/littleorgans/transport-matters/issues/565) | `keep` | - | WP-14 | Authenticate Canvas presenter registration and bind it to a genuine Electron instance: a rogue loopback process registering first cannot become the selected composited presenter or publish a devtools origin under a genuine identity. |
| [#573](https://github.com/littleorgans/transport-matters/issues/573) | `keep_scope_reduce` | - | WP-04 | Items 1 and 2 stand in full: LivePromptDeliveryBindings must hold every pending binding claimed by its own digest, and a Codex merged user message must match a delivery whose prompt text is one line of it with the per-delivery outcome ruled. Item 3 is PARTIALLY shipped: #629 gives evidence-driven reconciliation for deliveries created i... |
| [#574](https://github.com/littleorgans/transport-matters/issues/574) | `keep` | - | WP-03 | pane(run_id, max_chars?) returning the snapshot under the server cap, satisfied by an observer grant, resolving the gateway that actually owns the terminal, with the post-exit read decision recorded. |
| [#592](https://github.com/littleorgans/transport-matters/issues/592) | `keep` | - | WP-02 | Content-anchored overrides: anchor required for the four positional kinds and rejected at the store boundary without one, resolution by anchor with index as hint, a miss producing applied:false with reason anchor_miss and rewriting nothing. |
| [#593](https://github.com/littleorgans/transport-matters/issues/593) | `umbrella_keep` | - | WP-25 | Tracking only. Zero implementation. Acceptance aggregation across #595-#600. #2 and #594 shipped (PR #615 / 0ee82d2b) but do not complete the program. |
| [#595](https://github.com/littleorgans/transport-matters/issues/595) | `keep` | - | WP-09 | One pure resolver over requested / limiting / override / effective, omitted distinguished from explicit none, the frozen decision persisted and used for identity, bearer minting and home seeding. |
| [#596](https://github.com/littleorgans/transport-matters/issues/596) | `keep` | - | WP-09 | A validated ordered catalog of the current tool set with one capability and one minimum grant per entry, validated before first registration, with registrar-drift tests. Engineering resolution (was OD-7): assert the invariant (every registered tool appears exactly once, in order, with one capability and one minimum grant) and let the o... |
| [#597](https://github.com/littleorgans/transport-matters/issues/597) | `keep` | - | WP-10 | Run-scoped tools/list filtering from the frozen capability tuple plus effective role, rejecting hidden calls before dispatch. Existing call-time authorization stays as the backstop. |
| [#598](https://github.com/littleorgans/transport-matters/issues/598) | `keep_rewrite` | - | WP-15 | Preview of requested grant, Canvas ceiling, override state, effective grant and requested capabilities on the selected row; future-launch-only semantics; existing runs frozen. DOWNGRADE the #597 dependency from hard to sequencing unless the UI is changed to consume a server-filtered catalog. |
| [#599](https://github.com/littleorgans/transport-matters/issues/599) | `keep_scope_reduce` | - | WP-16 | Mechanical SDK port: mcp>=2.1,<3, lock regeneration, MCPServer, snake-case internals, HTTPX 2 client support, unchanged wire/auth/catalog behaviour. STRIKE the transport-setting relocation; #600 owns it. |
| [#600](https://github.com/littleorgans/transport-matters/issues/600) | `keep` | - | WP-16 | Sole owner of the transport settings move, the exact /mcp mount, explicit server version, the 4194304/4194305 boundary, legacy and modern client proof, seeded homes and one real bounded captured run. |
| [#602](https://github.com/littleorgans/transport-matters/issues/602) | `defer` | - | WP-24 | Deferred as a design note with a recorded trigger. Unique undecided product content: the SHA is the unit of handoff, gate evidence attaches to a SHA, the loop terminates only when both agents bless the same SHA, and one round trip's token cost is measured before tuning. |
| [#603](https://github.com/littleorgans/transport-matters/issues/603) | `keep_split` | - | WP-14 | Split: the diagnosability half (a refusal that names its cause, a separate mint verb) ships independently and immediately. Engineering resolution (was OD-8): the attach-window relaxation stays gated on #565, because it rests on a presenter binding #565 shows is forgeable by any same-host loopback process. Widening a window over a forge... |
| [#611](https://github.com/littleorgans/transport-matters/issues/611) | `keep` | - | WP-07/WP-17 | Derived request-purpose fixtures at harness/version/model/profile/class with a check mode that fails on a changed projection and names what changed. Explicit split out of #523, sequenced ahead of it. |
| [#624](https://github.com/littleorgans/transport-matters/issues/624) | `keep` | - | WP-03 | Preserve the code and message the gateway actually wrote so an idempotency conflict is distinguishable from a generic invalid_request; unknown codes still map from status. Decide launch_failed explicitly. |
| [#630](https://github.com/littleorgans/transport-matters/issues/630) | `umbrella_keep` | - | WP-25 | Tracking only. Zero implementation. The live regression epic for the three discovery/resolution/verification defects; keep #631/#632/#633 links and add the settled-doctrine pointer to docs/HARNESS-COMPATIBILITY.md. Engineering resolution (was OD-9): do NOT reparent #383/#384 here. #384 keeps the owned-overlay obligations under #381; cr... |
| [#631](https://github.com/littleorgans/transport-matters/issues/631) | `keep` | - | WP-01 | Refreshed codex enumeration as primary with bundled fallback, all visibility values admitted, separate enumeration timeout, typed sanitized failures, additive merge that retains a model absent from a successful result. |
| [#632](https://github.com/littleorgans/transport-matters/issues/632) | `keep_rewrite` | - | WP-01 | Version-independent target offering, installed version separated from observation provenance, deletion of allow_unverified_target/opt-in vocabulary, VerificationCell instead of a target_unavailable rejection. REWRITE the entitlement bullet: keep account_entitlement_unavailable in launch resolution, move only its evidence source to #470... |
| [#633](https://github.com/littleorgans/transport-matters/issues/633) | `keep_split` | - | WP-05 | Split into four landable slices: (a) reference selection policy with exact precedence and sibling alternatives, (b) verification phase/state contract, (c) durable deduplicated queue with restart recovery, (d) retention plus the read-only support-verdicts route. NOT blocked on a certify --all run: first-turn-only references are compared... |

## 4. Owner decisions

Three. Each is a case where two ratified positions disagree and engineering cannot choose without inventing a
product decision. Seven further questions raised by the proposal were ordinary engineering judgments and are
resolved on their own issues; `grooming-review.md` lists them and their resolutions.

### OD-1. How is a model that has never been compared presented, given that #633 asks for a provisional degraded and the codebase says an uncompared version has no state at all?

Affects: [#633](https://github.com/littleorgans/transport-matters/issues/633), [#384](https://github.com/littleorgans/transport-matters/issues/384), [#477](https://github.com/littleorgans/transport-matters/issues/477), [#630](https://github.com/littleorgans/transport-matters/issues/630)

**Recommendation.** Store no verdict and present 'verification pending' with an explicit phase and reason. Do not store degraded before a comparator runs, and do not display the word degraded for a pending model. The proposal's 'store unknown, display degraded, verification pending' was rejected on review: it gives the word two meanings at the only place an operator reads it, which is exactly the property support_state.py and CLAUDE.md protect. Truthful pending still satisfies #633's real outcome, that a first launch is never silently verdictless, because a pending phase with a reason is a state. What remains genuinely product policy is the posture: does the launch view treat pending as a caution (warn before launch) or as neutral information? Recommendation: neutral, with the phase visible, since nothing is ever blocked and the comparison completes on first launch anyway.

Evidence:

- support_state.py:63-73 verified at HEAD 56cd5755: two members only; an uncompared version is the absence of a SupportVerdict
- issue-633.md: 'An uncovered model begins at degraded with reason verification_pending'
- issue-384.md comment 3: comparator failure leaves the status unchanged; absence of evidence is a trigger to retry, not a verdict
- CLAUDE.md: degraded means overlay fidelity is compromised and carries that one meaning everywhere

### OD-2. Does a stored runtime provider refusal keep gating launch, reversing the 2026-09-04 approved removal, and what account identity scopes it?

Affects: [#470](https://github.com/littleorgans/transport-matters/issues/470), [#632](https://github.com/littleorgans/transport-matters/issues/632), [#477](https://github.com/littleorgans/transport-matters/issues/477)

**Recommendation.** Keep the gate, scoped to an account. #632's 2026-09-05 comment reverses its own body and the earlier approved removal, so this is a product-policy reversal and not a bookkeeping fix: it decides whether TM ever refuses a launch on evidence it learned at runtime. Recommendation is keep account_entitlement_unavailable in launch resolution reading from the session store (#470), remove only the baseline-attempt read from resolver snapshots (#632), because a 400 was actually observed and the vendor catalog is not account aware for this case. Scope the exclusion by an account identity derived from the credential or route in use, never provider+model alone and never the executor id; if no stable account identity is available, #470 must state that an account change requires an operator clear and carry it as acceptance. Provider is not an account.

Evidence:

- issue-632.md 2026-09-05 comment reverses the body's removal bullet
- issue-630.md: codex enumerates gpt-5.2 while this account's subscription answers 400, so vendor filtering is not account aware here
- issue-470.md: names the provider account as the natural key, then specifies provider+model
- #631's additive-merge rule keeps a dropped model's previous row, so vendor filtering could not be relied on even if it were account aware

### OD-3. Does #523's retained prohibition on byte splicing stand against #455/#457/#458's byte-diff and prose-regeneration requirements?

Affects: [#523](https://github.com/littleorgans/transport-matters/issues/523), [#455](https://github.com/littleorgans/transport-matters/issues/455), [#457](https://github.com/littleorgans/transport-matters/issues/457), [#458](https://github.com/littleorgans/transport-matters/issues/458)

**Recommendation.** Rule one way and edit the loser. #457 cannot meet its own byte-diff acceptance and #458 cannot regenerate tool prose on the wire without the mechanism, and #523's ruling predates #455's measurement while its own body has since cancelled the raw executor that motivated it. Recommendation: qualify #523's line to bar an unaudited splice rather than the mechanism, and require every splice to go through prepare_outbound_request so a failure forwards original bytes. If the ban stands instead, #457 and #458 need new acceptance criteria before either is scheduled.

Evidence:

- issue-523.md retained decision prohibiting byte splicing
- issue-457.md acceptance requires a per-harness byte diff
- issue-455.md carries the token measurement that postdates the ruling
- CLAUDE.md: prepare_outbound_request already returns the original IR and original bytes on any serialization failure

## 5. Declared unknowns

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
- Seven of the proposal's ten owner decisions were resolved here as ordinary engineering (OD-3 #457/#597 sequencing, OD-5 #482 credential placement, OD-6 #446 boundary, OD-7 #596 tool count, OD-8 #603 attach gate, OD-9 lifecycle parent, OD-10 certify --all ownership). Each resolution is recorded on the issue it belongs to. Any of them can be escalated, but none is a product-policy conflict.
- The repository has moved one commit past the snapshot: HEAD is 56cd5755 (#634, activity reconcile bounding and event run index) against manifest head 53511834. #634 touches packages/activity reconcileLoop and the event index only, so no disposition here depends on it. Every claim in this file is stated against the snapshot.
- The #381 retention is a scope judgement, not a measurement. If the owner promotes Goal 3 (power-user overlay versioning) to its own issue and accepts docs/HARNESS-COMPATIBILITY.md as the home of the lifecycle doctrine, #381 becomes closable at that point and the open count drops by one more.

---

43 issues, 43 dispositions, 25 packages, 1 closure, 3 owner decisions.
Snapshot `535118346ca5d0584a7a4a3da28a55be532dc3bd`; repository HEAD at review time `56cd5755`. No GitHub or source mutation.
