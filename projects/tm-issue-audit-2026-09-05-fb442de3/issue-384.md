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
