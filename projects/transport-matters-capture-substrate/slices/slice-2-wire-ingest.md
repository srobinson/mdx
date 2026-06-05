# Slice 2 — Wire ingest + sink

**Goal:** live wire capture populates tier-2 off the hot path. Inject a post-persist sink
at the exchange recorder that builds one `IndexJob` per captured exchange and submits it to
the slice-1 `IndexWriter`. First slice that touches the running proxy — but tier-1 stays
authoritative and the wire path never blocks on, nor fails because of, tier-2 (§7.1).

**Depends on:** slice 1 (writer, blocks, sessions, models, schema — merged @ #18 `44e89c0`).
**Unblocks:** slice 3 (query API now has rows to read), slice 4 (transcript correlates to
these wire rows via `session_id`).

## Read first (canonical spec)

- **§6.4** DAG-safe wiring — the no-`storage→index`-cycle sink injection (the load-bearing
  design of this slice).
- **§7.1** tier-1-first invariant; **§7.2** wire write path (field mapping, session row from
  `SessionBinding`, ordered `exchange_block` edges, `seq`).
- **§6.5** idempotency + ordering (`seq = MAX(seq)+1` per session, preserved on re-ingest).
- Slice-1 code for the contracts to compose: `index/{writer,blocks,sessions,models}.py`
  (`IndexWriter.submit`, `upsert_block`, `synth_session_id`/`upsert_session`, the staged
  `SessionBinding`).

## Files (≤700 LOC; functions ≤150)

1. `api/src/transport_matters/index/ingest.py` (~290) —
   `bind_exchange(entry, artifacts, run_facts) -> SessionBinding | None`;
   `build_wire_job(entry, artifacts, binding | None) -> IndexJob`; the §7.2 row mapping +
   `exchange_block` edge flattening. Imports `storage` + `ir` + `index` (allowed — `index`
   sits after `storage`).
2. **Injected post-persist sink (§6.4).** Declare an `ExchangeSink` Protocol (or
   `Optional[Callable[[IndexEntry, ExchangeArtifacts], None]]`) **in the storage layer**;
   the recorder invokes it at the post-persist point (`exchange_recorder.py:264`, right
   after `persist_exchange` at `:261`). `load_runtime()` (`addon_runtime.py:28-59`)
   constructs the `IndexWriter` and registers the sink, closing over the per-run static
   `SessionBinding` facts. **No `storage → index` import** anywhere.

## Invariants (must not break)

- **DAG:** `storage` must NEVER import `index` (cycle). The sink is a callable injected at
  `load_runtime`; only `ingest.py` (index layer) imports `storage` types (§6.4, api/CLAUDE.md).
- **tier-1 first:** the sink fires **only after** `persist_exchange` returns success; the
  enqueue is non-blocking (`writer.submit` → `put_nowait`); the wire path never blocks on /
  fails because of tier-2 (§7.1). Queue-full drops + logs + marks the run dirty (slice-1
  writer behavior) — never blocks.
- **session_id single source:** `binding.session_id` — minted (closure) or
  `synth_session_id(run_id, provider, native_session_id)` (slice-1 `sessions.py`) for
  read-back. `artifacts.request_ir.metadata` (`ir.py:118`) is **INPUT-only** to
  `bind_exchange`, never written verbatim. No binding → `wire_exchange.session_id` NULL
  (`ON DELETE SET NULL`), no session row written; a later correlation upsert backfills it.
- **Reuse, don't recompute:** `wire_exchange.req_*_chars` read straight from
  `ReqStats.system_chars/tools_chars/messages_chars` (`storage/base.py:37`) — the wire path
  already computed them (DRY, §7.2). `raw_dir` is a **pointer**; no raw bytes in tier-2.
- **Ordered `exchange_block` edges:** flatten `request_ir.system → tools → messages →
  response` with a single running `pos`; `role` + `section` live on the edge (§3.5/§7.2).
  `system`/`tool_def` blocks arise only here.
- **`seq`** assigned by the writer (`MAX(seq)+1` per session), preserved on re-ingest (§6.5).
- **#17 privacy:** cross-module symbols public; `test_private_import_boundary.py` green.
- **Idempotent:** re-ingest of the same `exchange_id` replaces the row + its edges (§3.7).

## Acceptance (§13.2 + §7.1; real temp SQLite)

- Drive a synthetic exchange through the recorder → `wire_exchange` row + ordered
  `exchange_block` edges + `block` rows; `session` row upserted when the binding resolves;
  `session_id` NULL when it does not.
- **Wire-path latency unchanged:** assert the recorder path enqueues and returns without
  awaiting tier-2 (the writer thread commits async, off the hot path).
- Idempotent re-ingest (same `exchange_id`) → stable rows, edges replaced not duplicated.
- DAG: `test_private_import_boundary` green; no `storage → index` import.
- `just ci` green.

## Grounding (current file:line, post #16/#17)

`exchange_recorder.py` post-persist `emit_exchange`:264 (after `persist_exchange`:261) — #16
split the module into `exchange_recorder_artifacts.py` + `exchange_recorder_unparsed.py`, the
persist→emit hook is intact at :264. `addon_runtime.load_runtime()`:28-59. `storage/base.py`
— `IndexEntry`:115, `ReqStats`:37, `ResStats`:63. `ir.py` — `RequestMetadata.session_id`:118,
`InternalRequest`:129, `InternalResponse`:154. The slice-1 `SessionBinding` is staged in the
`index/` package (see slice-1 in-file note) pending the full `index/adapters/base.py` model in
slice 4 — slice 2 composes the staged shape.

## Build order (TDD)

`bind_exchange` (closure facts + synth, test session_id resolution incl the NULL/no-binding
path) → `build_wire_job` (field map + edge flattening, test row + ordered edges + char reuse +
`raw_dir` pointer) → `ExchangeSink` in storage + recorder wiring (test post-persist fires,
tier-1-first, non-blocking) → `load_runtime` registration (test end-to-end capture →
`wire_exchange`) → DAG / privacy / idempotency tests.
