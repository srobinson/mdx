# Ready-before-first-activity review (claude family) — PR #268 `realtime-ready-before-first-activity`

**Verdict: clean.** No blocking, major, or minor findings. **CI never ran**: every job on the PR head (ad90135) failed in ~2s with zero steps executed — GitHub annotation reads "The job was not started because recent account payments have failed or your spending limit needs to be increased." All gates were therefore run locally in a scratchpad clone at the PR head against the local test Postgres (55432): `@tm/activity` 249/249 (pg integration suites confirmed executing by name), `@tm/activity` typecheck clean, full `@tm/shell` frontend suite 163 files / 1207/1207. Main working tree verified pristine before and after; all experiments in the clone.

## 1. The exact symptom — pristine run projects Ready and holds it

Two independent legs, both mutation-proven:

- **Time leg:** the unconditional `after: stallTimeout` on the `starting` state is removed; only `reasoning`, `generating`, and `running-tools` keep timers. A pristine run can never time out of `starting`.
  - **Mutation A** (re-add the timer to `starting`): 2 tests fail — `keeps a never-activated run starting past the silence timeout`, `keeps a never-activated run starting across later lifecycle reconciliation`. Red tests real.
- **Reconcile leg:** `wireCandidateAdmitted` for `anomaly`/`idle` now requires `recordSessionId === null && evidence.liveStatusObserved`. The extended slice-5 pg test inserts a lifecycle-only run plus a background `rate_limit_error` wire exchange (the exact production artifact), drives an explicit reconcile, waits for `wireRefused` to increment, and asserts the projection stays `starting`.
  - **Mutation B** (revert to `recordSessionId === null` only): 2 tests fail — the §3.2 unit contract test and the end-to-end pg reproduction `surfaces a lifecycle-only run as starting and keeps it owner scoped`. Red tests real, enforced against real Postgres.

Production-path validation of the fix's premise: the live tap installs only for streaming responses (`_should_stream_response` in `addon_handlers.handle_response_headers` gates on event-stream content-type / Codex responses flow). A startup rate-limit finalization is an immediate JSON error, so no tap installs, no `run_live_status` row is written (`_finish_tap`'s flow-abort terminal fires only for installed taps), and `liveStatusObserved` is false. The subagent guard is not what protects this case — the startup probe classifies as **parent** track via `TrackManager._assign_request`'s fallback — the SSE gate is.

## 2. Stall not over-suppressed

`reasoning`/`generating`/`running-tools` keep their timers untouched, and the new `stalls after genuine first-turn live activity while preserving the Ready baseline` test drives the full loop: live wire fact → `reasoning` → silence → `stalled` (`stalledFrom: starting`, the durable baseline) → usage restore → `starting`. A live fact moves the machine out of `starting`, so any genuinely activated run sits in a timered state while active.

- **Mutation C** (remove the `reasoning` timer): **7 tests fail across 5 files** (`stalls 'reasoning' after genuine activity goes silent`, the new first-turn live test, stall-reset, stalledFrom-restore, ingestion clock stall, runActor clock stall, context stalled-since). Post-activity stall behavior is heavily pinned; the fix removed exactly one timer, not the stall mechanism.
- The removed `starting` entry in the `restores the actual stalledFrom status for silence-stalled $name` it.each is correct: `starting` can no longer silence-stall by timer. The `usageRestoresStarting` / `retractionRestoresStarting` branches remain and are still driven (wire-overlay stalls record `stalledFrom: starting`).

## 3. Idle vs Ready

`STATUS_LABELS` in RunVitalsStrip: `starting: "Ready"`, `idle: "Idle"` — distinct, both render. `record.assistant_turn_ended` still targets `idle` from every active state, and T5 (activated end_turn → idle) passes. The wire contract is untouched: the status value stays `"starting"`; only the display label changed, and RunVitalsStrip is the only label map in the repo (grep over `packages` + `www/packages`, non-test).

- **Mutation D** (label back to "Starting"): `renders a never-prompted starting status as Ready` fails. Red test real.

## 4. Anomaly-fix scope — where the line is drawn

The line: finalize `idle`/`anomaly` admit on cold start only when the live plane has ever observed the run (any `run_live_status` row, open or closed — T5/T6 seed `closed: true`, pinning that observation is historical, not current). Soundness:

- **Legitimate cold-start anomalies still admit.** A real first turn streams SSE, so the tap installs and writes live rows before any finalize can commit; a mid-stream `response_error`/refusal then admits as anomaly with the reason (T6, now seeded with a live row, passes). Even an aborted first turn leaves a flow-abort terminal row, preserving admissibility.
- **The evidence is store-derived** (`liveStatus !== null` from `readLiveStatusForRun`), not process-local, so it survives gateway restarts — no post-restart flap window.
- **Residual narrowing, acceptable:** a first prompt rejected *immediately* with a JSON error (no SSE ever) no longer projects a prompt wire anomaly; the transcript journals the user turn, the machine enters `reasoning`, and the ordinary silence timeout reports the stall. Slower than the old wire path in that one race window, but the old path was exactly the false-positive source being removed, and nothing on the wire distinguishes a failed probe from a failed prompt.
- **Spec drift (orchestrator note, not a PR defect):** §5.2 of `tm-realtime-spec.md` still describes `anomaly`/`idle` as "cold-start-gated" on `recordSessionId === null` alone; the implementation now also requires live observation. The spec text should be synced to the new contract.

## 5. Label consistency

Single label surface (point 3). `activityStatusTier` and the `ActivityStatus` enum unchanged; no orphaned status, no second map to drift.

## 6. Scope / DRY / sizing

9 files, all serving the fix (machine timer, admission contract + evidence type, ingestion threading, unit + pg red tests, label + label test). The `WireAdmissionEvidence` object replaces the previous bare `lastLiveAssertId` parameter, keeping one admission signature rather than a second boolean tail-arg — reuses the existing candidate/stall plumbing throughout. Largest touched file 638 lines (`runActivityMachine.ts`); nothing over 700.

## Observation (non-blocking)

"First activity" is defined as "the live plane observed a streamed exchange on the run", which cannot distinguish a background streamed exchange from a user turn — if a startup probe ever *succeeds* over SSE, the run stops being pristine (live flicker plus a later cold-start idle would admit). That boundary is inherited from slice 3's plane design (only the transcript knows about prompts), not introduced here; the observed production failures are non-streamed JSON errors, which this fix handles exactly.
