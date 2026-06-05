# PR #312 review — provider-rejection verdict surface (Grok)

Date: 2026-07-19  
Branch: `feat/launch-verdict-surface`  
HEAD: `a18e2cb7` (3 commits: `f0bfb7e0`, `a333aa11`, `a18e2cb7`)  
Diff: `git diff main..HEAD` — 59 files, +1065 / −121  
Worktree after review: clean (no source edits by this reviewer)  
Gate: **PASS**

## Summary

Clean. The change implements the scouted surface-don't-gatekeep path: pure native classifiers, one sticky `model_rejected` live kind, rejection-first delivery proof, and Activity/roster/Watch projection. Closed vocabulary is complete across every required mirror. Both premature-`submitted` event orders are covered and rejection wins. No over-engineering: existing proof, live-status, roster, and drift seams are extended rather than replaced.

## Gate (authoritative full)

Judged by output content, not only process exit codes.

### `just check` — PASS (exit 0)

| Surface | Result |
| --- | --- |
| desktop typecheck + vitest | 18 files, **102** tests passed |
| shell biome format/lint | no fixes applied (schema info only) |
| package typechecks (`@tm/common`…`@tm/canvas`, shell) | all succeeded |
| api ruff format | 656 files unchanged |
| api ruff check | **All checks passed!** |
| api mypy | **Success: no issues found in 656 source files** |

### `just test` — PASS (exit 0)

| Suite | Passed | Skipped |
| --- | ---: | ---: |
| desktop | 102 | 0 |
| shell workspace (canvas/inspector/host/…) | 1247 | 0 |
| `@tm/common` | 24 | 0 |
| `@tm/contract` | 8 | 0 |
| `@tm/activity` | 288 | 33 |
| `@tm/runtime` | 186 | 2 |
| `@tm/gateway` | 21 | 0 |
| **TS total** | **1876** | **35** |
| **api/pytest** | **3291** | **2** |

Post-gate: `git status` clean; `git rev-parse --short HEAD` still `a18e2cb7`; `git diff --stat main..HEAD` unchanged at 59 files / +1065 −121.

## Focus 1 — closed-vocabulary completeness

Member under review: live kind `model_rejected` → Activity status `needs-you-model-rejected` / needs_you `{kind: "model_rejected"}`.

| Mirror | Location | Status |
| --- | --- | --- |
| DB check constraint | `api/migrations/versions/0027_model_rejected_kind.py` (`run_live_status_kind_check`) | present |
| Migration head | `session/testing.py` `EXPECTED_MIGRATION_HEAD_REVISION = "0027_model_rejected_kind"` | present |
| Python `LIVE_STATUS_KINDS` + Literal | `live_status.py` | present |
| Sticky set | `session/live_status_contracts.py` `RUN_LIVE_STATUS_STICKY_KINDS` | present |
| Python enum | `session/models.py` `RunLiveStatusKind.MODEL_REJECTED` | present |
| Activity status + needs_you Python mirrors | `controlplane/activity.py` | present |
| TS live kinds | `packages/activity/src/ports.ts` `RUN_LIVE_STATUS_KINDS` | present |
| TS pg contracts | `packages/activity/contracts/pg-contracts.json` | present |
| Wire contract statuses + payload | `packages/contract/src/activity/wire.ts` | present |
| Event union | `runActivityEvent.ts` `record.model_rejected` | present |
| Event mapping | `runActivityEvents.ts` case `model_rejected` | present |
| XState machine + transitions | `runActivityMachine.ts`, `runActivityTransitions.ts` | present |
| Machine graph coverage | `runActivityMachineGraph.test.ts` | present |
| Roster | `controlplane/service.py` passes `needs_you`; `observe_models.RosterItem` | present |
| Watch | `test_watch.py` parametrizes `needs-you-model-rejected` | present |
| Canvas label | `RunVitalsStrip.tsx` | present |
| Type-mirror pin | `test_type_mirrors.py` asserts both members | present |

No missing member found. A write of `kind=model_rejected` is admitted by migration 0027 and mirrored through Python, TS, Activity, wire, roster, and Watch.

## Focus 2 — premature `submitted` / rejection precedence

### Proof order (`delivery_proof.py::_query`)

1. Duplicate claims → `unknown` / `duplicate_provider_requests`
2. `model_rejected` → `failed` / `harness_rejected_prompt` (wins even with a claim present)
3. Exactly one claim with `finalized` **and** `response_succeeded` → `submitted`
4. Else pending until deadline → `unknown` / `proof_deadline`

Bare outbound / non-success finalized responses no longer seal `submitted`. Contract text in `LAUNCH-CONTRACT.md` matches this.

### Both event orders tested

| Case | Test | Outcome |
| --- | --- | --- |
| Early request, late rejection | `test_rejection_wins_when_request_arrives_before_late_verdict` | `failed` + exchange id; run-event wakeup |
| Rejection before any claim | `test_rejection_before_submission_resolves_failed_without_exchange` | `failed`, no exchange |
| Finalized error without semantic verdict | `test_failed_response_without_semantic_verdict_never_proves_submission` | `unknown` / deadline (not submitted) |

Codex path also awaits the live rejection write **before** the finalized wire exchange (`wire_store_observer.py::_submit_wire_exchange`; covered by `test_codex_model_rejection_persists_before_finalized_wire_exchange`).

### Surface-don't-gatekeep

`test_provider_rejection_surfaces_after_run_spawn` (claude + codex): `spawn_count == 1`, receipt `failed` / `harness_rejected_prompt`. No target preflight gate in the launch path.

## Other load-bearing spots (brief checklist)

| Concern | Verdict |
| --- | --- |
| Codex from **wire** `transport.json`, not rollout | Classifier runs on `artifacts.transport.messages` in `WireStoreObserver`; rollout not consulted |
| Classifiers are exact structured matches | Claude: `error` + `isApiErrorMessage is True` + `apiErrorStatus == 404`. Codex: server `type=error`, `status==400`, nested `error.type==invalid_request_error`. No human message parsing |
| Sticky until later success | `observe_model_rejection` → `_offer_sticky`; stop rows suppressed while sticky; later genuine terminal with different generation clears (`test_model_rejection_is_sticky_until_a_later_success`) |
| Tailer order | `LiveStatusObserver` constructed before `TranscriptTailer`; `on_record_observed=live_status.observe_transcript_record` |
| Known Codex `error` vocabulary | `CODEX_ERROR_EVENT_TYPE` admitted in `CODEX_KNOWN_SERVER_EVENT_TYPES` so semantic verdict and unknown-event drift do not double-report |
| CLEAN AND SIMPLE | Reuses delivery proof, live status, roster/Watch, and drift. No second proof service or parallel run-verdict API. Small `async_wait.wait_for_first` helper is justified |

## Issues

None.

## Verdict

**review: clean** — vocabulary complete, rejection-before-submitted races covered, full gate green, tree pristine.
