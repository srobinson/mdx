---
title: TM wire feature current state
type: projects
tags: [transport-matters, github, roadmap, wire-schema]
summary: Facts-only inventory of #381 and related issues, existing planning docs, and main callers for verify_provider_access and compare_request_schema
status: active
created: 2026-08-19
updated: 2026-08-19
project: transport-matters
---

# TM wire feature current state

Source of truth: GitHub `littleorgans/transport-matters` and `main` at `6f0b4a56`.
Where a document disagrees with GitHub or `main`, GitHub/`main` wins.

## 1. Issues

Parent #381 is OPEN. GitHub sub-issues of #381: #370, #382, #383, #384, #392 (2 closed, 3 open).

#381 body implementation order also names #385 then #386. Those two are CLOSED and are not GitHub sub-issues of #381.

| Number | Title | State | One line | Closed by |
| --- | --- | --- | --- | --- |
| #381 | TM Autopilot: first-turn education, controlled harness baselines, and owned overlays | OPEN | Parent for first-turn education, controlled baselines, and owned overlays | |
| #370 | Request inventory: exact JSON leaves, digests, and semantic labels | CLOSED | Reusable read-only inventory of every textual JSON leaf in a captured request | [PR 389](https://github.com/littleorgans/transport-matters/pull/389) |
| #382 | Autopilot baselines: controlled captures and observed request schemas | CLOSED | Controlled A/B/A captures and persisted observed request schemas | [PR 390](https://github.com/littleorgans/transport-matters/pull/390), [PR 395](https://github.com/littleorgans/transport-matters/pull/395) |
| #383 | Welcome report: explain the first full provider request in HTML | OPEN | Optional skippable HTML report of the first full provider-bound request | |
| #384 | TM Autopilot: release compatibility lifecycle and owned overlay application | OPEN | Detect harness release, classify drift, apply the matching TM overlay or passthrough | |
| #392 | Harden raw request to IR mapping, per harness schema | OPEN | Map each trusted raw schema onto `ir::InternalRequest` with computed coverage | |
| #393 | Autopilot baselines: request headers, path and query are outside the wire schema | OPEN | Add headers, path, and query to baseline evidence (not a GitHub child of #381) | |
| #394 | Autopilot baselines: controlled probes never provoke a tool call, so the richest schema branches are never observed | OPEN | Add a tool-turn probe so tool-call wire branches are observed (not a GitHub child of #381) | |
| #397 | Provider access verification never runs at app launch, so evidence expires into a dead end | OPEN | Re-verify provider access at launch so stale TTL is not a dead end (not a GitHub child of #381) | |
| #399 | Verify auth and reachability at startup by launching each harness hidden | OPEN | Hidden real-HOME launch per installed harness at startup (not a GitHub child of #381) | |

Referenced by #381 body, not in the GitHub sub-issue list:

| Number | Title | State | One line | Closed by |
| --- | --- | --- | --- | --- |
| #385 | Harness readiness: separate authentication from usable provider access | CLOSED | Separate authentication from usable provider access | [PR 387](https://github.com/littleorgans/transport-matters/pull/387) |
| #386 | Grok: promote to a first class managed harness | CLOSED | Promote Grok to a first-class managed harness | [PR 388](https://github.com/littleorgans/transport-matters/pull/388) |

#382 `closedAt` is `2026-08-19T01:38:57Z`, same second as PR 395 merge.

## 2. Planning documents

No document is titled or scoped as a roadmap for #381 / Autopilot / the wire feature.

What exists on `main`:

| Path | What it is |
| --- | --- |
| `NOW.md` | Current WIP, focus, and parking lot. States overlay is the landing spot, reached through first run. |
| `docs/NORTHSTAR.md` | Product vision and decision lens. Not a delivery sequence. |
| `docs/DESIGN.md` | Canvas visual and interaction principles. Not a feature plan. |
| `docs/plans/RUNTIME-SURFACING-PLAN.md` | Agent catalog, launch, and evaluation design. Points at `NOW.md` for current sequencing. |
| `docs/plans/RUNTIME-SURFACING-S1-PLAN.md` | S1 plan for agent source, lock, revision, and build. |
| `docs/plans/RUNTIME-SURFACING-S2-PLAN.md` | S2 plan for making harness compatibility executable at launch. |
| `docs/plans/.archive/` | Prior versions of the runtime-surfacing plans. |

`NOW.md` copies also exist under `.claude/worktrees/startup-verify/`, `.claude/worktrees/harvest-gates/`, and `.claude/worktrees/process/`. Those are worktree files, not extra `main` documents.

Document vs source: `NOW.md` sequences overlay via first run as the landing spot. #381 body sequences #385, #386, #382, #383, #384. GitHub is the source for issue state and that listed order.

## 3. Code on `main` for the two named symbols

### `harnesses/access_verification:verify_provider_access`

Definition exists on `main`: `harnesses/access_verification:verify_provider_access`.
Landed by [PR 400](https://github.com/littleorgans/transport-matters/pull/400) (`6f0b4a56`). PR 400 does not list a closing issue.

Production callers: no callers.

Test callers:

- `harnesses/test_access_verification:test_every_launch_eligible_harness_is_verified`
- `harnesses/test_access_verification:test_evidence_for_this_version_skips_the_turn`
- `harnesses/test_access_verification:test_lapsed_evidence_for_this_version_still_skips_the_turn`
- `harnesses/test_access_verification:test_a_new_harness_version_launches_against_its_real_home`
- `harnesses/test_access_verification:test_a_refused_provider_reports_its_fresh_reason`
- `harnesses/test_access_verification:test_one_failing_harness_does_not_stop_the_others`

### `request_schema:compare_request_schema`

Definition exists on `main`: `request_schema:compare_request_schema`.
Inside `baseline_capture`: `baseline_capture:harvest_controlled_baseline` calls it.

Callers outside `baseline_capture`:

- `test_request_schema:test_thirteenth_tool_of_a_known_type_is_exact`
- `test_request_schema:test_new_input_variant_is_degraded`
- `test_request_schema:test_function_call_losing_name_is_breaking`
- `test_request_schema:test_mixed_container_kinds_share_one_total_node`
- `test_request_schema:test_more_than_twelve_array_branches_falls_back_to_one_union`
- `test_request_schema:test_opaque_tool_payload_changes_do_not_reach_the_verdict`
- `test_request_schema:test_launch_identity_presence_never_reaches_the_verdict`
- `test_request_schema:test_nested_launch_identity_name_remains_structural`
- `test_request_schema:test_unparseable_candidate_is_breaking_and_profile_mismatch_raises`

`test_baseline_capture` patches `baseline_capture.compare_request_schema`; it does not call `request_schema:compare_request_schema`.

Production callers outside `baseline_capture`: no callers.
