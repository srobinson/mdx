# Latency investigation: audit agent slowdown

Observation window: 2026-09-05 03:25Z to 04:40Z (local UTC+7, 10:25 to 11:40).
Report written 2026-09-05 04:40Z. Read-only diagnosis. No run, process, or code was modified.

## Verdict

The bottleneck is **upstream provider response latency on the Codex / `gpt-5.6-luna`
path**, concentrated in two events: a cluster of WebSocket `1011` upstream failures at
03:41-03:49Z, followed by four reissued turns that each hung for **37.5 to 39.6 minutes**
and released in near-FIFO order at 04:29-04:33Z.

Local infrastructure is healthy. Gateway, proxy, tool dispatch, transcript persistence and
the Activity/roster projection all measured clean. The `stalled` roster label is derived
from `last_turn_at` age and is a symptom of the provider wait, not a cause.

## Measured timeline

All rows from `wire_exchange` in `transport_matters_preview`. `resp_s` is
`created_at - ts`, request issue to response persistence.

### Phase 1: normal, degrading with context (03:28 to 03:40Z)

`audit-reconciliation-check` (0c40ac42) gives the cleanest uninterrupted trace:

| context (input tokens) | per-turn resp_s |
| --- | --- |
| 19k | 26.8 |
| 44k | 42.1 |
| 105k | 11.1 |
| 198k | 56.8 |
| 240k | 43.6 |
| 241k (compaction) | 133.2 |
| 90k post-compaction | 84.2 |
| 98k | 88.4 |

Latency scales with context and is materially worse after 04:00Z at equal context
(98k costing 88s at 04:06 versus 105k costing 11s at 03:50).

### Phase 2: upstream WebSocket failures (03:40:59 to 03:49:28Z)

Five consecutive `ws_close_1011` terminations, one per Luna audit run, each after a long
hang. WebSocket close 1011 is an upstream internal error.

| run | id | ts | resp_s |
| --- | --- | --- | --- |
| authority | 347552a4 | 03:40:59 | 688.0 |
| catalog | 31a5591b | 03:41:09 | 546.3 |
| autopilot | 6e0672ae | 03:44:56 | 523.0 |
| orchestration | b380834f | 03:45:33 | 538.3 |
| runtime | ddac0df9 | 03:49:28 | 1653.8 |

### Phase 3: the 39-minute stall (03:50 to 04:33Z) — the measured bottleneck

Each run reissued its turn. Every reissue hung for roughly 2300 seconds and released in
submission order, the signature of an upstream queue draining.

| run | id | request issued | released | wall |
| --- | --- | --- | --- | --- |
| catalog | 31a5591b | 03:50:16 | 04:29:41 | **2363.6 s / 39.4 min** |
| authority | 347552a4 | 03:52:28 | 04:32:06 | **2376.5 s / 39.6 min** |
| autopilot | 6e0672ae | 03:53:40 | 04:31:13 | **2251.2 s / 37.5 min** |
| orchestration | b380834f | 03:54:32 | 04:33:17 | **2325.7 s / 38.8 min** |
| runtime | ddac0df9 | (still on its 03:49 failure, then idle) | — | last turn 04:17:03 |
| reconciliation-check | 0c40ac42 | 04:13:05 | still open at 04:39 | **>26 min, in flight** |

Every one of these runs was carrying 231k to 247k input tokens.

### Phase 4: post-release (04:29 to 04:40Z)

All four released runs immediately opened a new request. They are progressing, not dead.
Roster confirms live states (`generating`, `reasoning`, `running-tools`) with
`last_turn_at` inside seconds of the exchange timestamps.

## Stage-by-stage elimination

| stage | measurement | verdict |
| --- | --- | --- |
| prompt submission | `runs.json` receipts, all `RUNNING` with delivery ids at 03:28-03:29 | clean |
| harness request | requests issued within 0-1.2 s of the prior response (`gap_s` 0.0-1.2 across 25 sampled turns of ddac0df9) | clean |
| proxy / provider first byte and completion | 2251-2377 s for four turns; 5x `ws_close_1011`; 1x `ws_close_1006` | **BOTTLENECK** |
| tool dispatch / execution / result | inter-exchange gaps 0.0-1.2 s; no tool ever held time | clean |
| transcript persistence | `authority.md` mtime 04:32:00Z against exchange completion 04:32:06Z, report on disk within seconds of the provider answering | clean |
| Activity / roster / watch | roster `last_turn_at` matches `wire_exchange.ts` within seconds; no projection lag | clean |
| gateway responsiveness | `desktop.log` serving per-run `/v1/capture/*/health` and `/health` at ~1 s cadence, all HTTP 200, continuously through the stall | clean |
| proxy process | `shared-proxy.sock` and pid live since 03:25; `shared-mitmdump.log` unwritten since 09-02 (no proxy errors) | clean |

## Control comparison

- **Opus portfolio (287fcdb2), completed.** 41 exchanges, avg 22.0 s, span 17.9 min,
  finished 03:47:35Z — before the Phase 3 window opened. Different harness (`claude`)
  and different provider path. It has one 509 s tail outlier at the onset of the incident.
  It did not escape by being faster per turn; it escaped by finishing first.
- **Sol investigator (b81621b8), launched 04:29Z on the same host, proxy and gateway.**
  Running 10-137 s per turn on 19k-76k context, healthy throughout the stall. This is the
  decisive control: identical local infrastructure, low context, no problem. The
  difference is context size and provider path, not the machine.

## Likely cause

Provider-side capacity or queueing on the Codex `gpt-5.6-luna` endpoint, aggravated by
**seven concurrent Luna runs on one account each carrying 230-250k input tokens**. Each
turn re-submits a near-maximum context, so the account's aggregate prefill demand was
roughly 1.6M tokens per round across the fleet. The `ws_close_1011` cluster is consistent
with an upstream tier shedding those connections; the uniform ~39-minute FIFO release is
consistent with a queue that drained rather than with per-request timeouts.

Corroborating live evidence: this investigator's own Claude request at 04:37:17Z returned
`{"type": "rate_limit_error"}`. Account-level rate pressure is present right now.

## Alternative explanations considered and rejected

1. **Local gateway or backend overload.** Rejected: health endpoints answered HTTP 200 at
   1 s cadence throughout, and the Sol run took normal-latency turns during the stall.
2. **Tool orchestration or unfulfilled parallel tools.** Rejected: inter-exchange gaps are
   0.0-1.2 s. No time is held between a response landing and the next request going out.
3. **Shared workdir contention.** All nine runs share
   `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`, a real hazard, but it would show
   as gaps between exchanges. It does not; the time is inside single provider requests.
4. **Projection or watch lag hiding finished work.** Rejected: roster `last_turn_at`
   tracks `wire_exchange.ts` within seconds, and `authority.md` appeared on disk within
   6 s of its exchange completing.
5. **Runs genuinely hung or dead.** Rejected: four released at 04:29-04:33 and
   immediately opened new requests.
6. **Compaction cost.** Real but small: one 133 s compaction request on 0c40ac42. It
   explains tens of seconds, not 39 minutes.

## Recommended immediate action

**Wait. Do not restart, interrupt, or re-prompt any audit run.**

The four runs that released at 04:29-04:33Z are live and working. Restarting them would
discard 60 minutes of accumulated context and force a fresh 240k-token prefill against the
same congested endpoint, which is the one action guaranteed to make the incident worse.

Least disruptive ordered recommendations:

1. **Hold for 15 minutes and re-read the roster.** Confirm `31a5591b`, `347552a4`,
   `6e0672ae`, `b380834f` complete their in-flight turns. `347552a4` already wrote
   `authority.md` at 04:32Z, proving the full path works once the provider answers.
2. **Launch no further `gpt-5.6-luna` runs** until the fleet drains. Added concurrency
   feeds the queue that is holding the time.
3. **Watch `ddac0df9` (runtime) and `0c40ac42` (reconciliation-check).** These carry the
   `stalled` label. `0c40ac42` has an exchange open since 04:13:05 and is the next to
   release if the queue behaves as it did before. `ddac0df9` has taken no turn since
   04:17:03 and is the only candidate for intervention.
4. **If intervention becomes necessary after the hold**, prefer a `nudge` prompt asking
   the run to write its partial findings to disk immediately, over an interrupt or a
   restart. Target only `ddac0df9-ab44-4277-8ea4-bed514a51dda`.
5. **Structural fix for the next audit, not now:** partition work so no run approaches the
   context ceiling, and cap concurrent same-model runs. The latency curve above shows cost
   rising steeply past ~200k tokens even before the incident.

## Unverified boundaries

- Provider-side queue state is inferred from client-observed timing and close codes. No
  provider telemetry was available.
- `ws_close_1011` is read as an upstream internal error per the WebSocket specification.
  The specific upstream fault is not visible from captured metadata.
- The account rate-limit link is corroborating, not proof of a shared limiter between the
  Anthropic and Codex paths.
