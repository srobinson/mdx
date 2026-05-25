# LEDGER — Transport Matters Capture & Retrieval Substrate spec

- Spec:  `~/.mdx/projects/transport-matters-capture-substrate-spec.md`
- Brief: `~/.mdx/projects/transport-matters-capture-substrate-BRIEF.md`
- Orchestrator: `transport-matters:general:1:2.1`

## Current phase

**COMPLETE.** All four phases signed off by both panes (Claude author + Codex
reviewer). Spec is 2015 lines, §1-15 all filled, no placeholders. Ready for Stuart's
evaluation. One known wart: §7.3 (approved Phase C) carries a premise superseded by a
note in §11.1; a direct §7.3 edit is the only outstanding consistency-polish item.

## Phase status

- Phase A - Foundations (1, 2, 3, 12): APPROVED
- Phase B - Adapters (4, 5): APPROVED
- Phase C - Engine + data paths (6, 7, 8): APPROVED (both panes signed off 2026-05-31; 5 Bs across 3 rounds, session_id sourcing swept to binding.session_id)
- Phase D - Lifecycle + verification (9, 10, 11, 13, 14, 15): APPROVED (both panes signed off 2026-05-31; 3 Bs/3 rounds: durable iter_run_dirs() enumeration since manifests unlink on exit, rebuild requires connection-quiescence not just BEGIN-pause, §7.3/§11.1 supersession)

## Locked decisions (carry across phases)

- Hybrid two-tier. Tier-1 = per-run dir source of truth (raw bytes). Tier-2 = shared
  `~/.transport-matters/index.db` (WAL), rebuildable derived projection.
- Global content-addressed `block` (blake2b). FTS5 lexical first; vector deferred.
- Per-provider adapter port; MINT claude/gemini, proxy codex, api/export opencode;
  minted/synth session uuid = universal correlation key.
- Both streams first-class, never collapsed. No backcompat; LOC 700/file, 150/func.

### Phase A resolved (load-bearing)

- Block identity = SEMANTIC dedup (`identity_canonical` strips provider_data; cache_hint
  for system). Lossless reconstruction is tier-1's job. `block.n_chars` removed; nullable
  `n_tokens` back-fillable via COALESCE; immutability narrowed to identity+search cols.
- `session_id` PK = idempotency key: minted uuid (claude/gemini) or
  `uuid5(SESSION_NS, "{run_id}|{provider}|{native_session_id}")` for codex; partial
  unique index `WHERE native_session_id IS NOT NULL`.

### Phase B resolved (load-bearing)

- §4 port = ABC + dataclasses (`SessionBinding`, `TranscriptSource` file-tail/pull-api,
  `NormalizedTurn`, `normalize()`, `TurnContext.pending_calls` to bridge cross-record
  pairing). Block model reuses `ir.ContentBlock`.
- §5 adapters: claude (jsonl uuid/parentUuid, mint); codex (rollout+session_index,
  read-back, uuid5); gemini FORMAT-SPLIT (A live-session intra-record toolCalls[];
  B cross-record functionCall/Response via pending_calls; chats/*.jsonl vs Content[]);
  opencode (export info-wrapper/model/header-strip + opencode.db, one canonical reshape).

### Phase C resolved (load-bearing)

- §6 indexer = in-proxy writer thread (daemon rejected), fed by a DAG-safe injected
  post-persist sink (no recorder->index cycle); WAL+busy_timeout single-writer;
  `IndexJob` embeds `SessionBinding`; per-job `SAVEPOINT`/`ROLLBACK TO` batch isolation.
- Shared `index/sessions.py` (`SESSION_NS`/`synth_session_id`/`upsert_session`) so wire
  + transcript converge on one `session_id`. `binding.session_id` is the SINGLE
  authoritative source everywhere; `artifacts.request_ir.metadata` is INPUT-only to
  `bind_exchange`.
- §7 tier-1-first (authoritative), best-effort batched tier-2 off the hot path.
- §8 two-phase FTS; timeline reconstruction; wire<->transcript pivot/diff (join on stored
  session_id + block-hash); raw fetch via raw_path; query surface = `index/queries.py`
  + new `/api/index` router. Layering: index core imports ir+canonicalization only;
  storage coupled only at the ingest/writer boundary.

## Approved sections

- Phase A: §1, §2, §3 (+§3.8 exec verification), §12. Both signed off.
- Phase B: §4 port, §5 adapters. Both signed off.
- Phase C: §6 indexer, §7 write path, §8 read/query. Both signed off.
- Spec is 1561 lines. §9, 10, 11, 13, 14, 15 remain (Phase D).

## Open escalations

(none)
