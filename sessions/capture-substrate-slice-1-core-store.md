---
title: Capture Substrate Slice 1 — Core Store + Writer
type: sessions
tags: [backend, capture-substrate, sqlite, tier-2, slice-1, transport-matters, moe]
summary: Tier-2 SQLite core store + single-writer actor (schema, content-addressed block layer, sessions, writer) for the capture substrate; dual MoE sign-off at a05a18a.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Capture Substrate Slice 1 — Core Store + Writer

Warroom MoE build. Author = backend-engineer (`:3.1`); adversarial reviewer = Codex (`:3.2`);
orchestrator = `:2.1`. Branch `feat/capture-slice-1-core-store`, tip **a05a18a**, off `main` @ cbf1595.
Dual clean sign-off reached. Purely additive: touches nothing in the running proxy.

## Summary

Stood up tier-2's foundation (spec §3/§6/§12): the SQLite schema, the content-addressed block
layer, session correlation, frozen row models, and the single-writer thread. Key decisions:

- **Canonicalization extracted** to `canonicalization.py` (layer 1, stdlib only). `_json_string`
  and `_canonical_fields` were **promoted to public** (`json_string`, `canonical_fields`) because
  they are now consumed cross-module by both `override_audit.canonical_block_json` (char
  accounting, keeps `provider_data`) and `index.blocks.identity_canonical` (semantic identity,
  strips `provider_data`/`cache_hint`). The #17 privacy boundary forbids cross-module imports of
  `_`-prefixed names. `identity_canonical` is a **separate encoder**, never a call to
  `canonical_block_json`.
- **Semantic, stream-invariant block identity**: `hash = blake2b-256(identity_canonical(part))`,
  type emitted first, `provider_data`/`cache_hint` stripped uniformly (incl. recursive
  `tool_result` content), so wire and transcript representations of the same content hash equal.
  `SystemPart` emits `type="system"` (not its IR `"text"`) so it never collides with a `TextBlock`.
- **Writer** = one OS thread owning one write connection, bounded `queue.Queue`, batched
  `BEGIN IMMEDIATE` with per-job `SAVEPOINT` (`ROLLBACK TO j` then `RELEASE j` on failure), and
  non-blocking `submit` that drops + logs + marks the run dirty when full.

## API Contract (public surface, `transport_matters.index`)

- `connect(path) -> Connection` — §3.1 PRAGMAs, `isolation_level=None` (manual transactions).
- `transaction(conn)` ctx; `index_db_path() = default_storage_root()/index.db`.
- `apply_schema(conn)` — idempotent create + seed `schema_meta`; **self-healing version gate**
  (drop+rebuild on any gated-key mismatch, §3.2). `rebuild_fts(conn)`.
- `identity_canonical(part) -> str`, `block_hash(canonical) -> str`, `block_kind`, `block_text`,
  `upsert_block(conn, part, n_tokens=None) -> int` (`ON CONFLICT(hash) DO UPDATE SET n_tokens =
  COALESCE(excluded.n_tokens, block.n_tokens) RETURNING id`).
- `SESSION_NS`, `synth_session_id(run_id, provider, native) -> str` (uuid5),
  `resolve_session_id`, `upsert_session(conn, SessionBinding) -> str`.
- Frozen rows: `BlockRow`, `SessionRow`, `WireExchangeRow`, `TranscriptTurnRow`, `BlockEdge`.
- `IndexWriter(db_path, batch_max=64, flush_ms=50, queue_max=10_000)` + `IndexJob(kind,
  entity_id, run_id, apply)`; `start/submit/stop(drain)/dropped_for`.

`SessionBinding` (in `sessions.py`) is a **slice-1 local stage** of the shared model
`index/adapters/base.py` will own in slice 4; `session_id` is derived (minted passthrough or
read-back synth), not a binding input.

## Database Changes

New tier-2 DB at `~/.transport-matters/index.db` (WAL). Tables: `schema_meta`, `block`
(+`block_kind` idx, CHECK on kind enum, **no `block_au` trigger**, no `n_chars`), `session`
(+partial unique `session_native WHERE native_session_id IS NOT NULL` — closes SQLite's
multiple-NULL hole), `wire_exchange` (FK `ON DELETE SET NULL`), `transcript_turn` (FK
`ON DELETE CASCADE`), `exchange_block`/`turn_block` edges (block_id FK with **no** cascade → GC
is a safe mark-sweep), `block_fts` (fts5 external-content over `text`, `block_ai`/`block_ad`
triggers only). No migrations: `schema_meta` gate drops + rebuilds on mismatch.

## Security / Correctness Considerations

- Parameterized SQL only; identity stripping keeps transport-opaque blobs out of tier-2 identity
  (exact bytes stay in tier-1). FK `ON` is load-bearing for GC safety.
- Writer failure isolation: a failing job rolls back to its savepoint without polluting the batch;
  tier-1 remains source of truth, so a dropped/rolled-back job is recovered by the §10/§11 rebuild.

## Performance Notes

- Single-writer + WAL + `busy_timeout=5000` serializes cross-process writes at the file level;
  batched `BEGIN IMMEDIATE` amortizes fsync and bounds WAL growth (`wal_autocheckpoint=1000`).
- `upsert_block` is one statement (upsert + `RETURNING id`). FTS uses `unicode61` (no stemming) to
  preserve code identifiers.

## Review Outcome

One reviewer BLOCKER (valid): `_gated_mismatch` used `key in stored and …`, so a **missing** gated
key (an old shape predating `adapters_version`) read as clean → no rebuild → key silently seeded
onto the stale schema. Fixed @ b525344 (`stored.get(key) != constant` → absent counts as mismatch);
regression strengthened @ a05a18a to the only-`schema_version` repro. **`just ci` green, 1023
passed.** Dual clean sign-off at a05a18a.

## Open Items

- Slices 2-8 build on this: wire ingest + injected sink (2), read/query API (3), claude transcript
  + tailer (4), codex/gemini/opencode adapters (5/6), live-tail (7), delete/GC/backfill (8).
- `SessionBinding` converges with `index/adapters/base.py` in slice 4.
- Forward hooks (out of scope): `block_vec`/sqlite-vec (attaches to `block.id` like `block_fts`);
  per-occurrence char attribution as an optional edge column.
