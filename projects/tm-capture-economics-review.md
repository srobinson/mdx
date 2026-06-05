---
title: Transport Matters Capture Economics Review
type: projects
tags: [transport-matters, baseline, verification, review, capture-economics, persistence]
summary: Adversarial review of fix/capture-economics 6557f28d against the surfacing spec, the live store, and the branch's own brief
status: active
project: transport-matters
confidence: high
created: 2026-08-23
updated: 2026-08-23
---

# Capture Economics Review: `fix/capture-economics` @ `6557f28d`

**Verdict: not yet. Three major findings, six minor. Two of the majors are small fixes;
the third is a scope gap that `~/.mdx/projects/tm-verification-surfacing-spec.md` already
covers and can follow.**

**Conflicts with my spec: no contradiction. It builds on the same seam and stops short.**

## Inspection boundary

Read only. Working tree confirmed pristine before and after: `git status --porcelain` empty,
branch `fix/capture-economics`, HEAD `6557f28d25f28ffe711ad1af76ed80471d68ee04`. Nothing was
written, checked out, or stashed. No test suite was run, so gate status is unverified by me.
Two live verifications executed read-only through the repo interpreter (`api/.venv`, Python
3.14.5) against the embedded catalog and the operator's preview store.

## What the branch gets right

Recorded first, because several of these were the hard parts.

**The v8 persistence question is genuinely answered.**
`test_baseline_attempts.test_version_8_attempt_survives_retry_removal` writes a complete
version 8 record on disk **including `retry_after`** and reads it back under version 9,
asserting status, count, and both timestamps survive. That is a real old-shape round trip, not
a fresh one. `baseline_attempts._parse_baseline_attempt` handles it by popping one dropped key,
which is field tolerance rather than a parallel reader, so the DRY concern in hunt item 4 does
not materialize. The old `_AttemptHeader` is fully removed with no leftovers.

**The live case is proved, and I confirmed it against the operator's actual disk.**
`test_launch_verification.test_version_8_bundle_still_suppresses_provider_work_after_schema_bump`
writes a bundle, rewrites its stored version to 8, and asserts zero harvest calls. All three of
the operator's live bundles are version 8 on disk (`claude/opus` 2.1.241, `codex/gpt-5.6-sol`
0.149.0, `grok/grok-4.6` 1.0.5), and `baseline_store.has_baseline_bundle_for_version` now
accepts both versions, so **the three do not re-capture**. The nine turns of harm do not occur.

Resolving the gate live against the embedded catalog:

| channel | claude 2.1.241 | codex 0.149.0 | grok 1.0.5 | claude 2.1.211 | claude 2.1.100 |
| --- | --- | --- | --- | --- | --- |
| preview | above_ceiling | above_ceiling | above_ceiling | at_ceiling | below_minimum |
| stable | above_ceiling | above_ceiling | above_ceiling | at_ceiling | below_minimum |

All three installed versions are above their ceiling, so **a fourth unblessed cell still
captures**. The gate is a no-op against today's catalog, exactly as required.

**`below_minimum` spends nothing, and it is proved before the money.**
`LaunchVerificationCoordinator.submit` runs the range check **before** `quota_decision` and
before the executor hop, and
`test_launch_verification.test_blessed_and_below_floor_ranges_skip_before_provider_work`
asserts `quota_calls == []` and `harvest_calls == []` across `below_minimum`, `below_ceiling`,
and `at_ceiling`. Hunt item 6 is satisfied: no provider work is scheduled, not merely skipped
later.

**No third verdict is introduced.** `inventory.HarnessBaselineInfo` is a discriminated
projection of `BaselineAttemptStatus`, which already existed. It is a record view, not a
judgment. Hunt item 1's sub-question answers cleanly.

**The shared contract is additive and gated on both planes.** The new
`baseline_attempt_status` key is added to `shared/harness_inventory_vocabulary_v1.json` with no
existing key touched, and `harnesses.test_inventory_vocabulary` extends `_VOCABULARIES` and
`_literal_members` to pin the new `StrEnum` on the Python side while the TS mirror test pins
the same file. An old frontend against a new backend ignores an unknown property. The `v1`
filename is correct for a purely additive change.

**Two things I suspected and disproved rather than reported.**
`baseline_attempts._parse_baseline_attempt` and `baseline_store.has_baseline_bundle_for_version`
both use `except A, B:` without parentheses. That is PEP 758, valid on this repo's
`requires-python = ">=3.14"`, confirmed by parsing the file with `api/.venv/bin/python` 3.14.5.
And `api.v1.harnesses.baseline_output`'s fallback (`settings.storage_dir / "baselines"`) is
byte-identical to what `create_launch_verification_coordinator` builds, since `main` passes
`storage_root=settings.storage_dir`. Neither is a finding.

## Major findings

### M1. A crash leaves `in_progress` sticky forever, and the surface offers no way out

`LaunchVerificationCoordinator._capture_is_due` now reads:

```text
if attempt is None or attempt.status is SUCCEEDED:  return True
log("manual retry required"); return False
```

`IN_PROGRESS` therefore blocks automatic capture permanently. With the 24 hour cooldown
deleted, nothing ever clears it. A `SIGKILL`, a backend restart, or a laptop sleep during the
600 second A/B/A window leaves a record that says a capture is running when none is.

The surface makes it worse rather than better.
`inventory.HarnessBaselineInProgressInfo` pins `retry_command: None`, so the API renders an
orphaned attempt as indistinguishable from a capture running right now, with no completion
time, no reason, and no offered remedy. It will read "in progress" for the life of the machine.

The asymmetry is visible in the same file: `lock.WorkspaceLock` documents that it
"auto-releases when the owning process dies". The lock recovers from a crash. The attempt
record does not.

`baseline_harvest` does clear it, because `BaselineAttemptRecorder.start` calls
`start_baseline_attempt`, which overwrites regardless of prior status. So the recovery exists
and is simply never surfaced.

**Fix:** either treat `IN_PROGRESS` older than the hard deadline as recoverable in
`_capture_is_due`, or offer `retry_command` on `HarnessBaselineInProgressInfo` once the attempt
is older than `_ABA_TIMEOUT_S`. The first is better: it restores the one recovery the cooldown
used to provide, without reintroducing a retry policy.

### M2. Manual harvest now writes attempt state but still takes no lock, and the API hands the operator the command that races it

`baseline_harvest.main` gained a `BaselineAttemptRecorder` and an `on_client_spawn` hook. It
still imports no `lock.WorkspaceLock` and takes none.
`LaunchVerificationCoordinator._verify_under_lock` holds `WorkspaceLock(launch_verification_lock_root(...))`
for exactly this cell.

Before this branch the collision was tolerable: harvest wrote bundles and pointers, and the
attempt file had no second writer. Now both paths write
`attempts/<harness>/<provider>/<model>/<version>.json`, and `start_baseline_attempt` is a
read-then-write over `attempt_count`. Two concurrent captures of one cell means six provider
turns and a corrupted count.

This is not hypothetical. `inventory._baseline_info` puts
`["transport-matters", "baseline", "harvest", "--harness", ..., "--model", ...]` into the API
response, and the operator launching from the canvas is what triggers the automatic path. The
product is telling him to run the racing command.

**Fix:** take the same `WorkspaceLock` in `baseline_harvest.main`, or move the lock inside
`BaselineAttemptRecorder` so every writer of attempt state acquires it. The recorder already
exists as the shared seam; it is the natural home.

### M3. The surface reads attempts only, so it cannot answer three of the five facts, and both inert verdicts stay inert

`inventory._harness_item` populates `baselines` purely from
`baseline_attempts.read_baseline_attempts`. It never reads a `current` pointer, never calls
`baseline_staleness.assess_baseline_staleness`, and never carries `support_state.SupportState`.

Consequences, in order of operator impact:

- **A cell with a baseline and no attempt record shows nothing.** Every bundle captured before
  this branch through `baseline_harvest` has no attempt file. The operator has evidence on disk
  and the API reports an empty list.
- **Staleness is unanswerable.** `harness_version` on the info is the *attempt's* version.
  Nothing says whether the stored baseline still describes the installed harness, which is the
  question `assess_baseline_staleness` exists to answer and the one that decides whether the
  evidence is worth anything.
- **A cell skipped by the new gate produces no field and no reason.** `docs/HARNESS-COMPATIBILITY.md`
  correctly says a `below_minimum` version "records the compatibility verdict and upgrade
  recommendation without capture", and `HarnessCompatibilityInfo.range_position` does carry it.
  But nothing connects that to `baselines`, so an operator reading the new field sees an empty
  array whether the cell was skipped as blessed, skipped as below floor, or never launched at
  all. "Why nothing captured" remains unanswered.
- **`assess_baseline_staleness` and `SupportState` still have zero production callers** after
  this branch. Three inert verdicts were two before it.

This is a scope gap rather than a defect, and it is exactly the ground
`~/.mdx/projects/tm-verification-surfacing-spec.md` covers. The shapes are compatible: that
spec's `BaselineCellInfo` is keyed per cell and would carry this branch's attempt projection as
its `attempt` member. Nothing here has to be undone.

**On which of the two is right:** the branch is right about the home
(`HarnessInventoryItem.baselines`, built in `harnesses.inventory._harness_item`, served by
`api.v1.harnesses.get_harnesses`) and right about failure reason and remediation, which my spec
did not specify in that detail. My spec is right that the field must be keyed per cell rather
than per attempt, and that staleness is the verdict that makes it useful today. Merge the
branch's shape into that key.

## Minor findings

### m1. Attempt history is unbounded and nothing prunes it

`read_baseline_attempts` globs `attempts/<harness>/**/*.json` and returns every record for
every version ever attempted. No code in `baseline_attempts` or `baseline_store` deletes an
attempt file.

With auto-retry gone, failures accumulate permanently. A failure at a version the operator no
longer runs renders with `retry_command: null` (see m2) and can never be cleared by any
affordance in the product. Ten claude aliases against a harness that ships weekly is a few
hundred files read synchronously on every `/v1/harnesses` request, and `/v1/harnesses` is what
the first-run screen and the MCP inventory adapter both call.

For scale: the design in my spec reads one current pointer and one attempt per cell, measured
at 1,755 bytes for all three harnesses. This one reads all history.

**Fix:** bound the read to the installed version plus the latest attempt per cell, or prune on
successful capture.

### m2. `retry_command` is gated on the stored version, not a fresh probe

`_baseline_info` offers the command only when `installed_version == attempt.harness_version`,
and `installed_version` comes from `installation.normalized_version`, which is the stored
observation row.

`baseline_staleness.assess_baseline_staleness` documents this exact defect class by name: four
codex cells read `current` against a stored row that had drifted, and TLDR records that harness
state refreshes only at backend startup. A stored row that lags a mid-session harness upgrade
withholds the retry command precisely when the operator needs it, with no explanation for its
absence.

### m3. `"transport-matters"` is hardcoded where `CLI_COMMAND` exists

`_baseline_info` builds the retry argv from a string literal.
`product_identity.CLI_COMMAND` is that literal, and `infrastructure_guidance` already
demonstrates the convention of interpolating it.

The argv-over-API pattern itself is fine and precedented: `HarnessInventoryItem.authentication_command`
already ships a command string for the same reason.

### m4. `baseline_capture_range_position` defaults to the stable channel

The resolver signature is `(harness, version, now, *, channel: str = "stable")`, and the
`LaunchVerificationCoordinator.range_position` field defaults to the bare function. Production
is correct: `create_launch_verification_coordinator` binds
`partial(baseline_capture_range_position, channel=resolve_channel_spec(env=...).id)`.

But `launch_verification`'s own module docstring opens with "Verification is scoped to one
channel home", and TLDR's first rule is that channels do not share rows. A channel-scoped
component whose channel silently defaults to stable is a trap for the next constructor. Make
the parameter required, or derive it rather than defaulting it.

### m5. The dev channel is exempt from the gate entirely

`compatibility_releases_v1.json` declares channel states for `stable` and `preview` only. On
`dev`, `embedded_channel_state` returns `None`, `match_release` returns its early
`compatibility_release_unavailable` with `range_position` defaulting to `unknown`, and
`unknown` is capture eligible. Verified live: every version of every harness resolves to
`unknown` on dev, `below_minimum` included.

Consistent with the stated rule, and dev is a development channel. Worth stating out loud in
the docs paragraph, because one of three channels having no spend control at all is not
obvious from "unknown remains capture eligible".

### m6. `cli/baseline_cmd` re-marshals typed options into argv strings

`harvest` and `compare` accept typed typer options, stringify each into a `list[str]`, and hand
it to `baseline_harvest.main` / `baseline_compare.main` for argparse to re-parse. Type
information is destroyed and rebuilt, and a flag-name divergence between the two parsers fails
at runtime rather than at type-check time.

It also wraps two of the three baseline scripts. `baseline_publish.main` is left off the CLI
with no stated reason, so the operator surface is arbitrarily partial.

The pre-existing duplication note stands: `baseline_compare.main` and `baseline_publish.main`
were already flagged as a 0.945 similarity argparse pair. This adds a fourth surface over the
same three entry points rather than collapsing them.

### m7. `baselines` is required in TypeScript and defaulted in Python

`HarnessInventoryItem.baselines: tuple[HarnessBaselineInfo, ...] = ()` in Python against
`baselines: HarnessBaselineInfo[]` in `www/packages/core/src/types/harnessInventory.ts`.

A new backend always serializes the default, so new frontend against new backend is fine, and
old frontend against new backend ignores the extra property. New frontend against an **old**
backend gets `undefined` where the type promises an array. Given that `client_version.py`
exists to reason about skew, mark it optional or drop the Python default so the two planes
agree on whether it can be absent.

## Test coverage gaps

Not findings on their own; each is one assertion away.

- No test covers a version 8 record whose status is **failed**. That is the one that exercises
  `_baseline_info`'s `failure_reason or "failure reason unavailable for legacy attempt"`
  fallback, since version 8 had no such field. The surviving-record test uses `succeeded`.
- No test covers `retry_command: null`, so the stale-stored-version path in m2 is unasserted.
- `test_corrupt_current_attempt_is_absent_and_restartable` dropped the assertion that the newly
  started record round trips through `read_baseline_attempt`. The rename is right; the removed
  assertion was doing work.
- Nothing asserts an orphaned `in_progress` record's behaviour, which is M1.

## Answers to the six hunts

1. **Conflict with my spec:** none. Same home, same field name, compatible shape, and no third
   verdict. It stops at attempts and leaves staleness, support state, and the skip reason
   unsurfaced (M3). Where they differ, the branch is right about the home and the remediation
   detail; my spec is right about the per-cell key and about making `assess_baseline_staleness`
   live.
2. **The live case still captures:** verified live. All three installed versions resolve
   `above_ceiling` on preview and stable, and all three live bundles are version 8, which
   `has_baseline_bundle_for_version` now accepts, so they do not re-capture.
3. **Persistence:** correct, with a genuine old-shape record including `retry_after`. One gap:
   the failed variant is untested.
4. **DRY on the legacy reader:** clean. One dropped key popped in one parse helper, no parallel
   implementation. The DRY problem is elsewhere, in `cli/baseline_cmd` (m6).
5. **Shared contract:** additive, correctly pinned on both planes, `v1` filename appropriate.
   One asymmetry in optionality (m7).
6. **`below_minimum` spends nothing:** confirmed, gated before quota and before the executor
   hop, and asserted as such.

## Recommendation

Fix **M1** and **M2** before merge. Both are small and both concern the same file pair, and
both defeat the slice's own goal: M1 makes a crash permanently disable a cell, M2 makes the
product recommend a command that can double the spend the slice exists to prevent.

**M3** is a follow-up, not a blocker. The shape it needs is additive to what this branch ships.

The minors are worth taking in the same pass; m1 and m2 both make the new surface degrade over
time rather than at once, which is the kind of defect that is never worth revisiting later.

---

# Delta re-review: `6557f28d..aa74cd5f`

**Verdict: merge. Zero major, two minor, neither blocking.**

M1 and M2 are genuinely fixed, not papered over, and all seven minors are addressed. M3 stays
deferred by the orchestrator's decision and is not built here. Prior confirmations are not
reopened.

Tree pristine before and after: `git status --porcelain` empty, branch `fix/capture-economics`,
HEAD `aa74cd5f90463f261e9de14a9e75520cfec68990`. One commit, `fix(baseline): recover and
serialize capture attempts`. No gates run by me. Two live verifications executed read-only.

## M1: the lock-as-liveness design holds up

The orchestrator's instinct is right, and the reason is stronger than "the lock is a better
heuristic". The lock is not evidence about liveness here. It is the same mutual exclusion that
every writer of an `in_progress` record must already hold, which makes the invariant exact
rather than probabilistic.

**Q1. Can a live capture ever not hold the lock while still running?** No, and the invariant is
closed because there are exactly two writers.

`LaunchVerificationCoordinator._verify_under_lock` creates the record through
`BaselineAttemptRecorder.start`, called from `record_provider_start`, which is the
`on_client_spawn` callback of `self.harvest(...)` and therefore runs after
`WorkspaceLock(lock_root).__enter__()` and before the `finally` that releases it.
`baseline_harvest._capture_selected_baseline` does the same inside
`with exclusive_file_lock(...)`. `BaselineAttemptRecorder.start` is the only caller of
`start_baseline_attempt` outside tests. So an `in_progress` record with the lock free means the
writer is dead, with no third case.

The three windows named in the brief all close:

- *Between attempt start and lock acquisition*: cannot exist. The record is written strictly
  inside the lock, never before it.
- *After a lock timeout*: `fcntl.flock` has no timeout. `WorkspaceLock.__enter__` uses
  `LOCK_EX | LOCK_NB` and fails fast; `lock.exclusive_file_lock` uses bare `LOCK_EX` and blocks.
  Neither can abandon a held lock while its process lives.
- *Across a process boundary*: the reaping process must itself hold the lock before
  `_capture_is_due(..., reconcile_stale=True)` runs, so it cannot be reaping a peer that holds
  it.

Two further properties I checked rather than assumed:

`launch_verification_lock_root` **excludes effort**, and says why: effort controls the capture
but does not name a separate current pointer, so it must not create a second lock for one write
target. `baseline_harvest.harvest_baseline` builds a `VerificationCell` with
`effort=selected.default_effort` while the coordinator's cell carries whatever
`effort_policy.resolve_launch_effort` chose. Because effort is excluded, those still address one
lock. Had effort been in the path, M2 would have been fixed in appearance only.

The executor id agrees too. `LaunchVerificationCoordinator.submit` returns early when
`executor_id is None`, and the concrete value comes from `ProviderAccessReceipt.executor_id`,
built in `harnesses.access_policy` from `snapshots.executor_id`, which is `local_executor_id()`.
`harvest_baseline` passes `inventory.executor_id`, the same source. Verified live: the preview
home's `executor-id` is `ef9cd166-7f7b-4ee0-9054-4d365393d509` and the existing lock directory
under `~/.transport-matters-preview/baselines/.launch-verification-locks/` is that exact id.

**Q2. Can a stale lock be unreleasable?** No. `lock.py` holds `fcntl.flock` on an open
descriptor. The lock is kernel held and released when the file descriptor closes, process death
by `SIGKILL` included. Both helpers document that property and neither adds PID files or
timestamps that could outlive the holder. M1's stickiness cannot relocate into the lock.

**Q3. Does the deadline have one owner?** Yes.
`LaunchVerificationCoordinator.aba_timeout` defaults to `_ABA_TIMEOUT_S` and is read in three
places: `asyncio.timeout(self.aba_timeout)` and `deadline = time.monotonic() + self.aba_timeout`
in `_run_candidate`, and `recovery_at = attempt.started_at + timedelta(seconds=self.aba_timeout)`
in `_capture_is_due`. No literal is repeated at the reaper, and the failure reason interpolates
`self.aba_timeout` rather than restating 600.

The two clocks differ in kind, and in the safe direction. The capture deadline is monotonic and
starts at submit; the recovery window is wall clock and starts at `started_at`, which is written
later, after the lock and workspace setup. So `recovery_at` is always at or after the capture's
own hard deadline, and the reaper can never fire early even ignoring the lock.

That also disposes of the manual path's unbounded runtime.
`baseline_harvest` has no A/B/A deadline and its `--timeout` is per turn and operator settable,
so a manual capture can legitimately exceed 600 seconds. It is safe anyway, because it holds the
lock for its whole duration and the reaper only runs under that lock. The lock is what makes the
timestamp sound, which is precisely the argument for this shape over a heuristic.

## Q4: serialization queues rather than skips, as the standing rule requires

Both paths take `fcntl.flock` on the same file. `launch_verification_lock_root(...)` yields the
directory; the coordinator locks it through `WorkspaceLock.__enter__` and harvest through
`exclusive_file_lock(WorkspaceLock(lock_root).lock_path)`, which is the same `lock_root/"lock"`.

The asymmetry is the correct one and matches the owner's rule exactly:

- automatic capture uses `LOCK_EX | LOCK_NB` and **skips** on contention. Skipping is the
  explicit opt-in, and it is the path that must never delay a launch.
- manual harvest uses blocking `LOCK_EX` and **queues**. `lock.exclusive_file_lock`'s own
  docstring states the intent: concurrent holders serialize rather than error.

And harvest re-checks after acquiring, rather than assuming its pre-lock view still holds.
`harvest_baseline` runs its fresh version probe and `has_baseline_bundle_for_version` **inside**
the lock, returning `current: ...` with exit 0 and zero provider turns when the automatic path
produced the evidence while it waited. That is the loser-rechecks half of a single-flight gate,
which is what makes queueing correct rather than merely polite.

## Q5: `baseline_compare.py`, `baseline_publish.py` and `inventory.py` are the minors, not new scope

All three edits map to minors I raised, with nothing else riding along.

- `baseline_compare.compare_current_baselines` and `baseline_publish.publish_current_baselines`
  are new typed entries that the argparse `main`s now delegate to, and
  `cli.baseline_cmd` calls them directly. That is **m6**: the argv round trip is gone, `Path`
  survives as `Path`, and `publish` is no longer arbitrarily missing from the CLI. Confirmed by
  `cli.test_baseline_cmd`, which now asserts a typed kwargs dict rather than a list of strings.
- `inventory._baseline_info` drops its `installed_version` parameter (**m2**) and builds the
  command from `product_identity.CLI_COMMAND` (**m3**).

The m2 fix is better than what I proposed. Rather than passing a fresh probe into the gating
comparison, it removes the comparison: `retry_command` is now unconditional on
`HarnessBaselineFailedInfo` and `HarnessBaselineInProgressInfo`, and the freshness question moves
to where it is actually answerable, inside `harvest_baseline`, which probes the binary itself and
files the attempt under the version it observed. The stale stored row can no longer withhold the
affordance because the affordance no longer consults it.

The remaining minors are also closed: `baseline_capture_range_position`'s `channel` is now
required with no default (**m4**), the dev channel exemption is documented in
`docs/HARNESS-COMPATIBILITY.md` (**m5**), and `read_baseline_attempts` keeps the latest record per
cell while `_prune_superseded_attempt_versions` deletes superseded version files on each start
(**m1**).

One property makes that prune safe and is worth recording: the cell lock excludes on
`(executor, harness, provider, model)` without version, so two captures of one cell at different
versions cannot run concurrently, and the prune can never delete a record another live writer
owns. Its failure mode is a `logger.warning` and continue, so a read-only directory degrades the
history rather than the capture.

## Q6: the frontend contract is now correctly additive

`www/packages/core/src/types/harnessInventory.ts` makes `baselines?: HarnessBaselineInfo[]`
optional, matching `HarnessInventoryItem.baselines`'s Python default. That closes **m7**: a new
frontend against an old backend now types the absent property instead of promising an array that
is not there. An old frontend against a new backend was already safe and stays safe, since it
ignores an unknown property.

`retry_command` narrows from `string[] | null` to `string[]` on both variants that carry it,
mirroring the Python change exactly. Narrowing a union is safe for a consumer that already
handled the wider type. `shared/harness_inventory_vocabulary_v1.json` is untouched in this delta,
so the both-sides vocabulary pin is undisturbed.

## Q7: regression guard, re-verified live at `aa74cd5f`

Resolved through `api/.venv/bin/python` against the operator's preview store:

| cell | version | range | evidence | re-captures |
| --- | --- | --- | --- | --- |
| `claude/anthropic/opus` | 2.1.241 | above_ceiling | present | **no** |
| `codex/codex/gpt-5.6-sol` | 0.149.0 | above_ceiling | present | **no** |
| `grok/grok/grok-4.6` | 1.0.5 | above_ceiling | present | **no** |
| `claude/anthropic/sonnet` (fourth cell) | 2.1.241 | above_ceiling | absent | **yes** |

The property holds. `_capture_is_due` still tests `has_baseline_bundle_for_version` first and
returns before reaching the new `in_progress` branch, so the recovery path cannot reach a cell
that already has evidence.

## Q8: the new tests are honest

Three of them, each asserting observable end state and each failing before its fix.

`test_launch_verification.test_orphaned_attempt_recovers_only_after_the_live_writer_releases`
seeds a stale `in_progress`, holds the production lock from the test, and asserts the coordinator
performs **zero** harvest calls and leaves the record `IN_PROGRESS` while it is held. It then
releases and asserts one harvest call and a persisted `(SUCCEEDED, attempt_count=2)`. Before this
delta the final assertion fails, because `IN_PROGRESS` blocked forever. It asserts provider call
count and persisted state, never an intermediate branch.

`test_baseline_harvest.test_manual_harvest_queues_on_the_automatic_lock_and_rechecks_evidence` is
the strongest of the three. It holds the lock, starts harvest on a worker thread, asserts the
worker is **still alive** (queued, not skipped), writes a bundle while still holding the lock,
then releases and asserts the worker exits 0 with an empty provider call list. That is
serialization, the post-lock re-check, and zero double spend in one assertion set. Before this
delta harvest took no lock, so it would neither block nor re-check. It builds its lock address
from the production `launch_verification_lock_root` symbol, so the two paths agree by
construction rather than by a copied literal.

`test_baseline_harvest.test_manual_harvest_keys_the_attempt_from_a_fresh_version_probe` has the
stored inventory say 2.1.240 and the probe say 2.1.241, and asserts the attempt file exists under
2.1.241. Observable end state, and it fails before the probe was introduced.

Both coverage gaps I flagged are also closed.
`api.v1.test_harnesses.test_inventory_surfaces_a_legacy_failure_when_the_stored_version_lags`
writes a genuine version 8 **failed** record including `retry_after` and asserts the legacy
fallback reason through the HTTP response, and
`test_inventory_offers_recovery_for_an_in_progress_attempt` asserts the recovery command on the
in-progress variant. The round-trip assertion I noted as wrongly dropped from
`test_corrupt_current_attempt_is_absent_and_restartable` has been restored.

## Minor findings

### d1. Manual harvest has no way to re-capture existing evidence

`harvest_baseline` returns `current: ...` with exit 0 whenever
`has_baseline_bundle_for_version` finds a bundle for the freshly probed version. That guard is
right for the concurrency case and is what makes queueing free.

But it applies unconditionally, so a lone operator who suspects the stored evidence is wrong has
no path to refresh it short of deleting the bundle by hand. `docs/HARNESS-COMPATIBILITY.md`
describes the guard only in its concurrency framing ("If concurrent automatic work produced the
bundle, the manual command returns without spending provider turns"), which understates when it
fires.

Either add an explicit `--force` that skips the evidence check while still taking the lock, or
widen the doc sentence to say the manual command never re-captures a version that already has
evidence. The second is cheaper and may be the intended product answer.

### d2. The manual lock address is named through a `WorkspaceLock` that is never used as one

`baseline_harvest.harvest_baseline` writes
`exclusive_file_lock(WorkspaceLock(lock_root).lock_path)`, constructing a `WorkspaceLock` purely
to read `.lock_path` off it and then discarding it. It works and it is correct, but the one
sentence that matters, that these two paths lock the same file, is expressed by an object built
and thrown away rather than by a shared name.

A `launch_verification_lock_path(...)` helper beside `launch_verification_lock_root` in
`launch_verification`, returned by both call sites, would make the shared address explicit and
remove the temptation for a future edit to open `lock_root / "lock"` by hand.

## Outside the delta

Nothing severe. The one thing I would still want, `M3`, is the orchestrator's deferred
follow-up and remains additive to what this branch ships.
