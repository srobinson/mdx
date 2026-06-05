---
title: cm recall ranking + shadow-canary — merged build spec
type: projects
tags: [context-matters, cm, recall, ranking, shadow-canary, sqlite, rust, spec]
summary: Make kind/confidence/priority drive cx_recall ordering via a deterministic lexicographic rank key in cm-core, applied at the non-FTS recall re-sort, behind an observe-only shadow-canary (serve old, log diff) gated by a ranking-mode flag. Synthesis of two independent MoE designs (Claude + Codex).
status: active
source: warroom-orchestrator
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# cm recall ranking + shadow-canary — build spec

Merged from `cm-recall-ranking--claude.md` and `cm-recall-ranking--codex.md` (independent MoE designs, both graded high-confidence). Both verified against the repo. This is the authoritative build spec; the two designs are the source material.

## Motivation (verified)

`cx_recall` claims (MCP docs + `cx_store` schema) that feedback gets highest recall priority and high-confidence surfaces first "at the same scope level". The code does not honor this: `do_resolve_context` (cm-store) orders `updated_at DESC` per ancestor scope; `recall.rs` re-sorts only by `Reverse(scope_path.depth())`. `confidence`/`priority` are stored in `EntryMeta` and read by nothing at recall. This spec makes the documented contract true and adds a canary to prove any ranking change is an improvement before it ships.

## Decision: deterministic lexicographic, NOT a weighted score

Both panes independently chose lexicographic over a Vellum-style weighted sum. Rationale: cm fields (kind, 3-level confidence, int priority) are ordinal policy signals, not calibrated numerics; the non-FTS recall path has no relevance anchor (every candidate is already in-scope) so a weighted blend would be arbitrary; lexicographic makes the categorical doc-promises literally provable and every tie-break unit-testable; no weight profiles to tune blind.

## Ranking model (converged core)

Total order over candidate entries, lexicographic on (DECIDED: kind-primary / bold):
`kind-tier` · `confidence` · `priority` · `scope-depth` · `recency` · `id`

- **kind-tier** (`EntryKind::rank_tier`, single source of truth in cm-core): `feedback` is tier 0 (contractual, the only fixed point). Default mid-order: `feedback > decision > preference > lesson > pattern > fact > reference > observation`. The mid-order is a judgment call, canary-measurable and cheap to retune (panes disagreed on decision-vs-preference; not contractual).
- **confidence** (`Confidence::recall_rank`): `high > (medium == absent) > low`. Absent confidence ranks as medium, not bottom (most entries omit it; sinking them below explicit `low` would be wrong).
- **priority**: `meta.priority.unwrap_or(0)`, higher wins.
- **recency**: `updated_at` desc, tiebreak only.
- **id**: UUIDv7 desc, final tiebreak → order is total, deterministic across runs.

### DECISION 1 — rank key ordering: BOLD / kind-primary (decided by Stuart 2026-06-16)
kind-tier is the OUTERMOST key; scope-depth is demoted below priority. Global feedback/decisions can outrank a repo-local observation. Order: `kind > confidence > priority > scope-depth > recency > id`. This is a larger behavior change than the conservative scope-primary alternative, so it ships dark and the live flip stays canary-gated. The candidate-window risk (below) is MORE acute under kind-primary because a high-tier entry beyond the SQL fetch window now matters more: oversampling in slice 2 is load-bearing, and the canary's `window_truncated` counter is the gate on whether the SQL-push fix is needed before live.

## Placement

- `cm-core` (`crates/cm-core/src/types/entry.rs`): `EntryKind::rank_tier`, `Confidence::recall_rank`, `pub fn recall_rank_key(&Entry) -> RecallRankKey`. Pure arithmetic on existing fields (zero-I/O honored). Optional `cm-core/src/ranking.rs` for `priority_components`.
- `cm-capabilities` (`crates/cm-capabilities/src/recall.rs`): split `post_filter_rows` into `filter_rows` + `rank_legacy_rows` + `rank_priority_rows`; `recall_inner` reads ranking mode, widens the candidate window, computes both orderings. Token budget applied separately to served vs shadow rows so the diff reflects what each model would expose.
- `cm-store`: canary log table + write only. No ranking logic.

## FTS vs non-FTS

### DECISION 2 — FTS recall behavior: BOLD (decided by Stuart 2026-06-16)
The priority model applies to ALL `cx_recall` routes INCLUDING Search; BM25 `f.rank` is demoted to a tiebreaker AFTER kind/confidence/priority/scope-depth. This treats `cx_recall(query)` as priority-context-with-narrowing rather than relevance search. `cx_search` (`search.rs`) is UNTOUCHED and remains the pure BM25-first relevance surface for users who want text relevance. Canary reports diffs split by `RecallRouting` so Search behavior is judged separately, and the live flip is separately observable per route.

## Shadow-canary (observe-only, converged)

**Trigger:** in `recall_inner`, after filtering, on one in-memory candidate vector: compute `old` (legacy) and `new` (proposed) orderings, both truncated to `limit`. No second query.

**Serve policy** gated by ranking mode (env `CM_RECALL_RANKING` > `[recall] ranking_mode` in `.cm.config.toml` > default `legacy`, fail-closed, mirrors `Config` in `cm-store/src/config.rs`):
- `legacy` (default): old order, canary inert, zero overhead. Byte-identical to today (assert in tests).
- `shadow`: serve OLD, compute new, write diff row.
- `live`: serve new, still write diff row.

**Table** (additive migration `006_recall_shadow.sql`, CREATE TABLE only, reversible via DROP, self-contained like `mutations`; IDs only, no body/title/snippet logged; query stored as BLAKE3 hash + length):
`id` (uuidv7 PK), `ts`, `scope_path`, `query_hash`, `query_len`, `routing`, `tier`, `k`, `candidate_count`, `top1_changed` (bool), `topk_overlap` (real), `footrule`/`spearman` (real, rank correlation), `mean_abs_position_delta` (real), `position_deltas` (json), `old_ids` (json), `new_ids` (json), `window_truncated` (bool), `ranking_version`, `duration_ms`. Indexes on `ts`, `top1_changed`, `routing`, `scope_path`.

**Diff metrics:** `top1_changed` (headline moved?), `topk_overlap` (served set churn / truncation effect), a rank-correlation scalar (`footrule` or `spearman`) + per-entry `position_deltas` for worst movers.

**Write is best-effort:** `ContextStore::log_recall_shadow` default no-op (the `count_relations_for` default-impl precedent); `CmStore` overrides. A write failure is traced and swallowed, never propagated — a canary must not fail a recall.

**cm-web:** read-only API (`/api/recall-shadow`, mirrors `list_mutations`) + a "Recall Shadow" React panel near `RecentActivity`: divergence rate (% top1_changed), top-K-overlap histogram, drill-down of high-footrule recalls rendering old vs new top-K side by side with links to entry detail.

## Candidate-window truncation (shared #1 risk)

`do_resolve_context` applies `ORDER BY updated_at DESC LIMIT ?` per ancestor scope BEFORE re-ranking, so a high-priority entry beyond the fetch window can never be promoted. v1 mitigation: when ranking is active, oversample (`fetch_limit = (limit * OVERSAMPLE).min(MAX_LIMIT)`; precedent: `recall_inner` already x3-oversamples for kind/tag post-filtering), re-rank, truncate; log `window_truncated` so the canary measures clip frequency. Fully-correct fix (push rank into SQL `ORDER BY` via CASE + `json_extract`) couples ranking to cm-store SQL and is deferred unless the canary shows oversampling is insufficient.

## Slices (PR-sized)

1. **Pure ranking core, inert.** cm-core `recall_rank_key` + tier/confidence helpers + unit & property tests (total-order property). cm-capabilities reads ranking mode and wires `recall_inner`; `legacy` default keeps current sort. Ships dark, zero behavior change. Golden legacy-order test.
2. **Shadow canary.** Migration `006_recall_shadow`; `log_recall_shadow` default no-op + `CmStore` impl; `recall_inner` computes both orders, serves old, logs diff in `shadow`; window oversampling; diff-metric helpers + tests (shadow == legacy bytes; known divergence → exact metrics; log-write error → recall still succeeds).
3. **cm-web surfacing + promotion.** Read-only API + React panel; flip to `live` once shadow data is clean. *(Optional slice 4: FTS/BM25 fusion, designed from shadow data.)*

## Test plan

cm-core unit + property (total order; feedback outranks at equal scope+confidence; high>med>low; absent==medium; priority breaks kind+conf ties; recency then id). cm-capabilities integration on real SQLite (never mocked): seeded mixed scope/kind/confidence/priority, assert order under `live`; golden test pinning `legacy`. Canary: shadow byte-identical to legacy + exactly one row; seeded divergence → asserted metrics; best-effort error path. cm-web: API parity + panel render states. Gates: `just check`, `just test`, `just build`.
