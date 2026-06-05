---
title: Vellum Assistant memory subsystem — deep dive for context-matters (cm)
type: research
tags: [github-review, vellum-assistant, vellum-ai, memory-graph, recall, scoring, ebbinghaus-decay, sqlite, context-matters, cm, retrieval-ranking, dedup, shadow-canary]
summary: Exact mechanics of Vellum's memory recall/scoring/decay engine, mapped onto cm's keyword+scope store. Verified formulas; corrects the breadth review's invented `<memory_context>` tag and the prompt's wrong reinforcement formula and `tier-1>0.8` claim. Top borrows are read-time significance decay, the shadow-canary methodology, and an optional recency tiebreaker.
status: active
source: github-researcher
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Vellum Assistant memory subsystem — deep dive for cm

Companion to `vellum-ai-vellum-assistant.md` (breadth-first, graded A−). Re-cloned shallow at the same snapshot, analyzed memory only, removed. Every mechanism below carries file:line. Where the prompt or the prior review stated a formula/value that the code contradicts, I flag it explicitly.

cm anchor schema (verified in this repo, `crates/cm-store/migrations/001_initial_schema.sql`): `entries(id, scope_path, kind, title, body, content_hash, meta, created_by, created_at, updated_at, superseded_by)`. `confidence` and `priority` live inside the `meta` JSON (`crates/cm-core/src/types/entry.rs:88-109`). Recall (`crates/cm-capabilities/src/recall.rs`) walks target scope + ancestors, filters kinds/tags, then sorts by **scope depth desc** (recall.rs:108) and truncates; the FTS path orders by `bm25(f.rank)` (cm-store `sqlite/query.rs:135`), the non-FTS path by `updated_at DESC` (query.rs:69). cm already declares relation kinds `supersedes, relates_to, contradicts, elaborates, depends_on` (`crates/cm-core/src/types/relation.rs:16-26`) but **does not traverse them at recall time**.

---

## Q1. Multi-signal scoring model — the actual formula

`assistant/src/memory/graph/scoring.ts:235-262`, `scoreCandidate`. It is a **linear weighted sum** of seven components, each pre-normalized to [0,1], no multiplication, no division:

```
score = w.semanticSimilarity   * semanticSimilarity
      + w.effectiveSignificance * effectiveSignificance
      + w.emotionalIntensity    * emotionalIntensity
      + w.temporalBoost         * max(0, temporalBoost)
      + w.recencyBoost          * recencyBoost
      + w.triggerBoost          * triggerBoost
      + w.activationBoost       * activationBoost
```

Three weight profiles (scoring.ts:169-214), selected per retrieval mode:

| signal | DEFAULT (context-load) | PROCEDURAL | PER_TURN |
|---|---|---|---|
| semanticSimilarity | 0.25 | 0.45 | 0.60 |
| effectiveSignificance | 0.15 | 0.25 | 0.05 |
| emotionalIntensity | 0.15 | 0.00 | 0.05 |
| temporalBoost | 0.05 | 0.00 | 0.00 |
| recencyBoost | 0.15 | 0.05 | 0.05 |
| triggerBoost | 0.15 | 0.10 | 0.20 |
| activationBoost | 0.10 | 0.15 | 0.05 |

Weights sum to 1.0 each. Selection: context-load calls `weightsForContextLoad(node)` (scoring.ts:220-222) — a per-node dispatcher that returns `PROCEDURAL_WEIGHTS` if `node.type === "procedural"`, else `DEFAULT_WEIGHTS` (used at retriever.ts:679,767). Per-turn injection uses `PER_TURN_WEIGHTS` unconditionally (retriever.ts:1211,1253). The PROCEDURAL profile exists because procedurals have no emotional charge and no time-of-day pattern, so grading them on DEFAULT wastes ~45% of the weight budget on structurally-zero signals (scoring.ts:184-189, author's own comment).

**Correction to the prompt and the prior review: there is no `tier-1 > 0.8` cutoff.** `tier1Count` is hardcoded `0` at all four return sites (retriever.ts:437, 847, 936, 1344); `tier2Count` equals the reserved-capability count. "Tiers" in this code mean reserved capability slots, not a score band. The only numeric score gates in the pipeline are `INJECTION_THRESHOLD = 0.3` (per-turn floor, retriever.ts:1265) and `PROCEDURAL_SIM_FLOOR = 0.15` (retriever.ts:1257). semanticSimilarity is **not** rescaled in retriever.ts; the raw Qdrant `r.score` flows straight into `scoreCandidate` (retriever.ts:671,1203). The only in-file normalization is temporal: `(temporal + 1) / 2` mapping [-1,1]→[0,1] (retriever.ts:664).

## Q2. Decay model — read-time vs background, and the real reinforcement formula

This is a **hybrid split**, which the breadth review flattened:

- **Significance decay is computed at READ time, never stored.** `computeEffectiveSignificance` (scoring.ts:55-63): `S(t) = significance * exp(-elapsedDays / stability)`, where `elapsedDays = (now - lastReinforced)/86.4e6`. Default `stability = 14` → ~37% remains after 14 days. This is called fresh on every retrieval; the stored `significance` column never changes from decay.
- **Emotional intensity and fidelity decay are WRITTEN by an hourly background tick.** `runDecayTick(scopeId)` (decay.ts:134-195) selects all non-`gone` nodes in a scope and persists new `emotional_charge` and `fidelity`. decay.ts:128-133 comment is explicit: significance decay is *not* applied here, it lives in scoring.

**Reinforcement formula — the prompt is wrong.** The prompt cited `stability * (1 + 0.3*(reinforcement-1))`. That expression exists nowhere in the codebase. The actual code (`store.ts:594`, applied at store.ts:604-612 and 796-804) is multiplicative:

```
REINFORCEMENT_STABILITY_MULTIPLIER = 1.5
on reinforce:
  reinforcementCount += 1
  stability      = stability * 1.5            // geometric, not linear
  significance   = MIN(1.0, significance * 1.1)
  lastReinforced = now
```

So stability after N reinforcements is `14 * 1.5^N` (1 reinforcement → 21; 10 → ~807, matching scoring.ts:53 "essentially permanent"). The `×1.5 per reinforcement` comment at types.ts:89 is the correct one; the prompt's linear formula is stale. Note `lastAccessed` is NOT touched on reinforce, and `sourceConversations` is NOT merged on reinforce (only an explicit `updateNodes` change can rewrite it; store.ts:728-729).

**cm mapping:** cm could rank by a decayed score instead of static confidence/priority. The cheapest faithful port: a read-time recency multiplier on `updated_at` (cm already sorts non-FTS recall by `updated_at DESC`, so the signal is half-present). A full Ebbinghaus port needs new columns (`stability`, `last_reinforced`, `reinforcement_count`, a numeric `significance`) — see Q7 and the ranked list. The architectural lesson worth stealing regardless of columns: **decay that matters for ranking should be computed at read time, not by a background job** — it needs zero schema for the decay state itself and never goes stale between ticks.

## Q3. Fidelity ladder and emotional-charge decay curves

**Fidelity** `vivid → clear → faded → gist → gone` (types.ts:17). Thresholds in days from last consolidation (decay.ts:69-75): vivid<7, clear<30, faded<90, gist<365, then gist (never auto-`gone`; consolidation decides, decay.ts:99). High significance resists: `significance >= 0.9` triples thresholds, `>= 0.8` doubles them (decay.ts:91-92). Fidelity only ever downgrades (decay.ts:111-114). What it gates: fidelity is a **display/content-compression** signal driving the LLM consolidation pass (rewriting a vivid memory's prose into a gist), not a retrieval-score input — it does not appear in `scoreCandidate`. It is effectively "how much detail to keep," orthogonal to "how relevant right now."

**Emotional-charge decay curves** (decay.ts:29-62), gating the `emotionalIntensity` scoring component: `linear` (constant `originalIntensity - decayRate*t`), `logarithmic` (`I0 / (1 + rate*ln(1+t))`, sharp drop + long tail, used for negative events), `transformative` (`max(0.2*I0, I0*exp(-rate*t))`, floors at 20% — the feeling reshapes rather than vanishing, used for positive milestones), `permanent` (returns `originalIntensity`, no decay, for core identity markers). The curve is chosen at extraction time and stored in the `emotional_charge` JSON.

**cm verdict: skip both.** cm is a developer-context store (facts, decisions, lessons), not an autobiographical-memory engine. Emotional valence/intensity has no referent in cm's domain. The fidelity ladder presumes LLM rewriting of stored prose over time, which cm explicitly does not do (entries are immutable except via supersede). Porting either would be cargo-culting an autobiographical-memory metaphor into a keyword store.

## Q4. Trigger model

Schema `memory_graph_triggers` (migration 202, columns Q7) with three `type`s, all evaluated **live at retrieval time** (pure synchronous functions, no background job; triggers.ts comment line 97 notes "~5ms for 50 triggers, just vector math, no LLM"):

- **temporal** (triggers.ts:27-71): string-prefix match on `schedule`, not real cron — `day-of-week:monday`, `date:MM-DD`, `time:morning|afternoon|evening|night` (period boundaries at triggers.ts:73-86). On match, fixed `boost: 1.0` (triggers.ts:66).
- **semantic** (triggers.ts:99-126): cosine of the query embedding against the precomputed `condition_embedding`; fires if `>= threshold`; boost `= max(0.5, min(1.0, (sim - threshold)/(1 - threshold + ε)))` (triggers.ts:117-121), i.e. ∈ [0.5, 1.0].
- **event** (`computeEventRelevance`, triggers.ts:186-213): ramp curve around `event_date` — beyond `rampDays` → 0.05; in ramp window → `0.05 + 0.95*(1 - daysUntil/rampDays)`; day-of → 1.0; within `followUpDays` after → `exp(-(daysPast-1))`; else 0. Defaults `rampDays=7`, `followUpDays=2`.

The fired boost feeds the `triggerBoost` component (weight 0.15 default / 0.20 per-turn). Recurring triggers gate on `passesCooldown` (triggers.ts:219-223) using `last_fired`/`cooldown_ms`.

**cm verdict: niche, mostly skip — but `event` triggers map to cm's `expires_at`.** cm has no time-of-day or semantic-condition concept and gains little from temporal/semantic triggers. The one transferable idea: cm's `meta.expires_at` is a binary cliff. An *event ramp* (surface an entry more strongly as a deadline approaches, then fade it) is a richer version of the same idea, and cm already stores the timestamp. Low priority, but the cleanest trigger borrow if cm ever wants deadline-aware recall.

## Q5. Edge model vs cm's relations

Vellum edge relationships (types.ts:141-148): `caused-by, reminds-of, contradicts, depends-on, part-of, supersedes, resolved-by`, each with a `weight ∈ [0,1]`. Stored in `memory_graph_edges` (migration 202).

**Edges are used at RETRIEVAL time, not just storage** — this is the key finding. `computeActivationSpread` (scoring.ts:77-129) does a BFS from the already-matched node set out to `maxHops=2`, multiplying `edgeWeight * decayFactor(0.5)` per hop, taking the **max** across paths (not sum, to avoid double-counting, scoring.ts:118-119). The result feeds the `activationBoost` component (weight 0.10 default). So a memory that didn't match the query directly can still surface because it's strongly linked to one that did (spreading activation, ACT-R style). Edge *relationship type* is ignored by the spread — only `weight` matters.

**cm comparison:** cm already has `contradicts`, `depends_on`, `elaborates`, `relates_to`, `supersedes` as first-class relation kinds (relation.rs:16-26) — strictly richer than Vellum's *typed* use, since Vellum's retrieval ignores edge type. But cm **never traverses relations during recall** (recall.rs has no relation join). So the borrow is not "add a contradicts edge" (cm has it); it is "**use the edges you already have at retrieval time.**" The highest-value version for cm: when an entry matches, also surface entries it `contradicts` or `supersedes` (so the agent sees the live entry *and* the thing it overturned), and treat `elaborates`/`depends_on` as a 1-hop expansion. cm's relations carry no weight column, so a fixed per-hop decay (e.g. 0.5) is the natural analogue. A `caused-by` edge is *not* worth adding to cm — cm's domain has no causal-event chain; `depends_on` already covers the useful structural case.

## Q6. Extraction, dedup, and whether cm's BLAKE3 is stronger

`MemoryDiff` shape (types.ts:224-234): `{ createNodes, updateNodes, deleteNodeIds, createEdges, deleteEdgeIds, createTriggers, deleteTriggerIds, reinforceNodeIds }`. Applied **transactionally** in a single `db.transaction` (store.ts:683-863), ordered: deletes → creates → updates → reinforce → edges → triggers (store.ts:685-862). Deferred edges/triggers whose endpoints are newly-created nodes, plus Qdrant sync, run *after* the transaction because they need assigned IDs (extraction.ts:1116-1146). `sourceConversations` set to `[conversationId]` on create (extraction.ts:666); not merged on reinforce.

**Dedup is purely the LLM's job, with no mechanical gate.** The pipeline fetches up to 100 candidate existing nodes by embedding similarity (`findCandidateNodes`, extraction.ts:1413-1462, top-100 at :1443), injects them into the extraction prompt, and instructs the model to emit `reinforceNodeIds`/`updateNodes` instead of duplicating (prompt rules extraction.ts:231,238). The only mechanical dedup is *intra-content* (`deduplicateParagraphs`, store.ts:129-172) — within one node's text, not cross-node. **Correction: migration 189 did not drop a "memory_items fingerprint dedup table."** It dropped the simplified-memory-v1 tables (`time_contexts, open_loops, memory_observations, memory_chunks, memory_episodes`) and reverted to the legacy graph (189-drop-simplified-memory.ts:13-41). No fingerprint dedup table is referenced anywhere; the prompt's framing is mistaken, though the conclusion (graph dedup is LLM-only) is correct.

**cm's BLAKE3 content-hash dedup is genuinely stronger — at exact-duplicate prevention.** cm hashes `body` (`content_hash` column + `idx_entries_content_hash`) and rejects byte-identical re-writes deterministically and for free. Vellum cannot do this: a semantically-identical memory phrased differently is a new node unless the LLM happens to catch it. So for cm's use case (agents re-storing the same fact across sessions), cm wins decisively on cost and determinism. The honest caveat: BLAKE3 catches *exact* dupes only; it does nothing for near-duplicates ("FFmpeg needs -ac 2" vs "use -ac 2 for stereo in ffmpeg"). Vellum's LLM pass catches those at the cost of a model call per extraction. cm should not adopt Vellum's approach — but cm's *only* near-dup defense today is supersede-on-write, which requires the writer to know the prior entry exists. A cheap middle ground for cm: at `cx_store`, FTS-probe the target scope for high-BM25 matches and surface them to the writer as "possible duplicates," letting the agent choose supersede vs new. No LLM required, reuses existing FTS.

## Q7. Schema side-by-side

`memory_graph_nodes` (migration 202, `202-memory-graph-tables.ts`, with `event_date` added via later ALTER at :99-105):

| Vellum node column | type / default | indexed | cm equivalent | worth adding to cm? |
|---|---|---|---|---|
| id | TEXT PK | PK | id (UUIDv7) | have it |
| content | TEXT NOT NULL | — | body | have it |
| type | TEXT NOT NULL | yes | kind | have it (cm has 8 kinds too) |
| scope_id | TEXT NOT NULL DEFAULT 'default' | yes | scope_path (hierarchical) | cm's is richer (Q8) |
| created | INTEGER NOT NULL | yes | created_at | have it |
| last_accessed | INTEGER NOT NULL | — | — | **maybe** (decay-rate modifier only; low value) |
| last_consolidated | INTEGER NOT NULL | — | — | no (cm has no consolidation pass) |
| last_reinforced | INTEGER NOT NULL | — | — | **yes if porting decay** (drives Ebbinghaus clock) |
| reinforcement_count | INTEGER DEFAULT 0 | — | — | **yes if porting decay** (drives stability growth) |
| stability | REAL DEFAULT 14 | — | — | **yes if porting decay** (decay resistance) |
| significance | REAL NOT NULL | yes | meta.priority (i32, manual) | **partial** — a numeric, decayable importance is the gap |
| confidence | REAL NOT NULL | — | meta.confidence (enum hi/med/lo) | have it (cm's is coarser) |
| emotional_charge | TEXT (JSON) NOT NULL | — | — | no (Q3, out of domain) |
| fidelity | TEXT DEFAULT 'vivid' | yes | — | no (Q3, presumes prose rewriting) |
| source_conversations | TEXT (JSON) DEFAULT '[]' | — | created_by (single string) | **maybe** — provenance as an array beats one creator string |
| source_type | TEXT DEFAULT 'inferred' | — | — | **maybe** — direct/inferred/observed is a useful trust signal |
| narrative_role / part_of_story | TEXT nullable | — | — | no (autobiographical-narrative feature) |
| event_date | INTEGER nullable | yes | meta.expires_at (loosely) | covered by Q4 event-ramp idea |
| image_refs | (JSON, in struct) | — | — | no |

`memory_graph_edges`: `id PK, source_node_id (FK CASCADE), target_node_id (FK CASCADE), relationship TEXT, weight REAL DEFAULT 1.0, created`. vs cm `entry_relations(source_id, target_id, relation, created_at)` — **cm lacks `weight`**; adding it would let cm do weighted activation spread (Q5).
`memory_graph_triggers`: `id, node_id (FK), type, schedule, condition, condition_embedding BLOB, threshold, event_date, ramp_days, follow_up_days, recurring, consumed, cooldown_ms, last_fired`. No cm equivalent (Q4).

Net: the only Vellum columns with real cm leverage are the **decay quartet** (`last_reinforced`, `reinforcement_count`, `stability`, numeric `significance`) and **edge `weight`**. Everything else is either already present, coarser-but-fine, or out of cm's domain.

## Q8. Scope isolation — confirms cm's design, with a caveat

Vellum: one indexed `scope_id TEXT NOT NULL DEFAULT 'default'` (migration 202:33, `idx_graph_nodes_scope_id` :70-72), filtered at every retrieval. Flat namespace: `'default'` = guardian, custom strings = per-channel/guest. **No RLS; isolation is one-SQLite-DB-per-assistant-process** (breadth review §6). 

This **confirms cm's choice** that a single indexed scope column filtered at every read is sufficient isolation without RLS — and cm goes further with a *hierarchical* `scope_path` (global>project>repo>session) plus ancestor-walk recall, which Vellum's flat `scope_id` cannot express (Vellum has no notion of "broader scope visible at narrower"). So cm's design is strictly more expressive here; Vellum validates the cheap-single-column approach but does not challenge cm to change anything. The no-RLS / one-DB-per-instance point is **relevant to cm only as reassurance**: cm's `~/.context-matters/cm.db` single-file model is the same posture, and Vellum (a production multi-channel product) shipping it at scale is evidence cm need not reach for Postgres+RLS for isolation.

## Q9. Shadow-plugin canary — the methodology cm should adopt for ranking changes

This is the highest-value *process* borrow. Vellum runs a next-gen memory engine (v3) in production beside the live one (v2) and diffs, behind two registry flags (`shadow-plugin.ts:69-70`):

- `memory-v3-shadow` — **observation only**. `observeTurn` (shadow-plugin.ts:527) runs the v3 orchestrator and writes its selection set to a `memory_v3_selections` telemetry log (activation-log rows tagged `mode='v3_shadow'`, `memory-v2-activation-log-store.ts:134,177`), explicitly excluded from the live `mode='router'` set so shadow output **never enters the prompt**. In shadow mode the live `<memory>` block is bit-for-bit identical; only a side-effect log row differs.
- `memory-v3-live` — v3's selections are rendered into the live `<memory>` block and v2 retrieval is suppressed (`injector.ts:240-252`: both flags off → `return null`; empty/failed selection → `return null`, which preserves the v2 fallback).

Flag resolution (the prior review's open question, now traced): `getAssistantFeatureFlagValue` (`assistant/src/config/assistant-feature-flags.ts:285-299`) resolves in order gateway-IPC-override > registry `defaultEnabled` > `false` (fail-closed). The old engine's master switch `memory.v2.enabled` is a separate Zod config key defaulting **true** (`config/schemas/memory-v2.ts:49-54`) — it is v2's on/off, not the v3 gate. Wiring: registered as `post-compact` + `user-prompt-submit` hooks in the plugin loop (`plugins/defaults/index.ts:54-56`); a backstop `memory_v3_maintain` job in `jobs-worker.ts:802` gated by the shadow flag.

**cm mapping (direct):** when cm changes recall or ranking (e.g. adding any decay/recency signal from Q2), it should not flip the algorithm in place. It should run old+new ranking on the same `cx_recall` call, return the old result to the caller, and log the new result's ordering + a top-K diff to the mutations/telemetry table. cm already has a `mutations` audit table and a cm-web dashboard — the shadow log has a natural home. This makes a ranking change *measurable before it ships* (how often does new top-1 differ from old top-1, and is the new one better?), which is exactly the gate cm currently lacks. The mechanism is cheap: a feature flag, a second sort, a diff log row. No second engine.

## Q10. Tiered injection format vs cm's two-phase

**Correction: there is no `<memory_context>` XML block in the graph engine.** The prior review invented it. The v1 graph injection (`assembleContextBlock`, injection.ts:282-384) emits **Markdown sections**, not XML, not numbered tiers: `### Right Now`, `### Active Threads`, `### Skills You Can Use`, `### Upcoming`, `### What Today Means`, `### On My Mind`, `### Serendipity`. Routing into a section is by node type / trigger / recency (injection.ts:294-315), with per-section item caps (Right Now 3, Active Threads 5, Skills 5, Upcoming 5, etc.). Each entry is `- (${age}) ${content}` (injection.ts:264) with **full content inlined** — one-shot, not a snippet (the header comment claiming "1-2 sentence compression" is aspirational; injection.ts:142 confirms full content). The `<memory>` XML block is exclusively the **v2 concept-page / v3** path (`injector.ts`), a different engine. No token budget on text injection; the only enforced caps are image counts (3 context-load / 2 per-turn).

**cm comparison: cm's two-phase (snippet → `cx_get`) is the better default, and Vellum's own behavior is the cautionary tale.** Vellum inlines full content for 30-40 nodes every turn with no token budget (injection.ts:141 calls node count "the only limit") — that is a large, unbounded prompt cost, and they openly note it. cm's `cx_recall` returns metadata+snippet and defers full bodies to `cx_get`, with an explicit `max_tokens` budget (`recall.rs:113-132`, `apply_token_budget`). For an MCP store where the agent decides what to expand, cm's design is correct and should not change. The one idea worth borrowing is **type-based sectioning of the snippet list**: cm currently returns a flat depth-sorted list; grouping the snippets by kind (feedback first, then decisions, then facts...) in the projection would make the recall payload easier for the agent to scan, mirroring Vellum's section split — a presentation change, zero schema cost.

---

## Concrete cm changes ranked by leverage

Honest grading: cm is a keyword+scope store with a clean dedup story. Most of Vellum's machinery (vectors, emotional decay, fidelity, narrative) is autobiographical-memory scaffolding that does not belong in cm. The real wins are small and process-shaped.

1. **Shadow-canary for recall/ranking changes** — *what:* run old+new ranking on each `cx_recall`, serve old, log new + top-K diff behind a flag. *where:* `crates/cm-capabilities/src/recall.rs` (second sort + diff), log row into the existing `mutations`/telemetry path, surfaced in cm-web. *effort:* M. *why it beats today:* cm currently has no way to prove a ranking change is an improvement before shipping; this is the gate. *risk:* low (read-only shadow, never affects served result). **Highest leverage; adopt first, it de-risks #2-#3.**

2. **Read-time recency tiebreaker on recall** — *what:* multiply (or additively boost) the recall sort key by a recency factor on `updated_at`, e.g. `1 + k·recencyBoost(updated_at, halfLife)` using Vellum's linear `max(0, 1 - days/(2·halfLife))` (scoring.ts:143-151). *where:* `recall.rs` sort (currently scope-depth only, recall.rs:108) and/or the non-FTS store ORDER BY (already `updated_at DESC`, so the signal is half-present). *effort:* S. *why it beats today:* recall is "museum of greatest hits" with no recency awareness; a recently-touched decision should outrank a stale one of equal confidence. No new columns — `updated_at` exists. *risk:* low. Validate via #1.

3. **Use existing relations at retrieval time (bounded 1-hop expansion)** — *what:* when an entry matches, also surface entries it `supersedes`/`contradicts` (so the agent sees the live entry and what it overturned) and optionally 1-hop `elaborates`/`depends_on`, with a fixed per-hop score decay. *where:* `recall.rs` (add a relation join + spread; cm has `get_relations` on the store trait), projection to mark expanded entries. *effort:* M. *why it beats today:* cm stores rich relations and throws them away at read time; a contradicting entry surfacing alongside its target is high-signal for an agent. *risk:* medium (can balloon result size; cap hops at 1 and count). Optionally add an edge `weight` column (Q7) later for weighted spread.

4. **Duplicate-suggestion probe at `cx_store`** — *what:* before insert, FTS-probe the target scope for high-BM25 matches and return them as "possible duplicates," letting the agent choose supersede vs new. *where:* `cx_store` path in `cm-capabilities`. *effort:* S-M. *why it beats today:* BLAKE3 catches only exact dupes; near-duplicates accumulate silently because supersede requires the writer to already know the prior entry. Reuses existing FTS, no LLM. *risk:* low (advisory only).

5. **Numeric, decayable `significance` + reinforcement (the full Ebbinghaus port)** — *what:* add `significance REAL`, `stability REAL DEFAULT 14`, `reinforcement_count INT`, `last_reinforced` columns; on a duplicate-ish re-store, reinforce instead of insert (`stability *= 1.5`, `significance = min(1, significance*1.1)`, store.ts:594-612); rank by read-time `significance * exp(-days/stability)` (scoring.ts:55-63). *where:* new migration in `cm-store`, `EntryMeta` or first-class columns in `cm-core`, recall sort. *effort:* L. *why it beats today:* turns confidence from a static 3-level enum into a self-reinforcing signal — facts confirmed across sessions float up, one-off notes sink. *risk:* medium-high (schema migration, changes recall semantics, needs #1 to validate). **Real, but the heaviest; do only after #1-#2 prove the appetite.**

6. **Event-ramp recall for `expires_at`** — *what:* surface entries more strongly as their `meta.expires_at` approaches, then fade after, using Vellum's event curve (triggers.ts:186-213). *where:* recall sort, reading existing `meta.expires_at`. *effort:* S. *why it beats today:* `expires_at` is a binary cliff; a ramp is deadline-aware. *risk:* low. Niche; only if deadline-aware recall is wanted.

**Do NOT borrow:** emotional charge / decay curves (Q3, no domain referent), the fidelity ladder (Q3, presumes LLM prose rewriting cm doesn't do), Qdrant/vector hybrid retrieval (cm is deliberately keyword+scope; a vector store is a different product, not a recall tweak), full-content unbounded injection (cm's two-phase snippet→`cx_get` with `max_tokens` is already better, Q10), `caused-by`/narrative edges (out of domain), temporal/semantic triggers (no time-of-day or NL-condition concept in cm).

### Which of the prior review's §9 borrows do NOT survive deeper scrutiny

- **§9.2 "`scope_id` validates cm's design"** — survives, but as *reassurance only*. cm's hierarchical `scope_path` is strictly more expressive than Vellum's flat `scope_id`; there is nothing to adopt. Net: confirmation, not a borrow.
- **§9.3 "borrow multi-signal recall scoring (decay + recency + trigger + activation)"** — *partially does not survive as stated.* The full seven-signal model is over-built for cm: emotional intensity and temporal/time-of-day boosts have no cm referent, and trigger/activation need infrastructure cm lacks. What survives is the **read-time recency factor (#2)** and, with work, **read-time significance decay (#5)** — two of seven signals, not the model. The prompt's `tier-1>0.8` and `stability*(1+0.3*(r-1))` details that motivated this borrow are both factually wrong (Q1, Q2).
- **§9.4 "hybrid dense+sparse RRF + local-ONNX embeddings → cm if it ever embeds"** — *does not survive for cm.* cm is a keyword+scope store by design; bolting on Qdrant/embeddings is a new product, not a recall improvement, and would undercut cm's cheap-deterministic posture. Correctly belongs to knowledge-matters, not cm. Cargo-culting risk flagged.
- **§9.9 "shadow-plugin canary for cm migrations"** — *survives, strongest of the four, and is now #1.* The mechanism is fully traced (Q9) and lands cleanly on cm's existing `mutations`/cm-web infrastructure.

## Sources consulted

- Scoring/decay (read in full): `assistant/src/memory/graph/scoring.ts:1-262`, `decay.ts:1-195`, `types.ts:1-296`.
- Retrieval pipeline, injection, triggers, extraction/store, schema, shadow plugin (bounded subagent reads, file:line verified): `retriever.ts` (entry points 419, 921; tier1Count 437/847/936/1344; thresholds 1265/1257/1267; weight selection 679/767/1211), `injection.ts` (282-384 sections, 264 entry format, 141-143 full-content), `triggers.ts` (27-213), `extraction.ts` (224-234 diff, 666/1413-1462 dedup candidates, 1116-1146 deferred), `store.ts` (594-612/796-806 reinforce, 663-863 transaction, 129-172 intra-content dedup), `migrations/202-memory-graph-tables.ts`, `migrations/189-drop-simplified-memory.ts:13-41`, `plugins/defaults/memory-v3-shadow/{shadow-plugin.ts:69-70,527,601, injector.ts:240-252}`, `config/assistant-feature-flags.ts:285-299`, `config/schemas/memory-v2.ts:49-54`.
- cm mapping target (this repo): `crates/cm-store/migrations/001_initial_schema.sql`, `005_mutations.sql`, `crates/cm-core/src/types/entry.rs:68-146`, `relation.rs:16-35`, `crates/cm-capabilities/src/recall.rs:100-170`, `crates/cm-store/src/sqlite/query.rs:69-135`.

## Corrections to prior artifacts

- **Prompt:** reinforcement is `stability * 1.5` (geometric) + `significance * min(1.0, *1.1)`, NOT `stability * (1 + 0.3*(reinforcement-1))` (store.ts:594-612). `tier-1 > 0.8` does not exist; `tier1Count` is hardcoded 0 (retriever.ts:437 etc.). Migration 189 dropped simplified-memory-v1 tables, not a fingerprint-dedup table.
- **Prior review (`vellum-ai-vellum-assistant.md`):** the `<memory_context>` XML block is invented; graph injection is Markdown `###` sections (injection.ts:326-379). The `<memory>` XML block belongs to the v2/v3 concept-page engine, not the main graph. The "Ebbinghaus `stability*(1+0.3*(reinforcement-1))`" formula in §5 is wrong (same correction as above).

## Open questions

- Does cm have appetite for any schema growth on `entries`, or is the recall improvement constrained to read-time-only (no new columns)? Determines whether #5 is on the table at all.
- cm's actual recall ORDER BY for the non-FTS path is `updated_at DESC` at the store layer then scope-depth re-sort in recall.rs — is the documented "ranks by kind/confidence/priority" actually wired anywhere, or aspirational? (I found no confidence/priority term in the SQL ORDER BY; worth a cm-side audit before #2 so recency stacks on the real current behavior.)
