# Slice 1 — Core store + writer

**Goal:** stand up tier-2's schema, the content-addressed block layer, the session
helpers, and the single-writer thread — the foundation slices 2-8 build on. Purely
additive: touches nothing in the running proxy, so it ships behind no flag.

**Depends on:** nothing. **Unblocks:** slice 2 (wire ingest), slice 4 (transcript).

## Read first (canonical spec)

- **§3** in full — DDL (§3.1 PRAGMAs, §3.2 schema_meta + gate, §3.3 block hashing /
  canonical form, §3.4 core tables, §3.5 edges, §3.6 FTS5 + triggers, §3.7 upsert keys,
  §3.8 the executed verification you must reproduce as tests).
- **§2** — ubiquitous language (workspace/run/session/wire_exchange/transcript_turn/
  block/edge/correlation key). Names are load-bearing; match them verbatim.
- **§6.3** writer actor + **§6.5** idempotency/ordering.
- **§7.5** `sessions.py` placement; **§12** module layout + the canonicalization-DRY note.
- **Appendix A** (Phase A decision log) and **Appendix B** (code anchors).

## Files to create (all ≤ 700 LOC; functions ≤ 150)

1. `api/src/transport_matters/canonicalization.py` — **extract** the low-level helpers
   `canonical_json` / `_canonical_fields` / `_json_string` out of `override_audit.py`
   (depends on `ir` only). `override_audit.canonical_block_json` stays put and keeps
   importing them. This is a refactor + move; update `override_audit.py` imports. (§12)
   **#17 privacy:** any primitive consumed cross-module (by `override_audit` AND by
   `index/blocks.identity_canonical`) must be a **public** name in `canonicalization.py` —
   so `_canonical_fields`/`_json_string` are **promoted** (drop the underscore) on
   extraction, or expose a single public `canonical_json(part, *, strip_provider_data=…)`
   both encoders compose. A cross-module import of a `_`-prefixed name fails
   `test_private_import_boundary.py`.
1a. `api/CLAUDE.md` — extend the documented import DAG (`ir → adapters → rules → pipeline
   → storage → breakpoint → server`): `canonicalization` joins layer 1 (imports `ir` +
   stdlib only); the new `index/` package sits **after `storage`** (imports `ir` +
   `canonicalization` only). One-line doc edit, part of this slice.
2. `index/__init__.py` — public exports (`apply_schema`, `connect`, `upsert_block`, models).
3. `index/schema.py` (~200) — DDL constants (§3.1-3.6), `apply_schema(conn)`,
   schema_meta seed + boot gate check (**incl. the new `adapters_version`**, §3.2),
   `rebuild_fts(conn)`.
4. `index/db.py` (~140) — `connect(path) -> Connection` applying the §3.1 PRAGMAs;
   `index_db_path()` = `default_storage_root()/"index.db"`; `transaction()` ctx helper.
5. `index/blocks.py` (~240) — `identity_canonical(part) -> str` (dispatch to
   `canonicalization.*`, **provider_data/cache_hint stripped uniformly**),
   `block_hash(canonical) -> str` (blake2b-256), `block_kind(part) -> str`,
   `block_text(part) -> str` (clean FTS projection), `upsert_block(conn, part) -> int`.
6. `index/models.py` (~190) — frozen pydantic rows: `BlockRow`, `SessionRow`,
   `WireExchangeRow`, `TranscriptTurnRow`, `BlockEdge`.
7. `index/sessions.py` (~90) — frozen `SESSION_NS`,
   `synth_session_id(run_id, provider, native_session_id)` (uuid5),
   `upsert_session(conn, SessionBinding)`. (`SessionBinding` import lands with slice 4's
   `index/adapters/base.py`; for slice 1 define a minimal local row contract or stage the
   shared model — note the dependency, don't forward-import adapters.)
8. `index/writer.py` (~240) — `IndexWriter` (OS thread owning one write connection;
   bounded `queue.Queue`; batched `BEGIN IMMEDIATE` with per-job `SAVEPOINT`), `IndexJob`;
   `start()`/`submit()`/`stop(drain)`. Slice 1 builds the actor + lifecycle; the wire/
   transcript job *builders* land in slices 2/4.

## Slice-1 invariants (must not break)

- `identity_canonical` is a **separate encoder**, never a call to `canonical_block_json`
  (that would re-admit `provider_data` into identity). Emit `type` first for every kind.
- `block` is immutable except `n_tokens`: upsert is
  `ON CONFLICT(hash) DO UPDATE SET n_tokens = COALESCE(excluded.n_tokens, block.n_tokens)`.
  No `block_au` trigger (§3.3). No `n_chars` column on `block`.
- `session` idempotency on the PK; the native-id guard is a **partial** unique index
  `WHERE native_session_id IS NOT NULL` (dodges SQLite's multiple-NULL hole, §3.4).
- Writer: one thread, one write connection (sqlite3 is thread-affine). Per-job failure =
  `ROLLBACK TO j` **then** `RELEASE j` (bare try/except still commits earlier rows at the
  batch COMMIT). Queue-full **drops + logs + marks run dirty**, never blocks (§6.3).
- `schema.py` / `blocks.py` / `models.py` import `ir` + `canonicalization` only — no
  `storage`, no `server` (DAG, §12).
- **#17 privacy boundary** (api/CLAUDE.md): no non-test module imports a `_`-prefixed name
  or `_`-prefixed module from another module — promote to a public name instead. Enforced
  by `test_private_import_boundary.py`. Every cross-module symbol in `canonicalization.py`
  and the `index/` package must be public; intra-module helpers stay `_`-prefixed.

## Acceptance (reproduce §13.1 against a real temp `index.db`, never a mock)

- block dedup: same content under two roles/streams, once with `provider_data` once
  without → **one** row, identical hash.
- canonical identity: `identity_canonical(part)` emits `type` first, strips
  `provider_data`/`cache_hint`, and **differs** from `canonical_block_json` on the same part.
- kind determinism: text vs thinking vs system with identical inner text never collide.
- idempotent upsert: submit same entity twice → row count stable, edges replaced not
  duplicated; `n_tokens` back-fills NULL→value via COALESCE without touching identity/text.
- session synth: deterministic; partial unique index rejects two ids sharing one non-null
  native triple, allows multiple minted NULLs.
- GC mark-sweep: orphan deleted, referenced retained, FK blocks deleting a referenced
  block (`IntegrityError`), `block_ad` evicts the FTS row.
- FK cascade asymmetry: `wire_exchange.session_id` SET NULL vs `transcript_turn` CASCADE.
- writer smoke: `submit` two identical jobs → stable rows; `stop(drain=True)` flushes +
  `wal_checkpoint(TRUNCATE)`.
- Re-run the §3.8 DDL exec assertions as a test (all 11 pass).

## Grounding (current file:line, re-validated against main post #16/#17 — supersedes Appendix B)

`ir.py` — `TextBlock`:17 `ToolUseBlock`:25 `ToolResultBlock`:35 `ThinkingBlock`:45
`ImageBlock`:53 `UnknownBlock`:61, `ContentBlock` union:68-71, `SystemPart`:76,
`ToolDef`:85, `RequestMetadata.session_id`:118, `InternalRequest`:129, `InternalResponse`:154.
`override_audit.py` (UNCHANGED by #16/#17) — `_json_string`:54, `canonical_json`:90,
`_canonical_fields`:107, `canonical_block_json`:115, `block_chars`:172, `count_chars_parts`:180.
`storage/base.py` — `ReqStats`:37 (system_chars:41/tools_chars:43/messages_chars:45),
`ResStats`:63 (stop_reason:66/input_tokens:67/output_tokens:68), `IndexEntry`:115.
`workspace.py` — `WorkspaceId`:46-55 (slug:53/hash:54/root:55), `blake2b`:67, `run_root()`:83.
`storage_roots.py` — `default_storage_root()`:9, `default_workspaces_root()`:14.
Recorder seam (slice 2, noted now): `exchange_recorder.py` post-persist `emit_exchange`:264
(after `persist_exchange` at :261); `addon_runtime.load_runtime()`:28-59. #16 split
`exchange_recorder.py` (649→281) into `exchange_recorder_artifacts.py` +
`exchange_recorder_unparsed.py`; the persist→emit hook is intact at :264.

## Build order (TDD)

schema/db (apply + PRAGMAs + gate, test §3.8) → blocks (identity/hash/kind/text/upsert,
test dedup+determinism+COALESCE) → sessions (synth + upsert, test partial-unique) →
models → writer (thread + batch + SAVEPOINT, test idempotent submit + drain). Each unit
red→green before the next.
