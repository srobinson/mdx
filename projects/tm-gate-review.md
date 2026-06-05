---
title: Adversarial review of the unknown-compatibility verification gate
type: projects
tags: [transport-matters, launch-verification, adversarial-review, issue-381]
summary: Read-only review of fix/verification-unknown-compatibility, including delta re-review of da94d95b / PR 440.
status: active
created: 2026-08-23
updated: 2026-08-23
project: transport-matters
confidence: high
---

# Adversarial review: unknown-compatibility verification gate

Reviewed `fix/verification-unknown-compatibility` `52b2d087` against `main` `6d02aa86`. Six files, 156 insertions. Working tree was pristine at start and at verdict. No checkout, stash, or repo writes.

Authority: `docs/HARNESS-COMPATIBILITY.md` on main (Identity and release, Target authority, Publication lifecycle, Invariants) wins over `docs-blessing-journey:TLDR.md` (Blessing is a range, Support state and its cause are separate keys).

Counts: **0 blockers, 2 majors, 3 minors, 3 notes.**

---

## Hunt answers

### 1. Scope leak

The change does not loosen operator launch. Production `ResolverRequest` in `capture_rpc_routes._resolve_launch_target` still omits `allow_unverified_target` (default false). `resolve_launch_target_views` returns the first `resolve_target` result as the launch view. `launch_target_advisory` reads that view only. Replay lives inside `_launch_verification_cell` on a `model_copy`. Actuation still applies only when the caller named a model or an effort.

Explicit unverified targets already passed through to the harness via `_passes_to_harness` before this change. That is pre-existing launch policy, not a new permission.

### 2. Re-billing

This branch does not reopen the #436 unbounded re-bill. `launch_verification.py` is untouched. `_RETRY_COOLDOWN` remains 24 hours. `start_baseline_attempt` writes `retry_after` at `on_client_spawn`, which `captured_turn.run_captured_turn` fires before `ProcessSupervisor.spawn`. `_capture_is_due` refuses another harvest while `now < attempt.retry_after` for any non-success attempt.

`test_failed_provider_attempt_cools_then_retries` and `test_attempt_is_written_before_the_provider_boundary` still encode that bound. New cells enter that path; they do not delete it. First launch of each newly eligible cell may spend the A/B/A (three turns). A failure after spawn then cools for 24 hours.

Failures before `on_client_spawn` still write no attempt and retry on the next launch. That was already true on main, and those paths are supposed to be free of provider turns.

### 3. Default-model gap

Judgment: **sound refusal to guess among many unverified models at prepare time, and an unfixed half of the live feature.** See M1.

### 4. Cell identity

For an explicit unverified selector, replay uses the same native `ResolvedTarget.model_id` that `launch_target_advisory` already forwards from the rejection details. `test_canonical_unverified_request_passes_native_selector_to_harness` binds both to `NATIVE_SELECTOR`. `VerificationCell.harness` now comes from `resolved.harness_id`; `resolve_target` already refuses a request/snapshot harness mismatch, so this is equivalent to the old caller-supplied id on a successful resolve.

The #434 rule that both views read one `TargetResolution` is gone. Replay must remain a flag-only retry of the same selector or a bundle can be attributed to a tuple the operator did not run. See m1.

### 5. Test honesty

The new tests fail on main: `resolve_launch_target_views` does not exist, and the old `launch_verification_cell` returned `NoVerificationCell(reason="target_unverified_opt_in_required")` for these inputs. They do not prove that a live prepare schedules a harvest, and they do not cover the canvas launch shape that currently produces zero captures. See M2.

---

## Findings

### M1. CMDK launches with an empty tested catalog still name no cell

**Location:** `harnesses/launch_target._launch_verification_cell`, `harnesses/resolver._default_eligible`, `harnesses/resolver._select_edge`

**Observation:** Replay fires only when the strict rejection code is `target_unverified_opt_in_required`. That code is produced by `_validate_explicit_edge` for a named model. An omitted model walks `_default_eligible`, which still requires `support_tier == "tested"`. With a release that ships zero catalog edges, every live target is `observed_unverified`, default selection returns `target_unavailable` / `no_default_target`, and the cell stays `NoVerificationCell`.

`LauncherCommand` spawn carries a harness and no model (`www/packages/canvas/src/launcher/commandTypes.ts`). `test_a_launch_that_names_no_model_still_names_a_cell` documents that palette shape. `test_an_unresolvable_default_yields_no_cell_and_still_launches` documents the no-cell outcome as load-bearing.

**Impact:** Canvas palette launches, the path that #434 called the usual chokepoint, still never schedule `LaunchVerificationCoordinator.submit`. Explicit MCP launches that name a model will. If the operator's zero-capture machine is CMDK, this change leaves that machine at zero captures.

**Basis:** Target authority on main: defaults use tested, active, locally ready targets. Resolver is deliberately untouched, so verification cannot pick an unverified default without guessing which of the observed models the harness will choose.

**Caveat:** At prepare time, guessing one of ten claude models would be data corruption. The builder's refusal to invent a cell from an omitted request is the #434/#427/#429/#431 settlement. The missing half is *after* launch: `request_inventory.RequestCaptureProvenance.model` is a nonempty wire-observed model, filled from the operator run's captured exchange once the first turn correlates. `baseline_capture._run_probe` already reads that provenance for controlled harvests. Scheduling verification from that fact, rather than from the prepare-time resolver, would name the cell the operator actually ran without guessing beforehand. Compatibility facts on the run do not carry model; the wire provenance does.

### M2. New tests assert the resolver mapping, never the live launch that still captures nothing

**Location:** `harnesses/test_launch_target.test_an_unverified_target_is_eligible_for_verification_without_becoming_launchable`, `api/v1/test_capture_rpc_verification_cell.test_an_unverified_observed_model_becomes_a_cell_without_changing_actuation`, `harnesses/test_resolver_model_identity.test_canonical_unverified_request_passes_native_selector_to_harness`

**Observation:** Every new assertion names an explicit `model_id`. None constructs the live CMDK request (`model=None`, empty `make_release_entry(targets=())`, complete unverified observations). None calls `LaunchVerificationCoordinator.submit` or `schedule_prepared_launch_verification`. Coordinator tests still stub `verification_cell` to a fixture `VerificationCell`.

**Impact:** `just test` can pass while palette launches still produce `NoVerificationCell` and the coordinator still logs `no verification cell reason=target_unavailable`. That is the same class of mistake as shipping #436 with tests that asserted unbounded retry: the suite is green, the operator still gets the failure the change claimed to remove.

**Basis:** Diff of the three test files versus `test_an_unresolvable_default_yields_no_cell_and_still_launches`, which uses empty observations rather than the live "observed but unverified" catalog.

**Caveat:** For an *explicit* named model, asserting `domain.verification_cell == VerificationCell(...)` is the right seam, because `launch_verification_routes.schedule_prepared_launch_verification` already submits any `VerificationCell`. The wiring is not the hole. The hole is the untested request shape.

### m1. Replay can fill a default effort the actuation does not send

**Location:** `harnesses/launch_target._launch_verification_cell`, `harnesses/effort_policy.resolve_launch_effort`, `harnesses/launch_target.launch_target_advisory`

**Observation:** On the unverified rejection path, `launch_target_advisory` returns `request.effort` (often `None`). Replay then runs a successful `resolve_target`, and `resolve_launch_effort` returns `default` when `requested is None`. The cell can therefore carry a native default effort while the operator launch still omits effort.

`test_an_unverified_observed_model_becomes_a_cell_without_changing_actuation` uses `make_target_observation` defaults (`native_efforts=()`, `native_default_effort=None`), so the fill cannot appear.

**Impact:** The sidecar harvest in `LaunchVerificationCoordinator._verify_under_lock` builds `EnumeratedModel` from `cell.effort`. A filled default makes the controlled A/B/A send an effort the operator run did not. Store identity (`has_baseline_bundle_for_version`, `start_baseline_attempt`) keys harness/provider/model/version and ignores effort, so the bundle is still filed against that model version.

**Basis:** #434 promised both views read the same resolution so the cell is the tuple the actuation belongs to. This commit replaces that with a second resolve.

**Caveat:** For tested explicit targets, a successful first resolve already fills default effort into actuation via `launch_target_advisory`. The new divergence exists only on the unverified advisory path. Live opus observations may or may not carry a native default; the new tests cannot say.

### m2. Verification replay logs "failed open" while skipping the cell

**Location:** `harnesses/launch_target._launch_verification_cell`

**Observation:** `except Exception` around the second `resolve_target` logs `launch verification target replay failed open` and returns `NoVerificationCell(reason=rejection.code)`. Launch policy is unchanged. Verification is skipped.

**Impact:** A bug in replay (including `resolve_target`'s harness-mismatch `ValueError`) hides the cell forever for that launch, with a log line that names the opposite policy of #430 fail-open. Next launch retries the replay. No provider turn is spent. Diagnosis is inverted.

**Basis:** Same "failed open" phrasing as `LaunchVerificationCoordinator._run_candidate`, where it means "do not fail the operator launch."

**Caveat:** Broad `except Exception` is fail-closed for billing, which is the safer side if replay is wrong.

### m3. The #434 one-resolution invariant is replaced, and the module docs now say so

**Location:** `harnesses/launch_target` module docstring, `verification_cell` module docstring, `capture_rpc_routes._resolve_launch_target`

**Observation:** #434's load-bearing split was one `TargetResolution` read two ways. `resolve_launch_target_views` now calls `resolve_target` twice when the first rejection is unverified opt-in. Comments were updated to call that the one divergence.

**Impact:** Future edits that put more behavior behind `allow_unverified_target` than `_validate_explicit_edge`'s support-tier check will make verification name a different tuple than actuation. Today the flag only skips that one rejection, then the rest of the resolver (effort included) still runs.

**Basis:** `git show ca8f2f8b` (#434): "Because both read the same resolution, the cell is always the tuple the actuation belongs to rather than a second opinion about it."

**Caveat:** Deliberate. The resolver was left untouched, so a second call is the only way to open verification eligibility without changing launch policy.

---

## Contract disagreement (compatibility doc wins)

`docs/HARNESS-COMPATIBILITY.md` (main) splits two axes:

- **Version / range:** the ceiling never refuses; `above_ceiling` is unblessed until a comparison clears it. Only `minimum_version` withholds support.
- **Target authority:** `observed_unverified` needs explicit selection and opt-in. Defaults use tested, active, locally ready targets. Local evidence never mutates the global tested catalog.

`docs-blessing-journey:TLDR.md` speaks of an **unknown installed version** as the reason to compare, and says nothing is ever blocked. It does not name `support_tier`.

This change keys off `target_unverified_opt_in_required` (target axis), because the live catalog ships zero edges and every observed model is `observed_unverified`. That is the actual chokepoint. It is not the version-ceiling story the journey text describes. Compatibility wins: unverified defaults stay off the launch default path, and this commit preserves that.

`support_state` on main still says a release ships the reference schema captured at the top of its blessed range. `docs-blessing-journey` already corrected that to the baseline (`a02cd1ad`). Out of scope for this branch; recorded so the two docs are not treated as already aligned on main.

---

## Hygiene

- `harnesses/launch_target.py` is 150 lines after the change; `_launch_verification_cell` stays under the function budget.
- `api/v1/capture_rpc_routes.py` is 639 lines; this commit only rewrote the docstring and swapped the call. No split required yet.
- `launch_verification_cell` had no in-tree callers besides the capture route and tests. Privatizing it in the same commit is complete.
- Duplicate `resolve_target` is the seam you get when the resolver must stay frozen. Do not "simplify" by setting `allow_unverified_target` on the launch request.

---

## What holds

- Operator launch actuation is unchanged.
- Invalid effort on an unverified target still yields `NoVerificationCell(reason="invalid_effort")` after replay, while the launch still proceeds with the advisory.
- Off-catalog `target_unavailable` / `not_observed` still yields no cell.
- Hard rejections (`harness_not_installed`) still yield no cell and still raise from `launch_target_advisory` when the caller named a model.
- #436 cooldown, attempt-before-boundary, and `has_baseline_bundle_for_version` completion remain the bound for any cell this now schedules.
- `allow_unverified_target=True` is now written by production code for the first time, and only on the verification copy.

---

## Delta re-review

Reviewed `git diff 52b2d087..da94d95b` (`da94d95b` `fix(verification): preserve explicit launch actuation`) plus PR #440. Head matches `gh pr view 440`. Working tree pristine. Hunts 1, 2 and 4 from the first pass are not reopened. Did not re-run `just test`.

Delta counts: **0 blockers, 1 major, 1 minor.** #440 is **safe to merge as scoped.**

### Check 1. m1 effort fill

**Fixed, not narrowed.** `harnesses/launch_target._launch_verification_cell` now sets `VerificationCell.effort` to `request.effort` when `replayed_unverified`, else `resolved.effort`. On the unverified advisory path `launch_target_advisory` already returns `request.effort`, so the cell matches actuation.

`harnesses/test_launch_target.test_unverified_replay_does_not_actuate_a_discovered_default_effort` is the real case: complete observation with `native_default_effort="low"`, omitted request effort. A relaxed `resolve_target` would fill `"low"`; advisory effort stays `None`; the cell stays `None`. Replay can still refuse an invalid named effort (`test_unverified_verification_still_rejects_an_invalid_effort`).

No remaining window at this seam. Harvest `EnumeratedModel.default_effort` follows the cell, so a discovered native default is no longer pinned onto an omitted launch.

### Check 2. Palette test as M1 tripwire

`api/v1/test_capture_rpc_verification_cell.test_palette_unverified_catalog_is_a_known_gap_until_wire_trigger_lands` uses the real `_resolve` seam with omitted model, empty catalog, two complete unverified observations. Actuation stays `(None, None)`. The cell is `NoVerificationCell(reason="target_unavailable")`. That is today's live palette shape, not a stubbed cell.

`LaunchVerificationCoordinator.submit` is the real method. `object.__new__` skips `__init__`; the `NoVerificationCell` gate returns `False` before any instance state is read. That is the real skip, not a mocked return.

**It will not fail when the accepted M1 lands.** M1 is a post-exchange trigger from `RequestCaptureProvenance.model`, which leaves prepare-time `NoVerificationCell` in place. Both assertions stay true. The test is a characterization of the remaining prepare gap, not a tripwire. See D1.

### Check 3. m2 skip versus fail

The log in `_launch_verification_cell` now says `launch verification target replay failed; verification skipped`. `test_replay_failure_log_says_verification_was_skipped` forbids `failed open` on that path. A harvest that actually ran and failed remains the coordinator's attempt record (`BaselineAttemptStatus.FAILED`) plus `launch_verification.LaunchVerificationCoordinator._run_candidate`'s `failed open` line. Those are distinct.

The durable cell does not distinguish a replay crash from a policy decline: both are `NoVerificationCell(reason="target_unverified_opt_in_required")`. `submit` then logs `no verification cell reason=target_unverified_opt_in_required`. See d1.

### Check 4. m3 documentation

Accurate. `harnesses/launch_target` module docstring, `verification_cell` module docstring, `VerificationCell`, `capture_rpc_routes._resolve_launch_target`, and `resolve_launch_target_views` all state that #434's one-resolution invariant is replaced by a second, flag-only eligibility resolve of the same selector; the strict result remains the sole launch authority; replay may name a cell and does not change actuation.

"With only the unverified gate open" means the flag is the one request change. `_launch_verification_cell` still says the retry applies every other resolver gate, including effort validity. That is what the code does. Does not overstate what still holds.

### Check 5. PR #440 Scope and Contract

**Contract is true.** Version/range vs target authority matches `docs/HARNESS-COMPATIBILITY.md` on main. Resolver defaults stay tested. Local evidence still does not mutate the catalog.

**Scope is true except the flip-point sentence.** Production delta does not touch a post-exchange trigger, `launch_verification.py`, or a wire event hub. Tests import `LaunchVerificationCoordinator.submit`; that is not a production change. Explicit named-model cells, preserved omitted effort, skipped-verification log, #434 docs, and the palette characterization test are all in the delta.

The sentence "the later M1 slice has a precise flip point" is false given the accepted M1 design. See D1.

Nothing severe outside the delta.

### D1. Palette test will stay green after the accepted M1 slice

**Location:** `api/v1/test_capture_rpc_verification_cell.test_palette_unverified_catalog_is_a_known_gap_until_wire_trigger_lands`, PR #440 Scope

**Observation:** The test locks prepare-time `NoVerificationCell(reason="target_unavailable")` and `submit` returning `False`. Accepted M1 schedules from the first wire exchange and does not guess a model at prepare.

**Impact:** `just test` stays green while palette captures start firing from a different seam. The suite will not force M1 authors to update this file. PR Scope tells a future engineer the opposite.

**Basis:** Orchestrator disposition for M1; test body; `LaunchVerificationCoordinator.submit` first gate.

**Caveat:** As a characterization of prepare, the test is honest and should remain. Drop or rewrite the "flip point" claim. A real tripwire would assert the absence of a post-exchange schedule, which this PR correctly does not invent.

### d1. Replay crash still carries the policy reason on the cell

**Location:** `harnesses/launch_target._launch_verification_cell`

**Observation:** `except Exception` returns `NoVerificationCell(reason=rejection.code)` with the original `target_unverified_opt_in_required`. The log is now "verification skipped". The cell reason is still the launch-policy rejection.

**Impact:** Anything that reads only `verification_cell.reason` treats a replay exception as "declined because unverified." The stack is in the log. No attempt file is written, so this is not confused with a harvest failure.

**Basis:** Delta log string vs unchanged `NoVerificationCell` return.

**Caveat:** Verification never started, so skip is the right ontology. A distinct reason would only help diagnostics. Not a merge block.
