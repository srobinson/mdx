---
title: Adversarial review PR #268 — pristine Ready until first activity (grok)
type: review
tags: [transport-matters, realtime, activity, ready, stall, review]
summary: CLEAN. Never-prompted lifecycle runs hold starting/Ready; idle/anomaly need live_status evidence; post-activity silence still stalls. Mutations red-pin all three claims.
status: complete
source: grok
confidence: high
created: 2026-07-11
updated: 2026-07-11
pr: 268
sha: ad901354b57b413c045b4f472c257b086e93fe45
branch: realtime-ready-before-first-activity
verdict: CLEAN
---

# PR #268 adversarial review (grok)

Tree pristine at `ad90135`. Read-only review; mutations restored; `git status` clean after.

## Verdict: CLEAN

## Diff shape (9 files, +116/-33)

| Area | Change |
|---|---|
| `runActivityMachine.ts` | Remove `after: stallTimeout` from `starting` only |
| `wireCandidate.ts` | idle/anomaly admit only when `recordSessionId === null && liveStatusObserved` |
| `activityIngestion.ts` | Pass `{ lastLiveAssertId, liveStatusObserved: liveStatus !== null }` |
| `RunVitalsStrip.tsx` | `starting` label `"Starting"` → `"Ready"`; `idle` stays `"Idle"` |
| Tests | Unit + pg pins for hold-Ready, refuse cold idle/anomaly, stall after live, T5/T6 activated |

All touched files under 700 LOC (`runActivityMachine` 638). No unrelated churn. Reuses existing stall timers on reasoning/generating/running-tools and existing admission plumbing.

## Criteria

### 1. Exact symptom: pristine never-prompted holds Ready

**Machine:** `starting` has no silence timer. Never-activated actor past timeout stays `starting` with null stall fields.

**Admission:** Background rate_limit wire finalize (JSON error path, not SSE) has no `run_live_status` row. `liveStatusObserved` is false → idle/anomaly refused → stay `starting`.

**UI:** `STATUS_LABELS.starting = "Ready"`; `idle = "Idle"`.

**Red tests (pass on HEAD):**
- `keeps a never-activated run starting past the silence timeout`
- `keeps a never-activated run starting across later lifecycle reconciliation`
- `refuses finalized idle and anomaly without first-activity evidence`
- pg `surfaces a lifecycle-only run as starting…` seeds rate_limit wire exchange, asserts `starting`, re-reconcile increments `wireRefused`, still `starting`
- canvas `renders a never-prompted starting status as Ready`

**Mutation MUT1** (restore `return context.recordSessionId === null` only):
- unit: `wireCandidateAdmitted(idle, coldStart)` expected false, got true
- pg: status `stalled` instead of `starting` (anomaly from rate_limit)

**Mutation MUT2** (re-add starting `stallTimeout`):
- both never-activated tests: expected `starting`, got `stalled`

### 2. Stall not over-suppressed

Reasoning / generating / running-tools still have native `after: stallTimeout`. Starting is the only state without silence stall.

**Red tests:**
- `stalls $name after genuine activity goes silent` (reasoning, generating; running-tools covered elsewhere)
- `stalls after genuine first-turn live activity while preserving the Ready baseline` (wire reasoning → silence → stalled, stalledFrom=starting)

**Mutation MUT3** (strip reasoning `after: stallTimeout`):
- first-turn live stall test: expected stalled, stayed reasoning
- machine `stalls 'reasoning'…`: same

### 3. Idle vs Ready

- Never-prompted: machine `starting` → strip **"Ready"**
- Completed turn: finalize idle after live evidence → machine `idle` → strip **"Idle"**
- T5 renamed/updated: activated (live row present) + end_turn → idle
- T6: activated anomalies still project stalled with reason

### 4. Anomaly fix scope

Line drawn:

```
idle|anomaly ⇒ recordSessionId === null && liveStatusObserved
liveStatusObserved ≜ readLiveStatusForRun !== null  (row present, incl. closed kind=null)
```

Sound for the claimed bug:
- Live HTTP tap only when response is streamable SSE (`_should_stream_response` + `start_http_flow`). Rate-limit JSON errors finalize the wire without a live row → refused.
- Real mid-turn SSE writes live rows; closed kind-null still counts as observed so end_turn idle / response_error anomaly after a real live generation still admit (T5/T6).
- Warm transcript (`recordSessionId` set) still refuses wire idle/anomaly (E4 unchanged).
- Live facts (reasoning/tool/generating) admission unchanged.

Residual (non-blocking): a first user turn that fails with non-stream JSON error and no live row stays Ready until transcript error, not wire-anomaly Stalled. Intentional under the "first live activity evidence" contract; better than false Stalled on empty panes.

### 5. Label map

`STATUS_LABELS: Record<ActivityStatus, string>` still exhaustive. Only `starting` relabeled. No orphan status string. Idle/Stalled/Needs you/Thinking/Responding/Tools/Exited unchanged.

### 6. Scope / DRY / sizing

Minimal, focused. Evidence bag extends the third arg of `wireCandidateAdmitted` rather than a parallel API. Default `NO_WIRE_ADMISSION_EVIDENCE` keeps unit call sites safe.

## Verification (HEAD, pristine)

| Suite | Result |
|---|---|
| `@tm/activity` full | **249 passed** |
| domain machine + wire unit | 71 passed |
| pgIntegration + pgWireIntegration | 28 passed |
| shell vitest `RunVitalsStrip.test.tsx` | 10 passed |
| Mutations MUT1–MUT3 | restored; tree clean |

## Findings

No blocking issues. No medium defects found under the six judge axes.
