---
title: MemPalace review for history-matters and transport-matters capture-substrate
type: research
tags: [github-review, mempalace, history-matters, transport-matters, memory, mcp, chromadb, capture, retrieval, append-only]
summary: Local-first verbatim AI-memory system (ChromaDB semantic + BM25 hybrid, SQLite temporal KG, 29 MCP tools). Borrow the sweeper/cursor capture model and 4-layer wake-up; inspiration-only on the spatial metaphor.
status: active
source: github-researcher
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

# MemPalace review for history-matters + transport-matters capture-substrate

Repo: https://github.com/mempalace/mempalace (default branch `develop`)
Reviewed commit context: HEAD at 2026-06-03 (`fix/1619-hallway-pagination` merge), v3.3.6 line.

## Executive summary

MemPalace is a local-first AI memory system: it ingests agent/chat transcripts and project files, stores them **verbatim** as "drawers" in a vector store (ChromaDB by default), indexes them with a lossy compact "closet" layer, and retrieves with hybrid semantic + BM25 search. It adds a bi-temporal SQLite knowledge graph and a 29-tool MCP surface. For Helioy this is the most directly comparable artifact to history-matters yet reviewed: it does what CASS does (multi-platform session parsing, incremental ingest) but replaces CASS's lexical-only Tantivy/FTS5 retrieval with a **hybrid semantic-first** model, and adds a temporal forgetting model CASS lacks. For transport-matters it is a clean worked example of append-only, content-addressed, resume-safe capture driven off the durable transcript artifact rather than any liveness file.

## 1. Stats

53,435 stars, created 2026-04-05 (~2 months old), MIT license, 30 contributors, last commit 2026-06-03 (very active: 596 open issues, branch model `main`/`develop`/`release/*`). Primarily Python (~3.0 MB), with small TS/Vue/HTML for the docs/landing site. CI present (`.github/workflows/ci.yml`, `version-guard.yml`, `deploy-docs.yml`); pre-commit (ruff), pytest suite of ~80 test files, committed benchmark result files under `benchmarks/results_*`. Star count is anomalously high for the repo's age and `develop`-default posture; treat the 53k as a marketing/visibility signal, not a maturity proxy. The codebase itself is real and disciplined: ~27k LOC of core Python, an RFC-driven backend abstraction, explicit design principles in `CLAUDE.md`, and reproducible benchmark harnesses (LongMemEval 96.6% R@5 raw / 98.4% held-out hybrid; LoCoMo, ConvoMem, MemBench).

## 2. Grade

**B+** — Above claudex/cozodb (B−) and graphify (B); peer to superpowers (B+); below notebooklm-py/mngr/fallow (A−). Justification: it is a coherent, benchmarked, genuinely-shippable system with several primitives that map 1:1 onto two live Helioy targets (capture cursor, content-addressing, layered wake-up, hybrid retrieval, temporal KG). It falls short of A− because the headline novelty (spatial wings/rooms/drawers metaphor) is mostly organizational sugar over a flat vector store, the AAAK "compression dialect" is a regex/heuristic summary layer dressed up with emotion codes, and a large fraction of the LOC is platform-compatibility and HNSW-corruption firefighting rather than reusable architecture. The transferable core is a handful of files, not the whole edifice.

## 3. Primitives that transfer

1. **Resume-safe message-cursor sweep** — `mempalace/sweeper.py:147` (`get_palace_cursor`) + `:193` (`sweep`). Per-session cursor = `max(timestamp of already-ingested drawers)`; ingest only messages with `timestamp >= cursor`, using `< cursor` (not `<=`) as the skip test so messages sharing the max timestamp after a mid-sweep crash are still picked up. **Target: history-matters** (incremental capture loop) **and transport-matters capture-substrate** (this is the reconcile/backfill-from-durable-artifact pattern, stated as an algorithm).

2. **Deterministic content-addressed record IDs** — `mempalace/sweeper.py:183` (`sweep_{session_id}_{message_uuid}`) and `mempalace/miner.py:1253` (`drawer_{wing}_{room}_{sha256(source_file+chunk_index)[:24]}`). IDs are a pure function of stable identity, so re-ingest is an idempotent upsert and crashes never duplicate. **Target: transport-matters capture-substrate** (per-exchange IR file naming / dedup) **and history-matters**.

3. **Append-only / incremental-only design contract** — `CLAUDE.md` Design Principles ("Incremental only — append-only ingest after initial build... A crash mid-operation must leave the existing palace untouched"). Enforced via the cursor + deterministic IDs above. **Target: transport-matters capture-substrate** (durable `index.jsonl` + per-exchange IR is the same posture; this validates the "never destroy to rebuild" rule).

4. **Schema-version gate for silent rebuild** — `mempalace/palace.py:58` (`NORMALIZE_VERSION`) + `:720` (`file_already_mined`): drawers carry `normalize_version`; a drawer at a stale version is treated as "not mined," so the next pass rebuilds it with no manual erase. **Target: history-matters** (transcript schema evolves; this is how you migrate captured history without a destructive re-index) **and transport-matters capture-substrate** (IR format versioning).

5. **Hybrid retrieval: vector floor + BM25 rerank + index-as-signal-not-gate** — `mempalace/searcher.py:1` (module contract) + `:63` (`_bm25_scores`, Okapi BM25 over the retrieved candidate set). The drawer (verbatim) query always runs as the floor; the closet/index layer only *boosts* ranking and can never hide a drawer the direct path found. **Target: history-matters** (this is the retrieval model CASS does not have — semantic-first with lexical rerank, the exact upgrade over Tantivy-only BM25).

6. **Token-budgeted layered wake-up (L0–L3)** — `mempalace/layers.py:34` (`Layer0` identity ~100 tok) / `:76` (`Layer1` essential story ~500–800 tok, importance-scored top-N) / `:187` (`Layer2` wing/room-filtered) / `:247` (`Layer3` full semantic search). Wake-up loads only L0+L1 (~600–900 tok), defers the rest. **Target: history-matters** (session-start context injection with a hard token budget; structurally identical to cm `cx_recall` priority ordering and am salience surfacing).

7. **Bi-temporal entity-relationship graph with validity windows** — `mempalace/knowledge_graph.py:1`: triples carry `valid_from`/`valid_to`, queries take `as_of`, facts are **invalidated** (window-closed) not deleted, all in local SQLite. **Target: history-matters** retention/forgetting **and cm** (this is a richer supersession model than cm's single `supersedes` pointer: time-scoped truth rather than a boolean active/inactive flip).

8. **Two-tier store: lossy compact index → verbatim payload** — closets (`mempalace/palace.py:383` `upsert_closet_lines`, greedy ~1500-char packing, never splitting a pointer line) point to verbatim drawers via `→drawer_id` references. **Target: history-matters** (a cheap scannable index over an immutable verbatim corpus — the same shape as transport-matters' `index.jsonl`→IR-files split, arrived at independently).

9. **RFC-driven storage backend seam** — `mempalace/backends/base.py:185` (`BaseCollection` ABC) + `:308` (`BaseBackend` factory), typed `QueryResult`/`GetResult`, capability flags, `detect()` selection hook. Swap ChromaDB for Postgres/LanceDB without touching callers. **Target: history-matters** (if a sidecar vector index is added later, define the seam first; mirror the typed-result + capability-flag contract).

10. **Multi-platform transcript normalization** — `mempalace/normalize.py:153`+ dispatches Claude Code JSONL, Codex CLI rollout JSONL, Gemini CLI JSONL, Claude.ai/ChatGPT/Slack JSON into one canonical form; `mempalace/corpus_origin.py` adds heuristic+LLM provenance detection. **Target: history-matters** (same multi-agent-platform parsing surface as CASS, with an extra provenance layer worth borrowing).

## 4. Does NOT transfer

1. **The spatial memory-palace metaphor (wings/rooms/drawers/closets/tunnels/hallways)** — it is organizational labeling over a flat ChromaDB collection plus `where`-filters on `wing`/`room` metadata (`mempalace/layers.py:205` `build_where_filter`). cm already has a real, enforced scope hierarchy (global>project>repo>session) and am has geometric memory; the palace metaphor adds vocabulary, not a capability Helioy lacks. Inspiration-only.

2. **AAAK "compression dialect"** — `mempalace/dialect.py` is explicitly lossy (its own docstring: "AAAK is NOT lossless compression... The 96.6% benchmark score is from raw mode, not AAAK mode"). It is regex entity/topic extraction plus an emotion-code vocabulary (`vul`, `joy`, `grief`...). The closet *concept* (compact index → verbatim) transfers; the AAAK encoding itself, especially the affective codes, is product personality, not a Helioy primitive.

3. **ChromaDB-specific operational baggage** — a large share of LOC is HNSW-corruption avoidance (`mine_palace_lock` in `palace.py:594`, the 441GB→433KB `link_lists.bin` fix in `ROADMAP.md`, BLOB seq_id auto-repair, `repair.py` at 1,583 LOC). This is the cost of running ChromaDB as a writable multi-process store; it is a warning, not a pattern. If Helioy ever adds a vector sidecar, prefer an embedded read-mostly index (or the existing cm SQLite/FTS5 path) over a concurrently-written HNSW.

4. **The "no manifest" question is unaddressed because MemPalace has no run-manifest concept** — its durable artifact is the upstream transcript JSONL (Claude Code's own files), and its own state is the ChromaDB collection + KG SQLite. There is no per-run liveness beacon, so it offers no direct lesson on the manifest-as-beacon-vs-record distinction; it simply never had a manifest to confuse with a record. The *positive* lesson (always enumerate durable runs by globbing the durable artifact) is present in the sweeper; the manifest-specific lesson is not.

5. **Emotion/importance scoring for ranking** — `layers.py:131` scores L1 by `importance`/`emotional_weight`/`weight` metadata. Helioy salience already lives in am and cm `confidence`/`priority`; the affective weighting here is not a model Helioy wants.

## 5. Verdict

- **history-matters: borrow.** Lift the capture loop (sweeper cursor + deterministic IDs + version gate), the hybrid-retrieval contract (vector floor + BM25 rerank, index-as-signal), and the L0–L3 wake-up budget. This is the concrete upgrade path over the CASS lexical-only baseline, and the temporal KG is a better forgetting model than AHP's append-only audit trail for the *recall* use case.
- **transport-matters capture-substrate: borrow (algorithm), inspiration-only (manifest split).** `sweeper.py`'s cursor-from-durable-store reconcile is exactly the backfill algorithm to copy; but MemPalace has no manifest/liveness concept, so it confirms rather than refines Stuart's beacon-vs-record split.

## 6. Why

Both Helioy targets face the same root problem MemPalace solves: how do you turn an append-only stream of agent exchanges (which already live durably as transcript files) into a queryable, crash-safe, incrementally-maintained history without ever corrupting or re-deriving the source of truth? MemPalace's answer is disciplined and worth internalizing: the durable artifact is upstream and immutable; your derived store is rebuildable from it; every write is keyed by a content/identity hash so re-runs are idempotent; a cursor makes ingest resumable; a schema version makes migration silent; and retrieval is layered by cost so a wake-up is cheap and a deep search is unbounded. That is the whole transport-matters thesis (durable `index.jsonl`+IR enumerated by globbing the durable artifact, never the beacon) expressed in a different domain, plus the retrieval sophistication history-matters needs to beat CASS.

## 7. How to apply

- **history-matters capture:** model the ingest loop on `sweeper.sweep` — per-session timestamp cursor, deterministic `(session_id, message_uuid)` IDs, `< cursor` tie-break, batched idempotent upserts with an existence pre-check for honest add/already-present metrics (`sweeper.py:229` `_flush`). Carry a `normalize_version` on every captured unit (`palace.py:58`) so transcript-schema changes trigger silent rebuild instead of destructive re-index.
- **history-matters retrieval:** if/when history-matters adds semantic search, adopt the `searcher.py` contract verbatim: vector retrieval as the floor that always runs, BM25 rerank over the *candidate set* (IDF computed within candidates), and any summary/index layer as a rank booster that can never gate out a direct hit. This is the precise delta over CASS's Tantivy-only path.
- **history-matters wake-up:** implement a token-budgeted L0–L3 ladder (`layers.py`) and wire it to cm `cx_recall` (which already does ancestor-walk priority ordering) and am salience, rather than reimplementing scoring. L0=identity, L1=top-N recent/important, L2=scope-filtered, L3=deep search.
- **history-matters forgetting:** evaluate the bi-temporal KG (`knowledge_graph.py`) as the model for retention — close validity windows (`invalidate`) instead of deleting, support `as_of` queries. This is a strict superset of cm's `supersedes` and is the more honest "flight recorder" than AHP for recall (AHP stays better for tamper-evident audit; they are complementary, not competing).
- **transport-matters capture-substrate:** copy the reconcile algorithm only — enumerate durable runs by globbing the durable artifact (here, transcript JSONL; in transport-matters, `index.jsonl`+IR), derive a cursor from what is already persisted, and upsert by content-addressed ID. Do **not** import the spatial metaphor or ChromaDB; keep the existing manifest-as-beacon discipline, which MemPalace neither contradicts nor improves.
- **cm:** the validity-window triple model is worth a design note as a future evolution of `supersedes` toward time-scoped truth. Low priority, but cited here so it is not lost.

## 8. Artifact

This file: `~/.mdx/research/mempalace-mempalace.md`.

## Sources consulted

`README.md`, `MISSION.md`, `ROADMAP.md`, `CLAUDE.md` (design principles), `mempalace/backends/base.py`, `mempalace/palace.py`, `mempalace/layers.py`, `mempalace/sweeper.py`, `mempalace/knowledge_graph.py`, `mempalace/searcher.py` (head), `mempalace/dialect.py` (head), `mempalace/corpus_origin.py` (head), `mempalace/normalize.py` (dispatch), `mempalace/miner.py` (ID/metadata refs), `mempalace/mcp_server.py` (tool surface), `benchmarks/` (result files).

## Open questions

- How well does the hybrid v4/v5 tuning generalize off the LongMemEval/LoCoMo splits to coding-agent transcripts specifically (the CASS domain)? The committed results are conversational-QA benchmarks, not code-session retrieval.
- Does the bi-temporal KG actually get populated automatically during mining, or only via explicit `kg_add` MCP calls? (Reviewed the schema/query side, not the auto-extraction wiring in `entity_detector`/`general_extractor`.)
- ChromaDB write-corruption mitigations imply real pain at scale; what is the practical drawer-count ceiling before HNSW maintenance dominates? Relevant only if Helioy ever adopted ChromaDB, which this review recommends against.
