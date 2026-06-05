---
title: cm recall ranking model + shadow-canary — design
type: projects
tags: [backend, context-matters, cm, recall, ranking, shadow-canary, sqlite, rust]
summary: Make kind/confidence/priority actually drive cx_recall ordering via a deterministic lexicographic rank key in cm-core, applied at the non-FTS recall re-sort, with an observe-only shadow-canary (serve old, log diff) gated by a ranking_mode flag.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# cm recall ranking + shadow-canary

Design only. Verified against the repo (`do_resolve_context`, `post_filter_rows`, `route_query`, `EntryMeta`, `ContextStore`) and the Vellum deep-dive (`~/.mdx/research/vellum-ai-vellum-assistant-cm-deepdive.md`, Q1/Q9). Ground truth honored: non-FTS recall orders `updated_at DESC` per ancestor scope in `do_resolve_context`; FTS path orders `f.rank`; `post_filter_rows` re-sorts **only** by `Reverse(scope_path.depth())` (a *stable* sort, so SQL order survives within a depth band); `confidence`/`priority` live in `EntryMeta` and are read by nothing at recall.

## Decision: deterministic lexicographic, not a weighted score

I choose **(a) lexicographic** `scope-depth → kind-tier → confidence → priority → recency`, not **(b)** a Vellum-style weighted numeric sum. Why:

- **The docs make categorical promises, not blend promises.** The MCP server text and `cx_store` schema assert "feedback = highest priority" and "high-confidence first". Lexicographic makes those *literally true and provable*: feedback outranks non-feedback at equal scope, full stop. A weighted sum can let a recent fact overtake an old feedback for some weight vector — silently breaking the documented contract.
- **cm has no anchor relevance signal on the non-FTS path.** Vellum's sum works because `semanticSimilarity` (weight 0.25–0.60, Q1) dominates and the other six terms are modifiers. The non-FTS recall path (scope-walk, no query) has *no* similarity signal — every candidate is already in-scope. Porting a weighted blend without its dominant term yields an arbitrary mix of weak signals and forces artificial [0,1] normalization of categoricals (kind, 3-level confidence) and a small int (priority).
- **No weight-tuning, no profiles.** Vellum needs three weight profiles by retrieval mode (Q1). cm has no mode concept; picking weights is unvalidated guesswork — exactly what the canary is meant to *avoid* shipping blind. Lexicographic has one tunable (the kind tier order) and it is inspectable.
- **Determinism + explainability.** "X ranked above Y because X is feedback" beats explaining a float. Every tie-break is independently unit-testable.

The recency term folds in the research's #2 (read-time recency) as the final **tiebreak**, not a standalone weighted feature (keeps "recency as a standalone feature" out of scope per the brief).

## 1. The ranking model (exact)

A total order over candidate `Entry`s. Sort ascending on a tuple where each field is pre-oriented so smaller = better:

```rust
// cm-core, pure, zero-I/O
pub struct RecallRankKey(u16, u8, u8, i64, i64, u128); // all "smaller = ranks first"

pub fn recall_rank_key(e: &Entry) -> RecallRankKey {
    let depth      = u16::MAX - e.scope_path.depth() as u16;     // deeper (narrower) scope first
    let kind_tier  = e.kind.rank_tier();                         // 0=feedback … 7=observation
    let conf_rank  = confidence_rank(e.meta.as_ref());           // 0=high 1=med/none 2=low
    let priority   = -(meta_priority(e.meta.as_ref()) as i64);   // higher priority first; default 0
    let recency    = -e.updated_at.timestamp_millis();           // newer first (tiebreak)
    let id_tiebrk  = u128::MAX - e.id.as_u128();                 // UUIDv7 newest first; total order
    RecallRankKey(depth, kind_tier, conf_rank, priority, recency, id_tiebrk)
}

fn rank_tier(&self) -> u8 { match self {           // EntryKind::rank_tier — single source of truth
    Feedback=>0, Decision=>1, Preference=>2, Lesson=>3, Pattern=>4, Fact=>5, Reference=>6, Observation=>7 } }

fn confidence_rank(meta) -> u8 { match meta.and_then(|m| m.confidence) {
    Some(High)=>0, Some(Medium)|None=>1, Some(Low)=>2 } }   // absent confidence = neutral (medium), not bottom
```

- **`scope-depth` stays the outermost key** → ancestor-walk locality is preserved exactly (narrower scope still wins). kind/confidence/priority/recency only re-order *within* a scope band. This is the conservative choice: it delivers "feedback-first / high-confidence-first within what is relevant" without inverting scope locality. The alternative (kind-tier outermost, so global feedback could outrank repo facts) is a knob the canary can later test; I do not ship it by default because it breaks the verified "most-specific scope first" semantic.
- **Only `feedback = tier 0` is contractual.** The mid-order (decision>preference>lesson>pattern>fact>reference>observation) is a defensible judgment call (agent-value ordering) and is canary-measurable + trivially retunable; I flag it as the second-least-certain choice.
- **Absent confidence = medium**, not last — most entries omit confidence; sinking them below the few explicit `Low` entries would be wrong.
- **`id` (UUIDv7) is the final tiebreak** → the order is *total*; no two distinct entries ever compare equal, so output is deterministic across runs.

## 2. Where it lands

- **cm-core** (`crates/cm-core/src/types/entry.rs`): `EntryKind::rank_tier`, `confidence_rank`, and `pub fn recall_rank_key(&Entry) -> RecallRankKey`. Pure arithmetic on existing fields — honors zero-I/O. Single source of truth for tier/confidence weights.
- **cm-capabilities** (`crates/cm-capabilities/src/recall.rs`, `post_filter_rows`): replace `rows.sort_by_key(Reverse(depth))` with `rows.sort_by_key(|r| recall_rank_key(&r.entry))`. `recall_inner` reads `ranking_mode` and widens the candidate window (see §8).
- **cm-store** (`crates/cm-store`): the canary *log table + write* only (§5). No ranking logic here.

## 3. FTS vs non-FTS interaction

The model applies to the **non-FTS recall path only** in v1: the scoreless rows from `route_without_query` (`ScopeResolve`/`BrowseFallback`) and the tags walk (`TagScopeWalk`). That path is where the docs' promise lives — `cx_recall` with no query is the "give me my priority context" call, and it has no relevance signal, so categorical priority *is* the ranking.

The **FTS search path** (`route_search`, carries BM25 `f.rank`) keeps `f.rank` as primary. Reason: fusing categorical tiers with BM25 floats needs an RRF/weighted-fusion design; naively sorting FTS hits by kind-tier would let a barely-matching feedback entry bury a perfect keyword match — destroying relevance. v1 leaves FTS served-order unchanged; the **only** safe addition is `recall_rank_key` as a tiebreak among *exactly-equal* `f.rank` rows (rare). The canary still *observes* FTS recalls (logs BM25-order vs BM25+tiebreak) so we collect fusion data, but FTS rerank is a deferred slice, not v1. `cx_search` (search.rs) is untouched.

## 4. Back-compat / migration impact

- **Ranking: zero schema, zero default behavior change.** Reads only existing fields (`kind` column, `meta.confidence`, `meta.priority`, `updated_at`, `id`). Gated by `ranking_mode` defaulting to `legacy` → byte-identical to today until promoted. Purely additive.
- **Canary: one additive migration** `006_recall_shadow.sql` (CREATE TABLE only; reversible via DROP; no FK, self-contained like the `mutations` table). No change to existing tables.
- **Trait:** `ContextStore` gains `log_recall_shadow` with a **default no-op impl** (exact precedent: `count_relations_for` already ships a default impl on the trait) → no other implementor or mock breaks.
- **cm-web:** additive read-only endpoint + panel; mirrors the existing `get_mutations`/`list_mutations` surface.

## 5. Shadow-canary (observe-only)

**Trigger point:** `recall_inner`, immediately after `post_filter_rows` produces the candidate set. With one in-memory candidate vector we compute **two orderings** — `old` (current: `Reverse(depth)` stable) and `new` (`recall_rank_key`) — both truncated to `request.limit`. No second query; just a second sort.

**Serve policy** (mirrors Vellum's two-flag split, Q9), gated by `ranking_mode`:
- `legacy` (default, fail-closed): old order, canary inert, zero overhead.
- `shadow`: **serve old**, compute new, write a diff row. Served bytes are identical to legacy (assert in tests).
- `live`: serve new, still write the diff row (keep measuring post-promotion).

Resolution order: env `CM_RECALL_RANKING` > `[recall] ranking_mode` in `.cm.config.toml` > default `legacy` (same env>config>default, fail-closed pattern as `Config` in `cm-store/src/config.rs`).

**What is logged / storage** — new table `recall_shadow` (cm-store writes it, cm-web reads it, same as `mutations`):

```sql
recall_shadow(
  id TEXT PK,                 -- UUIDv7
  ts TEXT DEFAULT (now),
  scope_path TEXT, query TEXT,           -- query NULL for scope-walk recalls
  routing TEXT, k INTEGER, candidate_count INTEGER,
  top1_changed INTEGER,       -- bool: did served #1 differ?
  topk_overlap REAL,          -- |old_topK ∩ new_topK| / K  (membership churn from truncation)
  footrule REAL,              -- normalized Spearman footrule: Σ|Δrank| / max, over the served K
  window_truncated INTEGER,   -- bool: new order promoted an entry old order had dropped past K (see §8)
  old_order TEXT, new_order TEXT,        -- JSON arrays of entry ids (top-K), for drill-down
  ranking_version TEXT        -- forward-compat: which tier table / mode produced `new`
);
CREATE INDEX idx_recall_shadow_ts ON recall_shadow(ts);
CREATE INDEX idx_recall_shadow_top1 ON recall_shadow(top1_changed);  -- find divergences fast
```

**Diff metric:** three complementary scalars — `top1_changed` (does the headline result move?), `topk_overlap` (does the served *set* change, capturing truncation/window effects), `footrule` (how far do entries move overall). Per-entry deltas are recoverable from `old_order`/`new_order` for the worst movers. The write is **best-effort**: a `log_recall_shadow` failure is traced and swallowed, never propagated — a canary must not fail a recall.

**cm-web surface:** a "Recall Shadow" panel (new read-only API over `recall_shadow`, React panel like the activity feed): divergence rate (% `top1_changed`), `topk_overlap` histogram, and a drill-down list of high-`footrule` recalls rendering old vs new top-K side by side.

## 6. Test plan

- **cm-core unit (`recall_rank_key`):** feedback outranks every other kind at equal scope+confidence; high > medium > low at equal kind; absent confidence == medium (not bottom); higher priority wins at equal kind+confidence; recency breaks ties, then id; scope-depth dominates kind (narrower scope wins regardless of kind — locks ancestor-walk). **Property test:** total order (irreflexive, antisymmetric, transitive; no two distinct entries equal) over randomized entries.
- **cm-capabilities integration (real SQLite, never mocked):** seed entries across scopes/kinds/confidence/priority; assert `cx_recall` order under `live` matches expected; **golden test** pinning `legacy` order so a regression with the flag off fails loudly.
- **Canary:** `shadow` mode returns bytes identical to `legacy` AND writes exactly one `recall_shadow` row; seed a known divergence → assert `top1_changed=true` and the exact `footrule`; `>window` entries → assert `window_truncated=true`. Best-effort: inject a log-write error → recall still succeeds.
- **Determinism:** same input → identical `old`/`new`/diff (no clock in the key; `ts` is the only clock and is metadata).
- **cm-web:** endpoint returns rows; panel component renders divergence stats.

## 7. Slice plan (3 PRs)

1. **Pure ranking core, inert.** cm-core `recall_rank_key` + tier/confidence helpers + unit/property tests. cm-capabilities reads `ranking_mode` and wires `recall_inner`, but `legacy` default keeps current sort → ships dark, function fully tested, zero behavior change. Golden legacy-order test.
2. **Shadow canary.** Migration `006_recall_shadow`; `ContextStore::log_recall_shadow` (default no-op) + `CmStore` impl; `recall_inner` computes both orders, serves old, logs diff in `shadow`; widen candidate window when ranking active; diff-metric helpers + tests. End state: flip to `shadow`, collect data, served result still legacy.
3. **cm-web surfacing + promotion.** Read-only API + React panel; enable `live` once shadow data is clean. *(Optional slice 4: FTS/BM25 fusion, designed from shadow data.)*

## 8. Risks + least-certain point

**The one thing I am least sure about — candidate-window truncation.** `do_resolve_context` applies `ORDER BY updated_at DESC LIMIT ?` (per ancestor scope) *before* `post_filter_rows` ever runs. So the re-ranker can only reorder rows SQL already returned: an **old but high-priority feedback entry beyond the fetch window is invisible to ranking** and never gets promoted. Mitigation in v1: when ranking is active, oversample the window (`fetch_limit = (limit * OVERSAMPLE).min(MAX_LIMIT)`; precedent exists — `recall_inner` already ×3-oversamples when post-filtering by kind/tags), re-rank, truncate to `limit`; and log `window_truncated` so the canary *measures* how often the window clips a would-be top-K entry. The fully correct fix pushes the rank into SQL `ORDER BY` (CASE on `kind`, `json_extract(meta,'$.confidence')`, `json_extract(meta,'$.priority')`), but that couples ranking to cm-store SQL and partly violates "ranking in cm-core/cm-capabilities". **I am unsure whether oversampling suffices in practice or whether v1 must push rank into SQL from day one — the canary's `window_truncated` counter is designed precisely to answer this before we commit.**

Other risks:
- **Kind mid-order is a judgment call** (only feedback-highest is contractual). Wrong order = subtly worse recall. Mitigated: one source of truth, canary-measurable, cheap to retune.
- **Scope-depth-primary may under-deliver the literal "feedback highest globally" reading** (kind only reorders within a band). Deliberate, conservative; the priority-primary alternative is canary-testable later.
- **Recency-as-tiebreak does real work on the non-FTS path** (no relevance signal), so same-kind/same-confidence entries effectively sort by recency. Acceptable (kind/confidence dominate; recency only breaks genuine ties) but worth watching that recall does not feel like "recency sort with extra steps".
- **Perf:** one extra in-memory sort (≤ `MAX_LIMIT` rows) + one best-effort insert per recall in shadow/live — negligible vs the SQL round-trips.
