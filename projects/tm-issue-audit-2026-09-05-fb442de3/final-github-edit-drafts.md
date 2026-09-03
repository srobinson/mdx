# GitHub edit drafts, corrected

Local drafts only. **Nothing here has been applied.** No issue, comment, label or link was mutated.
Snapshot `535118346ca5d0584a7a4a3da28a55be532dc3bd`; all 43 issues open at synthesis time.

This supersedes `github-edit-drafts.md`. Changes from it: section B is now a retention amendment on #381 instead
of a closure, D2 is a cross-link instead of a reparenting, and sections F and G carry the drafts that were
previously deferred behind owner decisions now resolved as engineering.

Apply in order: survivor amendments first, then the one closure, then the scope corrections, then link hygiene.
A closing comment must never be posted before its survivor carries the transferred acceptance.

---

## A. The one closure: #459 into #460

### A1. First, amend #460, append this section to the body

```markdown
## Kernel research inputs absorbed from #459

The kernel decision covers the execution environment and result protocol, not only a tool schema: sandbox and
approval policy, known cwd and an explicit workdir, shell and PATH guarantees, process lifecycle, output limits
and truncation, structured patching, safety enforcement below the model, and verification guidance.

Preserve the just-bash benchmark and its reproduction script. `sed`, `find`, `grep` and `wc` matched native output
in the recorded benchmark; `rg` was the outlier, so the tool contract must not document `rg` until that
implementation gap is resolved.

Keep the isolation tradeoffs: OverlayFs, ReadWriteFs cost, and Vercel Sandbox, including the absence of process
lifecycle and hard VM isolation in just-bash.

The experiment measures end-to-end tokens, retries, wall clock, turns, success and failure categories alongside
request bytes. It must answer whether a provider accepts a `tool_use` for an undeclared tool, and whether a
companion mechanism is needed for PTY or long-running work. These findings decide whether the portable kernel is
worth building on and which controls #457 needs.

Absorbed from #459, which is closed as superseded. No result is claimed by that absorption.
```

Also on #460: keep the `Parent: #455` relationship, and once #455 gains real sub-issue links (section D1) let the
link replace the prose line.

### A2. Then, close #459 with this comment

```markdown
Closing as superseded by #460 after transferring the research record.

#459 was explicitly a back-pocket, unscheduled note. Its just-bash benchmark and reproduction method, the codex
execution-kernel checklist, the process and isolation gaps, and its open questions are now #460's reference
section and inputs to the concrete just-agent experiment.

#460 owns the remaining work: build the just-bash MCP server, run the same-task A/B unattended on a frontier
model, measure request bytes and end-to-end tokens separately, classify failures, and report the result whichever
way it falls.

No implementation and no experiment result is declared complete by this closure.
```

---

## B. #381 is retained, not closed (reverses the previous draft's section B)

The earlier draft proposed closing #381 into #630 once #383 and #384 were reparented. **Do not apply it.** #630's
own outcome is scoped to discovery, resolution and first-launch verdicts, with #631/#632/#633 as its children.
#381 owns the wider Autopilot arc, and its Goal 3 (inspect, fork, edit, save named versions, compare token impact,
restore, return to the TM-managed overlay) exists in no other open issue. Making the closure legal required moving
Goal 3 into #384 and reparenting two children under a bug epic. Amend instead.

### B1. #381, append to the body

```markdown
## Scope note, 2026-09-05

This issue is a tracking parent and carries no implementation of its own.

Goal 1 is #383. Goal 2's owned-overlay application authority is #384. Goal 3, power-user overlay inspection,
forking, named versions, token comparison and restore, remains future work here and is promoted to its own issue
once #384 proves the single overlay authority.

#630 is the live regression epic against Goal 2's release lifecycle: enumeration acting as permission, retained
targets not surviving a version change, and an unreferenced model getting no verdict. It is a separate parent with
its own children (#631, #632, #633). This issue does not absorb it and is not absorbed by it.

The settled lifecycle doctrine now lives in `docs/HARNESS-COMPATIBILITY.md`. This issue keeps only the parent
acceptance, including the older-release support policy decision.
```

### B2. #630, append to the body

```markdown
Related parent: #381 owns the Autopilot product arc these three defects regress. This issue stays scoped to the
three discovery, resolution and verification defects and to #631/#632/#633.
```

No closing comment is drafted for #381, and none should be posted.

---

## C. Stale-scope corrections (each is a body amendment, no closure)

### C1. #632, replace the entitlement bullet

Replace the scope bullet reading *Remove `account_entitlement_unavailable` from launch resolution ... The vendor's
refreshed catalog is account aware, so entitlement filtering arrives from the source* with:

```markdown
- Move the `account_entitlement_unavailable` read from the on-disk baseline attempts to the session store and
  **keep it in launch resolution**. #470 carries the storage change and this issue depends on it. Only the
  baseline-attempt read is removed from resolver snapshots.

  Corrected 2026-09-05: the catalog is not account aware for this case. Codex enumerates `gpt-5.2` while the
  provider answers 400 for a ChatGPT account. #631's additive-merge rule compounds it: a model a refreshed
  catalog drops keeps its previous row and stays offered, so vendor filtering could not be relied on even if it
  were account aware. Everything else in this issue stands: version equality, release attribution, observation
  status and the unverified opt-in all stop gating.

  This bullet reverses the 2026-09-04 approved removal and is pending owner ratification (OD-2).
```

### C2. #470, correct the identity key and the borrowed name

```markdown
## Correction, 2026-09-05

Two clarifications before implementation.

**Identity.** The scope says the natural key is the provider account, then specifies keying by provider and
model. Provider is not an account. Under provider+model, switching from a subscription to an API key, or running
two accounts on one machine, inherits a refusal that does not apply, with no way to clear it. Define the account
key from the credential or route identity, or record explicitly that an account change requires an operator
clear. Either way, add the criterion:

- A refusal recorded under one provider account is not applied to a different account on the same machine.

**Name.** This is a *runtime provider-refusal exclusion*, not an enumerated block in the #384 sense. #384's
`blocked_versions` are publisher-declared release data carrying a `block_reason_code`. This is per-operator
runtime evidence learned from a 400. Borrowing the name imports authority from a mechanism it does not use.
```

### C3. #573, strike the shipped half of item 3, restate the rest

Replace scope item 3 with:

```markdown
3. **Correlation without a waiter.** Partly shipped by #629 (HEAD `53511834`): `ResidentDeliveryReconciler`
   reconciles from durable facts after scoped doorbells, so a row nobody waits on now correlates. **Still open:**
   `ResidentDeliveryReconciler.track` is called only at delivery creation (`prompt_delivery.py:128`), and
   `startup_passes.py` registers lifecycle reconciliation only. A delivery row left pending by a previous gateway
   process is registered nowhere and never reconciles. Add a startup sweep that discovers open delivery rows and
   reconciles them. Test: restart with an open row and reach a terminal state without any `wait_for_reply`.

   This remaining half is inferred from source reading, not from a restart experiment. Confirm by restart before
   scheduling the fix.

   Note that #629 also removed this issue's accidental mitigation. A stranded row used to correlate on the next
   wait against that run. A row stranded across a restart now never will, so the remaining half is more urgent
   than the original P5 label suggests.
```

### C4. #384, strike the resolved blocker, keep the overlay contract

```markdown
## Status correction, 2026-09-05, verified at 53511834

**The `maximum_version` blocker in comment 2 is resolved.** All three parts are shipped:
`blessed_ceiling()` returns `maximum_version or baseline_version` (`compatibility.py:565`), `range_position()` is
the comparator trigger (`:581`), and `harness_version_blocked` is now raised only by an enumerated
`blocked_versions` entry of scope `version` (`:686`). The live-release table in that comment is stale.

**Comment 1 is superseded by comment 3.** Below-MIN blocking is *not* shipped and stays unshipped:
`COMPATIBILITY_ROLLOUT = "advisory"` (`compatibility_service.py:101`). Read comment 3 as the ruling.

**The settled lifecycle doctrine moves to `docs/HARNESS-COMPATIBILITY.md`** and out of this issue.

**What this issue still owns, and it is not doctrine.** No overlay application package exists at this SHA;
`overrides/` is the operator-authored path and `cli/home_overlay.py` is filesystem seeding. The acceptance below
stands unchanged and unbuilt:

- A known certified release selects and applies the expected TM overlay automatically.
- A provider-bound capture proves the actual outbound request contains the expected transformation.
- The original request, overlay version, provider-bound request, audit and response are inspectable.
- No-drift and compatible-drift fixtures continue safely; breaking drift, application failure and preimage
  failure each produce exact unoptimized passthrough with a truthful notice.
- The older-harness support policy is decided, documented and tested at its boundary.
- The upgrade button is specified: it executes rather than displays, and it knows whether a captured run is in
  flight.

This issue remains a child of #381 and is not reparented.
```

### C5. #477, remove the blanket advisory clause

Strike the requirement that every resolver rejection becomes advisory, and add:

```markdown
Scope correction: this issue owns the per-run status surface, not resolver rejection policy. #632 owns which
rejections stop gating. A sanctioned runtime provider-refusal exclusion (#470), a disabled harness, a missing
executable and a retired target remain hard prerequisites and must render as such. Acceptance must distinguish an
advisory target-recognition state from a hard launch prerequisite, and must show pending verification, blessed,
degraded, no reference and provider refusal truthfully and differently. Pending verification renders as pending,
never as degraded (see #633).
```

### C6. #368, rewrite the mechanism, keep the acceptance

```markdown
## Mechanism correction, 2026-09-05

This issue predates the request-purpose classifier (#557 / PR #559, now pinned by #611's fixtures) and #592.

- Drop *detection ships as data, not code*. Building a second detector for a question the classifier already
  answers would duplicate it. This issue is a **consumer** of the existing classification at the breakpoint pause
  branch.
- The second stated harm, a positional edit authored on an auxiliary shape clobbering the main turn, is #592's
  defect class and is fixed there for every request shape, not only auxiliary ones. Track it on #592.

The acceptance is unchanged: with a breakpoint armed, a title-generation turn and the quota probe cross
un-paused while the user-composed turn pauses; auxiliary passthrough is recorded in the exchange record, not
silent; the pinning test derives from run `163c35b4`'s three captured shapes.
```

### C7. #599, remove the duplicated transport relocation

```markdown
Scope correction: moving `stateless_http`, `json_response` and `streamable_http_path` from the server constructor
to `streamable_http_app()` belongs to #600, which already assigns itself the same work. This issue's constraint
already says transport configuration moves in the following issue; the implementation guide contradicted it.
Remove the relocation here. This issue is the mechanical SDK port and client-fixture migration, with wire, auth
and catalog behaviour unchanged.
```

### C8. #598, downgrade the #597 dependency

```markdown
Dependency correction: #597 is sequencing, not a code dependency. This UI renders requested grant, Canvas
ceiling, override state, effective grant and requested capabilities; it does not consume a server-filtered
catalog. The real dependency is #595's resolved decision plus #594/#596's requested capability metadata. Reinstate
a hard #597 dependency only if the UI is changed to display a server-produced filtered catalog.

Also: #472 should land first. Canvas settings do not currently survive a channel home wipe, so a consent
persistence claim here would be untrue until it does.
```

---

## D. Link hygiene (no body text)

### D1. #455, create real sub-issue links

`manifest.json` records `sub_issues: []` for #455 while #456, #457, #458, #459 and #460 each declare
`Parent: #455` in prose. Create the real links for #456, #457, #458 and #460. (#459 closes into #460 first, per
section A.) Until then the epic reads as unlinked work.

### D2. #630 and #381, cross-link only

Do **not** add #383 or #384 as sub-issues of #630; that was the previous draft's precondition for a closure this
review reverses. #383 and #384 stay under #381. Add the reciprocal related-issue references from section B
instead, so the regression epic and the product arc each stay legible without absorbing the other.

---

## E. Engineering resolutions, now drafted

These were owner decisions in the proposal. They are ordinary engineering judgments and are resolved here.

### E1. #457, sequencing rather than a dependency on #597

```markdown
Sequencing note, 2026-09-05: #597 is not a dependency of this issue. The codex and grok arms are independent of
it. On the claude arm only, disabling builtins un-defers the MCP tool schemas, so a token measurement taken
without #597 is a measured regression there.

Acceptance addition: the claude arm either lands after #597, or reports the un-deferred MCP tool schemas inside
its own token measurement and states the regression rather than hiding it.

Naming: this issue and the authority program (#595-#598) use "capability" for two different things, a harness
builtin tool here and an MCP grant capability there. Give them distinct names before either lands.
```

### E2. #446, document the boundary (the issue's option 2)

```markdown
Decision, 2026-09-05: take option 2. Document `harvest` as debug-only single-cell evidence that never changes a
release, with `publish` as the normal workflow, and put that sentence in the command help.

Rationale: the duplication a fold would remove is already absent. `baseline_publish` imports `harvest_baseline`
and passes each planned cell to it, so folding the CLI removes no implementation and only adds migration risk.
Revisit only if an operator needs harvest output to reach a release.
```

### E3. #596, assert the invariant, not a literal count

```markdown
Scope note, 2026-09-05: do not assert a literal tool count in prose or in a test. Assert the catalog invariant,
that every registered tool appears exactly once, in order, with one capability and one minimum grant, and let the
observer and director counts fall out of it. A number goes stale on the next tool; the invariant does not.
```

### E4. #603, the attach-window relaxation stays gated on #565

```markdown
Split and sequencing, 2026-09-05: the diagnosability half ships now and independently, a refusal that names its
cause plus a separate mint verb.

The attach-window relaxation stays gated on #565. It rests on a presenter binding #565 shows is forgeable by any
same-host loopback process, so widening the window before registration is authenticated is a security regression
rather than a scheduling preference.
```

### E5. #482, credentials must outlive the channel home

```markdown
Acceptance addition, 2026-09-05: the credential predicate is only a verdict if the credential outlives the
channel home. Either place the harness auth home outside the disposable channel home, or detect the invalidation
on the next launch and tell the operator. This is the same failure class as #470 and #472.
```

---

## F. Pending an owner ruling

### F1. #633, the pending-verification wording (OD-1)

Recommended text, to post once OD-1 is ratified. It replaces *An uncovered model begins at `degraded` with reason
`verification_pending`*:

```markdown
An uncovered model has no stored verdict until a comparator runs. It carries an explicit verification phase with a
reason, and the launch view and run status bar present it as *verification pending*, never as degraded.

`SupportState` keeps exactly two members and `degraded` keeps one meaning, overlay fidelity is compromised
(`support_state.py:63-73`). A pending phase is still a state, so the outcome this issue actually wants, that a
first launch is never silently verdictless, holds. It also needs no retraction path for every model that comes out
blessed.
```

### F2. #523, the byte-splicing prohibition (OD-3)

No amendment drafted. The owner rules between #523's retained prohibition and #455/#457/#458's byte-diff
acceptance; whichever loses gets the edit. Recommended shape if the prohibition is qualified:

```markdown
The prohibition bars an unaudited splice, not the mechanism. Every splice goes through
`prepare_outbound_request`, so a serialization failure forwards the original bytes with no audit and no partial
write.
```

### F3. A `certify --all` publication issue

A new issue outside this 43-issue snapshot. Recorded under `unresolved` in `final-grooming.json`. It is coverage
improvement, not a blocker: the gate compares what a release carries without refusing the shape it lacks, so
WP-05 must not be sequenced behind it.
