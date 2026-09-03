# 368: Intercept: auto-passthrough aux turns (title generation) when a breakpoint is armed

URL: https://github.com/littleorgans/transport-matters/issues/368
State: open
Labels: 
Updated: 2026-08-08T06:53:49Z

## Problem

An armed breakpoint pauses every request on the flow, including harness machinery turns the user never composed. In live run `163c35b4` (claude 2.1.225, 2026-08-08) the title-generation turn paused under the armed breakpoint alongside the real user turn. The user's mental model of arming is "pause *my* message"; pausing aux turns is UX noise, and an edit made against an aux shape can be stored as a standing override that later applies to the wrong shape (observed: a positional `system:2` edit from the title shape clobbered the main turn's output-style part in the curated view, chars_delta -17574).

## Evidence (captured run 163c35b4)

- Title turn `8ef59528`: 715 input tokens, `max_tokens` small, `tools=0`, **zero `cache_control` breakpoints, zero cache creation/read** — the harness itself treats the shape as disposable machinery.
- Quota probe `90dd55dc`: `messages=[{user:"quota"}]`, `max_tokens=1` — same aux class.
- Main turn `4ebc9944`: the only turn the user actually composed.

## Direction (agreed 2026-08-08)

- Auto-passthrough aux turns at the **pause branch only** (`addon_handlers` breakpoint evaluation). The overlay/curation layer needs no special-casing: content-digest operations apply wherever preimages match.
- **Detection ships as data, not code**: aux-shape fingerprints belong in the managed overlay artifact (same fingerprint machinery as variant selection in the overlay registry spec), never hardcoded in intercept code — what a title turn looks like is harness-shape knowledge that churns with every release. Corroborating signals available in-shape: no cache breakpoints, tiny `max_tokens`, zero tools.
- Interim acceptable: a conservative built-in heuristic behind the same seam the fingerprint data will later own, provided the seam is the artifact-consuming one.

## Acceptance

- With a breakpoint armed, a title-generation turn and the quota probe cross the wire un-paused; the user-composed turn still pauses.
- Aux passthrough is visible in the exchange record (aux classification recorded), not silent.
- Pinning test derived from run `163c35b4`'s three captured shapes.

Refs: overlay registry spec (`~/.mdx/projects/transport-matters-spec-overlay-registry.md`) aux-turn ruling; positional-clobber repro same run.

## Sub issues
[]


# 381: TM Autopilot: first-turn education, controlled harness baselines, and owned overlays

URL: https://github.com/littleorgans/transport-matters/issues/381
State: open
Labels: enhancement
Updated: 2026-08-12T13:26:24Z

## Product goal

Transport Matters is the harness and token optimization authority across supported harnesses, providers, and models.

The product has three ordered capabilities:

1. An optional first-time report that proves the problem using the user's real first full turn.
2. TM Autopilot, the core paid capability, which controls the harness environment, understands request shapes, manages release compatibility, and applies TM-owned optimizations.
3. Future power-user controls for inspecting, customizing, and versioning overlays.

## Goal 1: optional first-turn education

Provide a one-off welcome and onboarding HTML report. The user can skip it and invoke it later.

Value proposition:

> Let me show you how much junk your harness sent with your request and will send repeatedly.

The report uses the user's real harness environment and first full provider-bound turn. Auxiliary requests such as prewarm, title generation, token counting, and health checks are excluded.

The report must show:

- the complete captured request safely rendered
- total bytes, characters, and tokens
- exact token counts when authoritative, clearly labelled estimates otherwise
- totals by API role: system, developer, user, assistant, tool, and metadata
- totals by provenance: user-authored, user-configuration-derived, session-derived, static harness content, provider metadata, and unknown
- every textual leaf with exact JSON Pointer, digest, characters, tokens, role, provenance, and classification evidence
- observed facts separately from inferred classifications

This path is read only. It does not require overlay support.

## Goal 2: TM Autopilot

Autopilot is the product USP. TM controls harness configuration, settings, and ephemeral homes, then minimizes provider requests safely.

A temporary feature flag or emergency escape hatch may use a name such as `TM_AUTO_PILOT`. Final naming and user-facing behavior remain TBD. Mature Autopilot should be enabled by default.

### Controlled capture

Reuse the existing ephemeral-home and agent-runtimes integration. Do not create a second runtime-home mechanism.

For each relevant harness, harness version, provider, model or model family, and request shape, launch controlled probes with:

- the known minimum settings required to pass harness onboarding
- no user skills
- no user MCP servers
- no user memory
- no project customization
- deterministic probe prompts
- fresh session state

These captures are internal TM certification evidence.

### Derived artifacts

Produce and persist four distinct artifacts:

1. Observed wire schema: exact paths, types, cardinality, optionality, and structural relationships seen across controlled captures.
2. Semantic mapping: provider fields mapped into TM IR system parts, messages, tools, sampling, metadata, and provider extras.
3. Static baseline: exact harness-supplied content, content digests, and request fingerprints.
4. Overlay: approved transformations for a matching harness/provider/version and request shape.

A schema inferred from captures is an observed schema, not an exhaustive provider contract. Multiple deterministic probes should strengthen it over time.

### Harness release lifecycle

At runtime, detect the installed harness version and resolve its compatibility state:

- Known certified release with matching shape: apply the approved overlay.
- New release with no drift: certify and continue.
- New release with compatible drift: record the new shape and continue safely.
- New release with breaking drift: forward requests unoptimized, inform the user that support is being prepared, then update TM's adapter, IR mapping, schema family, or overlay.

Breaking drift must degrade optimization without breaking the user's harness request.

Supporting new harness releases is mandatory.

### Open support-policy decision

Decide how long TM supports older harness releases after a new release is blessed.

Initial proposal: support compatibility families rather than permanent version-specific branches. Keep the current and immediately previous breaking compatibility families. Older releases that still match an active family continue to work without separate code.

## Goal 3: future power-user overlay control

After Goal 2 establishes one TM-owned capture, classification, matching, application, audit, and persistence path, allow power users to:

- inspect the active TM overlay
- fork it into a user variant
- edit selected operations
- save named versions
- compare token impact
- restore an earlier version
- return to the TM-managed overlay

This must reuse Goal 2's overlay authority. No parallel mutation or persistence path.

## Cross-cutting requirements

- Multi-harness and multi-provider by design.
- JSON request extraction is generic. Provider adapters own semantic mapping.
- Every mutable text preimage corresponds to one actual raw string leaf. Aggregated display values retain constituent paths and digests.
- Preserve original request, overlay version, provider-bound request, audit, and response.
- Fail safely to unoptimized passthrough when compatibility or application cannot be proven.
- Keep first-turn education, internal certification, and overlay mutation as separate product concerns.

## Related work

- #370 tracks the narrower worksheet/export mechanism.
- #369 tracks the opaque Codex `additional_tools` request shape.
- Existing controlled capture and normalization work in `baseline_harvest.py` is the likely reuse owner.
- Existing request mutation remains `OverrideStore` through `run_pipeline` and `apply_overrides`.

## Implementation order

1. #385 separates authentication from usable provider access.
2. #386 promotes Grok to a first class managed harness.
3. #382 captures controlled baselines and observed request schemas after the supported harness contract is truthful.
4. #383 builds the optional welcome report from that evidence.
5. #384 applies TM-owned overlays through the certified release lifecycle.

## Parent acceptance

This parent is complete when:

- Goal 1 can render an optional first-full-turn HTML report from a real user launch.
- Goal 2 can capture a controlled harness baseline, derive an observed schema, classify release drift, select a compatible overlay, and prove the provider-bound optimized request.
- Breaking drift produces safe passthrough and a truthful user notice.
- The older-version support policy is decided and documented.

Goal 3 may remain a linked future issue once the underlying Goal 2 authority is proven.



## Comment by srobinson at 2026-08-12T12:03:30Z (updated 2026-08-12T12:03:30Z)

https://github.com/littleorgans/transport-matters/issues/381#issuecomment-5266550015

## Implementation order

GitHub sub-issues now track delivery:

1. #370 creates the generic exact-leaf request inventory.
2. #382 uses that inventory for controlled captures and observed schemas.
3. #383 consumes #370 and #382 for the optional first-turn HTML welcome report.
4. #384 consumes #370 and #382 for the runtime compatibility lifecycle and TM-owned overlay application.

#369 remains related parser work for the opaque Codex `additional_tools` shape. It does not block the raw request inventory.

Goal 3 power-user overlay versioning remains future work after #384 proves the single TM-owned overlay authority.


## Sub issues
[
  {
    "number": 370,
    "state": "closed",
    "title": "Request inventory: exact JSON leaves, digests, and semantic labels"
  },
  {
    "number": 382,
    "state": "closed",
    "title": "Autopilot baselines: controlled captures and observed request schemas"
  },
  {
    "number": 383,
    "state": "open",
    "title": "Welcome report: explain the first full provider request in HTML"
  },
  {
    "number": 384,
    "state": "open",
    "title": "TM Autopilot: release compatibility lifecycle and owned overlay application"
  },
  {
    "number": 392,
    "state": "closed",
    "title": "RESPONSES coverage table: declare the second hop for codex and grok"
  }
]


# 383: Welcome report: explain the first full provider request in HTML

URL: https://github.com/littleorgans/transport-matters/issues/383
State: open
Labels: enhancement
Updated: 2026-08-19T01:54:06Z

Parent: #381
Depends on: #370, #382

## Outcome

Provide an optional, one-off TM welcome and onboarding report that demonstrates the problem using the user's real first full provider-bound request.

Value proposition:

> Let me show you how much junk your harness sent with your request and will send repeatedly.

The user may skip the report during onboarding and invoke it later.

## Request selection

Use the first full user turn. Exclude auxiliary traffic such as:

- prewarm
- title generation
- token counting
- health checks
- other harness housekeeping

Selection evidence must be explicit. Do not assume the first chronological exchange is the first full turn.

## HTML report

Safely render:

- the complete captured request
- total bytes, characters, and tokens
- exact token counts when authoritative and clearly labelled estimates otherwise
- totals by API role: system, developer, user, assistant, tool, and metadata
- totals by provenance: user-authored, user-configuration-derived, session-derived, static harness, provider metadata, and unknown
- every textual leaf with exact JSON Pointer, digest, counts, role, provenance, confidence, and evidence
- observed facts separately from inferred classifications

The report is read only. It does not apply or author an overlay.

## Experience

- Available during first-time onboarding.
- Skippable without blocking launch.
- Reopenable later from the product.
- Large fields remain inspectable without making the report unusable.
- Sensitive content stays local and is escaped safely.

## Acceptance

- A real TM launch produces the report from the selected first full turn.
- The report clearly compares the user's prompt footprint with the complete provider request footprint.
- Static harness claims are backed by controlled baseline evidence; otherwise they remain unknown or lower confidence.
- Claude and Codex reports consume the same request inventory contract.
- Skipping the report does not block or alter the harness request.
- Reopening the report later renders the same persisted evidence.


## Comment by srobinson at 2026-08-19T01:54:06Z (updated 2026-08-19T01:54:06Z)

https://github.com/littleorgans/transport-matters/issues/383#issuecomment-5336550536

Prior art on disk: local branch `slice/native-capture-home`, checked out at `.claude/worktrees/harvest-gates`. Three commits, unmerged, and on a stale base (its diff against main would remove everything merged since, including #395).

Worth reading before starting this issue, particularly `1ce1e1ea fix(capture): use native homes for baseline harvest`, which is the same idea this issue asks for: capturing through the real HOME rather than a fresh empty one.

The other two are adjacent harvest-reliability fixes rather than capture design:

- `ca714eae fix(supervisor): close the pre-registration orphan window on both PTY spawn paths` shares `_rollback_failed_pty_spawn` between both spawn paths, makes the drain thread join deterministic before the master fd closes (a recycled fd could otherwise write one harvest cell's bytes into another's capture), and makes `baseline_harvest._capture_cell` report child exit instead of burning the full timeout. That last part is directly relevant to the slow-failure mode described in #397.
- `92ba19ab fix(harvest): require a trusted current workdir`.

It also carries one file main does not have: `api/tests/integration/test_captured_proxy_post.py`.

Treat it as a source to read and cherry-pick from, not a branch to merge. Rebasing it would be a fight.

## Sub issues
[]


# 384: TM Autopilot: release compatibility lifecycle and owned overlay application

URL: https://github.com/littleorgans/transport-matters/issues/384
State: open
Labels: enhancement
Updated: 2026-08-20T18:31:56Z

Parent: #381
Depends on: #370, #382

## Outcome

Make TM the harness and token optimization authority at runtime. Detect the installed harness release, prove compatibility against TM-owned evidence, select the matching TM overlay, and apply it before forwarding the request to the provider.

A temporary feature flag or emergency escape hatch may use a name such as `TM_AUTO_PILOT`. Final naming remains TBD. Autopilot is the core product capability, not a power-user overlay editor.

## Release lifecycle

At runtime:

1. Detect the installed harness and version.
2. Resolve its certified compatibility family and request shape.
3. For an unknown release, run the controlled capture and observed-schema comparison.
4. Classify the result:
   - no drift: certify and continue
   - compatible drift: record the shape and continue safely
   - breaking drift: forward unoptimized, notify the user truthfully, and await a supported TM release
5. Select and freeze the matching overlay for the run.
6. Apply it through the existing `OverrideStore` and `run_pipeline` / `apply_overrides` path.
7. Preserve the original request, overlay identity and version, provider-bound request, audit, and normal response.

No parallel mutation, validation, persistence, lock, or clock path.

## Safe degradation

When compatibility or application cannot be proven:

- forward the original request unoptimized
- keep the harness usable
- explain that optimization for the detected harness release is being prepared
- never claim an overlay applied without provider-bound evidence

## Older harness support policy

Decide and document the internal support policy before completion.

Initial proposal:

- model support as compatibility families rather than permanent per-version branches
- actively support the current and immediately previous breaking families
- allow older releases to continue when they still match an active family
- publish a minimum supported harness version when retiring a distinct family

Supporting new harness releases is mandatory.

## Overlay ownership

TM owns one approved overlay per compatible harness/provider/version and request shape. Each overlay binds to:

- compatibility family
- harness and release evidence
- provider
- applicable model family when required
- request fingerprint
- exact preimages
- operation set and overlay version

Power-user overlay editing and version management remain future work after this authority is proven.

## Acceptance

- A known certified release selects and applies the expected TM overlay automatically.
- A provider-bound capture proves the actual outbound request contains the expected transformation.
- The original request, overlay version, provider-bound request, audit, and response are inspectable.
- No-drift and compatible-drift release fixtures continue safely.
- A breaking-drift fixture produces exact unoptimized passthrough and a truthful notice.
- Application or preimage failure produces exact unoptimized passthrough.
- The older-harness support policy is decided, documented, and tested at its boundary.


## Comment by srobinson at 2026-08-20T10:30:26Z (updated 2026-08-20T10:30:26Z)

https://github.com/littleorgans/transport-matters/issues/384#issuecomment-5354680711

## Harness version lifecycle: owner decisions

Settled 2026-08-20. This is the lifecycle #384 exists to hold, and it supplies the trigger #399 phase 4 needs.

### The blessed range

A TM release blesses a harness across MIN..MAX. Example: TM v1.0.0 blesses HA.1 through HA.3.

| Observed version | State | Consequence |
| --- | --- | --- |
| below MIN | unsupported | surfaced; launch consequence still to decide |
| MIN..MAX, below MAX | supported, not current | meaningful upgrade reminder |
| MIN..MAX, at MAX | supported and current | nothing surfaced |
| above MAX | unblessed | run the comparator |

The below-MAX prompt is a reminder, not a nag. So "unsupported" and "supported but not current" are two distinct surfaced states with different urgency, and only the first carries a launch consequence.

### Above MAX: comparator outcomes

- **EXACT**: continue as normal. The next TM release widens MAX (min HA.1, max HA.4).
- **BREAKING**: every run on that version is flagged with a warning that normal operation may be degraded, with best effort to apply the request overlay. The next TM release moves to min HA.4, max HA.4.
- **DEGRADED**: `request_schema.py` ships three outcomes, not two. Degraded is the common case, a field added or a shape widened where nothing TM reads broke. Proposed, not ratified: launches and bumps MAX like EXACT, but records the delta so successive degradations cannot silently accumulate into a breaking change several releases later.
- **Comparator cannot run** (provider unreachable, harness not launchable, capture fails): the status does not change, and there is no new status for it. Deliberately the same principle already shipped in #398: absence of evidence is a trigger to retry, not a verdict. The runtime launches now and retries later; only the blessed range stands still.

### Single version, not many

TM does not aim to support multiple harness versions concurrently. Users want to be on the latest, and TM exists to manage that for them. So the BREAKING branch collapsing to min = max = HA.4 is intended, and stranding users on older versions is accepted rather than overlooked.

### Upgrade button

Surface a button that upgrades a harness in the background.

`credential_source.py` already holds a per-harness command table with `login_command` (`claude auth login`, `codex login`), surfaced through the inventory as `authentication_command`. `upgrade_command` belongs in that same table, which keeps adding a harness DRY.

Three implications, not yet decided:

1. It executes rather than displays, unlike `login_command`. TM would mutate a global install it does not own, and harnesses arrive via npm, homebrew, mise, or a native installer. `executable_path` is already recorded and is the strongest hint at install method; where the method is not confidently known, fall back to surfacing the command, as login already does.
2. Upgrading while captured runs are live will break them. The button needs to know whether any run is in flight.
3. It feeds the machinery already built: upgrade, re-detect, re-run verification (#402), then run the comparator if the new version is past the baseline. That is the #402/#408 startup chain triggered on demand, so the button is mostly reuse.

Sequenced after #399 phase 4. Once the comparator has a trigger this is a small addition; before it, it is a second half-built lifecycle.

### What this resolves for #399 phase 4

The comparator trigger must **not** be `maximum_version`. Verified on this tree: installed Claude is 2.1.237, TM's release is `claude-2.1.211-r2` with `minimum_version = 2.1.211` and **no `maximum_version`**. `compatibility:match_release` only returns `harness_version_blocked` when a maximum is declared and exceeded, so the branch is unreachable for claude and codex today, and only grok declares one. `maximum_version` also means "refuse to launch", which is harsher than "worth comparing". The blessed MAX above is the real trigger.


## Comment by srobinson at 2026-08-20T11:15:52Z (updated 2026-08-20T11:15:52Z)

https://github.com/littleorgans/transport-matters/issues/384#issuecomment-5355121601

## Lifecycle, refined

Three owner decisions that tighten the model posted earlier in this thread.

**1. The only process that upgrades MAX is a new TM release.** The comparator never mutates the blessed range at runtime. It produces evidence; widening MIN..MAX is a release-time decision made on that evidence. The blessed range stays declarative signed data.

**2. Below MIN blocks the agent.** It does not launch. This closes the open question from the earlier comment.

**3. Above MAX, BREAKING is best effort supported.** The run launches, carries a warning that normal operation may be degraded, and TM makes a best effort to apply the request overlay.

| Observed version | State | Consequence |
| --- | --- | --- |
| below MIN | unsupported | blocks the agent |
| MIN..MAX, below MAX | supported, not current | meaningful upgrade reminder |
| MIN..MAX, at MAX | supported and current | nothing surfaced |
| above MAX | unblessed | run the comparator, always launch, best effort |

Consequence for the three comparator outcomes: they all launch. EXACT, DEGRADED and BREAKING differ only in what is surfaced on the run and what evidence lands for the next release decision. DEGRADED's remaining open question is narrow, only whether it surfaces anything to the user. Proposed: silent, but recorded, so successive degradations do not accumulate unnoticed into a breaking change several releases later.

## Already shipped: below MIN

Nothing to build. `match_release` returns `harness_update_required`, and that literal is in `ResolutionRejectionCode` (`resolver_contracts.py`), so the launch target resolver already rejects it.

## Blocker for #399 phase 4: `maximum_version` means the opposite of blessed MAX

Verified in `compatibility.py:match_release`. When `release.maximum_version is not None and compare_versions(normalized, maximum) > 0` it returns `harness_version_blocked`, which is a `ResolutionRejectionCode`. Above MAX refuses to launch today. The lifecycle says above MAX always launches.

Live in `compatibility_releases_v1.json`:

| harness | release | min | baseline | max |
| --- | --- | --- | --- | --- |
| claude | `claude-2.1.211-r2` | 2.1.211 | 2.1.211 | none |
| codex | `codex-0.144.4-r2` | 0.144.4 | 0.144.4 | none |
| grok | `grok-1.0.4-r2` | 1.0.4 | 1.0.4 | 1.0.4 |

So grok 1.0.5 would be refused rather than compared, while claude and codex declare no ceiling at all and nothing can ever fire.

Proposed resolution, to settle in phase 4: `maximum_version` becomes the blessed ceiling and stops rejecting. Deleting that branch loses nothing, because "refuse this version" already has its own mechanism in `CompatibilityChannelState.blocked_versions`, which carries version, route, target and release scoped blocks with a `block_reason_code`. One concept per mechanism. Enumerated blocks refuse; the ceiling compares.

The trigger for the comparator is therefore: observed version above the blessed MAX. Installed Claude 2.1.237 against `claude-2.1.211-r2` is the live case waiting.


## Comment by srobinson at 2026-08-20T18:31:56Z (updated 2026-08-20T18:31:56Z)

https://github.com/littleorgans/transport-matters/issues/384#issuecomment-5360092711

## Two ratifications, and one correction to an earlier comment in this thread

Owner decisions, 2026-08-20 evening. Closes the two open rows in the lifecycle posted earlier.

### DEGRADED, ratified

DEGRADED launches like EXACT and is silent to the user, but the delta is recorded, so successive degradations cannot accumulate unnoticed into a breaking change several releases later.

Since nothing bumps the blessed MAX at runtime, this only ever concerned what is surfaced and what evidence is kept. The three comparator outcomes now all resolve:

| Outcome | Launches | Surfaced | Evidence |
| --- | --- | --- | --- |
| EXACT | yes | nothing | supports widening MAX next release |
| DEGRADED | yes | nothing | delta recorded so drift cannot accumulate silently |
| BREAKING | yes, best effort | warning that normal operation may be degraded | next release moves to min=max=new |

Note for sequencing: DEGRADED does not bite at the first harvest of a cell, because there is no stored reference so no comparison runs. It bites from the second.

### Below MIN does not block, and that stays

Correcting an earlier comment in this thread, which stated that below-MIN blocking was already shipped.

It is not. `COMPATIBILITY_ROLLOUT` is `"advisory"` in `compatibility_service`, and `resolver:_compatibility_disposition` only builds a `ResolutionRejection` when `compatibility_enforcing()` is true. So `harness_update_required` surfaces as an advisory and nothing refuses a launch today.

Making below-MIN actually block means flipping the rollout to enforcing, which changes behaviour for every gated launch rather than only for below-MIN. That is a larger decision than the one taken, so it is separated out.

Owner's decision: no change, no blocking. The blocking row in the lifecycle table is the intended end state, not current behaviour. Flipping the rollout is its own decision, taken on its own merits, later.

### What this leaves open on the lifecycle

Only the upgrade button, sequenced after the first harvest. Its three implications are recorded in the earlier comment and unchanged: it executes rather than displays, it needs to know whether a captured run is in flight, and it is mostly reuse of the #402 and #408 startup chain triggered on demand.


## Sub issues
[]


# 413: Revisit the overlay name sets and clean them up

URL: https://github.com/littleorgans/transport-matters/issues/413
State: open
Labels: 
Updated: 2026-08-20T18:31:13Z

The overlay carries eleven hardcoded name sets in `cli/home_constants.py`, three of which enumerate harness runtime state. They are a mirror of three harnesses' internals that Transport Matters does not own, cannot keep current, and that measurement suggests are largely inert. This issue is to revisit all of them and clean up.

## The three under most suspicion

| Set | Literal names | Effective |
| --- | --- | --- |
| `_CLAUDE_TEMPLATE_LOCAL_WRITABLE_NAMES` | 11 | 16, it unions `_CLAUDE_DAEMON_LOCAL_NAMES` |
| `_CODEX_TEMPLATE_LOCAL_WRITABLE_NAMES` | 33 | 33 |
| `_GROK_TEMPLATE_LOCAL_WRITABLE_NAMES` | 9 | 9 |

They tell `_symlink_template_content_entries` not to symlink an entry and `_materialize_local_writable_entries` to create a fresh empty one instead, so a launch cannot see or corrupt another run's session state.

## The measurement that prompted this

Checked all 58 effective names against every template in `~/.agent-runtimes/runtimes`: **zero matches**. Not one name in those sets corresponds to any entry in any of the eleven templates.

That is structural rather than luck. Both functions only act on an entry the template already carries. A template is generator-authored content that has never been launched into, so harness runtime state does not exist in it. And the protection actually relied upon is elsewhere: `_symlink_template_content_entries` only symlinks entries that *exist* in the template, so a name the harness invents at runtime is not there and lands in the overlay by construction. That mechanism needs no list, and it is why codex's `installation_id` already works.

The cost is a list that rots silently in the worst direction. An unlisted name gets symlinked, which is a write channel back into the source home.

## The complication, and why this is not a two line deletion

The sets are consulted for **every** template launch, not just captures. Specialist runtimes are not bare: eight of them ship a real `skills/` directory, and all eight declare codex.

So the sets are provably inert for control templates and **not** provably inert for specialist ones. That asymmetry is the actual question this issue exists to answer, and it must be settled before anything is deleted.

Related and separate, worth resolving alongside because it shares the mechanism: a codex launch from a specialist template symlinks `skills/` into the overlay, and `codex debug prompt-input` writes `skills/.system` as a bundled tree of six skills, roughly ninety entries. Verified against codex-cli 0.148.0 with `CODEX_HOME` pointed at an empty scratch directory. That is Transport Matters writing into agent-runtimes' runtimes, which breaks the clean contract rather than policing it.

## Also in scope

The other eight sets in the same module, for consistency and for whether each still earns its place:

- `_CLAUDE_DAEMON_LOCAL_NAMES`
- `_CLAUDE_OVERLAY_COPIED_NAMES`, `_CODEX_OVERLAY_COPIED_NAMES`, `_GROK_OVERLAY_COPIED_NAMES`
- `_CLAUDE_OVERLAY_CREDENTIAL_NAMES`, `_CODEX_OVERLAY_CREDENTIAL_NAMES`, `_GROK_OVERLAY_CREDENTIAL_NAMES`
- `_CLAUDE_OVERLAY_LOCAL_NAMES`, `_CODEX_OVERLAY_LOCAL_NAMES`, `_GROK_OVERLAY_LOCAL_NAMES`
- `_OVERLAY_NEVER_SYMLINK_NAMES`

The `_OVERLAY_LOCAL_NAMES` trio governs the native home path, where the source is the operator's real home and is genuinely full of runtime state. Those are load-bearing in a way the template sets are not, and the two families should stop looking alike if they are not alike.

Worth asking whether the per-harness split is the right shape at all, or whether one table keyed by harness would say the same thing in less code, which is also the repo's standing rule that adding a harness stays one edit.

## Definition of done

- A stated rule for what belongs in each family, written down, so the next name has an obvious home or an obvious rejection.
- Whichever sets are provably inert are deleted rather than trimmed.
- The specialist versus control asymmetry is resolved explicitly, not by omission.
- No new constraint is imposed on agent-runtimes. Per the owner: the contract is that the runtimes are always clean, and Transport Matters trusts it rather than guarding it.

## Context

The three template sets were briefly expanded during #412 (grok to 25 names, codex gained six) on a premise that turned out to be false, and reverted to byte-equality with main before merge. #412 also removed two guards built on that premise. This issue is the follow-up the owner asked for after that cull, and it is the question that prompted it: why do we need these at all.


## Comment by srobinson at 2026-08-20T18:31:13Z (updated 2026-08-20T18:31:13Z)

https://github.com/littleorgans/transport-matters/issues/413#issuecomment-5360084041

## Disposition: deferred, not P1

Owner's call, 2026-08-20. Worth digging into properly rather than patching now. agent-runtimes gitignores the `skills/` directory, so the pollution is regenerable and does not dirty their working tree.

Recording what is known so the dig starts from evidence rather than from scratch.

## The channel is confirmed real, and it has fired

agent-runtimes reports three specialist runtimes carried a `skills/.system` tree on 2026-08-19: `codebase-mapper`, `imagegen`, `transcript-matters`. All cleaned the same day. That sighting is what prompted their `--audit` in the first place.

It cannot be attributed. Three candidates and no surviving evidence to separate them: a TM codex launch through the overlay symlink, the owner's own testing pointing a harness directly at `~/.agent-runtimes`, or agent-runtimes' own `audit.py` running with `CODEX_HOME` pointed at a template. The `.codex-system-skills.marker` carried a build hash that would have dated the writer and it was deleted with the rest. So it is proof the channel exists, not proof TM wrote it.

## What codex actually writes

Verified against codex-cli 0.148.0, `CODEX_HOME` pointed at an empty scratch directory, `codex debug prompt-input`:

- `.sandbox_migration`, `installation_id`, `tmp/arg0` at the root
- `skills/.system` as a bundled tree of six skills (`imagegen`, `openai-docs`, `plugin-creator`, `review-agent`, `skill-creator`, `skill-installer`) plus `.codex-system-skills.marker`, around ninety entries

Codex-only. Claude writes `projects/`, `sessions/`, `shell-snapshots/` and daemon state, none of it into `skills/`.

## Exposure

Eight specialist runtimes ship a real `skills/` directory and all eight declare codex: `codebase-mapper`, `frontend`, `generalist`, `imagegen`, `orchestrator`, `research`, `skill-matters`, `transcript-matters`.

Control templates are not exposed. `tm/capture` and `tm/capture-grok` carry only regular files, so a baseline harvest cannot hit this.

## The option that does not work

Naming `skills` in `_CODEX_TEMPLATE_LOCAL_WRITABLE_NAMES` strips the skills. `home_overlay:_materialize_local_writable_entries` creates an empty directory and copies nothing, which is correct for `sessions`, `projects` and the sqlite files where empty is the point, and wrong for content the run has to read. Both this repo and agent-runtimes reached that conclusion independently, from opposite directions.

## The option both sides recommend

Copy `skills/` into the overlay on the codex path only.

agent-runtimes measured the worst tree in the catalog, `frontend/skills` at 73 files and 903 KB: `shutil.copytree` 15.1 ms, `cp -Rc` with clonefile 19.1 ms. The cost is metadata on small files rather than bytes, so APFS cloning loses once the subprocess is counted. Every other runtime is smaller; `codebase-mapper` and `orchestrator` are one skill each.

Since agent-runtimes vendored skills as real bodies (`c1ecbe4`), this is a plain recursive copy with nothing to resolve. It would not have been a week ago, when those were symlink farms.

## One nuance for whoever picks this up

The gitignore keeps the working tree clean, and it is also why the three `.system` trees survived long enough to be found by eye rather than by tooling. agent-runtimes wrote the lesson into their own `.gitignore`: how long a write-through survives is bounded by what the ignore rules hide, not by what the harness writes. `installation_id` lands at a template root, is not ignored, and has never shown in `git status`.

Not an argument against the deferral. Recorded so the dig knows why absence of evidence in `git status` is not evidence of absence here.


## Sub issues
[]


# 446: baseline_harvest and baseline_publish overlap: decide the boundary or fold one into the other

URL: https://github.com/littleorgans/transport-matters/issues/446
State: open
Labels: 
Updated: 2026-08-24T02:28:56Z

`baseline_publish` (#444) now supersedes `baseline_harvest` for the normal workflow, and the two overlap enough to mislead. Not urgent; capturing it so it does not drift.

## Today

Both are dev-only entry points and they already **share the capture path** — `baseline_publish` imports `harvest_baseline` rather than reimplementing it. The split is:

**`baseline_harvest`** — one cell, manually targeted.
- `--harness --model --effort`, or no args to print the launch view
- Calls `harvest_controlled_baseline` for that cell, writes a bundle and current pointer
- `--accept-degraded` / `--accepted-by`: the operator-judgment path for accepting a degraded baseline
- Requires a clean worktree (stamps source identity)
- **Never mints a release reference.** Evidence only.

**`baseline_publish`** — a cohort, planned and bound.
- `--harness <id>` or `--all`
- `build_baseline_publish_plan` reads launch state once and plans **without spending**
- Prints the provider-turn budget, requires `--confirm-spend` or an interactive typed `publish`
- Resumes cells that already have evidence, captures only missing ones
- **Mints immutable reference bindings** into the release, which harvest cannot do

## The problem

Harvest is mostly subsumed. What it still uniquely offers is single-cell targeting for debugging and `--accept-degraded`. Both are plausible `publish` flags.

Leaving two overlapping CLIs is the failure mode worth avoiding: someone captures a cell with `harvest`, sees a bundle written, and wonders why no release changed.

`NOW.md` already describes `baseline_harvest` as internal tooling for pre-populating a reference matrix that no user ever runs.

## Decide one

1. **Fold in.** Move single-cell targeting and `--accept-degraded` onto `publish`; delete `harvest`'s CLI, keeping `harvest_baseline` as the shared capture function.
2. **Keep both, documented.** `harvest` becomes an explicitly debug-only entry point, with its docstring and `NOW.md` stating that `publish` is the workflow and `harvest` never changes a release.

Option 1 is the DRY answer. Option 2 is cheaper and may be enough given both are dev-only.

## Not in scope

The shared `harvest_baseline` capture path is correct and stays either way.

## Sub issues
[]


# 448: Delivery channel: fetch signed compatibility updates, and nudge on a new TM release

URL: https://github.com/littleorgans/transport-matters/issues/448
State: open
Labels: 
Updated: 2026-08-24T03:49:49Z

The receiving half of out-of-band compatibility updates is built and tested. The delivery half does not exist. Until it does, updating a blessing means shipping a TM release and waiting for users to upgrade.

## What exists today

`harnesses/compatibility_store.py`:

- `embedded_compatibility_manifest()` loads `compatibility_releases_v1.json` as a **package resource**. It ships inside the wheel.
- `validate_channel_update()` is the entry point an update channel would call, with `_require_known_channels`, `_require_installed_revisions`, `_require_transport_matters_version`, `_require_digest_integrity`, `_require_certified_active_pointers`.
- `SignatureVerifier` is abstract, and the only concrete implementation is **`RejectAllSignatureVerifier`**.
- Manifest signatures are stubs (`"stub:embedded:stable:claude"`), consistent with nothing verifying them.

So: the safety checks are written, the door has a working lock, and there is no building attached to it.

## Why it matters

Harness releases are frequent — claude moved 2.1.237 → 2.1.241 inside a single working session. Without delivery, every harness release leaves users reading `above_ceiling` until a TM release is cut *and* installed. Blessings go stale on a multi-day cycle, which is the failure the compatibility system exists to prevent.

Per `docs/HARNESS-COMPATIBILITY.md`, the design already scopes updates narrowly: manifests, target descriptors, lifecycle state, digests, evidence references, channel pointers. No executable content.

## Scope

1. **Retrieval.** Where the manifest is served from, how often it is polled, and the offline story. The doc already requires that the last verified cache survives retrieval failure.
2. **A real `SignatureVerifier`**, replacing `RejectAllSignatureVerifier`, plus key distribution and rotation. This is a supply-chain boundary: the payload reaches machines running paid agents and holding captured prompts and source.
3. **Staged rollout via `channel_states`.** Bless on preview, watch, advance stable. Nothing currently writes `channel_states`; `reseal_compatibility_manifest.py` documents hand-editing JSON as the expected workflow.
4. **Remote kill switch.** `blocked_versions` should be usable to disable a specific bad harness version on every install without a release.
5. **New-release nudge.** Two distinct signals the user should receive, and they must not be conflated:
   - *Your harness version is now blessed* — arrives via a compatibility update, no upgrade needed.
   - *A new Transport Matters release is available* — an upgrade nudge, surfaced in the product.
   A user on an old TM build may be told a harness version is blessed while their installed adapter revisions cannot activate that release (`_require_installed_revisions`). That case must read as "upgrade TM to get this", never as a silent no-op.

## Not in scope

The authoring path (minting a release, sealing a successor, advancing channel state) is tracked separately. This issue is delivery and consumption only.

## Sub issues
[]


# 455: Canvas Overlay: control the system prompt and builtin tool surface per harness

URL: https://github.com/littleorgans/transport-matters/issues/455
State: open
Labels: enhancement
Updated: 2026-08-25T11:57:12Z

Parent: #381. Related: #392 (raw→IR hardening, parked behind this), #454 (grok serializer defect), #384.

Full record of the design session of 2026-08-25. Supersedes the first draft of this issue; `docs/plans/RAW-OVERLAY-PLAN.md` (branch `docs/raw-overlay-plan`) holds the delivery detail and needs a pass to match the scope below.

## What Canvas Overlay is

A Canvas Overlay changes what the harness puts on the wire, for two regions only:

1. **System prompts and system messages** — disable or replace.
2. **Builtin tools** — disable or replace.

Nothing else. No metadata, sampling, thinking config, reasoning, output_config, context management. The goal is token optimization and control of the agent's tool surface, and everything outside those two regions is noise.

## The measurement that sets the scope

Measured from the certified captures (claude 2.1.241, codex 0.149.1, grok 1.0.5, first probe of each class representative):

| harness | body | system prompt | tools | injected system | real user | untouched meta |
| --- | --- | --- | --- | --- | --- | --- |
| claude | 188,341 | 29,891 (15.9%) | **145,491 (77.2%)** | 11,313 (6.0%) | 25 | 1,621 (0.9%) |
| codex | 56,680 | 23,138 (40.8%) | **30,359 (53.6%)** | 491 (0.9%) | 25 | 2,667 (4.7%) |
| grok | 44,268 | 6,057 (13.7%) | **35,569 (80.3%)** | 2,065 (4.7%) | 52 | 525 (1.2%) |

Prompt + tools + injected system is **95–99%** of the request body. What is excluded is under 1% on claude and grok.

**Tools dominate.** Claude ships 145KB of tool schemas (~36k tokens) on every request. Controlling which builtin tools an agent has is the single largest lever, which is why it leads delivery.

## Where the content actually lives

- **claude**: `system[]` is 3 parts (70 / 57 / **29,764** chars). The big part is a monolith with 19 markdown sections; runtime content is *inside* the string ("Types of memory" alone is 7,217 chars). Tools are 30 flat objects in `/tools[]` keyed by `name`. Two injected system surfaces: the first content block of `messages[0]` (593 chars, `<system-reminder>`) and a `role: system` message (10,720 chars, the **agent catalog**). Both are confirmed schema branches (`role:literal:system`, `role:literal:user`).
- **codex**: `/instructions` is empty in practice; the prompt is `input[]` items with `role: developer` (17,730 chars) plus runtime blocks cleanly split into their own content parts with XML anchors (`<skills_instructions>`, `<collaboration_mode>`, `<apps_instructions>`). `/tools` is empty — tools live nested in an `additional_tools` input item.
- **grok**: `input[]` with `role: system`, content a **plain string** (6,057 chars). 27 tools in `/tools[type:function]` keyed by `name`.

Consequence: the same product noun has three different homes, so the region locator is authored per wire class and validated against the certified schema, never derived.

## Decisions taken

- **Raw, never IR, on the write path.** The IR write path reserializes whole bodies and is already fidelity-broken for grok (#454). The IR stays the read model (Canvas, transcripts, counting) and raw→IR hardening (#392) continues on that basis.
- **Wire class is the unit.** Structural equivalence partitions each release's reference schemas: claude 2, codex 2, grok 1. Five classes today. Class identity is structural (`compare_request_schema` EXACT), **never `request_schema_digest`** — verified, one claude class carries two digests because `opusplan` and `sonnet` differ only in tools enumerated at capture (84 vs 90).
- **Class schemas come from the shipped manifest** (`compatibility_releases_v1.json` `references[]`), not from local baseline bundles, which exist only on a machine that ran a certification capture.
- **Editing happens AT opaque roots.** `_inside_opaque` is strictly-below, so an opaque root survives minting as an editable leaf, and those roots are exactly the product surface. Removing a tool is a structural array-member removal and is *not* an opaque-root edit.
- **The schema is a locator, not a conformance check.** An overlay is a deliberate deviation from what the harness sends. The schema tells us where things are and whether our targets still exist.
- **Fail open, all or nothing.** Per NOW.md: a miss forwards the original bytes untouched, never half-overlaid.
- **TypeScript by default.** Artifact, catalog, validation, resolution and UI in TS. Python only for what must run inside the mitmproxy process: a dumb matcher and byte splicer with no schema knowledge and no product vocabulary. Application is **byte splicing**, not decode-and-reserialize (every writer in the codebase sorts keys).
- **Canvas, not Inspector.** Inspector's existing Overlays route stays and is improved separately; IR→Inspector Overlay is parked.

## Overlay content has two halves, and one depends on the other

- **Fixed content replacement** — static text we author, replacing a block.
- **Runtime generated content** — rendered from the overlay's own decisions. Claude's 10,720-char agent catalog is derived from what agents/tools exist; disabling a tool while leaving the prose that teaches it produces a lying prompt.

**Subtraction without regeneration degrades the agent.** The two halves ship together. Generation runs in TS when the decision changes (not per request) and the proxy verifies the request's actual tool set matches what the render assumed, failing open on mismatch.

Generation inputs include the platform, not only the tool set: shell, OS, available binaries and paths differ per machine, so the same overlay renders different text on macOS and Linux.

## Tool control model

A single tool overlay library, authored once, composed by per-runtime enablement:

- **Library**: our content per tool, keyed per harness because schemas genuinely differ. Each entry pins the tool schema digest it was authored against, so certification drift flags stale entries rather than letting a silent capability loss rot.
- **Enablement**: declared per runtime in agent-runtimes, **capability-level** (`shell`, not `bash`), so one declaration resolves across claude/codex/grok exactly as `[skills]` and `[mcp]` already do.
- **Gap to close**: agent-runtimes has `[skills]` and `[mcp]` but no `[tools]`. That is a new concept in that repo.
- **Enable vs disable is one field**, a default plus exceptions: `{default: keep, drop: [...]}` is a denylist, `{default: drop, keep: [...]}` an allowlist. Recommended default is `drop` (allowlist) so savings are deterministic; only safe once generation exists. Either way drift reports "N tools appeared your overlay has no opinion on".
- **Versioning**, following the `[mcp]` bare-bool convention:
  ```toml
  [tools]
  shell     = "v1"    # enabled, our overlay v1
  file-read = true    # enabled, harness content untouched
  web-fetch = false   # explicitly disabled
  # absent           = not enabled under default:drop
  ```
- **Risk split**: dropping unused tools is a pure win with no behavioural question. Replacing a kept tool's content is a behavioural claim and belongs behind evals.

## The mechanism boundary

**An overlay can subtract and rewrite. It cannot add executable capability.** The harness executes tools locally, so a tool we invent has nothing behind it. Adding capability is the MCP layer's job. Enforcement (sandboxing, approval policy) is the runtime's job. Three mechanisms, three owners:

- prefer **configuration** where the harness offers a knob (MCP servers, skills, `ENABLE_TOOL_SEARCH`)
- use **overlay** for what has no knob (builtin tool schemas, system prompt, injected system messages)
- use **MCP** to add anything genuinely new

Open empirical question: does a provider accept a `tool_use` for a tool that was not declared in the request's `tools` array? If yes, stripping schemas plus an MCP `describe_tool` reimplements `ENABLE_TOOL_SEARCH` for every harness, since the harness's executor still implements the tool.

## Evidence from the codex runtime (first-hand, 2026-08-25)

Asked a live codex-runtime agent how `exec` works in practice. Findings, verified against our capture where checkable:

- **Codex does not have three tools.** It has three *top-level* tools, and `exec` carries a **26,383-character description** (87% of codex's tool payload) documenting a nested API: `apply_patch`, `exec_command`, `write_stdin`, `update_plan`, `view_image`, `web__run`, MCP resource access, goal lifecycle. Tool definitions moved from structured schemas into prose.
- **The saving is still real**: 30,359 vs claude's 145,491 tool bytes (4.8×); whole request 56,680 vs 188,341 (3.3×), with a *smaller* system prompt.
- `exec` is a **fresh V8 isolate per call**, no filesystem or network API, state only via explicit `store`/`load`. The persistent node REPL is a separate MCP tool. Shell work goes through nested `exec_command`, returning a `session_id`; `wait` resumes a yielded JS cell, `write_stdin` polls a live shell session.
- **Costs**: three quoting layers (JS → JSON → shell) drive retries; no typed intent, so inspection and destruction look identical to policy; parsing human-oriented stdout burns tokens; portability depends on shell/OS/PATH/binaries; broad commands flood and truncate, hiding the decisive error.
- **A structured edit primitive is load-bearing.** Its own system prompt forbids `sed -i` and requires `apply_patch`.
- **Transplanting needs the execution environment and result protocol, not the schema**: sandbox and approval policy, known cwd plus explicit `workdir`, shell/PATH/binary guarantees, process lifecycle (session id, polling, stdin, PTY, cancellation), output shaping (token limits, truncation markers, chunking), safety teaching *with enforcement below the model*, a structured edit primitive, verification guidance.
- **Suggested eval boundary**: a small kernel rather than pure exec — exec + structured patch + async process control + explicit user interaction + typed media/web where shell cannot preserve semantics.
- **Measurement warning**: count total request **and response** tokens plus behavioural success, not tool-definition bytes. Cost moves into the system prompt, command construction, stdout and retries.

Useful consequence for us: **codex's entire tool surface is one editable string**, the easiest overlay target of the three, where claude's is 30 separate objects.

## Back pocket: a portable exec kernel

Not scheduled. Recorded so the option is not re-derived.

[`just-bash`](https://github.com/vercel-labs/just-bash) (Vercel Labs, beta) is a virtual bash environment with an in-memory filesystem, written in TypeScript for agents. It answers most of codex's transplant checklist by **dissolving the OS from the contract** rather than teaching it: commands are implemented in TS, so the same `sed`, `grep`, `jq`, `awk` behave identically on every machine, and GNU vs BSD, missing binaries, PATH and locale all disappear. Filesystem classes are the policy boundary (`InMemoryFs`, `OverlayFs` = reads real disk / writes to memory, `ReadWriteFs`, `MountableFs`), network is off by default with URL and method allow-lists, and `defineCommand` would let us add a structured `apply_patch` in TS. Core shell also runs in the browser, so Canvas could preview a kernel's behaviour client-side.

Gaps and caveats:

- **No process lifecycle**: exec-and-return only, no session id, no `write_stdin`, no PTY. Dev servers, test watchers and anything streaming have no equivalent.
- **No VM isolation** (their words): hardened against prototype pollution, but a policy boundary rather than a hard one against a hostile agent. They point to [Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) for a full VM with arbitrary binary execution — the natural companion when hard isolation or real binaries are required.
- Real edits need `ReadWriteFs`, which spends much of the sandbox benefit. `OverlayFs` is the interesting middle for exploration and planning.
- Beta software.

**Benchmarked against this repo (api/, ~850 Python files) on 2026-08-25**, OverlayFs over the real tree, output identical to native in every case:

| operation | just-bash | native | ratio |
| --- | --- | --- | --- |
| read file slice (`sed -n`) | 6ms | 7ms | 0.8× |
| list files (`find` + `wc`) | 248ms | 199ms | 1.2× |
| **grep** (`grep -rn`) | 142ms | 87ms | 1.8× |
| count lines (`xargs wc`) | 49ms | 21ms | 2.3× |
| **rg** (`rg -n`) | 3,700ms | 40ms | **93×** |

Verdict: performance is a non-issue **except for `rg`**, which is consistently ~26× slower than `grep` doing the identical job *inside just-bash itself* — an implementation quirk, not a limit of the approach. Since we would own the kernel's prose contract, the mitigation is simply not to document `rg`.

## Sequencing

Tool control is the priority; it carries most of the value on its own.

1. **#456** — read-only Canvas surface showing the raw request per harness wire class. Uses data we already ship. Identifies runtime-generated content visually and is the acceptance surface for everything after.
2. **#457** — capability library, agent-runtimes `[tools]`, enablement applied to the wire.
3. **#458** — re-render runtime prompts from the tool decision so subtraction never leaves lying prose.
4. **#459** — back-pocket exec kernel, gated on evals.

## Open questions

- Overlay scope: this issue treats an overlay as global per (harness, class). NOW.md places overlays in the launch specification (`FrozenLaunchSpec` / `candidate_key`), where N candidates differing by overlay is the same verb as N differing by model. **"When to apply an overlay" is explicitly still open** and decides the storage and API shape.
- Does a provider accept a `tool_use` for an undeclared tool (see mechanism boundary)?
- End-to-end token comparison (kernel vs native tools, same task, counting retries) needs either the overlay or a standalone agent loop; request-byte savings alone would be misleading.

## Comment by srobinson at 2026-08-24T20:04:22Z (updated 2026-08-24T20:04:22Z)

https://github.com/littleorgans/transport-matters/issues/455#issuecomment-5400666941

Delivery plan drafted at `docs/plans/RAW-OVERLAY-PLAN.md` (branch `docs/raw-overlay-plan`), corrected after an architect review round that found six blockers. The corrections changed the design materially; recording them here so the issue body is not read as current:

1. **Source of truth is the shipped manifest, not the local baseline store.** The issue implied minting class schemas from certified bundles. That evidence exists only on a machine that ran a certification capture (verified: no `baselines` directory in the stable or dev home). Classes come from `compatibility_releases_v1.json` `references[]`, which ship schemas and digests in the wheel. Consequences to carry: releases before the current three have `references: []`, and there is no dev channel state, so overlays are dark on dev.
2. **Class identity is structural, never `request_schema_digest`.** Verified: one claude class carries two digests. `opusplan` and `sonnet` are structurally identical and differ only in `observation_count` at `/tools` (84 vs 90 tools enumerated at capture). Pinning an overlay to a digest would judge it stale for a member of its own class.
3. **Editing happens AT opaque roots.** `_inside_opaque` is strictly-below, so an opaque root survives minting as an editable leaf. Those roots are exactly the product surface: claude `/system[type:text]/text`, `/tools[]/description`; codex `/instructions`, `/tools[type:*]/description`. The first draft had this inverted and would have locked the entire feature.
4. **The comparator's pointers cannot address one location.** `_child_pointer` appends property keys only, array branches are carried in a `branch_tag` overwritten per level, and indices are absent: `/tools/description` names all ninety tool descriptions. The plan introduces a real `SchemaAddress` (property / branch / member selector incl. `where(key,value)`) plus a resolver with an explicit cardinality contract. This is what makes the value-addressed IR verbs expressible.
5. **Application is byte splicing, not decode-and-reserialize.** Every writer in the codebase sorts keys, so a round trip re-emits and reorders the whole body, failing this issue's own acceptance criterion.
6. **Fail open, all or nothing.** Per NOW.md: a miss forwards the original bytes untouched rather than applying a partial overlay.

Also folded in: two apply points (codex production traffic is WebSocket; the `--force-http-fallback` body is not described by the certified class), precedence against the downstream IR pipeline, class resolution by wire model (the addon never sees the launch alias), propagation to the proxy subprocess over the existing control socket, and the form seeded from the operator's own captured exchange since the release ships schemas without bodies.

New finding, sibling of #454: grok's message content is a plain string at `/input[type:message]/content` with `opaque=false`, because the RESPONSES opaque roots assume codex's array-of-parts shape. Grok's prose is classified differently from codex's identical prose. Noted for the gate owner, not handled by this plan.

Three decisions are left open for the owner in the plan: plane ownership for the artifact store and CRUD (ARCHITECTURE.md says new product contexts do not extend the Python plane), overlay scope (global vs the launch-specification scoping NOW.md describes), and whether the shipped-but-inert Inspector Overlays route is hidden or accepted as a duplicate.

## Comment by srobinson at 2026-08-25T11:56:34Z (updated 2026-08-25T11:56:34Z)

https://github.com/littleorgans/transport-matters/issues/455#issuecomment-5410018564

## Experiment, 2026-08-25: the two verbs are already available on claude as CLI flags

Captured claude's real request bytes at three configurations by pointing `ANTHROPIC_BASE_URL` at a local sink that records the body and returns 500. **Zero provider spend.** All three arms are `-p` (sdk-cli entrypoint), so they are directly comparable.

| configuration | total | tools | system | messages |
| --- | --- | --- | --- | --- |
| `claude -p` (default) | 114,619b | 21 (56,991b) | 27,856b | 28,664b |
| `--tools ""` | 123,737b | 86 MCP (87,062b) | 26,990b | 8,588b |
| `--tools "" --strict-mcp-config --mcp-config empty --system-prompt "..."` | **5,717b** | **0 (2b)** | **203b** | 4,859b |

**A 20× smaller request, achieved with pure configuration and no overlay machinery.**

The flags that do it:

- `--tools <names...>` — "Specify the list of available tools from the built-in set. Use `""` to disable all tools, `default` to use all tools, or specify tool names." Confirmed on the wire: every builtin disappears.
- `--system-prompt <prompt>` — replaces the system prompt outright. Claude's 27,720-char prompt became our 67 chars. Two parts survive and are not removable by flag: the 74-char billing header and a 62-char "You are a Claude agent, built on Anthropic's Claude Agent SDK."
- `--strict-mcp-config --mcp-config <file>` — only the MCP servers we name.

### The subtle finding: deferral is itself a builtin tool

`--tools ""` alone made the request **bigger** (123,737 vs 114,619). Cause: `ToolSearch` and `DeferredToolPlaceholder` are *builtin* tools, so disabling all builtins disables MCP tool deferral, and all 86 MCP tool schemas inline. Under the default config only 21 tools ship because deferral is doing the work.

Consequence: "disable all builtins" can cost tokens unless MCP tools are also constrained. The two levers interact and must be reasoned about together.

### What this changes

For **claude**, the wholesale form of both Canvas Overlay verbs is already available natively, and per the mechanism-boundary rule (prefer configuration over interception) we should use the flags rather than splice.

The overlay's remaining value on claude is **granularity**, which the flags cannot express:

- keep a tool but replace its content (`--tools` is include/exclude only)
- keep the system prompt but drop or replace one section (`--system-prompt` is wholesale)
- regenerate derived prose (#458) to match a partial tool set

For **codex** there are no equivalent flags at all, and for **grok** there is only `--disallowed-tools` (a denylist, no allowlist, no prompt replacement). So cross-harness parity remains overlay work.

### Unblocked

The `just-agent` experiment (#(just-agent)) needs no overlay machinery. The only missing piece is an MCP server exposing a bash tool.

## Comment by srobinson at 2026-08-25T11:57:12Z (updated 2026-08-25T11:57:12Z)

https://github.com/littleorgans/transport-matters/issues/455#issuecomment-5410025021

See #460: the `just-agent` A/B experiment (all builtins off, our system prompt, one just-bash tool). Unblocked on claude today via native flags — measured floor 5,717 bytes vs 114,619 default, zero provider spend. Only missing piece is the just-bash MCP server.

## Sub issues
[]


# 456: Canvas: raw request viewer per harness wire class

URL: https://github.com/littleorgans/transport-matters/issues/456
State: open
Labels: enhancement
Updated: 2026-08-25T11:42:07Z

Parent: #455. First slice of Canvas Overlay, and the acceptance surface for every slice after it.

## Outcome

A read-only Canvas surface that shows the raw provider request for a chosen harness and model, grouped by wire equivalence class, with the two regions Canvas Overlay cares about broken out and measured: **system prompts / system messages** and **builtin tools**.

Read-only on purpose. No artifact store, no apply engine, no proxy changes. It exists so the shape of the problem is visible before anything mutates it.

## Why this first

- It runs on data we already ship. Class schemas come from `compatibility_releases_v1.json` `references[]`; request bodies come from the operator's own captured exchanges.
- It makes runtime-generated content identifiable by eye, which is the input to the regeneration slice.
- It is the user-acceptance surface: every later change is judged by looking at this view before and after.

## What it shows

Select harness → select model (resolved to its wire class, five classes today) → the request, with:

- **Region breakdown with byte and token counts.** System prompt, builtin tools, injected system messages, real user content, untouched remainder. The certified reference numbers for comparison (claude 145,491 tool bytes / 77.2%, codex 30,359 / 53.6%, grok 35,569 / 80.3%).
- **System prompt structure.** claude's `system[]` parts individually, and the internal section outline of the 29,764-char part (19 markdown headings) so the operator can see that "Types of memory" is 7,217 chars on its own. codex's `input[]` developer items with their XML-anchored runtime blocks (`<skills_instructions>`, `<collaboration_mode>`, `<apps_instructions>`). grok's single system string.
- **Injected system messages.** claude's `<system-reminder>` block in `messages[0]` and the `role: system` agent catalog (10,720 chars). codex's `<environment_context>`. grok's `<user_info>`.
- **Tool list with per-tool cost.** Name, description size, schema size, sorted by bytes, so the expensive tools are obvious. codex's nesting inside the `additional_tools` item and its 26,383-char `exec` description shown as what it is.
- **What is addressable.** Editable targets marked per the certified schema, so it is clear up front what a later overlay could and could not touch.

## Scope

- Canvas pane registered through the enforced path (`model/paneRecords.ts` + its contract test, the three switches in `model/paneIdentity.ts`, `viewers/registry.tsx`, `viewers/registry.test.ts`, and the launcher pair dispatched via `workbench/CanvasCommandDispatcher.ts`).
- TypeScript throughout, per the plane rule. A `/v1/harnesses/{id}/wire-classes` read endpoint exposes classes, members and schemas; the request body comes from the operator's captured exchanges through the existing exchange endpoints.
- No import from `@tm/inspector`; the read-only `viewers/resource/primitives/JsonTree.tsx` idiom is the model for structure display.
- With no captured exchange yet for a class, the view lists the class's addressable targets and their kinds with nothing to prefill, and says so.

## Acceptance

- All five current wire classes render with correct region breakdowns, cross-checked against the certified reference figures.
- The claude system prompt's section outline and the codex runtime blocks are visible without reading raw JSON.
- Per-tool costs are sortable and the total matches the measured tool region.
- `just check` and `just test` green (the latter runs the shell suite).

## Sub issues
[]


# 457: Canvas Overlay: builtin tool enablement via capability library and agent-runtimes [tools]

URL: https://github.com/littleorgans/transport-matters/issues/457
State: open
Labels: enhancement
Updated: 2026-08-25T11:57:14Z

Parent: #455. Depends on: #456 (viewer, as the acceptance surface).

## Outcome

An agent's builtin tool surface is declared per runtime and applied to the wire. Tools the runtime does not enable never reach the provider.

This is the largest single lever in Canvas Overlay: tool definitions are 77% of a claude request (145,491 of 188,341 bytes, ~36k tokens every request), 80% of grok, 54% of codex.

## Three pieces

**1. Capability declaration in agent-runtimes** (new concept in that repo)

`runtime.toml` has `[skills]` and `[mcp]` but no `[tools]`. Add it, following the existing bare-bool convention:

```toml
[tools]
shell     = "v1"    # enabled, our overlay content v1
file-read = true    # enabled, harness's own definition untouched
web-fetch = false   # explicitly disabled
# absent           = not enabled under default:drop
```

Keys are **capability names, not harness tool names**: `shell`, not `bash`, because codex calls it `exec` and grok calls it `run_terminal_command`. One declaration resolves across all three harnesses, exactly as `[skills]` and `[mcp]` already resolve per platform.

Enable-vs-disable is one field, a default plus exceptions. `{default: keep, drop: [...]}` is a denylist; `{default: drop, keep: [...]}` an allowlist. Default `drop` is recommended so savings are deterministic across harness releases; it is only safe once regeneration exists (see #458). Either posture, drift reports tools the overlay has no opinion on.

**2. Tool overlay library**

Our content per tool, authored once and composed by enablement rather than copied into each overlay. Keyed per harness beneath the capability, because schemas genuinely differ. Each entry pins the tool schema digest it was authored against, so certification drift flags a stale entry instead of letting a silent capability loss rot: if claude adds a parameter to Bash and our stored version omits it, the model loses access to it with no signal.

**3. Application**

Resolution at apply time uses the **wire** model, since the addon never sees the launch alias (`launch_fields` does not carry it and wire→launch is many-to-one: `default`, `opusplan`, `sonnet`, `sonnet[1m]` all put `claude-sonnet-5` on the wire). Harness comes from `harnesses:harness_id_for_wire_provider(ir.provider)`.

Two apply points: `addon_handlers:handle_http_request` (claude, grok, codex HTTP fallback) and `handle_codex_websocket_message` (codex production traffic). Byte splicing, never decode-and-reserialize. All-or-nothing per request, failing open with the original bytes.

Tools live in three different homes: claude `/tools[]` (30 flat objects keyed by `name`), grok `/tools[type:function]` (27, keyed by `name`), codex nested inside an `additional_tools` input item. The region locator is authored per wire class and validated against the certified schema.

## Scope discipline

**Dropping unused tools only.** Replacing a kept tool's *content* with a shorter description is a behavioural claim about how the model chooses and calls that tool, and belongs behind evals. This issue ships the subtractive half, which has no behavioural question and carries most of the value.

Per the plane rule: declaration, library, validation and resolution in TypeScript. Python gets only the byte splicer inside the mitmproxy process, with no schema knowledge and no product vocabulary. Overlay state reaches the proxy over the existing control socket, mirroring `SharedProxyManager.set_overrides`.

## Acceptance

- A runtime declaring a reduced `[tools]` set launches with only those tools on the wire, verified by byte-diffing the captured request against the same launch without the overlay: changes confined to the tool region, everything else byte-identical.
- Measured token reduction reported per harness against the certified baseline.
- A capability declared once resolves correctly on all three harnesses.
- A stale library entry (tool schema digest moved) is reported, not silently applied.
- An unresolvable target forwards the original bytes untouched.
- `just check` and `just test` green.

## Note

Prefer configuration over interception wherever the harness offers a knob. `ENABLE_TOOL_SEARCH` is confirmed to defer tool schemas on claude; where an equivalent exists natively it should be used ahead of splicing.

## Comment by srobinson at 2026-08-25T11:57:14Z (updated 2026-08-25T11:57:14Z)

https://github.com/littleorgans/transport-matters/issues/457#issuecomment-5410025265

See #460: the `just-agent` A/B experiment (all builtins off, our system prompt, one just-bash tool). Unblocked on claude today via native flags — measured floor 5,717 bytes vs 114,619 default, zero provider spend. Only missing piece is the just-bash MCP server.

## Sub issues
[]


# 458: Canvas Overlay: regenerate runtime prompts from the tool decision

URL: https://github.com/littleorgans/transport-matters/issues/458
State: open
Labels: enhancement
Updated: 2026-08-25T11:42:51Z

Parent: #455. Depends on: #457 (tool enablement).

## Outcome

When a runtime's tool set changes, the prose that teaches those tools is re-rendered to match. An overlay never leaves the model reading instructions for tools it no longer has.

## Why this is not optional

Subtraction without regeneration degrades the agent while claiming to optimize it:

- claude ships a **10,720-char `role: system` message** that is the agent catalog ("Available agent types for the Agent tool:"). Disable the Agent tool and that entire block describes capabilities that no longer exist.
- The 29,764-char system prompt has a "# Using your tools" section teaching tools by name.
- codex's runtime blocks (`<skills_instructions>`, `<collaboration_mode>`, `<apps_instructions>`) are separate content parts that describe the surface.

This is why the two Canvas Overlay verbs are coupled. The codex runtime confirmed the same thing empirically from the other direction: its tool contract lives in a 26,383-char prose description, not in schema.

## Design

**Two content kinds in an overlay:**

- **fixed replacement** — static text we author for a block.
- **runtime generated** — rendered from the overlay's own decisions.

**Where generation runs:** TypeScript, when the decision changes, not per request. The proxy receives rendered strings and splices bytes; it never templates. This keeps the Python side dumb per the plane rule.

**Guard:** the render records the tool set it assumed. The proxy compares that against the request's actual tool set and fails open on mismatch (an MCP server or plugin can add tools after the render), flagging the overlay for re-render. Consistent with the all-or-nothing rule.

**Generation inputs are not only the tool set.** Platform matters: shell, OS, available binaries and paths differ per machine, so the same overlay renders different text on macOS and Linux. The codex runtime listed environment guarantees (shell semantics, PATH, OS, utilities, timeouts) as a hard requirement for any prose that teaches a tool surface.

**Targets differ per class.** codex's runtime blocks are cleanly separated content parts, so part-level replacement works. claude's runtime content is *inside* one 29,764-char string, so it needs anchored section edits (heading or tag), which keep the artifact small and make staleness detectable when a release moves the anchor.

## Acceptance

- Disabling a tool via #457 re-renders the prose that references it; the agent catalog and tool-teaching sections match the surviving tool set, verified on the wire.
- A rendered overlay whose assumed tool set does not match the live request forwards original bytes and reports the mismatch.
- Rendering is platform-aware and produces different, correct output for at least two platform profiles.
- Byte-diff shows changes confined to the prompt and tool regions.
- User acceptance through the #456 viewer: the operator can see, before and after, exactly what changed.

## Sub issues
[]


# 459: Research: portable exec kernel as a standard builtin surface (just-bash / Vercel Sandbox)

URL: https://github.com/littleorgans/transport-matters/issues/459
State: open
Labels: 
Updated: 2026-08-25T11:57:15Z

Parent: #455. **Back pocket — not scheduled.** Recorded so the option is not re-derived. Gated on evals and on #457/#458 shipping first.

## The question

Can one standard builtin tool surface work across claude, codex and grok, replacing each harness's native tools, validated by evals?

Codex is the existence proof that a small surface works: 3 top-level tools versus claude's 30, and 4.8× fewer tool bytes (30,359 vs 145,491) for comparable work.

## What the codex runtime reported first-hand

- It is **not** three tools. `exec` carries a **26,383-char description** documenting a nested API (`apply_patch`, `exec_command`, `write_stdin`, `update_plan`, `view_image`, `web__run`, MCP resources, goals). Definitions moved from structured schema into prose; the saving is still real.
- `exec` is a fresh V8 isolate per call, no filesystem or network API, state only via explicit `store`/`load`.
- Costs: three quoting layers (JS → JSON → shell) driving retries, no typed intent separating inspection from destruction, token spend parsing human-oriented stdout, portability tied to shell/OS/PATH/binaries, broad output flooding and truncating past the decisive error.
- **A structured edit primitive is load-bearing** — its own prompt forbids `sed -i` and requires `apply_patch`.
- Transplant requires the **execution environment and result protocol**, not the schema: sandbox and approval policy, known cwd plus explicit `workdir`, shell/PATH/binary guarantees, process lifecycle (session id, polling, stdin, PTY, cancellation), output shaping (token limits, truncation markers, chunking), safety teaching *with enforcement below the model*, verification guidance.
- Suggested boundary: **a small kernel, not pure exec** — exec + structured patch + async process control + explicit user interaction + typed media/web where shell cannot preserve semantics.

## Candidate: just-bash

[`just-bash`](https://github.com/vercel-labs/just-bash) (Vercel Labs, beta) is a virtual bash environment with an in-memory filesystem, written in TypeScript for agents. It **dissolves the OS from the contract** instead of teaching it: commands are implemented in TS, so `sed`, `grep`, `jq`, `awk` behave identically everywhere and GNU vs BSD, missing binaries, PATH and locale stop mattering. Filesystem classes are the policy boundary (`InMemoryFs`, `OverlayFs` reads real disk / writes to memory, `ReadWriteFs`, `MountableFs`); network is off by default behind URL and method allow-lists; `defineCommand` would let us add a structured `apply_patch` in TS. Core shell runs in the browser, so Canvas could preview kernel behaviour client-side.

It answers five of six items on the codex checklist. It is also TypeScript, which matches the plane rule.

### Benchmark, 2026-08-25

OverlayFs over this repo's `api/` tree (~850 Python files), output identical to native in every case:

| operation | just-bash | native | ratio |
| --- | --- | --- | --- |
| read file slice (`sed -n`) | 6ms | 7ms | 0.8× |
| list files (`find` + `wc`) | 248ms | 199ms | 1.2× |
| **grep** (`grep -rn`) | 142ms | 87ms | 1.8× |
| count lines (`xargs wc`) | 49ms | 21ms | 2.3× |
| **rg** (`rg -n`) | 3,700ms | 40ms | **93×** |

Performance is a non-issue except `rg`, which is ~26× slower than `grep` doing the identical job *within just-bash itself* — an implementation quirk, not a limit of the approach. Since we would own the kernel's prose contract, the mitigation is to not document `rg`. Reproduction script: benchmark against `OverlayFs({root})`, comparing `bash.exec(cmd)` wall time to `execSync(cmd)`.

### Gaps

- **No process lifecycle**: exec-and-return only. No session id, no `write_stdin`, no PTY. Dev servers, test watchers and streaming work have no equivalent — the one codex requirement it does not meet.
- **No VM isolation** (their words). Hardened against prototype pollution, but a policy boundary rather than a hard one against a hostile agent. [Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) is the companion for a full VM with arbitrary binary execution, and the natural answer where real binaries or hard isolation are required.
- Real edits need `ReadWriteFs`, spending much of the sandbox benefit. `OverlayFs` is the interesting middle for exploration and planning.
- Beta software.

## How it would compose

Consistent with the mechanism boundary in #455 — an overlay subtracts and rewrites but cannot add executable capability:

- **MCP adds**: TM's MCP server exposes one `bash` tool backed by the kernel; the harness routes the call to us and we execute.
- **Overlay subtracts and rewrites**: strip the harness's builtin tools, rewrite the system prompt to teach the kernel.
- **agent-runtimes declares**: which capabilities, and which filesystem mode — a per-runtime trust level as configuration.

## Open work before this is more than a note

- End-to-end token comparison: kernel versus native tools on the same real task, counting **retries and response tokens**, not tool-definition bytes. Needs #457 (to strip tools) or a standalone agent loop. Request-byte savings alone would be misleading; the codex runtime was explicit about this.
- Eval suite along its suggested axes: quoting adversaries, hostile paths, wrong cwd, missing binary, denied network, truncation hiding the decisive error, long-running PTY work, dirty worktree preservation, exact edit plus mutation check, notebook integrity, secret redaction.
- Whether a provider accepts a `tool_use` for an undeclared tool (see #455) — decides whether schema deferral is transplantable.

## Comment by srobinson at 2026-08-25T11:57:15Z (updated 2026-08-25T11:57:15Z)

https://github.com/littleorgans/transport-matters/issues/459#issuecomment-5410025524

See #460: the `just-agent` A/B experiment (all builtins off, our system prompt, one just-bash tool). Unblocked on claude today via native flags — measured floor 5,717 bytes vs 114,619 default, zero provider spend. Only missing piece is the just-bash MCP server.

## Sub issues
[]


# 460: Experiment: just-agent — one bash tool, our system prompt, A/B against an untouched agent

URL: https://github.com/littleorgans/transport-matters/issues/460
State: open
Labels: 
Updated: 2026-08-25T12:56:24Z

Parent: #455. Related: #459 (kernel research), #457 (tool control), #456 (viewer).

## The experiment

Build one agent-runtime, `just-agent`, with:

- all builtin tools disabled
- the harness system prompt replaced with our own
- exactly one tool: `bash`, backed by [just-bash](https://github.com/vercel-labs/just-bash) over an MCP server

Give the same task to `just-agent` and to an untouched agent. Measure.

This tests the entire Canvas Overlay thesis end to end: can a small, portable, self-owned tool surface do the work that a harness's native surface does, and at what token and behavioural cost.

## It is unblocked today on claude

Confirmed by capturing real request bytes against a local sink (zero provider spend, see #455 comment). No overlay machinery required:

```
claude -p "<task>" \
  --tools "" \
  --strict-mcp-config --mcp-config just-bash.json \
  --system-prompt "<our prompt>"
```

Measured floor: **5,717 bytes total, 0 tools, 203 bytes of system prompt** — against 114,619 bytes for the default configuration. A 20× smaller request before the task even starts.

The only missing component is the MCP server exposing `bash`.

## Build

**1. just-bash MCP server** (TypeScript, per the plane rule)

One `bash` tool over `Bash` + a filesystem mode chosen per runtime: `OverlayFs` (reads the real repo, writes to memory) for exploration arms, `ReadWriteFs` where the agent must actually ship changes. `defineCommand` supplies a structured `apply_patch`, which the codex runtime identified as load-bearing — general shell editing is too easy to misquote and too hard to audit.

Benchmarked at 0.8–2.3× native for `sed`, `find`, `grep`, `wc` over this repo, with identical output. **Do not document `rg` in the tool contract**: it is ~93× native and ~26× slower than `grep` doing the identical job inside just-bash.

**2. The system prompt**

Our own, teaching the one tool. It must carry what the codex runtime said an exec-shaped surface cannot work without: sandbox and approval policy, known cwd plus explicit working directory, shell and binary guarantees, output shaping and truncation behaviour, the structured edit primitive, and verification guidance. just-bash makes most of these *statable as facts* rather than per-machine guesses, because the command set is implemented in TypeScript and behaves identically everywhere.

**3. Harness coverage**

claude works via flags today. codex has no equivalent flags and grok has only `--disallowed-tools`, so extending the experiment to them depends on #457.

## Measurement design

Getting this wrong is the main risk.

- **Both arms identical** except tools and prompt: same model, same effort, same repo state, same task text, same non-interactive mode.
- **Multiple runs per arm.** Agents are stochastic; N=1 measures noise. Start at N=5.
- **Record per run**: total input tokens, output tokens, turns, wall clock, and task success judged against a fixed rubric written before the runs.
- **Classify every failure** using the taxonomy the codex runtime supplied from experience: quoting errors, hostile paths, wrong cwd, missing binary, denied network, truncation hiding the decisive error, long-running process needs, dirty worktree damage, incorrect edit, secret exposure.
- **Report request bytes and end-to-end tokens separately.** Request-byte savings are easy and misleading; the codex runtime was explicit that cost moves into the system prompt, command construction, stdout and retries.

## Task selection

Tasks must be ones a shell can plausibly do, chosen before any runs and not adjusted after seeing results. just-bash has **no process lifecycle** — no PTY, no `write_stdin`, no long-running sessions — so dev servers, watch modes and streaming test runners are out of scope until a companion mechanism exists.

Codex flagged shell-hostile domains that would unfairly penalise the kernel arm: browser and authenticated app state, images, PDFs, web results needing citations, notebooks. Excluding them is legitimate; silently excluding anything the kernel merely happens to lose is not.

## Fairness caveat, stated up front

The untouched arm has a tool surface tuned over years. `just-agent` will have a prompt written in a day. An early loss is evidence about our prompt, not about the thesis. The prompt should be iterated against the failure taxonomy before any result is treated as a verdict, and the iteration count should be reported alongside the outcome.

## Acceptance

- Both arms run the same task set unattended and produce a comparison table: request bytes, total tokens, turns, wall clock, success rate, failures by category.
- The result is reported honestly whichever way it falls, including the prompt iteration count.
- Findings feed #459 (whether a portable kernel is worth building on) and #457 (which granular controls are actually needed).

## Comment by srobinson at 2026-08-25T12:56:24Z (updated 2026-08-25T12:56:24Z)

https://github.com/littleorgans/transport-matters/issues/460#issuecomment-5410692592

## Correction to the fairness caveat: the baseline is already aggressively cut, but only on prompts

The issue body says the untouched arm has "a tool surface tuned over years". That is wrong, and the correction sharpens the experiment.

Anthropic removed ~80% of Claude Code's system prompt for frontier models (Opus 5 / Fable 5) with no measurable loss on coding evals, stating they had been over-constraining the model. The reduction is **frontier-only** — Sonnet 5 and Haiku 4.5 keep the full prompt. The headline 80% is the memory-disabled figure; with memory on it is closer to 70%.

Measured independently from our own certified captures (claude 2.1.241, first probe per cell), which reproduce exactly that split:

| alias | wire model | system prompt | tools | tool bytes |
| --- | --- | --- | --- | --- |
| sonnet | claude-sonnet-5 | 29,764 | 30 | 145,522 |
| haiku | claude-haiku-4-5 | 29,878 | 33 | 149,344 |
| fable | claude-fable-5 | **12,959** | 30 | 127,079 |
| opus | claude-opus-5 | **11,819** | 30 | 126,767 |

Opus 5's prompt is 60% smaller than Sonnet 5's in characters, consistent with the ~70% word-count figure once measurement bases are reconciled.

### The consequence that matters

**They cut the prompt. They did not cut the tools.** Opus gets 126,767 bytes of tool schemas against 11,819 bytes of system prompt — the tool surface is **10.7× the prompt** and only 13% smaller than Sonnet's. Against an Opus baseline, tools are **91% of the addressable mass**.

So the vendor has already proven the principle this experiment tests, on the region they chose to address, and left the larger region untouched. That is the strongest available argument for #457 leading delivery.

### What this changes for the experiment

- **Run the A/B on Opus 5 or Fable 5**, not Sonnet. Against Sonnet, prompt replacement would flatter us with a win the vendor already banks on frontier models.
- **The prompt-replacement win is smaller than the Sonnet numbers implied.** Our 203-byte prompt replaces 11,819 bytes on Opus, not 29,764.
- **The tool win is undiminished** and is where the result will be decided.
- The revised fairness caveat: the untouched arm is the product of deliberate, evaluated reduction, which makes it a *harder* prompt baseline than assumed — and an *unoptimized* tool baseline.

Anthropic's stated principle, which is also this experiment's hypothesis: the smarter the model, the fewer instructions it needs.

Sources: [Thariq (Anthropic) on X](https://x.com/trq212/status/2080710971228918066), [independent per-model prompt capture](https://x.com/PawelHuryn/status/2079700261581271487?lang=en), [AI Weekly summary](https://aiweekly.co/alerts/anthropic-deletes-80-of-claude-codes-system-prompt-for-claude-5)

## Sub issues
[]


# 470: Home wipe: entitlement exclusions are lost, so refused models are offered again

URL: https://github.com/littleorgans/transport-matters/issues/470
State: open
Labels: bug
Updated: 2026-09-05T03:11:02Z

Deleting a channel home makes TM forget which models the operator's account cannot use. It then offers them again and the provider refuses.

## Observed

Before wiping `~/.transport-matters-preview`, TM held:

```json
{ "launch_model": "gpt-5.2", "status": "failed",
  "target_exclusion": { "reason": "account_entitlement_unavailable", "provider_status": 400,
    "provider_message": "The 'gpt-5.2' model is not supported when using Codex with a ChatGPT account." } }
```

That is real knowledge, earned from a real 400. It lived in `baselines/attempts/codex/codex/gpt-5.2/0.149.1.json` and died with the home.

The resolver reads it from disk:

```python
excluded_models = account_entitlement_excluded_models(
    read_baseline_attempts(output=baseline_output, harness=harness_id), provider=provider)
```

(`harnesses/resolver_snapshots.py`, feeding `snapshots.account_excluded_models`.)

After the wipe, codex 0.149.1 still enumerates `gpt-5.2` as `ok`, so it becomes launchable again and a launch will be refused by the provider.

## Why this one and not the rest of the home

Most of the home regenerates for free: `settings.toml` is byte-identical to the shipped template, `runtime/` is scratch, current harness inventory repopulates at the next startup refresh. Drift evidence orphans under the new executor id, which the TLDR already calls harmless and which no operator acts on.

Entitlement exclusions are different. They are per-account facts that only a refused provider turn can establish, and losing them changes what the product offers.

## Outcome

Entitlement exclusions survive a home wipe.

## Scope

Options, in rough preference order:

1. Record the exclusion in the session store alongside the existing quota decisions (`read_known_quota_decision` already lives there), keyed by provider and model rather than by executor.
2. Keep them on disk but outside the channel home.

Note the natural key is the provider account, not the executor id. Two homes on one machine with one ChatGPT account share the refusal.

## Acceptance

- Wipe the channel home, restart, and `gpt-5.2` is still excluded without a new provider turn.
- Test covering an exclusion recorded, home discarded, exclusion still enforced.
- `just check` and `just test` green.


## Comment by srobinson at 2026-09-05T03:11:02Z (updated 2026-09-05T03:11:02Z)

https://github.com/littleorgans/transport-matters/issues/470#issuecomment-5548958570

## Still live, and now a boundary decision

Verified on `main` at 53511834: `harnesses/resolver_snapshots.py:138` and `harnesses/inventory.py:552` still read entitlement exclusions from the on disk baseline attempts under the channel home. The only reason `gpt-5.2` is excluded in the preview launch view today is that the home has not been wiped since `baselines/attempts/codex/codex/gpt-5.2/0.150.1.json` was written. No commit references this issue.

#632 proposes removing `account_entitlement_unavailable` from launch resolution and keeping it in certification and publishing, on the premise that the vendor's refreshed catalog is account aware. It is not for this case: codex 0.153.2 enumerates `gpt-5.2` with `visibility: list` and the provider still answers 400 for a ChatGPT account. The refusal is learned only from a provider turn.

Decision this issue should hold, so #632 does not encode the opposite:

- An entitlement exclusion is runtime evidence about this operator's provider account. It is never release data, because a release cannot know which account will run it.
- The session store owns it, keyed by provider and model, beside the quota decisions `read_known_quota_decision` already reads. Not the channel home, not the executor id.
- It is an enumerated block in the #384 sense: the one sanctioned refusal mechanism. Version and schema verdicts never refuse; a provider's own 400 does.

Scope of this issue is unchanged: record the exclusion in the store when the provider refuses, read it at resolution, and prove it survives a home wipe.


## Sub issues
[]


# 471: Logging: make log destination env-configurable and let foreground persist

URL: https://github.com/littleorgans/transport-matters/issues/471
State: open
Labels: enhancement
Updated: 2026-08-26T14:08:12Z

Backend log location and foreground persistence should be environment configuration.

## Today

`cli/desktop_cmd.py::run_desktop_detached` opens `desktop_runtime.py::desktop_log_path`, which is `<channel home>/runtime/desktop.log`. `transport-matters tail <channel>` reads it.

Two consequences:

- `--foreground` persists nothing. Output goes to the tty and is gone when the pane scrolls. Diagnosing a launch required re-running the whole scenario detached purely to obtain a readable log.
- The log lives inside the channel home, so wiping the home deletes the logs that would explain what happened before the wipe.

## Outcome

Log destination is env-configurable, and foreground mode can persist.

## Scope

- Env var for log destination, defaulting to today's `<channel home>/runtime/desktop.log` so nothing changes for existing users.
- `--foreground` writes to that destination as well as the tty (tee), or gains a flag to.
- `transport-matters tail` resolves the same configured path.

## Acceptance

- Foreground run produces a readable log file.
- Log destination outside the channel home survives a home wipe.
- `just check` and `just test` green.


## Sub issues
[]


# 472: Canvas: launch toggles silently reset to off after a home wipe

URL: https://github.com/littleorgans/transport-matters/issues/472
State: open
Labels: bug
Updated: 2026-08-26T14:08:14Z

Wiping a channel home silently resets the Canvas launch toggles to off.

## Observed

After deleting `~/.transport-matters-preview` and relaunching, both toggles came back off:

- **Bypass all permission checks** ("spawned agents skip permission prompts")
- **Control plane access** ("Director: spawned agents can inspect and manage peer runs")

Nothing said they had changed. The next spawned orchestrator was launched without control plane access, which is not a state an operator would think to re-check after a restart.

## Outcome

The toggles survive a home wipe, or the operator is told they were reset.

## Scope

- Establish where these are persisted today. `electron-user-data/` is one candidate, the session store is another.
- If they belong to the operator rather than the channel, they do not belong in a directory that is treated as disposable.

## Acceptance

- Set both toggles, wipe the channel home, relaunch, and the settings are unchanged.
- `just check` and `just test` green.


## Sub issues
[]


# 477: Launch: never block on target resolution; surface the verdict in the run status bar

URL: https://github.com/littleorgans/transport-matters/issues/477
State: open
Labels: enhancement
Updated: 2026-08-26T16:08:37Z

Stuart, 2026-08-26: nothing should ever block a launch. The launch's compatibility status (in range / above ceiling, blessed / degraded / no reference yet, unverified, unmatched) belongs in the run pane status bar next to the activity status (`RunVitalsStrip`).

## Today

`harnesses/launch_target.py::_passes_to_harness` passes only `invalid_effort`, `target_unverified_opt_in_required`, and `target_unavailable/not_observed` through as advisories. Every other resolver rejection raises `LaunchTargetRejected` (4xx on the capture RPC): `target_ambiguous`, `target_unavailable` with `no_agent_target` / `no_default_target` / `retired` / `target_probe_failed`, `account_entitlement_unavailable`. NOW.md's "never block on recognition" covers versions and unknown models; targets still refuse.

`launch_advisories` are stored on the run (`capture_rpc_routes.py`) but nothing in www reads them. Support verdicts (`support_verdict_store.py`) are keyed per release digest / route / model / version, not per run, so the status bar has no data path yet.

## Outcome

1. Every resolver rejection becomes an advisory. The launch goes out with what was asked for; the harness decides. Decide per code what string is sent (ambiguous canonical id verbatim; `no_agent_target` sends no model). Flip `docs/LAUNCH-CONTRACT.md` and the hard-failure tests.
2. A per-run launch status reaches `RunVitalsStrip`: range position, verification state (pending / blessed / degraded / no reference), and any advisories. Fed from the run's `launch_advisories` plus the verdict once verification lands.

NOW.md defers the status message behind the control-plane UI redesign. This issue records the rule and the data gap so both land together when that gate opens.

## Sub issues
[]


# 482: First run: in-app harness login driver (NOW.md 1.3)

URL: https://github.com/littleorgans/transport-matters/issues/482
State: open
Labels: enhancement
Updated: 2026-08-26T21:17:34Z

## Why

Launch readiness already reports `credential_unavailable` per harness (`captured/readiness.py::_credential_check` -> `/v1/launch-readiness` -> `templateRows.ts::launchBlockedReason`), but the only remediation is a terminal command. NOW.md Phase 1 says every reported state must carry an action that fixes it in the app. This issue delivers that action: TM spawns the harness's own login flow against the right home, shows it, and re-reads readiness on exit.

## Design

Architect design package, arena-synthesized and adjudicated: [`docs/plans/LOGIN-DRIVER-PLAN.md`](https://github.com/littleorgans/transport-matters/blob/main/docs/plans/LOGIN-DRIVER-PLAN.md). It owns the usage (director HTTP calls, palette and first-run card, gateway spawn), the type sketch, the slice order, tests, and gates. Where this issue and the plan disagree, the plan wins on shape and this issue wins on scope.

Load-bearing decisions:

- Exit is the trigger, the credential predicate is the verdict. `login_outcome` is a pure function of process evidence plus a fresh `_credential_check`; outcomes `succeeded | failed | cancelled | spawn_failed | lost`. Never match on `Login successful.` text.
- Public identity is harness-keyed: `POST/GET/DELETE /v1/logins/{harness}`, `POST /v1/logins/{harness}/input`. Start twice rejoins. No attempt id, home path, argv, env, or PTY types on any public surface.
- The fallback URL is read from a bounded raw `output_tail`; nothing parses it.
- Gateway sibling composition: `LoginSessions` over `ptyPort`, env as a `{set, unset}` patch over `browserPtyEnvironment(process.env)`, called by Python only. Never through `POST /v1/runs`, `RunManager`, or `cli/`.
- An app-scoped `HarnessLoginCoordinator` watches `GET ?wait_ms` and invalidates `launchReadinessKey` and `harnessInventoryKey` on settle; closing the pane detaches, never cancels. Lazy pane behind `viewers/registry.tsx`, no modal.
- `LaunchReadinessCheck.action {kind: "harness_login"}` drives the card and palette button; grok ships `command_verification: "unverified"` and renders disabled until the binary is observed.
- Claude fleet home moves to `default_storage_root() / "claude-auth"` (per channel) with env override `TRANSPORT_MATTERS_CLAUDE_AUTH_HOME`; `claude auth login` creates the directory itself (verified), so TM never mkdirs a harness home. Existing `~/.claude-auth` logins are invalidated (keychain service name derives from the config dir); no migration.
- `login_command` shell string is replaced by a structured `LoginSpec`; display derived. Fleet constants get one owner importable by `credential_broker.py`.

## Slices (one PR each, in order)

1. Fleet home resolver and `LoginSpec` (Python only, no wire change).
2. `action` on the readiness check; shared unset-key policy with `probe_environment`; grok unverified.
3. Gateway `LoginSessions`, routes, login terminal connection (`FakePtyPort` tests).
4. Python routes, `login_outcome` truth table, bridge extraction from `run_proxy.py` then the login WS.
5. `CardView` extraction from `FirstRunScreen.tsx` (mechanical).
6. Frontend driver: coordinator, pane, card button, palette row; inventory drops `authentication_command`.

Gates verbatim per slice: `just check`, `just test`, `pnpm --filter @tm/runtime test`, `pnpm --filter @tm/gateway test`, `pnpm --filter @tm/shell test`.

## Open questions (plan section "Open questions and risks")

- `GET` before any start returns `lost` when the credential is unavailable; acceptable for the director, or should the frontend treat pre-`POST` `lost` as idle?
- Cancel: SIGTERM to the process group, then SIGKILL after which grace period?
- Codex binds `127.0.0.1:1455`; should `spawn_failed` carry a port-in-use hint?
- Should the gateway login routes require the origin header the Python client sends?
- MCP tool wrapping of the director surface is a follow-up to this issue.

## Not in scope

`transport-matters codex -- login` stays CLI remediation. The startup gate (store picker, doctor at every start) is a separate Phase 1 item.

## Comment by srobinson at 2026-08-26T21:17:34Z (updated 2026-08-26T21:17:34Z)

https://github.com/littleorgans/transport-matters/issues/482#issuecomment-5431228269

Plan peer-reviewed (codex, independent of the synthesizing model): conditional sign-off with five corrections applied in 7e29c9bf (dropped `LoginSpec.harness`, acyclic shared owner as a new leaf `tm/harness_login.py`, env patch precedence so the active home key survives, internal attempt identity as a stale `onExit` guard, `verification` removed from the gateway types), then a clean sign-off on `docs/plans/LOGIN-DRIVER-PLAN.md` as filed.

## Sub issues
[]


# 496: conversation read: revisit summary selection and add a tool-parts projection

URL: https://github.com/littleorgans/transport-matters/issues/496
State: open
Labels: enhancement
Updated: 2026-08-27T21:28:59Z

The `conversation` read has two projection axes that are currently conflated into one parameter. `shape` selects **which messages** are returned. Tool visibility would select **which parts of each message**. Today only the first exists, and its `summary` value is underspecified.

Both were found while reading a delegated run's output over MCP, where the caller could see an agent's conclusions but not the tool calls behind them.

## 1. Revisit `summary`

`packages/activity/src/projections/conversation.ts:212`

```ts
const firstUser = messages.findIndex((m) => m.source.role === "user");
const selectedIndices = new Set<number>();
if (firstUser >= 0) selectedIndices.add(firstUser);
for (let index = Math.max(0, messages.length - 4); index < messages.length; index += 1) {
  selectedIndices.add(index);
}
```

`summary` is *first user message + last 4 messages*, deduped and re-sorted. The intent reads as a sound anchor: what was originally asked, plus where it ended up. The implementation has gaps.

- **Silent elision.** A caller receives first-user + last-4 with no explicit marker that anything was dropped. It can be inferred from a jump in `turn`, but `has_older` / `has_newer` already set the precedent for stating this outright. A caller that does not diff turn numbers will read a summary as a complete conversation.
- **`4` is an unnamed literal**, and it counts *messages*, not turns. Assistant preamble text is its own message, so "last 4" can collapse to roughly the final two turns on a long run. Defensible as a policy, but it is neither named nor documented.
- **Identical to `feed` below 5 messages.** With 3 messages, `firstUser` is 0 and `Math.max(0, 3 - 4)` is 0, so every index is selected. The two shapes are provably indistinguishable at small sizes. Observed in practice: `shape=feed` and `shape=summary` returned byte-identical payloads for a 3-message run.
- **No coverage of the divergence.** Worth confirming whether any test exercises a conversation long enough for the two shapes to differ.

Questions for the revisit: should the tail be counted in turns rather than messages, should the elision be reported in the result, and should the count be a named constant or caller-supplied.

## 2. Tool visibility

Text-only by default is correct and should stay the default. Bulk evidence belongs in the delegated run, conclusions in the caller's context. But there is currently no way to opt in, so a caller reading a delegated agent gets assertions with no access to the evidence. The Inspector already renders `TOOL_USE`, so the data exists in capture; it is the read projection that omits it.

**Proposed shape.** Not `include_tools` / `tools_only` booleans: two flags give four states, one contradictory, and `tools_only` is a filter value in a flag's clothing. It also collides with `shape` (what would `shape=summary, tools_only=true` mean?).

A projection over part types instead:

```
include: ["text"]                    # default, today's behaviour
include: ["text", "tool_use"]        # the common verification case
include: ["tool_use", "tool_result"] # full trace
```

No invalid states, composes with `shape` on its own axis, and extends to thinking blocks or attachments without another boolean.

**Why the parts must be separately selectable.** `tool_use` and `tool_result` have opposite economics. The call is small and high-signal: seeing `du -sh /private/tmp/*` establishes that an agent measured rather than inferred. The result is large and low-signal-per-token. In the motivating case `tool_use` alone would have closed the gap and the result was never needed. A single boolean forces the caller to buy both.

### Blocking design questions

- **Truncation.** Tool results are the largest payloads in a transcript. If opting in means inheriting a 200KB file read, the flag defeats the purpose it was added for. `max_chars_per_message` is per-message today; with parts it likely needs to be per-part, and results likely want a tighter budget than text.
- **Pagination.** `text_offset` / `total_chars` are per-message. If parts become addressable, cursor semantics change. Note `read_user_messages` in `api/src/transport_matters/controlplane/conversation_scan.py` walks fragments with strict contiguity assertions (`text_offset != expected_offset` raises 502) and pins `shape="feed"`, so any part-level change to offsets must keep that scan correct.
- **Reuse over reinvention.** The Inspector already projects tool blocks. A part taxonomy and serializer likely exist; this should reuse that projection rather than introduce a second one.

## Touch points

- `packages/activity/src/projections/conversation.ts` — `selectMessages`, the projection itself
- `packages/activity/src/ports.ts`, `packages/activity/src/server/activityRouter.ts` — request type and query parsing
- `api/src/transport_matters/controlplane/observe_models.py` — `ConversationShape`
- `api/src/transport_matters/api/v1/controlplane_gateway_reads.py` — query construction
- `api/src/transport_matters/api/v1/controlplane_mcp.py` — MCP tool surface
- `api/src/transport_matters/controlplane/conversation_scan.py` — fragment contiguity scan


## Sub issues
[]


# 498: Transcript recall is unusable: indexed FTS exists but is unexposed, and channel scoping makes 'not found' indistinguishable from 'not reachable'

URL: https://github.com/littleorgans/transport-matters/issues/498
State: open
Labels: enhancement
Updated: 2026-08-27T22:03:02Z

## Summary

Transcript recall is the capability that makes a session store worth keeping, and today it does not work. I was asked to reconstruct the history of the browser-pane CDP/devtools work from transcripts alone. I could not, and the interesting part is *why*: four independent gaps, each of which alone would be enough to make a recall question return "nothing found" when the truth is "not reachable from here".

The headline: **the store already has a populated, GIN-indexed full-text column that no endpoint exposes.**

Everything below was measured on this machine, 2026-08-28.

## What a recall question costs today

The documented path is: page `/v1/sessions`, pull `/v1/sessions/{id}/events` for each, grep client-side. Measured:

| channel | sessions | events | span |
| --- | --- | --- | --- |
| stable | 152 | 1,857 | 2026-07-15 .. 08-27 |
| preview | 341 | 7,830 | 2026-07-19 .. 08-27 |
| dev | 8 | 884 | 2026-08-27 |

Dumping 7 dev sessions produced 3.4 MB. Full history extrapolates to ~40 MB pulled over HTTP, one session at a time, to answer one question. Add a second keyword later and you pay it again unless you cached.

## Gap 1: a backend serves exactly one channel, and nothing says so

`/v1/sessions` returns only the channel its backend is bound to. The backend I was attached to had **8 of 501** sessions. Nothing in the response, the skill, or the error surface indicates the other 493 exist. A recall agent asks its question, gets an empty result, and reports "no history" with total confidence.

To reach the rest I had to hand-start two extra uvicorn backends against `preview` and `stable`, unsetting six inherited `TRANSPORT_MATTERS_*` variables so they would not bind the current run's storage. That is not a search surface, it is a workaround, and it writes to those channels on startup (`run_startup_refresh`).

**Ask:** cross-channel read, or at minimum an explicit statement of scope in every list response, so "empty" is distinguishable from "elsewhere".

## Gap 2: full-text search already exists in the schema and is not exposed

`public.event` has:

```
search_text  text
content_tsv  tsvector
```

and

```
event_fts_gin  CREATE INDEX ... USING gin (content_tsv)
```

It works:

```sql
select count(*) from event
where content_tsv @@ websearch_to_tsquery('english','browser');
-- 51
```

There is no API endpoint over it. The skill tells agents "no server-side full-text search" and sends them to grep 40 MB, while an indexed tsvector sits in the same table.

Coverage is partial, which is the real work here:

| kind | rows | with `search_text` |
| --- | --- | --- |
| meta | 5,187 | 0 |
| turn | 2,643 | 2,192 |

5,641 of 7,830 rows carry an empty tsvector. So `meta` events are invisible to FTS, and 451 `turn` rows were missed. `raw::text ~* ...` catches what FTS misses today, which is exactly the signal that backfill is incomplete.

**Ask:** `GET /v1/sessions/search?q=...` over `content_tsv`, returning `session_id, seq, ts, headline`, with `ts_headline` for snippets. Backfill `search_text` for all kinds, or state deliberately which kinds are excluded and why.

## Gap 3: the list surface cannot filter on what it returns

`/v1/sessions` returns `harness`, `provider`, `status`, `createdAt`, `lastActivityAt`, `turnCount`. It accepts none of them as filters. Params are `owner, workspaceId, spaceId, worktreeId, purpose, visibility, includeInternal, limit (≤100), cursor`.

So "codex sessions from last week" means paging all 501 rows and filtering locally. On this store `purpose`/`visibility` are the only filters offered and they have exactly one value each (`user`/`user_visible`), i.e. the filters that exist discriminate nothing and the fields that discriminate are not filters.

**Ask:** `harness`, `provider`, `status`, `createdAfter`, `createdBefore`, `minTurnCount`.

## Gap 4: the good read shape is gated, run-keyed, and live-only

`/v1/controlplane/conversation/{run_id}` is the right projection — clean `{turn, role, text, total_chars}` with `older_cursor`/`newer_cursor`. Three things stop it being a history surface:

1. It needs a control plane bearer; without one: `403 forbidden: invalid or revoked control plane bearer`.
2. It is keyed by `run_id`, while the history surface is keyed by `session_id`.
3. The `conversation` MCP tool that holds the bearer is bound to the current backend and reads the live roster (13 runs, all from today).

The correlation exists but is only recoverable by string-scraping: conversation item ids are `message:<session_id>:<seq>`, and a timeline item's `source.sourcePath` embeds the run id.

Meanwhile the ungated historical path (`/events`) returns raw rows whose field names vary per harness, which is precisely why grep beats structured extraction across mixed history.

**Ask:** an ungated read-only conversation projection keyed by `session_id`, and a first-class `runId` field on `SessionSummary`. Adjacent to #496.

## Gap 5 (smaller): `source_path` points at files that are gone

`timeline` items carry `source.sourcePath` into the harness's native JSONL, which invites a filesystem grep. Runtime homes get cleaned:

```
~/.transport-matters          0 native transcript files
~/.transport-matters-preview  0
~/.transport-matters-dev      2
```

The database is the only durable copy. Worth saying so where `sourcePath` is documented.

## The test case that motivated this

Reconstructing the browser-pane CDP/devtools arc from transcripts. Result: **the work is not in the store.** Across all three channels the only matches are noise:

- `cdp` — 3 hits in stable, all `meta`, all the same skill-catalog string: `"browser-harness: Direct browser control via CDP"`.
- `browser.?pane` — 48 hits in stable, all `meta`, all `cwd` fields naming `/T/tm-browser-pane-proof-*` temp dirs from an automated proof harness on 2026-08-27.
- `WebContentsView` — 0 hits anywhere.
- `devtools` — 0 hits outside the dev channel, where the 28 hits are this investigation itself.

The commits exist. The sessions that produced them were never captured into any channel's store. **That is the most serious finding**, and it is invisible from inside the API: an agent asking this question gets an empty grep and no way to tell "never captured" from "wrong channel" from "FTS gap". Capture coverage needs its own answer, and probably its own issue once someone determines whether this is workspace scoping, channel drift, or sessions that simply ran outside TM.

## Suggested shape

1. **Expose the tsvector.** Highest value per unit work; the index is already built.
2. **Make scope explicit in every response.** Cheapest fix for the worst failure mode, which is confident wrongness.
3. **Backfill `search_text` across kinds**, or document the exclusion.
4. **Add the obvious filters.**
5. **Ungate a `session_id`-keyed conversation projection.**
6. **Investigate capture coverage** — why a month of browser-pane work left no transcript.

## Notes

`skills/transcript-search/SKILL.md` in `littleorgans/.agent-runtimes` has been corrected against the live API: it documented the wrong prefix (`/api` vs `/v1`), wrong params, wrong response shape (bare array vs `{items, nextCursor}`), offset vs cursor paging, and a nonexistent `transport-matters status` command. It now also warns that piping a response through `echo` under zsh corrupts JSON escapes and produces a misleading `Invalid string: control characters` jq error. That is documentation catching up with the API, not a substitute for the gaps above.


## Comment by srobinson at 2026-08-27T22:03:02Z (updated 2026-08-27T22:03:02Z)

https://github.com/littleorgans/transport-matters/issues/498#issuecomment-5445747524

Verified the negative result behind this issue against Postgres directly. It holds, but it had been established on the same incomplete index the issue proposes exposing, and one attribution in it is wrong. Both details sharpen Gap 2.

## The coverage gap is uniform across all three channels

The table above measures `preview`. It is the same everywhere:

| channel | meta rows | with `search_text` | turn rows | with `search_text` |
| --- | --- | --- | --- | --- |
| stable | 1,247 | 0 | 610 | 451 (73.9%) |
| preview | 5,187 | 0 | 2,643 | 2,192 (82.9%) |
| dev | 517 | 0 | 491 | 382 (77.8%) |

Every `meta` row in the store carries an empty tsvector, and roughly a fifth of `turn` rows do. Across all channels that is 6,951 meta rows and ~1,300 turn rows invisible to any query over `search_text` or `content_tsv`.

## The original negative finding was drawn on that index

The conclusion reported was that the browser-pane CDP/devtools work is absent from the transcript store. Re-running the scan against `raw::text`, which covers the rows FTS cannot see:

| term | stable | preview | dev |
| --- | --- | --- | --- |
| `devtools` | 0 | 0 | 49 rows / 3 sessions |
| `WebContentsView` | 0 | 0 | 11 rows / 2 sessions |
| `browser pane` | 0 | 0 | 27 rows / 3 sessions |
| `cdp` (word-boundary) | 3 | 1 | 73 rows / 3 sessions |

The conclusion survives: the sessions that produced #492 / #493 / #495 are genuinely not in the store, and the stable/preview `cdp` hits are the skill-catalog noise already identified.

The point is that this verification had not been run. The claim "the counts match the underlying tables exactly, so nothing is hidden from me" was true of *session counts* and not of searchable *content*. A negative answer over `search_text` today is a negative over roughly 70% of turn rows and 0% of meta rows.

## Correction: the dev-channel devtools hits span three sessions, not one

They were attributed to a single session. Actual distribution:

| session | rows |
| --- | --- |
| `89c3b50f-6744-4989-824a-944e195bf86c` | 16 |
| `5819a0bf-9749-49c1-b407-dc2db52e806a` | 14 |
| `c055d100-71a2-41fc-aa43-c0516a1f448f` | 5 |

`c055d100` is a separate earlier run whose transcript contains the pane reporting `attach: unavailable / reason: devtools_disabled`. Part of the arc **is** captured, and the scan passed over it.

That matters for the framing at the end of the issue: the capture gap is narrower than stated. Discussion of the feature is captured; only the sessions that implemented it are missing. Whoever picks that up should scope it to implementation sessions rather than the topic as a whole.

## Consequence for the Gap 2 ask

This is the argument for treating the `search_text` backfill as a blocker on the endpoint rather than follow-up work.

Shipping `GET /v1/sessions/search?q=...` over `content_tsv` at current coverage produces an endpoint that answers confidently and wrongly. A caller gets `[]` and cannot distinguish "not in the corpus" from "in a `meta` row" or "in one of the 1,300 unbackfilled turn rows". That is Gap 1's failure mode, "empty" indistinguishable from "not reachable", reappearing inside the search surface itself.

Two things worth pinning to the endpoint:

- Backfill `search_text` for every kind before exposing it, or have the endpoint report the coverage it searched so a caller can qualify an empty result.
- Whatever populates `search_text` on write is not running for `meta` at all and is skipping ~20% of `turn`. Worth finding out which, since a backfill that does not fix the writer will drift straight back.

All figures measured 2026-08-28 against `transport_matters`, `transport_matters_preview`, and `transport_matters_dev` on `localhost:55432`.


## Sub issues
[]


# 504: Gateway-owned back stack for browser panes (multi-presenter history)

URL: https://github.com/littleorgans/transport-matters/issues/504
State: open
Labels: 
Updated: 2026-08-28T06:23:46Z

## Problem

Back and Forward on a browser pane step the native view's own history stack (`webContents.navigationHistory`), and each `WebContentsView` has its own. The Gateway stores a history step as pane state and broadcasts it to every registered presenter, and takes `can_go_back` / `can_go_forward` from whichever presenter reported last (`packages/browsing` `browserPaneView`, `BrowserPaneSessions`).

With one presenter (the desktop app today) this is exact. With two, each steps its own stack, which can diverge, and the strip's button state can come from a presenter that has since disconnected. Raised as finding #6 on #500 and deferred; noted in `docs/plans/BROWSER-PANE-PLAN.md`.

## Trigger

A second presenter becoming real (second desktop window, remote viewer). Not before.

## Proposed shape

The Gateway owns the back stack: `BrowserPane` gains `entries[]` and `index`; `open` / `navigate` push and truncate forward entries; `history` moves the index and issues a URL navigation; `reload` re-issues the current entry. `can_go_back` / `can_go_forward` are derived from the index, so every presenter converges on the same URL and the observation no longer reports them.

- Desktop: the history intent, `HostedView.documentSeq` stamping for history, and the `goBack` / `goForward` path are removed; everything is a URL load.
- Contract, Python, canvas: drop the history intent variant and the two booleans from the observation wire; keep them on the presentation as derived values. The strip reads the same fields.
- Open design question: in-page `pushState` observed from the presenter must append an entry or the stack drifts from what the user sees.

## Estimate

One PR, roughly the size of #500; likely removes more code than it adds.

## Sub issues
[]


# 515: Add a read-only watch status verb to the control-plane MCP

URL: https://github.com/littleorgans/transport-matters/issues/515
State: open
Labels: enhancement
Updated: 2026-08-29T02:26:08Z

## Problem

`watch` and `unwatch` are the only verbs on the watch surface. There is no way to ask what this run is currently subscribed to.

The consequences show up in real orchestration:

- **Subscriptions are invisible.** An orchestrating run that registered a watch several turns ago has no way to confirm it still holds one. After a context summarization or a resume, the only record is the model's recollection of a tool call.
- **Observation requires mutation.** The one signal available is `changed` on the `watch` response, so the only way to learn whether a subscription exists is to re-register it. That works because registration is idempotent, but reading state by writing it is the wrong shape.
- **Redundant watches are undetectable.** A workspace watch covers runs launched after it was registered, and runs the session never launched. A per-run watch on a covered run therefore delivers a second copy of every event. Nothing in the API reveals the overlap.
- **Stale watches accumulate.** A watch on a run that has since been closed stays registered with nothing to report, and there is no way to enumerate and reap them.

Observed directly: a session registered a workspace watch alongside a per-run watch on the same run and double-pinged on every event, with no way to see why. Separately, `state_changed` on a workspace target fires on every `reasoning` to `running-tools` flip of every live run, so a redundant registration multiplies an already high-volume event.

## Proposal

A read-only status verb, consistent with the existing separate-verb style rather than an action discriminator on `watch`:

```
watch_status()                 -> every subscription held by this run
watch_status(target="<id>")    -> just that one
```

Per subscription:

| field | purpose |
| --- | --- |
| `target` | run id, or the workspace target |
| `events` | the subscribed event set |
| `registered_at` | when it was established |
| `last_event_at` | last delivery, so a silent watch is distinguishable from a dead one |
| `deliveries` | count since registration |
| `target_state` | live, exited, or unknown; identifies watches worth reaping |
| `shadowed_by` | set when a workspace watch already covers this target |

`shadowed_by` is the field that carries the most value. It turns an invisible duplication into something an orchestrator can detect and fix with one `unwatch`, and it is derivable from state the server already holds.

An empty result is a legitimate answer and should be distinguishable from an error, so a caller can tell "no subscriptions" from "could not determine".

## Notes

- Watches are session-local, so status is scoped to the calling run, matching `unwatch`, which the tool description already frames as removing "this run's watch".
- Purely additive. No change to `watch` or `unwatch` semantics.
- Naturally pairs with a follow-up: having enumerated stale subscriptions, a caller wants to drop several at once, so `unwatch` accepting a list would compose well. Out of scope here.

## Documentation impact

The `tm-orchestrate` skill recommends registering exactly one workspace watch on `turn_completed` and avoiding per-run duplicates. That guidance is currently unverifiable at runtime by the agent following it.


## Sub issues
[]


# 523: Harness request audit: publish the captured shapes, build the control matrix, export the corpus

URL: https://github.com/littleorgans/transport-matters/issues/523
State: open
Labels: 
Updated: 2026-09-03T20:24:00Z

## Problem

Transport Matters certification proves request shapes for a controlled probe. Request overlays need evidence for the complete interactive request lifecycle and for the model visible content each harness, runtime, workspace and user action contributes.

Since this issue was written, the capture primitive gained the tool turn and the envelope. Neither has ever been published. The remaining work is therefore narrower and differently shaped than the original body described.

## Already delivered

Cold start facts, current at `6d8e21dc`.

- **The tool turn is a captured shape.** #394 closed through #604. `RequestShape` carries `FIRST_TURN` and `TOOL_TURN` as a coordinate of every cell, and the probe provokes exactly one call to the harness's own shell tool: [baseline_plan.py:33](https://github.com/littleorgans/transport-matters/blob/main/api/src/transport_matters/baseline_plan.py#L33). The original claim in this issue, that the capture primitive "rejects multiple completed exchanges for one delivery", no longer holds. The limit now is exactly one tool call, one result and one result request; more fails the probe.
- **The envelope is a captured schema.** #393 delivered `project_request_envelope` and `mint_envelope_schema`, and `GateProjection` carries `envelope_schema` beside the body schema: [transport_envelope.py:84](https://github.com/littleorgans/transport-matters/blob/main/api/src/transport_matters/transport_envelope.py#L84), [baseline_projection.py:112](https://github.com/littleorgans/transport-matters/blob/main/api/src/transport_matters/baseline_projection.py#L112).
- **Nothing published uses either.** Across all seven certification records at HEAD: **26 `first-turn` references, zero `tool-turn`, zero `envelope_schema`**. The gate compares what a release carries, so both shapes are currently invisible to it.
- **Empty capture is legible.** #519 closed through #609: a run that captured nothing now says so on the roster.

The gap is publication, not machinery.

## Cut from this issue

**The raw overlay executor follow up is cancelled.** This issue previously ended with "Defer raw request overlay execution to a following issue." That issue should not be opened.

The architecture recommendation reviewed at `6d8e21dc` concludes that a raw semantic executor requires a second per harness parser for roles, tool namespaces, anchors and request classes, duplicating what the adapters already own, and that its one genuine advantage, retaining every unknown JSON value across an edit, is obtained instead by generalizing preserved raw write back. See #384 and the `request schema -> IR -> overlay` contract.

Consequence for this issue: capture evidence no longer has to be shaped for a raw executor's selectors. It has to serve the support gate, the IR coverage declaration and the control matrix.

## What remains

### 1. Dependency: the certification publication

Not owned here. A full `certify --all` run publishes the `tool-turn` and envelope references, and
that run is sequenced ahead of this issue.

It matters here because until a release carries both, a launch at an unknown version compares the
body of one shape and answers for nothing else. Every profile below assumes the gate already grades
two shapes per target. Do not start items 2 through 4 against a manifest that still carries 26
`first-turn` references and nothing else.

### 2. `native-control` matrix

Unchanged from the original scope and still entirely unbuilt. One controlled experiment per harness control, each recording the native flag or config value, interactive or headless applicability, precedence, the actual raw request delta, and whether the control removes model context or only gates execution.

#### Claude

`--system-prompt`, `--append-system-prompt`, `--tools`, `--allowedTools`, `--disallowedTools`, `--disable-slash-commands`, `--safe-mode`, `--bare`, `--mcp-config`, `--strict-mcp-config`, `--setting-sources`

#### Codex

Runtime profile and `-c` overrides, developer instruction configuration, project document discovery, feature flags, plugin configuration, MCP configuration, sandbox and approval controls, web search, model and reasoning effort. Use `codex debug prompt-input` as a provider free diagnostic. Raw captured requests remain the wire authority.

#### Grok

`--system-prompt-override`, `--rules`, `--agent`, `--allow`, `--deny`, `--disable-web-search`, `--no-subagents`, native skill, plugin and MCP configuration, compatible Claude and Cursor source imports, model and reasoning effort. Use `grok inspect --json` as a provider free discovery diagnostic. Grok `--tools` and `--disallowed-tools` are headless only and outside the interactive product path. Record that limitation in the matrix.

### 3. `runtime-overlay` and `interactive-direction` profiles

`runtime-overlay`: launch from a controlled agent runtime with known instructions, skills, MCP configuration, plugins, workdir fixtures and harness configuration, to attribute model visible nodes to the runtime.

`interactive-direction`: capture a controlled lifecycle where a human director interrupts and redirects an active harness. This exists to stop later capture or overlay design from assuming single shot headless execution. Human direction stays a product requirement, and Grok headless mode is not adopted to gain its headless only flags.

### 4. Request class vocabulary

The audit vocabulary must identify at least bootstrap, primary user request, tool continuation, follow up, auxiliary or title generation, human interruption, human redirect, and compaction. A harness version emits several classes, so applicability cannot rest on harness and version alone.

Manual Codex 0.150.1 captures show bootstrap requests carrying tools in an `input` item of `type: "additional_tools"`, primary requests carrying separate developer content nodes for runtime instructions, skills, permissions, collaboration mode and plugin instructions, tool continuations carrying `custom_tool_call_output`, and later turns receiving a different skills inventory from the first. #607 has since lifted top level namespace tools into the IR.

### 5. Capture derived request purpose fixtures

Split out to #611. Raised from #557 and PR #559, it reads the captures this issue produces but
changes no publish path, and it is sequenced ahead of the rest of this issue.

### 6. Public audit export

Immutable versioned audit artifacts for complete interactive turns, with a sanitized public projection. Host the capture history in a separate repository so this one does not grow. Astro on GitHub Pages is the first deployment target. Provider access and capture stay local; public CI validates and publishes committed artifacts without provider credentials.

## Retained product decisions

- Preserve the A/B/A `intrinsic-first-turn` baseline as the structural compatibility baseline.
- Keep manual capture as a supported source of empirical evidence.
- Bind observations to harness, exact harness version, model, effort, capture profile and request class.
- Record complete controlled node content and publish a sanitized projection.
- Defer the choice between harness native controls and raw request overlays until the empirical control matrix exists.
- Do not introduce a byte splicer.

## Suggested sequencing

The two items that were sequenced ahead of this issue have left it. The publication is the certify
run, and the fixtures are #611.

What remains is program sized and starts after both:

1. Item 4, the request class vocabulary, because items 2 and 3 classify against it.
2. Items 2 and 3, the control matrix and the runtime and direction profiles.
3. Item 6, the public export, once there is a corpus worth publishing.

Each should become a child issue when started.


## Comment by srobinson at 2026-08-31T14:04:35Z (updated 2026-08-31T14:04:35Z)

https://github.com/littleorgans/transport-matters/issues/523#issuecomment-5479504649

## Capture derived classifier fixtures

#557 and PR #559 exposed a contract this audit system should own.

Synthetic `make_request_ir()` fixtures prove classifier behavior against shapes we wrote by hand. They do not become stale visibly when a new harness version changes its traffic. The current launch comparison catches structural schema drift, but request purpose also depends on values such as tool presence, token budget, beta headers, and request class. A harness can preserve its schema while changing those values.

Each new audit capture should generate a small, sanitized request purpose fixture keyed by harness, exact version, model, capture profile, and request class. The projection should retain only the request IR and headers read by the provider classifier. Full raw captures remain outside this repository.

The generator needs a check mode. A changed capture projection should fail the check until the fixture and its expected purpose are reviewed. Classifier replay should then assert:

- primary agent requests classify as `True`
- known housekeeping and auxiliary requests classify as `False`
- no captured request class capable of prompt collision rests on `None`

This gives the synthetic unit tests a measured source and a clear invalidation path. It also preserves the structural compatibility baseline while adding the behavioral check #557 needs.

Related: #557 and PR #559.

## Sub issues
[]


# 555: Roster: grok observed_model reports grok-4.6-build, the harness name leaking into a model field

URL: https://github.com/littleorgans/transport-matters/issues/555
State: open
Labels: 
Updated: 2026-09-03T20:18:14Z

## Summary

Every grok run reports `observed_model: grok-4.6-build`, a model id that appears in no target
catalog. The launch declared `grok-4.6`, the request carried `grok-4.6`, and the response reported
`grok-4.6-build`. The roster surfaces an id an operator cannot look up and that matches no
launchable target.

This is a reporting question rather than a correctness failure. `observed_model` has no consumer
that makes a decision from it, so nothing downstream is currently wrong.

## Observed

Four grok runs across one session, two launched with `model=grok-4.6` and one native launch with
no declared model, all reported the same thing:

```
"model":"grok-4.6", "observed_model":"grok-4.6-build"
```

Compare the other harnesses in the same session:

| harness | declared | observed | in catalog |
| --- | --- | --- | --- |
| codex | `gpt-5.6-sol` | `gpt-5.6-sol` | yes |
| claude | `opus` | `claude-opus-5` | yes, as `canonical_model_id` |
| grok | `grok-4.6` | `grok-4.6-build` | no |

Claude's declared to observed change is an alias resolving to a documented canonical id that
`harnesses` publishes. Grok's has no such entry anywhere.

## Evidence

The two stores disagree because they record different halves of the exchange.

```sql
select distinct model from event where run_id='2fb54ba9-869c-471e-b6ba-a32e64749f21';
-- grok-4.6-build

select distinct model from wire_exchange where run_id='2fb54ba9-869c-471e-b6ba-a32e64749f21';
-- grok/grok-4.6
```

`wire_exchange` holds the request model, normalised. `event` holds the response model, raw.
`observed_model` is projected from the latest turn (`roster_projection.py:85-91`), so it reports
the response value.

The target catalog knows only two grok models:

```sql
select distinct native_model_id from harness_target_observation where harness_id='grok';
-- grok-4.5
-- grok-4.6
```

No `-build` id exists in `harness_target_observation`, and `harnesses` offers only `grok-4.5` and
`grok-4.6`, the latter `blessed`.

Normalisation cannot account for the difference. `model_ids.py:4-13` only adds or strips a prefix:

```python
def normalise_model(model: str, prefix: str) -> str:
    if model.startswith(prefix):
        return model
    return f"{prefix}{model}"
```

Nothing strips a `-build` suffix, so the response id is carried through as the provider sent it.

## Impact

`observed_model` is written at `roster_projection.py:47` and defined at `observe_models.py:54`.
Searching the API source finds no other consumer: no comparison against the declared model, no
input to support state, no gate on launch. The compatibility contract keys on harness version, not
on the response model id, so the blessed range for grok 1.0.5 is unaffected.

What it costs is discoverability. An operator reading the roster sees a model that is not offered
by `harnesses`, is not in the catalog, and cannot be launched by that name. Any future check that
compares declared against observed would mismatch on every grok run.

## Resolved: the suffix is the harness, not the model

`grok-4.6-build` is not a model id. xAI publishes `grok-4.6` as the API id, and **Grok Build is the
name of xAI's coding agent CLI**, which is the harness Transport Matters launches. The suffix names
the agent surface the request arrived through, not a deployed build variant.

That answers the question this issue originally put to the maintainers. Option 2 is correct, and on
firmer ground than the issue assumed: this is not a build tag the catalog is failing to track. It is
a harness identifier leaking into a model field, so no catalog entry will ever exist for it.

Sources: [Grok Build overview](https://docs.x.ai/build/overview),
[Grok 4.6 docs](https://docs.x.ai/developers/grok-4-6),
[Introducing Grok 4.6](https://x.ai/news/grok-4-6).

## Current state

Still reproducing. `roster_projection.py`, `model_ids.py` and `observe_models.py` are unchanged
between `1d199d18` and `6d8e21dc`.

Every grok response ever recorded in the preview channel carries the same value, with no variation:

```sql
select model, count(*), min(ts)::date, max(ts)::date
from event where model like 'grok%' group by model;
-- grok-4.6-build | 148 | 2026-08-31 | 2026-09-01
```

## Fix

Strip the agent suffix on the grok projection path. `model_ids.py:4-13` currently only adds or
strips a prefix, so the suffix rule belongs beside it rather than in the roster.

`event` keeps the raw response value as captured evidence. Only the projection resolves. The
operator gets an id that `harnesses` can answer for, and the capture keeps what the provider
actually sent.

This is safe to do now. The compatibility contract keys on harness version rather than the response
model id, so the blessed range for grok 1.0.5 is unaffected, and `observed_model` still has no
consumer that makes a decision from it.

## Verification

1. Regression pinning declared to observed resolution per harness, so an unresolvable id fails a
   test rather than reaching the roster. This is the durable guard and the reason the issue is worth
   closing properly rather than patching the string.
2. `observed_model` for grok resolves to something an operator can find in `harnesses` output.

## Remaining boundaries

- The 148 samples span two days and exercise only `grok-4.6`. Nothing here establishes how
  `grok-4.5` reports, and the fix should not assume the suffix is the only variant.
- The Grok Build finding comes from xAI's public documentation, not from an authenticated
  `/v1/models` call on this account. That call is the cheap way to close the question against the
  account actually in use.

## Environment

Branch `main` at `1d199d18`, preview channel, grok harness 1.0.5, launched as `grok-4.6` at
`tm/generalist`, medium effort. Also observed on a native launch with no declared model.



## Sub issues
[]


# 565: Authenticate Canvas presenter registration and bind it to the genuine Electron instance

URL: https://github.com/littleorgans/transport-matters/issues/565
State: open
Labels: bug, browser
Updated: 2026-08-31T21:24:56Z

## Problem

The Gateway accepts Canvas presenter registration through an unauthenticated loopback SSE route. A caller chooses the Canvas, presentation capability and devtools origin in the request:

- [`GET /canvases/:canvasId/browser-panes/stream`](https://github.com/littleorgans/transport-matters/blob/e3e61d6f1f710601d156fef58b4a73790fc9d5e6/packages/browsing/src/server/browsingRouter.ts#L98-L125)
- [`presenterDeclaration`](https://github.com/littleorgans/transport-matters/blob/e3e61d6f1f710601d156fef58b4a73790fc9d5e6/packages/browsing/src/server/browsingRouter.ts#L269-L293)

The Canvas devtools selection then takes the first composited presenter with a live endpoint:

- [`canvasDevtoolsFor`](https://github.com/littleorgans/transport-matters/blob/e3e61d6f1f710601d156fef58b4a73790fc9d5e6/packages/browsing/src/domain/presenters.ts#L60-L73)

A same-user local process can register first for a known Canvas, claim `composited`, and advertise a loopback endpoint it controls. A later Director `browser_panes` or `whoami` read can then direct automation to that fake presenter.

## Impact

The fake presenter can misdirect or deny browser automation and fabricate the pane surface an agent observes. This is an integrity and availability problem: an agent may believe it is driving a genuine browser pane while it is connected to an impersonator.

[#524](https://github.com/littleorgans/transport-matters/issues/524) and [PR #564](https://github.com/littleorgans/transport-matters/pull/564) contain the damage. Python never sends a Director bearer to the declared endpoint, attach capabilities are bound to the declared origin, and a capability intercepted at a fake origin cannot be relayed to the genuine front. The spoof therefore gains no control-plane credential, genuine pane access, or app-renderer access.

The endpoint selection itself remains unauthenticated and predates PR #564.

## Design constraints

A static launcher secret does not cover every launch path. In hosted mode, Electron may join a runtime that the CLI started earlier, so there is no common parent process to distribute a per-launch secret.

Harness processes also run unsandboxed as the same user. A durable secret in the channel home or another process environment would be readable by the process this boundary needs to exclude.

The trust bootstrap needs to work across packaged, hosted and development launches without relying on a same-user secret at rest.

## Work to scope

1. Define the identity of a genuine Electron presenter and the authority that can attest it.
2. Authenticate presenter registration and reconnection before it enters the live presenter set.
3. Bind the declared devtools origin and browser-pane observations to that authenticated presenter instance.
4. Prevent an unauthenticated competing presenter from winning `canvasDevtoolsFor` selection.
5. Preserve multiple legitimate Canvas windows, renderer reloads, desktop restarts and presenter failover.
6. Keep the pane-only CDP front and the origin-bound Director capability from PR #564 unchanged unless the new identity boundary can simplify them without weakening revocation or renderer isolation.
7. Record the chosen trust model and rejected alternatives in `docs/plans/BROWSER-PANE-PLAN.md`.

## Verification

- A rogue loopback process registers for the same Canvas before the genuine renderer and cannot become the selected composited presenter.
- A rogue process cannot publish a devtools origin or pane observation under a genuine presenter identity.
- A genuine packaged desktop registers, reconnects after renderer reload, and resumes presentation.
- A hosted desktop can join an already-live runtime and authenticate without a common launcher.
- Multiple genuine Canvas windows remain independently addressable.
- Revoking or closing a presenter removes its observations and devtools origin from selection.
- `just check` and `just test` pass.


## Sub issues
[]


# 573: a second queued nudge strands the first delivery; deliveries only reconcile inside wait_for_reply

URL: https://github.com/littleorgans/transport-matters/issues/573
State: open
Labels: bug, P5
Updated: 2026-09-02T01:09:06Z

## Summary

Two nudges queued during one turn strand at least the first delivery, on Claude and on Codex. The run's live prompt binding holds one slot, so the second nudge overwrites the first, and the first prompt's request goes out with no delivery id. On Codex the queue is also released as one merged user message, so neither digest matches and both strand. Stranded rows stay `pending proof_deadline` through every `wait_for_reply` and only end as `run_ended` / `target_exited` when the run closes. Grok is untested.

Separately, delivery rows are only reconciled inside `wait_for_reply`. A row nobody waits on stays uncorrelated however complete the evidence is. The original report's four rows were this second case: they correlated on the first wait against that run and reached correct terminal states.

## Reproduction (2026-09-02, preview, main at `5a30f478`)

Same steps on both harnesses. Codex run `17d9de97`, Claude run `c540eb28` (sonnet).

1. `prompt` a long task (A). Receipt `submitted`, wire claim recorded.
2. While A runs, `prompt` nudge B1 `... Reply with exactly one word: FIRSTQUEUED`. Receipt `proof_deadline`, as expected mid-turn.
3. `prompt` nudge B2 `... SECONDQUEUED`. Receipt `proof_deadline`.
4. `interrupt` the run. Codex aborts A and releases the queue.

Observed on Claude:

- Claude releases the queue as two separate turns and answers `FIRSTQUEUED` then `SECONDQUEUED`.
- The wire request for the first turn has `delivery_id IS NULL`; the second carries B2's delivery id and the binding file is consumed.
- `wait_for_reply` on B2 returns `completed` with the `SECONDQUEUED` reply. B1 returns `pending` / `proof_deadline`, `prompt_cursor IS NULL`.

Observed on Codex:

- The transcript holds one user turn with both prompts concatenated by a newline:
  `Forget the previous task. Reply with exactly one word: FIRSTQUEUED\nForget the previous task. Reply with exactly one word: SECONDQUEUED`
  The assistant answered `SECONDQUEUED`.
- The wire request for that turn has `delivery_id IS NULL`. The run's `.live-prompt-delivery.json` held only B2's digest (B1's binding was overwritten at step 3) and that digest did not match the merged text, so the binding file is still armed after the turn.
- `wait_for_reply` on B1 and B2 returns `pending` / `proof_deadline`, `prompt_cursor IS NULL`. A on the same run resolves `interrupted` correctly.
- After `close`, both return `run_ended` / `target_exited` with no prompt cursor.

## Why

Correlation requires a wire claim before it will bind. `DeliveryReconciler._claim_deliveries` reads `wire_delivery_claims`, `_bind_deliveries` skips any row whose `claim_exchange_id` is null, so a delivery with no wire claim can never gain a `prompt_cursor`.

Two things remove the claim for queued prompts:

1. Every harness: `LivePromptDeliveryBindings.arm` holds one binding per run and overwrites unconditionally. `claim` only unlinks on a digest match. The second nudge discards the first's binding, so the first prompt's request carries no delivery id.
2. Codex only: queued prompts are merged into one message, so `latest_user_prompt_digests` never contains either prompt's digest, and the transcript digest comparison in `_bind_deliveries` fails the same way. Fixing the binding slot alone does not correlate a merged turn.

## Original report (2026-09-01, run `ff6ca51b`), re-examined against the database

The four deliveries `af63b1c0`, `a3c2dc43`, `766ba874`, `1be4c1b6` are all terminal today with correct ranges (interrupted, completed `REDIRECTED`, interrupted, completed `QUEUED`), all updated at 13:28:34 UTC. `control_plane_action` shows no `wait_for_reply` for any of them. The first wait against that run, for a later delivery, started at 13:28:34 and reconciled every open row. The SQL snapshot in the report predates it.

Their evidence was durable within seconds of each turn. Each queued prompt there was released alone by an interrupt before the next nudge was armed, so its wire request carried the delivery id and correlation succeeded once something ran the reconciler.

`DeliveryReconciler.reconcile_target` is called only from `DeliveryWaiter._reconcile_scoped`. `VerifiedPromptDelivery.deliver` and `_LedgerRecorder._record_receipt` claim or fail, never bind. Nothing since `cd32124a` changes this; the startup reconcile in `#585` covers lifecycle rows only.

## Scope

1. **Multiple pending bindings.** Make `LivePromptDeliveryBindings` hold every pending binding for the run rather than one, claiming each by its own digest. This alone fixes Claude. Test in `test_delivery_binding.py`: arm two, claim requests carrying each digest in turn, both deliveries claimed.
2. **Codex merged queue.** Let `claim` and `_bind_deliveries` match a delivery whose prompt text is one line of a merged user message. Decide the outcome per delivery (both `completed` on the same range, or the earlier one `superseded`). Test in `test_delivery_reconcile.py` with a Codex fixture holding a concatenated queued message.
3. **Lazy correlation.** Either reconcile on evidence (subscribe to wire delivery and run event signals on `SessionEventHub`, run `reconcile_target` for targets with open rows, keep the per target lock from `DeliveryWaiter._serialize`) plus a startup sweep in `startup_passes.py`, or document in the `prompt` and `wait_for_reply` tool descriptions that rows correlate only when waited on. Add a test that one wait binds and finishes a sibling delivery on the same target.


## Sub issues
[]


# 574: pane capture verb: an agent cannot see a blocked run's screen, and the snapshot route already returns it

URL: https://github.com/littleorgans/transport-matters/issues/574
State: open
Labels: enhancement
Updated: 2026-09-04T14:32:02Z

## Summary

An agent driving the control plane cannot see what a pane is showing. When a run misbehaves in a
way the conversation and roster do not capture, there is no verb that answers "what is on the
screen". Something equivalent to `tmux capture-pane`, with a scrollback bound.

The capture path itself is built and correct. Verified end to end on 2026-09-02 against a live
blocked run: the snapshot route returns the exact screen. Only the verb is missing.

## Verified reproduction (2026-09-02, preview, main at `8a55fb41`)

Codex released `0.152.1` while `0.152.0` was installed, which arms the interactive update gate.
Three launches, three outcomes:

| launch | result |
| --- | --- |
| MCP `launch` with agent + `first_prompt` | ran normally, replied, 4 exchanges captured |
| MCP `launch` NATIVE (no agent) + `first_prompt` | ran normally, captured |
| launch with no initial prompt (⌘K, terminal, MCP) | parked on the update gate, never takes a turn |

The discriminator is the initial prompt, not the version cache. Every MCP launch passes a prompt
in argv (`_initial_prompt_argv`), so codex goes straight into the turn and never renders the gate.
⌘K and a bare terminal start the TUI with nothing to do, which is where it renders. Ruled out:
a NATIVE run's child home receives a copy of `~/.codex/version.json` already showing `0.152.1`
available at startup and still does not gate, so a populated version cache is not the trigger.

What the blocked run (`ef008927`) looked like on each surface:

- `roster`: `state: "starting"`, `needs_you: null`, `last_turn_at: null`. Indefinitely.
- The run's own supervised gateway (`:61063`): healthy, `GET /v1/runs` returns `{"items":[]}`,
  and `terminal-snapshot` returns `run_not_found`.
- The canvas gateway (`:58244`): holds the run, and `terminal-snapshot` returns it exactly.

```
GET /v1/runs/ef008927-8a12-47cf-9fcf-939a15ecb813/terminal-snapshot?owner=local
{"cols":107,"rows":49,"truncated":false,"text":
"  ✨  Update available! 0.152.0 -> 0.152.1

  Release notes: https://github.com/openai/codex/releases/latest

› 1. Update now (runs `npm install -g @openai/codex`)
  2. Skip
  3. Skip until next version

  Press enter to continue"}
```

Finding it required scanning every listening port for a gateway that knew the run id. Each run
supervises its own gateway, but the one that holds the terminal is the canvas gateway. No agent
should have to discover that.

## Why

Three things this reproduction makes concrete, beyond the original 2026-09-01 defects (#572, a
codex launch dying on an interactive update prompt; and a pane still displaying a run the control
plane considered gone):

1. **The one existing path to a snapshot is unsafe on exactly this run.** `wait_for_reply`
   populates `pane`, but only alongside a delivery. Prompting a run parked on the update gate
   types into the gate, where enter selects **1. Update now**, running `npm install -g
   @openai/codex` unattended and swapping the harness binary under TM mid-session. So the agent
   must either stay blind or risk an unattended global install.
2. **`needs_you` is null on a run that literally needs you.** A blocked run is indistinguishable
   from a slow-starting one. Whatever populates that field should read the same signal the verb
   exposes.
3. **This is the release-day failure mode.** Capture survived the codex release intact; both
   prompted runs captured normally. What broke was a run that never starts and cannot say why.
   That makes the verb the thing standing between an operator and a silent stall on the day a
   harness ships. See #519, which predicted a release-day capture failure and did not get one.

Neither the conversation projection nor the activity stream carries harness UI: modals, update
prompts, auth challenges, and errors printed outside the transcript. That is exactly the class of
failure where an agent gets stuck and cannot report why.

## Most of this already exists

- `TerminalEmulator.textSnapshot(maxChars)` (`packages/runtime/src/service/TerminalEmulator.ts:323`)
  returns `{ text, cols, rows, truncated }` and already takes a character bound.
- Gateway serves it at `GET /runs/:runId/terminal-snapshot`
  (`packages/runtime/src/server/runtimeRouter.ts:197`).
- The control plane already consumes it: `read_terminal_snapshot`
  (`api/src/transport_matters/api/v1/controlplane_gateway_reads.py:128`), called from
  `delivery_wait.py:531` to populate the `pane` field on a wait result.

So the work is a service verb plus the two skins, not new capture machinery.

## Shape

- `pane(run_id, max_chars?)` returning the snapshot as it already exists, with the server cap
  applied the way observe responses are capped.
- Observer grant is sufficient: it is a read.
- The verb must resolve the gateway that owns the terminal. The reproduction above shows a run
  registered on the canvas gateway and absent from its own supervised gateway, so a caller
  guessing wrong gets `run_not_found` on a live run.
- Worth deciding whether it should also be reachable for a run that has exited, since that is the
  case that motivated it. The emulator is disposed on exit
  (`TerminalEmulator.ts:341`), so the last screen may need to be retained at teardown for the
  post-mortem case to work at all.


## Comment by srobinson at 2026-09-04T14:32:02Z (updated 2026-09-04T14:32:02Z)

https://github.com/littleorgans/transport-matters/issues/574#issuecomment-5541946941

## Consider an `isPromptBufferDirty` predicate on the same capture

A second consumer for this capture, from the #616 investigation.

#616 is fusion: text left in a composer joins the next prompt. The remedy being taken is a blind
unconditional clear written immediately before every prompt, in the same PTY write as the
bracketed paste. It needs no proof, because an unobserved clear degrades to today's behaviour
rather than to something worse. It is deliberately the KISS answer.

What it cannot do is answer the question the fix actually wants asked: **is there anything in the
composer right now?** Three separate research agents converged on the same wall. From the
runtime's current PTY boundary, proving a composer is empty means either a harness supplied
semantic event, which none of the three provides reliably, or reconstructing the rendered screen
and identifying the composer region. The first does not exist. The second is what this issue is
already building.

The signals that look like acknowledgements are not. Claude's `render_acknowledged` proves a
render cycle happened, not what it drew. Grok's `Input cleared · ctrl+z to undo` is an ephemeral
tip, capped at three displays per session and suppressed for small collapses. Codex's empty
placeholder is the strongest of the three and still requires a completed differential redraw plus
confidence that the ordinary composer is the visible surface.

So the predicate belongs here rather than in the runtime's escape stream parsing. The snapshot
route already returns the exact screen, as this issue's reproduction demonstrates.

**What it would take beyond the verb.** The verb returns a screen. A dirty predicate needs the
composer's location and extent within that screen, per harness, plus the cursor position. That is
per harness UI knowledge, which is real work and is why this is a follow on rather than a
prerequisite. `TerminalEmulator` already performs robust ANSI parsing, but its public snapshots do
not expose cursor or region state, so the parsing is not the missing part.

**What it would buy.**

- #616 could verify its clear rather than assume it, and could skip the write entirely when the
  composer is already empty.
- Rollback on failure becomes possible at all. It is rejected today specifically because a
  rollback that cannot confirm its own effect is a blind write into a possibly running harness.
- The `needs_you` gap this issue already names has the same shape: a predicate over the captured
  screen rather than over the transcript.

Not a dependency for #616, which ships without it. Recorded here so the verb's design leaves room
for a predicate over the same capture rather than only a text blob for a human to read.


## Sub issues
[]


# 592: Positional system and message overrides misapply on Codex continuation requests carrying previous_response_id

URL: https://github.com/littleorgans/transport-matters/issues/592
State: open
Labels: 
Updated: 2026-09-02T10:30:15Z

## Summary

System and message overrides are addressed by position. Codex continuation requests carry `previous_response_id` and contain only the new input for that turn, so their positions do not line up with the initial request the operator authored against. `run_pipeline` in `api/src/transport_matters/request_pipeline.py` applies every override in scope to every request, so a positional override authored on the first request rewrites the wrong item on every later one.

Observed live on branch `feat/overlay-registry`: a `message_text` override on `msg:0:blk:0`, authored against the full initial request where that block was the AGENTS.md instructions, matched the user's fresh prompt on the next request and replaced "Can you review the codebase" with the prior AGENTS.md text.

## Mechanism

- `message_block_target` and `system_target` in `api/src/transport_matters/overrides/targets.py` mint targets of the form `msg:{i}:blk:{j}` and `sys:{i}`. The inspector mints the same targets through `messageBlockTarget` in `www/packages/inspector/src/lib/overrideTargets.ts`, called from `BlockRow.tsx`, `MessagesSection.tsx`, `GlobalSection.tsx`, and `InspectTab.tsx`.
- `apply_overrides` in `api/src/transport_matters/overrides/__init__.py` dispatches the four positional kinds `system_part_toggle`, `system_part_text`, `message_block_toggle`, `message_text` to `ops_messages.py`, which resolves the index against whatever `ir.system` and `ir.messages` the current request happens to carry.
- On the WebSocket transport, only the first `response.create` frame carries the full context. Each later frame sets `previous_response_id` and sends only the delta. The HTTPS Responses fallback behaves the same way. `previous_response_id` reaches the IR through `provider_extras`, and `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` in `api/src/transport_matters/request_extras.py` already names it as a continuation identity key.
- Tool overrides are unaffected. `tool_toggle` and `tool_description` match by tool name via `tool_target`, and `truncate_tool_result` matches by `tool_use_id` via `tool_result_target`.

## Reproduction with fresh captures

Run `dda34ad8-090a-4790-b78e-64a263595b7b`, captured 2026-09-02 on the preview channel. Codex `0.152.1`, model `gpt-5.6-sol`, WebSocket transport.

Capture root:

```
~/.transport-matters-preview/workspaces/dev-helioy-transport-matters/ecd9b0df/dda34ad8-090a-4790-b78e-64a263595b7b/
```

| exchange | `previous_response_id` | `sys:0` | `msg:0:blk:0` |
| --- | --- | --- | --- |
| `20260902T094637Z-69b93589` | absent | "You are Codex, an agent based on GPT-5…" | developer `additional_tools` item (see #369) |
| `20260902T094654Z-cfffac8f` | set | none | tool result |
| `20260902T094721Z-f84d914f` | set | `<skills_instructions>` developer message | user text "list your tm identity info" |

An operator who authors `system_part_text` on `sys:0` against exchange `69b93589` intends to edit the Codex base prompt. On exchange `f84d914f` the same target is the skills instructions block. An operator who authors `message_text` on `msg:0:blk:0` against `69b93589` hits the user's prompt on `f84d914f`. The pipeline applies both without any check.

Each exchange directory holds `request.ir.json` and `request.audit.json`. With overrides disabled, `request.audit.json` shows `entries: []` and equal before and after character counts, which is the baseline a regression test should hold for continuation requests carrying positional overrides.

## Code map

- `api/src/transport_matters/request_pipeline.py`: `run_pipeline`. Called from `api/src/transport_matters/addon_handlers.py` for both the HTTP and WebSocket request paths.
- `api/src/transport_matters/overrides/__init__.py`: `apply_overrides`, `_apply_override_value`, `_PRIORITY`.
- `api/src/transport_matters/overrides/ops_messages.py`: `apply_system_part_toggle`, `apply_system_part_text`, `apply_message_block_toggle`, `apply_message_text`, `codex_has_tool_result_only_turn`.
- `api/src/transport_matters/overrides/targets.py`: `system_target`, `message_block_target`, `parse_system_index`, `parse_message_target`, `adjust_system_index`, `adjust_blk_index`.
- `api/src/transport_matters/overrides/state.py`: override store and scope.
- `api/src/transport_matters/request_extras.py`: `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`.
- `api/src/transport_matters/codex/request_parser.py`: `parse_codex_request` leaves `previous_response_id` in `provider_extras`.
- `www/packages/inspector/src/lib/overrideTargets.ts`: `messageBlockTarget`.

## Settled design: content anchored positional overrides

Position is not an identity. The Codex continuation is the loudest case, but `adjust_system_index` and `adjust_blk_index` in `targets.py` already exist because indices shift after removals inside one request, and overlays are saved as reusable bundles meant to apply across exchanges and runs where positions are never guaranteed. The fix is to resolve positional overrides by the content they were authored against, with the index kept as a hint.

Shapes compared:

| shape | what it does | verdict |
| --- | --- | --- |
| Drop positional kinds on continuation (branch `1d5c9b72`) | `run_pipeline` filters the four kinds when `previous_response_id` is set | Safe and small, but Codex specific, loses recurring block overlays, and fixes only this one drift. |
| Scope overrides by request shape | Record initial versus continuation at authoring time and apply only to the same shape | Continuation shapes vary (tool result only, user turn with developer message), so the rule stays positional inside each shape and still misfires. |
| Content anchor (chosen) | Each positional override carries a digest of the block it was authored against. Apply resolves by anchor. | Provider neutral. Survives continuations, removals, and reordering. A miss is explicit and audited. |

Design:

- `Override` in `api/src/transport_matters/overrides/__init__.py` gains `anchor: str | None`. For `system_part_toggle`, `system_part_text`, `message_block_toggle`, and `message_text` it is required and holds a short digest over role, block type, and original text. `SystemPart` and `TextBlock` are the only anchorable shapes, which matches what `apply_system_part_text` and `apply_message_text` accept today. The store boundary rejects a positional override without an anchor.
- One digest function, defined twice and pinned equal: `block_anchor` in `api/src/transport_matters/overrides/targets.py` and `blockAnchor` in `www/packages/core`. A shared fixture of blocks and expected digests is checked by a test on each side.
- The inspector computes the anchor where it mints the target, next to `messageBlockTarget` in `www/packages/inspector/src/lib/overrideTargets.ts`, called from `BlockRow.tsx`, `MessagesSection.tsx`, `GlobalSection.tsx`, and `InspectTab.tsx`. The block is already in hand, so nothing new crosses the wire at authoring time.
- One resolver in `api/src/transport_matters/overrides/ops_messages.py` replaces the four index lookups. Order: the block at the stored index whose anchor matches, then a unique anchor match anywhere in `ir.system` or `ir.messages`, then miss. The index stays as the fast path and as the tie breaker when a block recurs.
- A miss is recorded, never silent. `OverrideAuditEntry` in `api/src/transport_matters/overrides/audit.py` gains `reason: str | None`, set to `anchor_miss` when a positional override finds no block. `applied` stays false.
- No provider branch. `previous_response_id` never enters the pipeline. On a Codex continuation the base prompt anchor is absent and the skills block anchor is present, and the resolver does the right thing for both without knowing what a continuation is.
- No legacy path. The persisted bundles in `www/packages/inspector/src/stores/overlaysStore.ts` are the only durable copies and the overlay store is still pre-release. Anchorless positional entries are dropped on load with a console warning.

What this buys beyond this defect: a saved overlay becomes portable across runs, harness versions, and the initial versus continuation split, and the audit gives a truthful answer when a block the operator edited no longer exists. That is the property the overlay registry needs and cannot get from indices.

## Prior art, unmerged

Commit `1d5c9b72` on `feat/overlay-registry`. The branch is 144 commits behind `main`. Treat it as a design reference.

It added `_is_codex_continuation` to `request_pipeline.py`, which reads `previous_response_id` from `provider_extras` for `provider == "codex"`, and had `run_pipeline` drop the four positional kinds from the override list before calling `apply_overrides` on a continuation. Named tool overrides stayed eligible. It added `test_codex_continuation_does_not_replay_positional_overrides` to `test_request_pipeline.py`. Verification at the time: exact replay of the captured initial request applied all six intended text overrides, exact replay of the captured continuation applied zero positional overrides and preserved the user prompt byte for byte.

The branch shape is not the one to implement. It is Codex specific, it loses recurring block overlays such as the skills instructions message, and it leaves every other positional drift unaddressed. See the settled design below.

## Acceptance

- `Override` carries a required `anchor` for the four positional kinds. The store rejects a positional override without one.
- `block_anchor` and `blockAnchor` produce identical digests over a shared fixture, proven by a test on each side.
- Positional overrides resolve by anchor in `ops_messages.py` with index as hint. A miss produces an `OverrideAuditEntry` with `applied: false` and `reason: anchor_miss`. Nothing is rewritten on a miss.
- A regression test in `test_request_pipeline.py` replays exchange `69b93589` and exchange `f84d914f` from run `dda34ad8` with a `system_part_text` anchored to the Codex base prompt and a `message_text` anchored to the AGENTS.md block stored in scope. The initial request applies both. The continuation applies neither, audits two `anchor_miss` entries, and serializes byte identical to the capture.
- A second test authors a `system_part_text` anchored to the skills instructions block against exchange `f84d914f` and shows it applies on that continuation and misses on exchange `69b93589`.
- Tool overrides and `truncate_tool_result` are unchanged and still apply on continuations.
- Behaviour is identical on the WebSocket transport and the HTTPS Responses fallback, with no reference to `previous_response_id` anywhere in the override path.
- The inspector mints the anchor alongside every positional target and shows an audit miss where it shows applied overrides today.
- `overlaysStore.ts` drops anchorless positional entries on load with a console warning. No compatibility shim.


## Sub issues
[]


# 593: Program: Per-runtime control-plane grants and MCP tool catalogs

URL: https://github.com/littleorgans/transport-matters/issues/593
State: open
Labels: enhancement, P2
Updated: 2026-09-02T15:54:15Z

# Problem

Transport Matters currently combines two mismatched launch policies:

- The persisted Canvas control-plane setting applies one grant to every direct CMDK agent launch.
- MCP `launch()` defaults child authority to `none` unless the caller supplies `grant`.
- A granted run discovers the full 34-tool Transport Matters MCP catalog, even when its runtime needs only a subset.

Agent runtimes need to declare their requested control-plane grant and MCP capabilities. Transport Matters must apply the Canvas setting as the global user consent gate, calculate effective authority, and expose only the permitted tool catalog.

# Decisions

- The persisted Canvas setting remains the global user consent gate.
- Each runtime under `~/.agent-runtimes` declares its requested grant and MCP capabilities.
- Effective authority cannot exceed the Canvas gate or the launching principal.
- Transport Matters keeps one MCP endpoint and one control-plane service.
- `tools/list` is filtered from the run-scoped bearer policy.
- Every tool keeps call-time authorization and audit checks.
- Tool catalogs remain fixed for the lifetime of a run.
- Directory and worktree restrictions belong to a future security design.
- Filtering ships on MCP SDK 1.28.1 before the isolated MCP 2.x migration.

# Work

1. Publish runtime grant and MCP capabilities from `.agent-runtimes`.
2. Consume the runtime capability contract in Transport Matters.
3. Resolve and persist effective control authority.
4. Define the canonical 34-tool MCP catalog.
5. Filter MCP discovery by run policy.
6. Update Canvas consent and launch UX.
7. Migrate mechanically to MCP 2.x.
8. Migrate MCP transport and prove real clients.

# Acceptance criteria

- Each subissue maps to one independently reviewable PR.
- Runtime declarations drive CMDK and MCP launch behavior.
- The Canvas gate can prevent a runtime from receiving its requested authority.
- Observer and director runs receive deterministic, bounded tool catalogs.
- Direct calls to hidden tools still fail through authoritative call-time checks.
- Claude, Codex, and Grok pass real launch and MCP smoke tests.
- `.agent-runtimes` generation and audit pass.
- Transport Matters `just check` and `just test` pass.

# Upstream references

- MCP tools specification: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx
- Python SDK migration guide: https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md
- Scope-filtered discovery proposal: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1881

## Sub issues
[
  {
    "number": 2,
    "state": "closed",
    "title": "Publish per-runtime control-plane grants and MCP capabilities"
  },
  {
    "number": 594,
    "state": "closed",
    "title": "Consume runtime authority and MCP capability schema v4"
  },
  {
    "number": 595,
    "state": "open",
    "title": "Resolve and persist effective control-plane authority"
  },
  {
    "number": 596,
    "state": "open",
    "title": "Define the canonical Transport Matters MCP tool catalog"
  },
  {
    "number": 597,
    "state": "open",
    "title": "Filter MCP tool discovery by run policy"
  },
  {
    "number": 598,
    "state": "open",
    "title": "Update Canvas consent and runtime authority UX"
  },
  {
    "number": 599,
    "state": "open",
    "title": "Port Transport Matters mechanically to MCP 2.1.1"
  },
  {
    "number": 600,
    "state": "open",
    "title": "Relocate MCP transport policy and prove dual-protocol clients"
  }
]


# 595: Resolve and persist effective control-plane authority

URL: https://github.com/littleorgans/transport-matters/issues/595
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:10:31Z

# Outcome

Calculate and persist one effective control-plane grant for every agent runtime launch.

Parent: #593
Blocked by: #594

# Policy

Use the ordered grant set `none < observer < director`.

- The selected runtime supplies its trusted requested grant.
- The persisted Canvas setting supplies the limiting grant for direct CMDK launches.
- The launching principal supplies the limiting grant for MCP launches.
- An optional MCP `launch()` grant supplies one additional bound when present.
- For a selected runtime, the effective grant is the minimum of the runtime request, the limiting grant, and the optional override when present.
- An omitted MCP `launch()` grant adds no bound, so the runtime request remains subject to the launching principal limit.
- An explicit MCP `launch()` grant of `none` reduces the effective grant to `none`.
- An observer or none runtime request cannot be raised by a director override.
- A raw launch with no selected runtime uses the safe effective grant `none`.

# Scope

- Change the MCP launch grant parameter so omitted and explicit `none` remain distinct.
- Add a pure policy function that resolves the effective grant.
- Apply the policy to direct CMDK and MCP launches.
- Persist requested, limiting, override, and effective values as launch provenance.
- Keep control-plane bearer minting and MCP home seeding driven by the effective grant.
- Update self identity to report the effective grant.
- Add audit fields needed to explain the decision.

# Constraints

- Canvas remains the user consent gate.
- Child launches remain bounded by the launching principal.
- Tool discovery filtering lands separately.
- Directory and worktree scope is deferred.

# Acceptance criteria

- A runtime requesting `director` receives no more than the Canvas gate permits.
- An observer principal cannot launch a director.
- Omitted and explicit `none` produce distinct policy inputs.
- CMDK and MCP launches use the same pure resolver.
- Restart and replay preserve the effective policy and provenance.
- No grant creates no bearer and no Transport Matters MCP client.
- Grant resolution, provisioning, launch skin, audit, and exact-response tests pass.
- `just check` and `just test` pass.

## Implementation guide

### Start here

Land issue 594 first and read the trusted requested grant from `runtime_templates.py` (`RuntimeTemplateRef`). Resolve the selected runtime through `launch_resolution.py` (`agent_runtime_ref`). Reuse `controlplane/models.py` (`ControlPlaneGrantOption`, `ControlPlanePrincipal`) for vocabulary and the caller limit. Apply the policy once in `capture_rpc_routes.py` (`_resolved_domain_request`) after runtime selection and before any home is prepared. Keep provisioning on `captured/context.py` (`_prepare_home_and_grant`) and MCP limits on `launch_service.py` (`ControlPlaneLauncher`). Direct CMDK launches send the persisted Canvas setting from `capturedRunStore.ts` (`ensureRun`) as the limit only.

### Direction

- Compute the effective grant as the minimum of the runtime request, the caller limit, and an optional reducing override when present. Use the ordered set `none < observer < director`. Persist the four decision values `requested`, `limiting`, `override`, and `effective`. A missing selected runtime uses null for `requested` and `none` for `effective`. An omitted override uses null. An explicit `none` uses `none`.
- Python owns policy. TypeScript transports inputs without calculating authority. Direct CMDK launches use the Canvas setting as the limit and never send an override. MCP launches use `ControlPlanePrincipal.role` as the limit and the `launch()` grant as the optional additional bound. Omission adds no bound. Explicit `none` reduces to `none`. A director override or director principal cannot raise an observer or none runtime request. A raw launch is effective `none`.
- Replace the single launch grant carrier with a limit plus an optional override, and delete the old carrier in the same change. Pass only the effective value to bearer minting, home seeding, and `whoami`. Return the frozen decision on the private capture and gateway path for audit. Keep public `LaunchResult` unchanged.

### Guardrails

- Resolve authority only after `agent_runtime_ref`. Never accept caller supplied runtime policy. Freeze the decision before `prepare_control_plane_grant`. Effective `none` creates no bearer and no Transport Matters MCP client. `whoami` reports only the effective grant.
- Do not filter `tools/list`, redesign Canvas consent, add directory or worktree authority, or add a database table for provenance. Use existing `launch_fields`. Prove the full ordered intersection table, omitted versus explicit `none`, and restart replay, then `just check` and `just test`.


## Sub issues
[]


# 596: Define the canonical Transport Matters MCP tool catalog

URL: https://github.com/littleorgans/transport-matters/issues/596
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:10:33Z

# Outcome

Replace decorator order and name-prefix inference with one canonical, ordered catalog for all 34 Transport Matters MCP tools.

Parent: #593

# Current baseline

- 34 tools total.
- 14 tools are available to observers.
- 20 tools require director authority.
- Natural domains are core control plane, Space and Canvas management, and browser control.

# Scope

- Introduce one catalog that maps every tool name to a stable capability identifier and minimum grant.
- Record read-only, destructive, and open-world hints where the current behavior supports them.
- Make the catalog the source for deterministic registration order and contract tests.
- Keep existing tool implementations and response types unchanged.
- Reject duplicate names, missing catalog entries, unknown capabilities, and catalog entries with no registered implementation.
- Document capability identifiers as a contract. Raw prefixes remain an implementation detail.

# Constraints

- No behavior change in this PR.
- Do not split the MCP server.
- Do not move domain operations out of the existing control-plane service.
- Tool exposure remains separate from call-time authorization.

# Acceptance criteria

- All 34 tools appear exactly once.
- Catalog order is deterministic.
- Every tool has one capability and one minimum grant.
- Existing MCP schemas and outputs remain byte-equivalent where ordering permits.
- Contract tests fail when a registrar and catalog drift.
- Existing MCP inventory and skin tests pass.
- `just check` and `just test` pass.

## Implementation guide

### Start here

Reuse `controlplane_mcp.py` (`create_control_plane_mcp`) as the single mounted server, `space_mcp.py` (`register_space_mcp_tools`, `SpaceMcpAdapter`) for the thirteen Space, Canvas, and Worktree callables, and `browsing_mcp.py` (`register_browsing_mcp_tools`) for the eight browser callables. Keep result envelopes in `mcp_tooling.py` (`McpToolOutput`). Reuse the closed capability type from issue 594 in `controlplane/models.py` (`ControlPlaneGrantRole`). Leave call time checks in `ControlPlaneService` and `ControlPlaneLauncher`. Extend `test_controlplane_action_skins.py` (`test_mcp_tool_schemas_are_the_agent_contract`).

### Direction

- Create one ordered catalog for all 34 tools. Each entry has a tool name, the capability identifier from issue 594, a minimum grant, and `ToolAnnotations`. Own that catalog in `mcp_tool_catalog.py` (`McpToolCatalogEntry`, `McpToolRegistry`, `MCP_TOOL_CATALOG`). Collect existing nested callables first, validate catalog and implementation sets, then register with `FastMCP.add_tool` in catalog order.
- Keep the current 34 name order and the fourteen observer / twenty director split. Map tools onto the producer identifiers for core control plane, Space management, and browser control. Do not store domain labels as a second string vocabulary. Read only does not imply observer access. `wait_for_reply`, `space_list`, and `space_get` remain director tools.
- Tool names, descriptions, schemas, and result bodies stay unchanged. Only deterministic order and annotations change in `tools/list`. Catalog metadata is declarative. It never authorizes a call.

### Guardrails

- Existing authorization remains. Bearer resolution, core director checks, Space `require_director` and `require_bound_space`, and browser gateway checks stay on their current paths. No catalog value enters the principal. Validation completes before the first `FastMCP.add_tool`, so a broken catalog never exposes a partial server. Runtime ids, skill names, tool names, and prefixes have no capability meaning.
- Do not filter `tools/list`, parse runtime capability declarations, resolve effective launch authority, split the MCP server, rename tools, or retain prefix inference. Prove exact 34 name order, the grant split, annotation presence, unchanged input and output schemas, and registrar drift, then `just check` and `just test`.


## Sub issues
[]


# 597: Filter MCP tool discovery by run policy

URL: https://github.com/littleorgans/transport-matters/issues/597
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:24Z

# Outcome

Return only the Transport Matters MCP tools permitted by the authenticated run policy during `tools/list`.

Parent: #593
Blocked by: #595 and #596

# Scope

- Add a small MCP server adapter that overrides tool listing.
- Resolve the run-scoped bearer for each request.
- Filter the canonical catalog by effective grant and allowed runtime capabilities.
- Preserve canonical deterministic ordering.
- Return the full catalog for explicit in-process contract inspection with no request principal, if that remains the chosen test contract.
- Keep all tools registered internally.
- Preserve existing call-time identity, live-capture, role, domain entitlement, and audit checks.
- Keep filtered policy fixed for the bearer lifetime.

# Protocol constraints

- Filtering must be a pure function of the presented credential.
- The list must not vary by connection identity or prior requests.
- Hidden tools must not leak through `tools/list` metadata.
- Tool annotations remain advisory.
- Call-time authorization remains authoritative.

# Acceptance criteria

- Observer runs list only observer tools within their runtime capabilities.
- Director runs list only director and observer tools within their runtime capabilities.
- Two bearers with different runtime capabilities receive different deterministic catalogs.
- A guessed call to a hidden director tool fails before side effects.
- An expired or revoked bearer receives no usable catalog.
- Catalog filtering does not fork domain authorization rules.
- MCP inventory, auth, action, and real-client smoke tests pass.
- `just check` and `just test` pass.

# Upstream reference

https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx

## Implementation guide

### Start here

Use `api/src/transport_matters/api/v1/mcp_tool_catalog.py` (`McpToolCatalogEntry`, `McpToolRegistry`, `MCP_TOOL_CATALOG`, `catalog_tool_is_eligible`), `api/src/transport_matters/api/v1/controlplane_mcp.py` (`create_control_plane_mcp`, `ControlPlaneMcpAuthApp`, `_McpControlPlaneAdapter._principal`), `api/src/transport_matters/controlplane/models.py` (`ControlPlanePrincipal`), `api/src/transport_matters/capture_rpc.py` (`_CaptureRunFacts`, `CaptureLeaseRegistry.prepare_capture`, `CaptureLeaseRegistry.resolve_control_plane_grant`), `api/src/transport_matters/api/v1/test_controlplane_mcp_discovery.py`, `api/src/transport_matters/api/v1/test_controlplane_skins.py` (`_skin_app`, `_mcp_session`), and `docs/CONTROLPLANE.md`.

### Direction

Start after #595 and #596. This issue applies one role plus capability eligibility rule to `tools/list` and `tools/call` and keeps domain auth. Freeze the validated runtime capability tuple in `_CaptureRunFacts` when `CaptureLeaseRegistry.prepare_capture` registers the live capture, then copy it into `ControlPlanePrincipal` from `CaptureLeaseRegistry.resolve_control_plane_grant`. Add one pure `catalog_tool_is_eligible` predicate beside the canonical catalog. Its only policy inputs are the catalog entry, the principal effective role, and the frozen capability tuple. Both axes are required. Subclass FastMCP so list and call use that predicate for authenticated requests. List keeps eligible original tool objects in canonical order. Call rejects unknown or ineligible names with the existing unknown tool error before FastMCP dispatch. Keep all 34 implementations registered. Eligible calls continue through existing adapters and domain authorization. Hidden calls stop before implementation, adapter, audit, or gateway work. Filtering is a pure function of the presented credential and stays fixed for the bearer lifetime. Direct in process listing with no request principal may retain the full catalog for contract inspection. Network requests always have identity after auth. Keep `tools.listChanged` false. Document the intersection of effective role and frozen capabilities in `docs/CONTROLPLANE.md`.

### Guardrails

Do not add a second grant order, catalog, capability vocabulary, or eligibility rule. Do not unregister hidden tools, mutate the shared tool manager, or infer policy from names, prefixes, runtime ids, or skills. Do not fork domain authorization or drop call time role, workspace, owner, Space, Canvas, Worktree, DevTools, audit, live capture, or revocation checks. Do not change Canvas consent, MCP SDK versions, or transport. Do not add a database migration, connection scoped cache, or registry reread during list or call. Prove the predicate, real client list and call, hidden versus absent error shape, and frozen capability projection. `just check` and `just test` must pass.


## Sub issues
[]


# 598: Update Canvas consent and runtime authority UX

URL: https://github.com/littleorgans/transport-matters/issues/598
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:26Z

# Outcome

Make Canvas show and enforce the relationship between user consent, runtime requested authority, and effective launch authority.

Parent: #593
Blocked by: #595 and #597

# Scope

- Keep the persisted Canvas control-plane setting as the global user consent gate.
- Show the selected runtime requested grant and MCP capabilities in the launch expansion.
- Show the effective grant when the Canvas gate limits the runtime request.
- Ensure direct CMDK launches send the global gate and selected runtime identity through the canonical launch path.
- Remove copy or controls that imply one global grant is assigned directly to every runtime.
- Add clear consent copy for enabling observer or director access.
- Preserve keyboard navigation and compact CMDK behavior.

# Constraints

- This issue does not add directory or worktree scoping.
- This issue does not add per-launch tool checkboxes.
- Runtime manifests own requested capability defaults.
- Transport Matters owns effective policy.

# Acceptance criteria

- A user can see the requested and effective grants before launch.
- A runtime requesting `director` is visibly limited when the Canvas gate is `none` or `observer`.
- Changing the gate persists through reload.
- Existing runs do not silently change policy when the gate changes.
- CMDK, captured-run store, transport payload, accessibility, and keyboard tests pass.
- One browser test proves the consent flow and resulting launch payload.
- `just check` and `just test` pass.

## Implementation guide

### Start here

Use `packages/contract/src/runtime/index.ts` (`CONTROL_PLANE_GRANT_OPTIONS`, `ControlPlaneGrantOption`, `DEFAULT_CONTROL_PLANE_GRANT`), `www/packages/core/src/types/runtimeTemplates.ts` (`RuntimeTemplateSummary`), `www/packages/core/src/transport.ts` (`createCapturedRunView`), `www/packages/canvas/src/model/capturedRunStore.ts` (`useCapturedRunStore`, `cycleControlPlaneGrant`), `www/packages/canvas/src/launcher/commandTypes.ts` (`CommandRow`, `LauncherCommand`), `www/packages/canvas/src/launcher/templateRows.ts` (`buildAgentRows`, `agentSpawnRows`, `spawnCommand`), `www/packages/canvas/src/launcher/CommandCenter.tsx` (`CommandCenter`, `LauncherRow`), and `www/packages/shell/tests/e2e/spawn-palette.spec.ts`.

### Direction

Start after #595 and #597. Keep Canvas as the global ceiling for new launches and leave existing runs frozen. Consume the authority decision and filtered catalog contracts as shipped. Do not recreate the Python resolver, capability vocabulary, or tool mapping. Carry requested grant and ordered MCP capability identifiers from catalog fixtures into launcher rows. Change Settings copy so the persisted value is a ceiling for future launches rather than authority assigned to every runtime. For the highlighted agent row only, show requested grant, Canvas consent, absent launch override as `Not set`, effective grant, and requested MCP capabilities. When Canvas reduces the request, mark it limited by Canvas consent. Native harness rows stay native launches with no requested capabilities and effective `none`. Keep launch execution on the existing path: selected runtime id with the spawn command, current Canvas consent as the limit, and no override. Canvas never raises a request. Changing consent persists through reload and must not mutate existing captured run records. Python remains authoritative. Use `CONTROL_PLANE_GRANT_OPTIONS` for the direct CMDK comparison.

### Guardrails

This issue does not add directory or worktree scoping, per launch tool checkboxes, or an override control. Do not duplicate authority resolution or tool filtering from #595 through #597. Do not infer policy from names, skills, descriptions, MCP server names, or tool prefixes. Do not change MCP SDK versions, transport, bearer minting, or home seeding. Prove persistence, frozen existing run policy, payload shape, accessibility, keyboard behavior, and one browser consent flow. `just check` and `just test` must pass.


## Sub issues
[]


# 599: Port Transport Matters mechanically to MCP 2.1.1

URL: https://github.com/littleorgans/transport-matters/issues/599
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:27Z

# Outcome

Port the Transport Matters MCP code and tests mechanically from Python MCP SDK 1.28.1 to MCP 2.1.1 without changing transport behavior.

Parent: #593
Blocked by: #597

# Scope

- Change the dependency to `mcp>=2.1,<3` and regenerate `uv.lock`.
- Replace `FastMCP` imports and annotations with `MCPServer`.
- Delete the obsolete `FastMCPSettings.model_rebuild()` workaround.
- Rename SDK model fields from camel case to snake case.
- Preserve wire assertions with `model_dump(mode="json", by_alias=True)`.
- Update the shared test client fixture for `httpx2` and the two-item `streamable_http_client()` result.
- Update all affected MCP skin tests.

# Dependency expectations

- Add the matching `mcp-types` package.
- Add `opentelemetry-api`.
- Promote the existing `httpx2`, `httpcore2`, and `truststore` packages to runtime dependencies.
- Remove the MCP 1.x `httpx-sse` edge.
- Keep the direct Transport Matters `httpx` dependency.

# Constraints

- Keep the existing endpoint, stateless behavior, JSON response mode, and auth behavior unchanged.
- Transport configuration moves in the following issue.
- Do not add 2026-only cache or subscription features.

# Acceptance criteria

- No `mcp.server.fastmcp` import remains.
- No SDK camel-case attribute access remains.
- Dependency resolution succeeds on Python 3.14.
- MCP schema, inventory, auth, and action tests pass.
- `just check` and `just test` pass.

# Upstream reference

https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md

## Implementation guide

### Start here

Use `api/pyproject.toml`, `api/uv.lock`, `api/src/transport_matters/api/v1/controlplane_mcp.py` (`create_control_plane_mcp`, `ControlPlaneMcpAuthApp`), `api/src/transport_matters/api/v1/mcp_tool_catalog.py` (`McpToolRegistry`, `MCP_TOOL_CATALOG`), `api/src/transport_matters/main.py` (`create_app`), `api/src/transport_matters/api/v1/mcp_tooling.py` (`mcp_tool_result`), `api/src/transport_matters/api/v1/controlplane_mcp_test_support.py` (`control_plane_http_client`, `control_plane_mcp_session`), and `api/src/transport_matters/api/v1/test_controlplane_skins.py` (`_skin_app`, `FakeService`, `FakeResolver`).

### Direction

Start after #597. This is the mechanical MCP 2.1.1 port with the minimal transport argument move, `McpToolRegistry`, and extracted shared MCP test support. Port the landed FastMCP shape: one server in `create_control_plane_mcp`, one `McpToolRegistry` that registers collected callables, and Space plus browsing registrars collecting into that registry. Do not restore server ownership to the domain registrars. Change the direct SDK range to `mcp>=2.1,<3` and regenerate `api/uv.lock` for that path only. Replace FastMCP with `MCPServer`. Delete the obsolete settings rebuild workaround. Rename Python protocol fields to snake case and keep wire assertions with JSON aliases. Extract the two reusable client context managers into `controlplane_mcp_test_support.py` before protocol adaptation, then migrate every caller without forwarding aliases. Adapt the MCP session helper to `httpx2` and the two stream result. Keep the REST helper on `httpx`. Move the existing three transport arguments from `create_control_plane_mcp` to the existing `streamable_http_app` call in `create_app`. Keep endpoint, stateless behavior, JSON response mode, auth, catalog, filtered discovery, and call time authorization unchanged.

### Guardrails

Do not change tool catalog, effective authority, runtime capabilities, or discovery policy from #597. Do not restore direct SDK registration in Space or browsing modules. Do not add a compatibility wrapper, parallel server, or direct `mcp-types` import. Do not redesign transport policy; #600 owns the durable mount, server version, 4 MiB boundary, and dual protocol proof. Do not add cache, subscriptions, dynamic tool list changes, or SSE. Do not remove the direct `httpx` dependency or convert unrelated HTTP clients. `just check` and `just test` must pass.


## Sub issues
[]


# 600: Relocate MCP transport policy and prove dual-protocol clients

URL: https://github.com/littleorgans/transport-matters/issues/600
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:29Z

# Outcome

Complete the MCP 2.1.1 migration by relocating transport policy, setting server identity, and proving legacy and modern clients against the real mounted endpoint.

Parent: #593
Blocked by: #599

# Scope

- Add one owner for constructing the mounted control-plane MCP ASGI app.
- Pass `streamable_http_path="/"`, `json_response=True`, and `stateless_http=True` to `streamable_http_app()`.
- Keep the public endpoint at `/mcp` through the existing exact-path wrapper.
- Supply the Transport Matters server version explicitly.
- Accept and test the MCP 2.x 4 MiB request-body limit.
- Verify that auth and token resolution remain per request.
- Add dual-era tests for the 2025 handshake path and 2026 request path.
- Run one real Claude or Codex home against the preview backend.

# Constraints

- The same URL must serve supported legacy and modern protocol clients.
- Do not add dynamic tool-list changes in this PR.
- Do not add directory or worktree authorization.
- Keep filtered catalogs fixed for each run bearer.

# Acceptance criteria

- Omitting any of the three required transport settings fails a focused test.
- Legacy initialize, `tools/list`, and `tools/call` succeed.
- Modern `server/discover`, `tools/list`, and `tools/call` succeed where supported.
- A valid MCP request of exactly 4194304 bytes reaches normal request handling and returns 200; the same request at 4194305 bytes returns 413.
- Claude, Codex, and Grok seeded configurations remain compatible.
- A real captured run lists its bounded catalog and completes one MCP call.
- The API MCP skin suite passes.
- `just check` and `just test` pass.

# Upstream references

- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md
- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md

## Implementation guide

### Start here

Use `api/src/transport_matters/api/v1/controlplane_mcp.py` (`ControlPlaneMcpMount`, `mount_control_plane_mcp`, `create_control_plane_mcp`, `ControlPlaneMcpAuthApp`, `ControlPlaneMcpExactPathApp`), `api/src/transport_matters/main.py` (`create_app`, `lifespan`), `api/src/transport_matters/api/v1/controlplane_mcp_test_support.py` (`control_plane_http_client`, `control_plane_mcp_http_client`, `control_plane_mcp_session`), `api/src/transport_matters/api/v1/test_controlplane_mcp_transport.py`, `api/src/transport_matters/api/v1/test_controlplane_skins.py` (`_skin_app`), `api/src/transport_matters/cli/test_control_plane_home.py`, and `api/src/transport_matters/cli/test_grok_home.py`.

### Direction

Start after #599. This issue owns the durable mount, lifecycle, allowed host test seam, 4 MiB proof, and legacy plus modern client proof. Keep #599 dependency, server, protocol field, catalog registry, and extracted test support changes intact. Add one owner for constructing the mounted control plane MCP ASGI app, public `/mcp` exact path, inner SDK path `/`, wrappers, routes, and session manager lifetime. Pass the three required transport settings to `streamable_http_app` and omit a body size override so the SDK 4 MiB default remains authoritative. Supply the Transport Matters server version explicitly. Keep `control_plane_http_client` as the REST helper. Add `control_plane_mcp_http_client` as the one raw in process MCP HTTP seam with allowed Host and Origin. Evolve `control_plane_mcp_session` to the high level client with explicit protocol mode and disabled response caching. Prove legacy initialize plus list and call, modern discover plus list and call, exact 4194304 byte success, 4194305 byte 413, per request revocation, seeded Claude Codex and Grok homes, and one real captured run against preview.

### Guardrails

Do not change dependencies, lockfile, MCP imports, protocol field names, `McpToolRegistry`, or the two stream adaptation owned by #599. Do not construct another raw MCP client outside `control_plane_mcp_http_client`. Do not add dynamic tool list updates, directory authorization, a separate legacy server, an SSE route, or a Transport Matters body limit constant. Do not disable DNS rebinding protection or change seeded configuration formats. `just check` and `just test` must pass.


## Sub issues
[]


# 602: Port the two-agent ping pong review loop from tmux to Canvas

URL: https://github.com/littleorgans/transport-matters/issues/602
State: open
Labels: 
Updated: 2026-09-02T16:49:29Z

## Position

The two-agent "ping pong" review loop was designed for agents in tmux panes talking over
helioy-bus. The delivery contract still holds; the transport around it was scaffolding for
tmux and should not be ported. This issue records where the Canvas translation stands and
the threads still open.

Source workflow: cm entry `01a05554-0534-7933-b7a9-9967b69e8efd` (scope
`global/project:helioy/repo:transport-matters`).

### Survives unchanged

The exact commit SHA is the unit of handoff. Gate evidence attaches to a SHA and is reusable
while the head is unchanged. The loop terminates only when both agents bless the same SHA.
A blessing of an earlier SHA does not bless a later one. PR after both blessings, merge on
Stuart's authorization. All of this is transport independent.

### Was scaffolding for tmux

| tmux mechanism | Canvas replacement |
| --- | --- |
| pane discovery, "never hardcode pane numbers", re-register after pane changes | `launch` returns a durable `run_id`; `roster` lists them. The re-registration section deletes. |
| helioy-bus mail, "you have mail!" nudges, do not poll | `prompt` returns a `delivery_id`, `wait_for_reply` returns that delivery's bounded reply. Correlation is in the transport. `watch` on `turn_completed` / `needs_you` covers the rest. |
| model and role contract discovered at runtime | Composition is declared at launch: agent id, harness, model, effort. |
| one shared checkout, implicit | One Workdir per agent via `worktree_create`. Handoff travels by SHA through the shared origin. Two agents in one checkout is a live hazard today. |

### New in Canvas: there is a director

In tmux the agents were peers, each privately remembering whose turn it was and which SHA was
blessed. In Canvas the orchestrator sees both conversations and can hold that state machine
centrally. Two candidate shapes:

1. **Director relays.** Agents launch with grant `none`. The orchestrator prompts A, waits,
   reads the SHA, prompts B with it, waits. The blessing ledger is orchestrator state.
   Deterministic, observable, cannot deadlock on unread mail.
2. **Peers with a referee.** Agents get `director` grant and prompt each other. Closer to the
   original, more moving parts, reintroduces the "did they read it" question.

Current lean is shape 1. It also gives the architecture-disagreement step a real home: the
escalation goes to the director, who puts it to Stuart, rather than two agents negotiating
design in mail.

## Primary constraint: token efficiency

This is the governing concern for the next iteration, ahead of fidelity to the original
workflow. Where the loop currently spends tokens:

- Two agents each carry full repo context. Round N carries rounds 1..N-1 of argument.
- A relaying director puts every handoff through a third context.
- Prose handoffs restate what the diff already says.
- Both agents re-read the same files every round.
- `conversation` pulls are expensive next to a bounded `wait_for_reply`.

### Threads to explore

Nothing below is decided.

- **Pointer, not payload.** A handoff carries branch and SHA. The reviewer reads the diff from
  git. No diff, no file content, and no restated rationale travels in a message.
- **Capped reply schema.** Agents answer in a fixed small shape: SHA, verdict, changed
  behaviour, gates run or reused. Anything longer is a bug in the prompt.
- **Fresh run per round.** Instead of two long-lived agents accumulating context, launch a run
  per round whose context is the brief plus the diff. Cheaper, and a reviewer with no memory of
  writing the code may review it better. Trade-off: loses continuity and earned judgment.
- **Director holds addresses, not content.** The orchestrator's context stays near constant
  regardless of round count.
- **Asymmetric models.** Decide deliberately which side gets the expensive model. Implementation
  and review do not obviously deserve equal spend.
- **Measure it.** No target is meaningful until a round trip has a token cost attached. Worth
  instrumenting before tuning.

## Next

Iterate on the shape here, then supersede the cm entry with the Canvas version once settled.


## Sub issues
[]


# 603: CDP attach capability expires 30s after minting, and a refused attach gives a bare 401

URL: https://github.com/littleorgans/transport-matters/issues/603
State: open
Labels: bug, browser, P1
Updated: 2026-09-02T17:38:02Z

A CDP attach capability expires 30 seconds after minting, and minting is only available as a side effect of listing panes. An agent that reads the pane listing, decides what to do, then connects, routinely arrives after the window has closed and gets an unexplained `401`.

## Observed

Road testing #601, driving the inspector from an orchestrator run:

1. `browser_panes` returned `devtools_url` carrying a freshly minted capability.
2. A few tool calls later, the CDP client connected and the WebSocket handshake failed with `Unexpected server response: 401`.
3. Nothing in the failure named the cause. Working out that the capability had lapsed meant reading `api/src/transport_matters/api/v1/devtools_access.py`.
4. Calling `browser_panes` again and connecting in the same step succeeded immediately.

The controls in `DevtoolsCapabilityStore` are three:

- `open()` spends the capability once and refuses a second open (`devtools_access.py:94`).
- The capability is bound to the origin it was minted for, and the front must present it back naming the origin it is actually listening on.
- `OPEN_WINDOW_SECONDS = 30.0` bounds how long an unspent capability stays live.

Live sessions are not affected: `keep()` refreshes `last_seen` on every command and only `IDLE_SECONDS = 600` of total silence retires a socket. The cost is entirely at the door, and it lands hardest on an agent, whose read-then-act gap is exactly where the 30 seconds goes.

Because `open()` is one shot, a dropped socket also cannot be re-attached with the token in hand. Every reconnect means re-enumerating panes.

## Threat the window actually covers

The front is loopback bound, and `loopback_origin` (`devtools_access.py:225`) refuses to mint for any other host, so a remote holder of the capability cannot reach the socket to spend it. A capability that lands in a transcript or a provider log is not reachable from where it lands. What remains is local replay: session files on disk are readable by any process running as the same user, including the codex and grok runs this workspace launches with shell access. That is a real path, but `open()` being one shot already closes replay more decisively than the window does.

The window's distinct contribution is narrow: it bounds a minted-but-never-spent capability. Weighed against the friction it creates for the in-app browser's whole purpose, which is live debugging of a locally running server, the trade is not obviously worth it.

## Outcome

Attaching to a pane is predictable, and a refused attach says why.

## Scope

- Decide whether `OPEN_WINDOW_SECONDS` earns its place given that one-shot spend and origin binding already carry the security weight. Options: drop it; or widen it substantially.
- Give a refused attach a distinguishable reason. A bare `401` on the WebSocket handshake is indistinguishable from a wrong origin, an already-spent capability, and an unknown one.
- Consider a mint verb separate from the pane listing, so re-attaching after a dropped socket does not require re-enumerating panes.

## Acceptance

- List panes, wait past the current window, attach, and the outcome is either success or a refusal naming the cause.
- Re-attaching after a dropped socket does not require a fresh `browser_panes` call, or the issue records why it must.
- `just check` and `just test` green.


## Sub issues
[]


# 611: Capture derived request purpose fixtures with a check mode

URL: https://github.com/littleorgans/transport-matters/issues/611
State: open
Labels: 
Updated: 2026-09-03T20:23:22Z

## Problem

Request purpose classification is proved by synthetic `make_request_ir()` fixtures: shapes written by hand. They cannot become visibly stale when a harness changes its traffic, because nothing ties them to observed traffic.

The launch comparison catches structural schema drift. Request purpose does not depend on structure alone. It depends on values such as tool presence, token budget, beta headers and request class. A harness can hold its schema exactly and change every one of them, and no current check would notice.

Raised on #523 from the evidence in #557 and PR #559. Split out of #523 because it is small, self contained, protects the certify run, and requires no change to the publish path.

## Deliverable

Each audit capture generates a small sanitized request purpose fixture, keyed by:

- harness
- exact harness version
- model
- capture profile
- request class

The projection retains only the request IR and the headers the provider classifier reads. Full raw captures stay outside this repository.

## Check mode

The generator needs a check mode. A changed capture projection fails the check until the fixture and its expected purpose are reviewed. This is the invalidation path the synthetic fixtures lack.

Classifier replay asserts:

- primary agent requests classify as `True`
- known housekeeping and auxiliary requests classify as `False`
- no captured request class capable of prompt collision rests on `None`

## Why this ordering

This gives the synthetic unit tests a measured source without removing them, and it lands before the full certification publication so that a classifier regression is caught by a fixture rather than by a published release.

It changes no publish path and adds no new evidence artifact. It reads captures that already exist.

## Acceptance

- A capture produces a fixture at the five keys above.
- Check mode fails on a changed projection and names what changed.
- Replay asserts the three classifications.
- The existing synthetic fixtures remain, now with a documented measured counterpart.

## Related

#523 for the audit corpus this reads from, #557 and PR #559 for the classifier gap that motivated it.


## Sub issues
[]


# 624: control plane: run failures the vocabulary cannot name lose their code and message, so an idempotency conflict reads as an invalid request

URL: https://github.com/littleorgans/transport-matters/issues/624
State: open
Labels: bug, P3
Updated: 2026-09-04T17:23:58Z

The Gateway's run routes reject with codes the control plane has no word for. Each one falls
back to a code derived from the HTTP status and a synthetic message, so a precise condition
the server already named arrives as a coarser one, and the reason it computed is dropped.

This is the residue #617 did not reach. #617 fixed the two losses it found and this branch
widened the recognized set twice more, always by carving a hole in the same generic default.
The remaining codes cannot be carved in, because the control plane cannot say them.

## Observed

Creating a run with an idempotency key already used for a different launch:

```
launch(...)
  -> {"failure":{"detail":{"code":"invalid_request",
      "message":"gateway run request failed with 409"}}}
```

`RunManager` raised `RunManagerError("idempotency_conflict", "idempotency key was already
used for a different launch request")` (`runManagerSupport.ts`, `RunManager.createWithDisposition`).
`replyRunManagerError` sent both faithfully as `{error, message}`. Neither survives.

The caller learns that something about the request was invalid, which is the same answer a
malformed body gets, and cannot tell that retrying with a fresh key would work.

## The five codes and what each becomes

`RunManagerErrorCode` in `runManagerSupport.ts` is the whole vocabulary the run routes
answer with, plus a capture RPC `upstreamCode` passed through by `RunManagerError`.
`gateway_response_error` in `controlplane/action_policy.py` derives the code from the status
whenever the body's code is unrecognized, which is all five.

| gateway code | status | caller sees | the message that is dropped |
| --- | --- | --- | --- |
| `idempotency_conflict` | 409 | `invalid_request` | idempotency key was already used for a different launch request |
| `run_terminated` | 409 | `invalid_request` | run `<id>` was terminated |
| `run_not_attachable` | 409 | `invalid_request` | run `<id>` is `<state>` |
| `launch_failed` | 500 | `delivery_failed` | the spawn or capture RPC failure, verbatim |
| `run_manager_closed` | 503 | `delivery_failed` | run manager is closed |

Three distinct conditions collapse onto `invalid_request`, which already means "you sent
something malformed". A caller cannot branch on any of them.

## Why the message goes with the code

`gateway_error_from_response` in `api/v1/controlplane_gateway_errors.py` keeps the body's
message only when the body's code is one the caller accepts, and replaces it otherwise. That
gate is deliberate and should stay: a control plane error is a pair, and forwarding a message
while deriving its code from the HTTP status would describe one failure in two vocabularies.

The consequence is that a message cannot be rescued on its own. The code has to become
sayable first, and then the message follows for free.

## Two remedies, not one

Not every gateway code needs a new word.

**Alias.** `run_manager_closed` is what `control_plane_unavailable` already means, and a
capture RPC `worktree_not_found` is a `not_found`. These need a gateway-code to
control-plane-code mapping at the run front, not a wider union. The message survives because
the code was recognized, which is the existing rule working as intended.

**Promote.** `idempotency_conflict`, `run_terminated` and `run_not_attachable` name
conditions the control plane has no way to express and a caller would act on differently.
These belong in `ControlPlaneErrorCode`.

`launch_failed` is the one that needs a decision rather than a default. Its message is
whichever OS or capture RPC error text the launch produced, so promoting it publishes
machine-generated internal text to every skin. `test_run_proxy_keeps_non_enablement_gateway_failures_opaque`
pins today's behaviour with `spawn /private/path EACCES` as its example. Whether that example
is a warning or an accident of drafting is not recorded anywhere: PR #301 introduced both the
parser and that test in one commit, the parser's docstring says only "Preserve hard enablement
codes from the gateway before generic mapping", and neither the PR body nor any doc mentions
leaks. The only documented opacity policy is `invoke_control_plane` in `controlplane/errors.py`,
and that one covers unexpected Python exceptions, not gateway bodies.

## Not the fix

Forwarding the message whenever the body carries one, and leaving the code status-derived.
It is the smaller change and it is wrong: the pair stops agreeing, so a caller reading
`invalid_request` alongside a message about a terminated run has to decide which half to
believe.

Widening `_RUN_ACCEPTED_CODES` in `api/v1/controlplane_gateway_runs.py` to admit the five
strings. `accepted_codes` is typed `Collection[ControlPlaneErrorCode]`, so a code that is not
in the union cannot be admitted without lying to the type, and `GatewayResponseError.code`
would then carry a value no skin can render.

## Outcome

A caller that hits a run condition the server named reads that condition, and can branch on it.

## Scope

- Add the promoted codes to `ControlPlaneErrorCode` in `controlplane/errors.py`, and to
  `CONTROL_PLANE_ERROR_STATUS` in `api/v1/controlplane_routes.py` with the status each maps to.
- Map the aliased gateway codes onto existing control plane codes at the run front, so their
  messages survive the same gate every recognized code passes.
- Extend `_RUN_ACCEPTED_CODES` to the promoted codes.
- Decide `launch_failed` explicitly, and record the decision where the next reader will find it.

## Acceptance

- An idempotency conflict returns its own code and the message `RunManager` wrote.
- A gateway code with no control plane meaning still returns the status-derived code and the
  generic message, so the default stays closed.
- The REST status map still exhausts the vocabulary, which
  `test_rest_status_map_exhausts_the_control_plane_error_vocabulary` already enforces.

## Blast radius

- `ControlPlaneErrorCode` is a closed union rendered into the MCP tool output schemas through
  `ControlPlaneFailure` and `ControlPlaneErrorDetails`, so promotion changes the published
  agent contract.
- `CONTROL_PLANE_ERROR_STATUS` must gain every new code or
  `test_rest_status_map_exhausts_the_control_plane_error_vocabulary` fails. That test is the
  guardrail; `control_plane_error_handler` falls back to 500 rather than raising, so an
  unmapped code degrades quietly rather than crashing.
- `LaunchTerminalError` in `controlplane/launch_ledger.py` stores a `ControlPlaneErrorCode` and
  round-trips it, so persisted ledger rows carry the wider vocabulary.
- No browser mirror of the union exists. The codes are not enumerated anywhere under `www/`.

## Map for the next agent

```
RunManagerError raised            packages/runtime/src/service/RunManager.ts
  the five codes                  packages/runtime/src/service/runManagerSupport.ts
replyRunManagerError sends both   packages/runtime/src/server/runtimeRouter.ts
_typed_run_request                api/v1/controlplane_gateway_runs.py
  >> code unrecognized            gateway_error_from_response, api/v1/controlplane_gateway_errors.py
  >> message replaced             same call
gateway_response_error            controlplane/action_policy.py
  >> code derived from status     same function
control_plane_failure             controlplane/errors.py
```

## Verified

Every symbol above was read on this branch at `29ee0af8`. The status column is
`RUN_MANAGER_HTTP_STATUS` in `runtimeRouter.ts` read against `gateway_response_error`; the
messages are the literals at each `new RunManagerError(...)` site. `run_not_found` is
deliberately absent from the table: those three routes send a bare code with no message, and
404 already maps to `not_found`, so nothing is lost there today.


## Sub issues
[]


# 630: harness discovery: enumeration acts as permission, so a model released today is undiscoverable and unverdicted

URL: https://github.com/littleorgans/transport-matters/issues/630
State: open
Labels: bug, P1
Updated: 2026-09-05T02:52:12Z

Transport Matters supports every new harness release and every new model automatically. A version inside the blessed range is supported. A version outside it is evaluated on first launch and comes out blessed or degraded. Nothing is ever blocked, and nothing is ever hidden.

Three independent defects break that premise today. `gpt-6-astra` released on 2026-09-04 and no Transport Matters user can discover it.

## Observed

`gpt-6-astra` is enumerated by the installed `codex-cli 0.153.2`, runs correctly, and is captured correctly. It does not appear in the launch view, and it has no support verdict.

```
launch view codex models   gpt-5.2, gpt-5.5, gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra
codex exec --model gpt-6-astra   model: gpt-6-astra   ASTRA_OK   exit 0
wire_exchange.model              codex/gpt-6-astra    (11 exchanges)
roster.observed_model            gpt-6-astra
harness_target_observation       no row
support verdict                  none
```

The runtime never objected. Capture never objected. Discovery and verification are the layers that failed.

Separately, `claude` disappeared from the launch view entirely for part of the same session, while claude runs continued to launch and complete normally.

## The three causes

**1. The enumeration probe reads the build time catalog.** `harnesses/probes/codex.py:147` runs `("debug", "models", "--bundled")`, which is embedded in the binary and by construction cannot contain a model released after that binary shipped.

```
codex debug models --bundled    11 models, gpt-6-astra visibility=hide
codex debug models               9 models, gpt-6-astra visibility=list priority=1
```

The refreshed catalog also carries `gpt-5.3-codex-spark`, a second model no user can currently select, and omits `gpt-5.2`, `gpt-5.4` and both daybreak variants. The omission matters: `gpt-5.2` is the model this account's subscription cannot use, so the vendor's live catalog is already account aware.

A second, smaller filter sits behind it. `harnesses/probes/codex.py:113` discards every model whose `visibility` is not exactly `list`. Upstream `visibility` is presentation only: `list` means `show_in_picker=true`, `hide` and `none` mean `show_in_picker=false` with metadata still available for explicit selection, and `none` is what upstream mints for an unknown slug without rejecting it. Explicit model resolution never consults it. Proven by `codex exec --model gpt-6-astra` returning `ASTRA_OK` at exit 0.

**2. Resolution treats target observations as version locked permission records.** `harnesses/resolver.py:370` requires `target.harness_version == installed.normalized_version`. A harness patch release therefore erases every retained target.

```
target 2.1.260 / installed 2.1.260   10 launch options
target 2.1.260 / installed 2.1.261    0 launch options
```

Zero options makes `api/v1/harness_launch_view.py:155` emit `launchable: false` with the fallback reason `target_unavailable` at `:286`. The rows go stale because enumeration failed silently: `claude -p /model` under the shared five second probe limit returned TIMEOUT at 5.048s, while the identical command completed in 7.411s and parsed to all ten models. Failures collapse to `None` at `harnesses/probes/runner.py:229`.

Actuation is unaffected throughout. `harnesses/launch_target.py:185` converts `target_unavailable` into advisory launch arguments, which is why runs kept working while the picker offered nothing.

**3. A model the shipped release does not reference gets no verdict at all.** `support_verdict_store.py:224` requires an exact launch model match and `:78` returns silently when none exists, so the model is neither blessed nor degraded. `launch_verification.py:220` compounds this by skipping capture whenever the installed harness version sits inside the blessed range, so a new model on an in range harness is never captured and never compared.

## Outcome

A model or harness version released today is discoverable, launchable, captured, and classified blessed or degraded on its first launch. Enumeration is discovery. It is never permission.

## Sub issues

- [ ] Probe and catalog recovery
- [ ] Resolution and launch semantics
- [ ] First launch verdict for an unreferenced model


## Sub issues
[
  {
    "number": 631,
    "state": "open",
    "title": "codex enumeration: probe the refreshed catalog, admit every visibility, and stop collapsing probe failures to None"
  },
  {
    "number": 632,
    "state": "open",
    "title": "resolution: retained targets must survive a harness version change and never gate launchability"
  },
  {
    "number": 633,
    "state": "open",
    "title": "verification: a model the release does not reference must come out of first launch blessed or degraded"
  }
]


# 631: codex enumeration: probe the refreshed catalog, admit every visibility, and stop collapsing probe failures to None

URL: https://github.com/littleorgans/transport-matters/issues/631
State: open
Labels: bug, P1
Updated: 2026-09-05T02:52:14Z

Sub issue of the harness and model discovery epic.

The codex enumeration probe reads the catalog embedded in the binary, so a model released after that binary shipped can never be discovered. A second filter discards models the vendor marks as hidden in its own picker. Enumeration failures collapse to `None`, so a slow probe silently preserves stale rows.

## Observed

```
codex debug models --bundled    11 models, gpt-6-astra visibility=hide
codex debug models               9 models, gpt-6-astra visibility=list priority=1
```

The refreshed catalog additionally carries `gpt-5.3-codex-spark` (`list`, priority 26) and `gpt-reserve`. It omits `gpt-5.2`, `gpt-5.4` and both daybreak variants, so it is account aware.

`visibility` is presentation only. `list` means `show_in_picker=true`; `hide` and `none` mean `show_in_picker=false` with metadata still available for explicit selection, and `none` is what upstream mints for an unknown slug without rejecting it. Explicit resolution never consults it. `codex exec --model gpt-6-astra` printed `ASTRA_OK` at exit 0.

Measured in a production style probe environment:

| command | latency |
| --- | --- |
| refreshed, stale cache | 0.557s |
| refreshed, fresh cache | 0.15 to 0.20s |
| bundled | 0.154s |
| refreshed, unauthenticated isolated home | exit 0 in 0.164s, bundled catalog |

The refreshed command is a catalog GET. It sends no model turn and costs no tokens. It advances `~/.codex/models_cache.json`, so it does perform network and filesystem IO. Startup is unaffected because `run_startup_refresh` is an unawaited background pass at `main.py:455`.

The claude enumeration probe measured 4.731s against a five second shared limit, leaving 0.269s of headroom, and was observed to time out at 5.048s earlier the same day against a command that completes in 7.411s.

## Scope

- `harnesses/probes/codex.py`: make `("debug", "models")` the primary command with `("debug", "models", "--bundled")` as fallback. Parse `list`, `hide` and `none` identically; delete the visibility filter at `:113`. Bump to `codex-model-enumeration-r2`.
- `harnesses/probes/__init__.py`: add `fallback_commands`, `refresh_policy` and `snapshot_policy` to `ModelEnumerationProbeAdapter`. Add typed `ModelEnumerationSuccess` and `ModelEnumerationFailed` results.
- `harnesses/probes/runner.py`: add a 30 second enumeration timeout distinct from the five second authentication timeout. Run primary then fallback. Return structured results with a closed failure vocabulary (`timeout`, `nonzero_exit`, `invalid_output`, `execution_failed`) and no raw stderr, paths or arguments.
- `harnesses/state_refresh.py`: consume structured results, log sanitized failure and fallback reasons, and record codex results as partial snapshots. Codex refreshes on every startup, because the remote catalog changes while the CLI version does not, so a revision bump alone would only repair the first startup.

Merge rules when the two catalogs disagree: a successful refreshed result wins for every model it returns and bundled is not consulted; if refreshed fails and bundled succeeds, bundled wins for models it returns; a model absent from the successful result retains its previous row unchanged, including version, timestamp, efforts and default effort; if both attempts fail, no target rows change. A model present only in the last known set stays offered. `record_target_snapshot` already upserts without deleting omissions under `partial` completeness, so no storage change is needed.

Do not persist upstream `show_in_picker`. Importing codex's presentation policy would recreate a hidden model class inside Transport Matters.

## Verification

- `probes/test_codex.py`: assert refreshed then bundled command order, `r2`, and retention of `list`, `hide` and `none` models with their effort fields.
- `probes/test_runner.py`: primary success, timeout fallback, nonzero fallback, parser fallback, both attempts failing, sanitized failures, and the separate 30 second enumeration timeout.
- `test_state_refresh.py`: fake store honours partial merge; codex refreshes at an unchanged CLI version; refreshed models update; omitted models retain provenance; complete failure changes no rows.
- A production style codex refresh run once authenticated and once in an isolated unauthenticated home.

## Outcome

`gpt-6-astra` and `gpt-5.3-codex-spark` appear in the launch view. The claude enumeration timeout stops silently preserving stale rows.


## Sub issues
[]


# 632: resolution: retained targets must survive a harness version change and never gate launchability

URL: https://github.com/littleorgans/transport-matters/issues/632
State: open
Labels: bug, P1
Updated: 2026-09-05T03:11:03Z

Sub issue of the harness and model discovery epic.

Target observations are treated as version locked permission records, so a harness patch release erases every retained target and the harness disappears from the launch view. Runs continue to launch throughout, because actuation is fail open.

## Observed

```
target 2.1.260 / installed 2.1.260   10 launch options
target 2.1.260 / installed 2.1.261    0 launch options
```

`harnesses/connections_store.py:276` already reads every target row by `(executor_id, harness_id)`, so storage is correct. `harnesses/resolver.py:342-376` then removes rows whose observed harness version does not exactly equal the installed version. Zero options makes `api/v1/harness_launch_view.py:153-161` emit `launchable: false`, and `_unavailable_reason` at `:278` falls through to `target_unavailable`.

`harnesses/resolver.py:547` copies the target observation's older version into `ResolvedTarget`, so deleting the equality alone is not sufficient. No runtime consumer reads `ResolvedTarget.harness_version`: the constructor and `test_resolver.py:350` are the only direct references. First launch verification already reads the actual version from prepared run facts at `launch_verification.py:215-246`.

`harnesses/launch_target.py:185-196` passes an explicit unobserved selector through to the harness, which is why claude runs kept working while the picker offered nothing.

## Scope

- `harnesses/resolver.py`: simplify `_offered_targets` to decorate every row already scoped to the executor and harness. Remove the installed version equality, active release attribution filtering, observation status filtering, account entitlement filtering, and the enumeration derived unverified opt in. The compatibility release continues to supply canonical identity, lifecycle and launch adapter metadata through `decorate_target`. Net deletion keeps this 692 line file under the 700 line limit.
- Separate the two version authorities:

```python
class TargetObservationProvenance(_ResolverModel):
    compatibility_release_id: str | None
    harness_version: str
    observed_at: str
    observation_revision: str
    observation_adapter_revision: str

class ResolvedTarget(_ResolverModel):
    ...
    installed_harness_version: str
    target_observation: TargetObservationProvenance
```

  `installed_harness_version` comes from the current `LocalHarnessObservation`, normalized where available. Nesting is preferred over flat fields so the two authorities cannot be confused by name.
- Remove `allow_unverified_target`, `target_unverified_opt_in_required` and `requires_unverified_opt_in`. `observed` and `declared` describe provenance; requiring an opt in turns enumeration into permission. Touches `harnesses/resolver_contracts.py`, `www/packages/core/src/types/harnessInventory.ts` and the shared `LaunchOption` fixture.
- Remove `account_entitlement_unavailable` from launch resolution and `harnesses/resolver_snapshots.py`. Keep it in certification and publishing, where it prevents known futile provider spending. The vendor's refreshed catalog is account aware, so entitlement filtering arrives from the source.
- `api/v1/harness_launch_view.py`: an installed, enabled, launch capable harness with zero options returns `launchable: true` with `models: []`, `efforts: []`, authentication `unknown` and access `missing`. Probe absence, stale evidence and probe failure must never reach the unavailable branch. Keep the unavailable projection for a missing executable, a disabled harness, a retired target and an explicit authored block.
- `harnesses/launch_target.py`: convert a `target_unavailable` rejection carrying `reason=not_observed` into a `VerificationCell` using the requested harness, model and effort, so enumeration failure never prevents first launch assessment. Apply the same rule to a configured native model discovered from the launch home.
- Docs: replace the target authority table at `docs/HARNESS-COMPATIBILITY.md:168-189`, whose freshness and opt in rules this overturns. Update `docs/LAUNCH-CONTRACT.md:91-99,113-128` and remove the obsolete rejection from `docs/plans/LOGGING-PLAN.md:237-242`.

No lifecycle field is added to `harness_target_observation`. Lifecycle remains compatibility metadata applied by `harnesses/resolver_targets.py:26`.

## Verification

The integrated regression belongs in `test_state_refresh.py`:

1. Record ten successful target observations at `2.1.260`.
2. Change the installed harness observation to `2.1.261`.
3. Return a structured enumeration timeout.
4. Assert all ten prior rows remain stored with `2.1.260` and their original timestamp.
5. Assert all ten launch options remain offered.
6. Resolve one option and assert `installed_harness_version == "2.1.261"`.
7. Assert its target provenance still says `2.1.260`.
8. Assert support is unknown for the unassessed installed version.
9. Assert `resolve_launch_target_views` produces a `VerificationCell`.

Also update `test_resolver.py`, `test_resolver_launch_options.py`, `test_resolver_snapshots.py`, `test_resolver_model_identity.py`, `test_resolver_support.py`, `test_launch_target.py`, `test_capture_rpc_verification_cell.py` (the unknown explicit model case changes from `NoVerificationCell` to `VerificationCell`), `test_controlplane_mcp_inventory.py` and `harnessInventory.test.ts`.

## Outcome

A harness patch release never removes a harness from the launch view. Absent, stale or failed enumeration leaves every retained target offered and verifiable.


## Comment by srobinson at 2026-09-05T03:11:03Z (updated 2026-09-05T03:11:03Z)

https://github.com/littleorgans/transport-matters/issues/632#issuecomment-5548958695

## Entitlement filtering does not arrive from the source

One scope bullet needs correcting before implementation: "Remove `account_entitlement_unavailable` from launch resolution ... The vendor's refreshed catalog is account aware, so entitlement filtering arrives from the source."

Verified against codex 0.153.2: the bundled catalog enumerates `gpt-5.2` with `visibility: list`, and the provider answers 400 `The 'gpt-5.2' model is not supported when using Codex with a ChatGPT account`. The catalog is not account aware for this case. The refusal is learned only from a provider turn, which is exactly what #470 records.

Certification and publishing cannot own it either. A release cannot know which account will run it, so an account fact in signed release data is wrong by construction.

Boundary, as recorded on #470:

- Entitlement exclusions are runtime evidence in the session store, keyed by provider and model, beside the existing quota decisions.
- They are the one sanctioned refusal at launch, an enumerated block in the #384 sense. Everything else in this issue stands: version equality, release attribution, observation status and the unverified opt in all stop gating.

So the bullet becomes: move the entitlement read from the on disk baseline attempts to the store, and keep it in launch resolution. #470 carries the storage change; this issue should depend on it rather than delete the read.


## Sub issues
[]


# 633: verification: a model the release does not reference must come out of first launch blessed or degraded

URL: https://github.com/littleorgans/transport-matters/issues/633
State: open
Labels: bug, P2
Updated: 2026-09-05T02:52:19Z

Sub issue of the harness and model discovery epic.

A model the shipped release does not reference receives a verification cell but no verdict, so it is neither blessed nor degraded. It falls out of the compatibility contract entirely.

## Observed

`gpt-6-astra` released on 2026-09-04. The shipped codex release reference carries only `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` and `gpt-5.5`. `support_verdict_store.py:224` requires an exact launch model match and `:78` returns silently when none exists. `launch_verification.py:220` skips capture whenever the installed harness version is inside the blessed range, so a new model on an in range harness is never captured and never compared.

Once the enumeration probe reads the live catalog, new models arrive routinely and several at a time, so this becomes the normal path rather than a corner case. `gpt-5.3-codex-spark` is a second present example.

## Reference selection: exact precedence, then alternative sibling contracts

For each required `RequestShape`:

1. Select references from the pinned release matching the candidate's harness, exact route, body profile and request shape.
2. If an exact launch model reference exists, use it exclusively. A failed exact comparison cannot escape through a sibling.
3. Otherwise compare separately against every eligible sibling, each call keeping the shipped reference on the left of `assess_support_state`.
4. Bless the cell when at least one complete comparison is blessed. Otherwise degrade it.
5. A complete comparison covers body and envelope from the same reference whenever both sides carry an envelope. A passing body from one sibling may not be paired with a passing envelope from another.
6. Sort references by their existing reference key; the first passing reference is the displayed witness. Persist every comparison result with reference identities and digests. Ordering affects presentation only.

Alternatives beat a fixed representative because the shipped references disagree with each other. `gpt-5.5` differs in schema from sol, terra and luna, so a candidate carrying sol's schema is degraded against `gpt-5.5` and blessed against the other three. A fixed representative or an all siblings requirement would degrade a schema Transport Matters already ships as supported. The accepted tradeoff is that an unreferenced model can satisfy a less demanding shipped variant; exact precedence takes over once its own reference ships.

Candidate identity is preserved everywhere. Reference identities are provenance, never replacement identities. `RequestShape`, `SupportState` and the directional comparator are unchanged, and `baseline_comparison.compare_model_pair` keeps its two direction peer comparison for cohorts.

Runtime blessed newcomers never become references for other models. A local verdict establishes compatibility against publisher owned evidence; it does not confer authority to extend the reference set. Allowing it would make results depend on a machine's launch history.

## Every first launch has a state

An uncovered model begins at `degraded` with reason `verification_pending` and phase `queued` or `running`. A completed comparison replaces that assessment. Missing references, failed capture, provider refusal, unavailable provenance and derivation failure each retain degraded with their own reason. No compatible reference at all yields `degraded` with reason `no_compatible_reference`, retaining first turn evidence and inventing no structural findings. Blessed requires every required shape satisfied; partial completion stays degraded. Pending or failed verification must never manufacture a missing property finding.

## Verification queue

`launch_verification_support.py:114` rejects excess submissions. Three simultaneous submissions returned `accepted: true, true, false`, so one verification is silently dropped. With several new models arriving from one catalog refresh this becomes routine.

Replace it with a durable, deduplicated queue of requested verification cells, keeping the existing two worker execution limit: repeated launches of one cell join existing work; distinct models get separate records; saturation queues rather than discards; workers recheck existing evidence under the cell lock before spending provider requests; capture deadlines start at execution so queue waiting does not consume the capture budget; restart recovery discovers pending work without another launch. Queue admission must not increment `attempt_count`.

## Capture cost

Refresh itself spends zero provider requests. Capture is per launched model and independent of sibling count, since comparison is local.

| capture required | provider requests per model |
| --- | ---: |
| first turn | 3 |
| tool turn | 6 |
| both shapes | 9 |
| valid captured evidence reused | 0 |
| already referenced model inside the blessed range | 0 |

Today's codex release carries first turn references only, so astra costs 3 and spark costs 3. Existing evidence reconciliation precedes the quota check, so a refusal to spend further provider requests must never prevent a local comparison.

## Retention

A verdict answers what support a captured model earned on a route and harness version against a release. Catalog membership answers what the vendor currently offers this account. Removing `gpt-5.2` or `gpt-5.4` from the latter does not invalidate the former. Refresh never deletes or downgrades a verdict, a stored verdict never reintroduces a model into the picker, and disappearance triggers no capture. Reappearance at the same evidence coordinates reuses the verdict; changed coordinates require a new assessment.

Add a read only `GET /v1/harnesses/{harness_id}/support-verdicts` with model, route, version and release filters, backed by the same store validation functions. `GET /v1/harnesses` exposes only baseline attempt information today (`harnesses/inventory.py:549`) and is not a complete reader.

## Scope

| file | change |
| --- | --- |
| new `support_reference_policy.py` | own `SupportReferencePlan`, required shapes, exact precedence, sibling alternatives, empty set behaviour. Shared by writer, reader, resolver and capture planner |
| `support_verdict.py` | separate candidate identity from a collection of `ReferenceComparison` records; distinct typed variants for comparison backed assessments and conservative degraded reasons |
| `support_verdict_store.py` | replace `_matching_reference`; write under candidate identity; discover verdicts independently of release model names and live targets |
| `harnesses/resolver.py`, `resolver_snapshots.py` | consume the same plan and candidate assessments |
| `launch_verification.py`, `launch_verification_support.py` | model aware capture eligibility, reconcile before quota, drain queued work through bounded workers |
| new `launch_verification_queue.py` | one `VerificationRequest` per capture key; admission, deduplication, restart discovery |
| `baseline_capture.py`, `baseline_evidence.py` | bind the actual capture route, prevent evidence reuse across routes, retain candidate identity |
| new support diagnostics route | expose retained verdicts independently of catalog membership |
| `CLAUDE.md`, `docs/HARNESS-COMPATIBILITY.md` | model aware eligibility, provisional degradation, publisher only reference authority, queueing, retention |

`baseline_store.py` is 699 lines and `resolver.py` is 692. Extract before expanding either.

## Verification

1. Astra and spark arrive together; each receives its own first launch verdict on an in range harness.
2. At least three distinct new models launch simultaneously. All work drains, at most two captures run concurrently, none is dropped.
3. Duplicate launches share one capture; reversing launch and completion order preserves results.
4. Runtime blessed newcomers never enter another candidate's reference set.
5. First turn only capture costs three requests per new model; both shapes cost nine; sibling count adds no provider requests.
6. Exact precedence, sibling alternatives, directionality, envelope pairing and shape separation behave as specified.
7. No reference, queued, partial, failed and corrupt evidence cases always produce explicit degraded assessments.
8. Removing a model from a complete refreshed catalog preserves its artifact and diagnostics result without restoring its picker entry.
9. Reappearance reuses valid evidence; changed coordinates cannot reuse the wrong verdict.
10. Writer, reader and resolver agree on the selected reference set and reject tampered identities or digests.

## Outcome

A model released today comes out of its first launch blessed or degraded, never verdictless.


## Sub issues
[]
