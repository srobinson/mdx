---
title: Live-capture tier-2 sink fix (provisional finalize seam)
type: sessions
tags: [backend, transport-matters, capture-substrate, tier-2, live-capture, root-cause, moe]
summary: Real Claude turns wrote zero index rows because emit_to_index was only wired to the dead non-provisional persist branch; fixed by emitting from the finalize seam.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Live-capture tier-2 sink fix

## Summary

`transport-matters claude` captured ZERO rows in a real run (index.db wire_exchange/transcript_turn/session/block all 0) despite 80/80 tier-2 unit tests green and tier-1 persistence working. Root cause: the tier-2 post-persist hook `emit_to_index` had a single call site on the NON-provisional branch of `persist_http_exchange` (exchange_recorder.py:268). Claude Code streams, so every parsed turn takes the provisional path — `handle_request` → `persist_http_provisional_exchange` sets `provisional_exchange_id`, then `persist_http_exchange` early-returns through `_finalize_http_provisional_exchange` and never reaches the hook. The sink got zero jobs.

Cascade: the transcript tailer cursor registers via `on_binding` *inside* `make_index_sink` (ingest.py:160), so a never-called sink also explains zero `transcript_turn` rows. One missing call broke wire rows + session binding + transcript tailing.

Three reviewers (Claude 3.1, Codex 3.2, orchestrator) converged independently on the same root cause. mitmdump.log evidence (tier-2 started OK, tier-1 persisted, zero sink-failure/traceback lines) ruled out the competing hypotheses (sink throwing on real payload / metadata.session_id deref / startup failure): the sink was never invoked, not failing.

Branch: `fix/livecapture-provisional-tier2-sink` @ 5158870 (off main 7c65c50). No PR — orchestrator gates on dual sign-off.

## API Contract

No API surface change. `/api/stream` SSE contract unchanged. Behavioral fix: real streaming exchanges now produce `transcript_turn` events and populate the tier-2 read API (`/api/index/sessions/{sid}/timeline?stream=wire|transcript`, `/diff`, `/search`).

## Database Changes

No schema/migration change. Fix restores writes to existing tier-2 tables (wire_exchange, transcript_turn, session, block) on the streaming path. `build_wire_job` reads `entry.res` for token counts, which is only populated at finalize — confirming finalize is the correct emit seam.

## Security Considerations

None changed. `emit_to_index` remains best-effort/non-fatal (tier-1 authoritative). Observability hardened: the sink-failure swallow was raised from silent to `_log.warning(..., exc_info=True)` so a future capture regression cannot hide as silent zero-rows.

## Performance Notes

`emit_to_index` enqueues to the async single-writer actor (non-blocking); adding it to the finalize seam adds one non-blocking enqueue per finalized exchange. Idempotent at the row level via wire upsert; called once per exchange at finalize.

## Open Items

- Codex finalize seams (codex/exchange.py:136/257/403/526) have the identical gap — deferred to slice 5 (codex) per orchestrator.
- Awaiting Codex (3.2) adversarial verification / second sign-off before the orchestrator opens the PR.
- Verified e2e: index.db 0 → wire=14/transcript=29/session=4/block=72; live transcript_turn on /api/stream; timeline/diff/search work for SID 098e107d. just (api) ci green (1073 passed).
