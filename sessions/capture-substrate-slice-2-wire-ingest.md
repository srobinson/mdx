---
title: Capture Substrate Slice 2 — Wire Ingest + Sink
type: sessions
tags: [backend, capture-substrate, sqlite, tier-2, slice-2, transport-matters, moe]
summary: Injected post-persist sink + wire ingest that maps each captured exchange to a tier-2 wire_exchange row off the hot path; dual MoE sign-off at b200cc3.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Capture Substrate Slice 2 — Wire Ingest + Sink

Warroom MoE. Author = backend-engineer (`:3.1`); reviewer = Codex (`:3.2`); orchestrator = `:2.1`.
Branch `feat/capture-slice-2-wire-ingest`, tip **b200cc3**, off main (slice 1 merged @ #18 `44e89c0`).
Dual clean sign-off reached. First slice to touch the running proxy; tier-1 stays authoritative.

## Summary

Live wire capture now populates tier-2 off the hot path via dependency inversion (§6.4):

- **`storage/exchange_sink.py`** — an injectable `ExchangeSink = Callable[[IndexEntry,
  ExchangeArtifacts], None]` registry (`set_exchange_sink` / `clear_exchange_sink` /
  `emit_to_index`). `emit_to_index` is best-effort: a missing sink is a no-op and any sink
  failure is logged + swallowed, so the wire path never fails because of tier-2 (§7.1). The
  module imports only `storage.base` — **no `storage → index` import** (the cycle the DAG forbids).
- **`index/ingest.py`** — `bind_exchange` resolves the FK-parent `SessionBinding | None`;
  `build_wire_job` maps to the `wire_exchange` row + ordered edges and wraps the writes in an
  `IndexJob`; `make_index_sink(writer, run_facts)` is the closure `load_runtime` registers.
- Recorder seam: `emit_to_index(entry, artifacts)` at the post-persist point
  (`exchange_recorder.py:264`), only after `persist_exchange` returns success.
- `addon_runtime.load_runtime` constructs + starts the `IndexWriter`, registers the sink
  (guarded so a tier-2 startup failure can't stop the proxy), and drains the writer off the
  event loop on shutdown (`run_in_executor`).

## Load-bearing decisions (for slices 3-8)

- **`RequestMetadata.session_id` is INPUT-only.** There is **no proxy-side `--session-id`
  mint**: the anthropic adapter parses `metadata.session_id` straight off the wire
  (`anthropic.py:512-528`; Claude sends its own session id, nullable). So `bind_exchange` uses
  it as the correlation id and routes it through a `SessionBinding` — minted-authoritative for
  anthropic/gemini (used directly), read-back synth for codex/opencode (`_READBACK_PROVIDERS`).
  Refined per-provider in slices 5/6. No correlation id (or no run_id) → `None` → `session_id`
  stays NULL, no session row; a later correlation upsert backfills it.
- **Char reuse, not recompute.** `wire_exchange.req_*_chars` are read straight from
  `IndexEntry.req` (`ReqStats` already IS the production char accounting). Tokens from
  `ResStats.input_tokens/output_tokens`.
- **`raw_dir` is a pointer.** `str(DiskStorageLayout().new_exchange_dir(entry.id, now=entry.ts))`
  — pure path computation matching the backend's own `_prepare_exchange_write(entry.id,
  now=entry.ts)`. Tier-2 uses the default storage root (consistent with slice-1 `index_db_path`).
- **Ordered edges:** flatten request `system → tools → messages → response` with one running
  `pos`; role/section live on the edge. System + tool_def blocks arise only here.
- **`seq` = per-session `MAX(seq)+1`, NULL while uncorrelated.** The upsert's `DO UPDATE` sets
  `seq = COALESCE(wire_exchange.seq, excluded.seq)`: an assigned seq is preserved on re-tail
  (§6.5), but a NULL seq is back-filled to the per-session rank when a later correlation
  supplies the session (§7.2) — so a non-NULL `session_id` never has a NULL `seq` (§8.3 timeline).
- **Sink injected only at the `:264` finalized-http seam.** Codex and provisional persist paths
  (recorder/codex `persist_exchange` call sites) are deferred to later slices.

## Review Outcome

One reviewer BLOCKER (valid): the correlation upsert backfilled `session_id` but left `seq`
NULL. Fixed @ b200cc3 with the `COALESCE` clause above + two regression tests. Both flagged
decisions (no-mint correlation; single `:264` seam) accepted. `just ci` green, 1037 passed.

## Open Items

- Slice 3 (query API) can now read these wire rows; slice 4 transcript correlates via
  `session_id` and backfills `session_id`/`seq` on previously-uncorrelated wire exchanges.
- Slices 5/6 refine read-back correlation (codex native id via `codex/session_metadata.py`).
- Extending the sink to codex/provisional persist paths (and possibly centralizing it in the
  `persist_exchange` helper) is a future consideration once those streams are in scope.
