# S2 fix round 2 gate re-verify (Grok)

Date: 2026-07-23  
Fix SHA: `09dbc291` (`fix(runtime): await unbound create cleanup`)  
Diff: 13 files, +375/−16  
Reviewer: `multi-launch:general:1:2.4` (read-only)

## Full gate

| Gate | Result | Content |
|------|--------|---------|
| `just check` | **PASS** | desktop 102; shell clean; api ruff + mypy 692 |
| `just test` | **PASS** | JS **1929** passed / **36** skipped + API **3464** passed / 0 failed = **5393 passed / 36 skipped** |
| `just migration-smoke` | **PASS** | **9/9**; head **`0031_claim_affinity`** |

## M2 unbound-bind-race + m1 fail-closed (present + green)

| Regression | Result |
|------------|--------|
| M2 managed: `test_unbound_started_cancellation_waits_for_cleanup_confirmation[managed_run]` | **PASSED** |
| M2 plain: `test_unbound_started_cancellation_waits_for_cleanup_confirmation[plain_terminal]` | **PASSED** |
| M2 Node managed: `RunManager.idempotency` "does not settle cancellation before prepared capture cleanup during bind" (file 11 tests green) | **PASSED** |
| M2 Node plain: `PlainTerminalSessions` "does not settle cancellation before spawned shell cleanup during bind" (file 15 tests green) | **PASSED** |
| m1: `test_claim_fails_closed_when_locked_branch_observation_fails` | **PASSED** |
| Related: `test_successful_prepare_marks_the_unbound_claim_started` | **PASSED** |

## LOC ceiling

| File | LOC | Note |
|------|----:|------|
| `space/runtime_claims.py` | **700** | **At hard limit** (was 695; +5 this round). Did not cross above 700. Next touch requires split first. |
| `RunManager.ts` | 666 | under |
| `store.py` | 693 | under |
| No prod file **over** 700 from this commit | — | Pre-existing `addon_runtime.py` / `run_proxy.py` also sit at 700, not grown here |

## Sign-off

Full gate green on `09dbc291`. Migration head stays `0031`. M2 managed+plain unbound cleanup waits and m1 fail-closed are present and green. Flag: `runtime_claims.py` is now **at** the 700 ceiling.
