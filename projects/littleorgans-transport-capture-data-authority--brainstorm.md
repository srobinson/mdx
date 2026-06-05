---
title: littleorgans-owned capture — durable artifact and data authority model
type: brainstorm
tags: [littleorgans, capture, data-authority, durability, storage]
summary: Data authority model for a littleorgans-native capture context, derived from transport-matters as experimental evidence, with no tm dependency proposed
status: complete
source: backend-engineer
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

## Inspected SHAs

| Repo | SHA | Commit |
|---|---|---|
| littleorgans (monorepo) | `98d8928941b5b5db670ed73ed06af57f61dcfa0a` | docs(build): sccache fallback + clean-sccache recipe |
| transport-matters (pinned phase-one baseline) | `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55` | fix(auth): close credential review residuals |

### Baseline revalidation

Initial inspection ran against transport-matters `ed099336` (the checkout HEAD). Phase one is pinned to `a252df24`, so every transport-derived load-bearing finding was revalidated against the immutable `a252df24` tree via `git show` and `git cat-file`, with no checkout and no repo edits. Result: all 18 cited source files, the full `api/migrations` directory, and every cited package (`storage`, `session`, `index`, `run`, `captured`) are byte-identical between `a252df24` and `ed099336` (`git diff --quiet` per path). The two commits diverge from merge base `101287bf` only in auth/credential code, canvas slices outside `api/src`, docs, and one test file (`harnesses/test_inventory_vocabulary.py`, present only at `ed099336` and not cited). Load-bearing anchors were additionally confirmed directly in the pinned tree: the wire-store docstring "Raw bytes never enter Postgres" (`a252df24:api/src/transport_matters/session/wire_store.py:8`), `WIRE_COMMIT_WATERMARK_LOCK_KEY` (`wire_contracts.py`), `os.fsync` (`atomic_io.py:89`), and `_RUN_INDEX_GLOB = "*/*/*/index.jsonl"` (`backfill.py:38`). No finding in this document rests on later-only evidence; every citation below holds verbatim at `a252df24`.

transport-matters is cited as experimental evidence only. No dependency on the `transport_matters` package, its schema, or its storage tree is proposed. `transport-matters/NOTES` was not read. No repo edits were made.

## Scope

The durable artifact and data authority model littleorgans needs to own capture as a first class bounded context. The model answers, per data class: who is authoritative, what durability it gets, what transaction and crash boundary protects it, and how it is retained, deleted, replayed, backed up, and recovered.

## Data class taxonomy

Eleven distinct classes, each with a different authority answer. Conflating any two of these is the primary design hazard.

1. **Exact wire bytes.** The verbatim request and response bodies as they crossed the proxy. Evidence: tm stores these as `request.raw` / `response.raw` per exchange directory (`api/src/transport_matters/storage/disk_layout.py:14-19`, `ExchangeArtifactPaths`). The tm wire-store docstring states the load-bearing rule verbatim: "Raw bytes never enter Postgres; `exchange_id` is the pointer into the tier-1 run dir" (`session/wire_store.py:1-10`).
2. **Normalized IR.** The parsed, provider-neutral representation (`request.ir.json`, `response.ir.json`, plus curated variants `request.curated.raw` / `request.curated.ir.json` for pause-and-edit). Derived from exact bytes by adapter code; re-derivable whenever the parser improves.
3. **Transcript snapshots.** A byte-faithful, append-only prefix copy of the harness native transcript file, teed at consume time into `<run_dir>/transcripts/<session_id>.jsonl` (`storage/transcript_snapshot.py:1-25`). Exists because the harness or user can GC the native file; ownership of the bytes must not depend on harness retention.
4. **Fidelity findings.** Drift between what the harness believed and what the wire carried: override audits (`request.audit.json`, `OverrideAudit`, `storage/disk.py:390-395,532-534`), transcript drift evidence routed through an injected hook (`index/tailer_drift.py`, migration `0023_harness_drift_evidence`). Findings are derived; their evidence excerpts are durable.
5. **Compatibility facts.** Frozen per-run record of harness version, adapter and contract revisions, and release digests, in `<run_dir>/compatibility.json` beside `sessions.json`; historical readers dispatch from recorded revisions and unknown `fact_schema_version` surfaces `historical_contract_unsupported`, never a guessed parse (`harnesses/compatibility_facts.py:1-21`, `storage/disk_layout.py:71-77`).
6. **Launch facts.** The owned-launch record a rebuild needs to bind transcripts back without the live env: native session id, source descriptor, harness, minted flag, home dir (`storage/session_facts.py:1-26`, `<run_dir>/sessions.json`). Written once, by the launcher, before any wire frame.
7. **Indexes.** Relational rows keyed for query: exchange rows, content-addressed blobs, component sets, request messages, response blocks (`session/wire_contracts.py:18-25`: `wire_blob`, `wire_component_set`, `wire_component_set_member`, `wire_exchange`, `wire_request_message`, `wire_response_block`), plus session event rows and lifecycle rows. All rebuildable from classes 1, 3, 5, 6.
8. **Product projections.** Conversation and timeline shapes computed from index rows (`session/conversation_projection.py`, `session/timeline*.py`). Pure functions; zero storage authority.
9. **Retention and deletion state.** Staged delete directories (`.del` suffix), backup directories (`.bak`), delete tombstone events (`wire_exchange_deleted` payload, `session/writer.py:252-266`).
10. **Replay inputs.** The durable run marker `index.jsonl` enumerated by `iter_run_dirs` (`session/backfill.py`, glob `*/*/*/index.jsonl`), together with classes 3, 5, 6.
11. **Operational streams.** Live status, run lifecycle, notify channels. Ephemeral by intent; durable only insofar as lifecycle rows land in the index.

## Authority table

| Data class | Authoritative store | Durability | Rebuildable from | littleorgans home (proposed) |
|---|---|---|---|---|
| Exact wire bytes | Filesystem, per-exchange dir | Immutable once finalized; atomic dir activation | Nothing. This is the root of trust | `~/.lilo/data/capture/<run>/<exchange>/` via a new `lilo_paths` accessor family (pattern: `crates/lilo-paths/src/lilo.rs:56 data_root`, `runtime.rs:43 event_log_path`) |
| Normalized IR | Filesystem beside raw; mirrored into index rows | Durable but re-derivable | Exact bytes + adapter revision | Same exchange dir; normalized rows in Postgres |
| Transcript snapshot | Filesystem, append-only per session | Prefix-exact; gap is a hard failure | Nothing once native file is GC'd | `~/.lilo/data/capture/<run>/transcripts/<session_id>.jsonl` |
| Fidelity findings | Findings: index rows. Evidence excerpts: filesystem | Findings re-derivable; evidence immutable | Raw + snapshot + adapter revision | Findings in Postgres; excerpts beside the exchange |
| Compatibility facts | Filesystem, frozen per-run document | Written once at gated launch | Nothing; records the observed world | `<run>/compatibility.json` twin |
| Launch facts | Filesystem, written once by launcher | Survives process exit; idempotent upsert per native id | Nothing; launcher is the only witness | `<run>/sessions.json` twin; writer is the `lilo run` launch path |
| Indexes | Postgres (`LILO_DATABASE_URL`, unified schema `internal/db/migrations/0001_unified_schema.sql`) | Transactional; fully rebuildable | Replay over run dirs | New `capture_*` tables in the same unified schema, keyed by `SessionId` |
| Product projections | None (computed) | None | Index rows | `internal/session/app` query layer |
| Retention/deletion state | Filesystem staged dirs + index tombstones | Two-phase; reconciled at startup | n/a | Same suffix conventions |
| Replay inputs | Filesystem run marker | The run dir IS the backup unit | n/a | `index.jsonl` twin per run dir |
| Operational streams | None durable | Best-effort | Lifecycle rows | Existing `runtime_lifecycle` / event path |

The single organizing invariant: **tier-1 filesystem artifacts are the sole authority; every Postgres row is a replayable projection.** tm encodes this in three independent places, which is what makes the evidence strong: the wire-store docstring (raw never enters Postgres), the sink contract ("Tier-1 is authoritative", `storage/exchange_sink.py:7-9`), and the rebuild path that reads only run dirs (`session/backfill.py`).

littleorgans already runs the same authority pattern natively on the runtime axis: the runtime event JSONL (`lilo_paths::event_log_path`) is the durable stream, and `SessionStore::apply_runtime_events_and_cursor` (`internal/session/store/src/postgres/events.rs:23-30`) applies events and cursor in one transaction. Capture extends an existing littleorgans idiom; it does not import a foreign one.

Join key: the control-plane `SessionId` (UUIDv4, issued at spawn, injected as `LILO_AGENT_SESSION_ID`), per the locked typed-id decision. The capture context stamps it into launch facts at spawn, before any wire frame, so every artifact class correlates by platform id rather than a provider-minted conversation id.

## Transaction and crash boundaries

**Filesystem boundary (tier-1).**
- File writes: temp file, `fsync`, rename (`atomic_io.py:89`; `storage/disk.py:198-205` index rewrite via `.tmp` + rename).
- Exchange finalization: directory swap via `rename(2)` with tmp/backup/final co-located on one filesystem (`storage/disk_helpers.py:89-110`); crash mid-swap leaves either the old or the new dir, never a torn one.
- Deletion: two-phase. Rename live dir to `.del`, then remove; restore on downstream failure (`storage/disk.py:285-321`); startup reconciles orphaned staged deletes (`_reconcile_staged_deletes`, `storage/disk.py:133-145`).
- Transcript tee: append-only; snapshot size equals owned prefix length, so a re-tail from offset 0 appends only bytes beyond the current size (idempotent). A gap (start offset ahead of snapshot size) raises rather than skips, so the cursor can never advance past un-snapshotted data (`storage/transcript_snapshot.py:14-24`).

**Postgres boundary (index).**
- One caller-owned transaction per event batch; the writer opens it and the wire write runs inside (`session/wire_store.py:3-9`). littleorgans twin: events plus cursor in one `sqlx` transaction (`events.rs apply_runtime_events_and_cursor`).
- Idempotent under replay: blob and component-set inserts are insert-if-absent (content-addressed by hash), the exchange row upserts by `exchange_id`, manifest and block rows are delete-and-reinsert (`wire_store.py:3-9`, `_upsert_blobs`, `_ensure_component_set`).
- Completion watermark assignment serialized under an advisory lock (`WIRE_COMMIT_WATERMARK_LOCK_KEY`, `wire_contracts.py:16`), with `created_at DEFAULT clock_timestamp()` and a partial index on completed rows (migration `0014_wire_commit_watermark`), so downstream replay cursors see a monotonic frontier.
- Poison records: quarantine with bounded attempts (`session/quarantine.py`, `QUARANTINE_MAX_ATTEMPTS`) and a dead-letter table (migration `0003_event_dead_letter`) instead of a wedged pipeline.

**Cross-boundary ordering rules (the crash contract).**
1. Durable tier-1 write precedes index submit; index commit precedes cursor or watermark advance. The commit dispatcher returns a `CommitResult` only after the Postgres transaction commits (`session/writer.py:54-61`, `index/commit_dispatcher.py`), and the tailer advances `byte_offset` only past committed, complete records (`index/tailer.py:1-13`).
2. Post-persist sinks fire exactly once, at the terminal persist, never at a provisional seam: `emit_to_index` fires when the completed exchange persists; a provisional exchange repaired away before release fires `emit_deleted` instead and never reaches the index (`storage/exchange_sink.py:11-17`). Sink failures are isolated per subscriber and never fail the wire path.
3. Deletion ordering: stage tier-1 delete, emit the `wire_exchange_deleted` tombstone, then GC unreferenced blobs (`sweep_wire_store`, `wire_store.py:208`). Tier-1 delete and index GC are separate transactions by design; the reconciler, not a cross-store transaction, closes the gap. Batch delete plus GC must never be described as atomic.
4. Launch facts are written once by the launcher before any wire frame, so a crash at any later point still leaves a rebuildable run dir (`session_facts.py:21-25`).

## Lifecycle states

**Exchange:** `provisional` (request persisted and released to provider; request-only index row) → `finalized` (response persisted; same row gains response, delivery identity stable) → `deleted` (staged `.del` → tombstone event → blob GC). Side branch: `unparsed` (synthetic exchange for traffic no adapter could parse, so drift detection still sees it). Transient dir states `.tmp` and `.bak` exist only inside an activation swap.

**Run dir:** `active` (liveness beacon manifest, unlinked on exit) → `durable` (marked by `index.jsonl` plus `sessions.json` plus `compatibility.json`) → `replayable` (enumerable by the rebuild glob) → `retired` (retention policy removes the tree; index rows follow via tombstones or full rebuild).

**Session correlation (littleorgans):** `session_spawn_intents` (`pending` → `resolved`/`aborted`) → `session_sessions.state` with `runtime_lifecycle.state` alongside, both carrying the `owner` seam for a future hosting tier (`0001_unified_schema.sql:1-8,30-55,130-150`). Capture artifacts attach to this lifecycle by `SessionId`; they never define their own session lifecycle.

**Index rows:** written → superseded by replay (idempotent upsert) → tombstoned. Never authoritative, so "corrupt index" has a defined answer: drop and rebuild.

## Retention, backup, corruption recovery

- **Retention** is a tier-1 policy: age or count based removal of run dirs through the staged-delete path, with index tombstones following. Postgres carries no independent retention clock.
- **Backup unit** is the run dir tree. Copying `~/.lilo/data/capture/` captures every authoritative byte; Postgres backup is an optimization for rebuild time, never a correctness requirement.
- **Corruption recovery**, by class: torn file → `.tmp` convention means the original survives; torn dir swap → backup dir restores; orphaned staged delete → startup reconciliation; corrupt index rows → replay from run dirs (idempotent writes make partial replay safe); poison transcript record → quarantine and dead-letter, pipeline continues; missing native transcript → owned snapshot is the surviving copy, which is the reason class 3 exists.

## What littleorgans builds (no tm dependency)

A `capture` bounded context inside the monorepo: path policy added to `crates/lilo-paths` (the existing single owner of tree layout), tables added to `internal/db/migrations` in the unified schema with the `owner` seam, writes composed behind the session app layer the way runtime events already are, and the CLI surface under the already-reserved `lilo transport ...` operator namespace. transport-matters contributed the validated invariants above as experimental evidence; the implementation, schema, and storage tree are littleorgans-native.

## Worker Status

No nested worker was spawned for this study. All evidence was gathered in-pane by `littleorgans:helioy-tools:backend-engineer:5:3.5` through direct repository inspection (Bash, Read, fmm) at the recorded SHAs. Scope executed: transport-matters storage, session, index, exchange_recorder, harnesses, and migrations modules as experimental evidence; littleorgans `internal/db`, `internal/session/store`, `internal/wire`, and `crates/lilo-paths` as the native substrate. Final state: research complete, artifact complete, no delegated subtasks outstanding.

## Highest-value durability invariant

Exact wire bytes and transcript snapshots on the local filesystem are the single source of truth, written atomically before any database touch; every Postgres row is an idempotently replayable projection whose cursor and watermark advance only after commit acknowledgment.
