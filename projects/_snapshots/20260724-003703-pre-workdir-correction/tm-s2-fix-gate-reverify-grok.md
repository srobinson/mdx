# S2 fix gate re-verify (Grok)

Date: 2026-07-23  
Fix SHA: `6e644363` (`fix(runtime): harden claim lifecycle ordering`) on `7df0d907`  
Diff: 23 files, +565/−116  
Reviewer: `multi-launch:general:1:2.4` (read-only)

## Full gate

| Gate | Result | Content |
|------|--------|---------|
| `just check` | **PASS** | desktop 102; shell clean; api ruff + mypy 691 |
| `just test` | **PASS** | JS **1925** passed / **36** skipped + API **3460** passed / 0 failed = **5385 passed / 36 skipped** |
| `just migration-smoke` | **PASS** | **9/9**; head **`0031_claim_affinity`** |

## Major-regression tests (present + green in full suite)

| Regression | Result |
|------------|--------|
| `test_cancelled_claim_rejects_late_capture_prepare` | **PASSED** |
| `test_claim_observes_branch_after_the_projection_can_go_stale` | **PASSED** |
| `test_force_resources_requests_cancel_before_termination` | **PASSED** |
| `test_failed_forced_termination_preserves_the_live_claim_guard` (failed + unknown) | **PASSED** |

Also green: Node inventory/cancel regressions in `RunManager.idempotency.test.ts` (unkeyed blocked claim list/cancel) and plain-terminal cancel-during-CWD.

## LOC after M3 inventory change

`packages/runtime/src/service/RunManager.ts` = **666** LOC (was 695 at prior review; net **down**, comfortably under 700).

## Sign-off

Full gate green on `6e644363`. Migration head remains `0031`. RunManager razor risk relieved by this fix round.
