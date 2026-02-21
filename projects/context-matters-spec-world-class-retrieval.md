---
title: cx_* world-class retrieval spec
type: project-spec
tags: [context-matters, cx_recall, cx_browse, fts5, bm25, mcp, projection, cm-web, benchmarks]
summary: Follow-on work to ALP-1725 that moves cx_* from structurally correct YAML rendering to retrieval excellence. Query robustness, match highlighting, surface parity, result enrichment, protocol upgrade, bench infra.
status: active
source: claude-code
confidence: high
created: 2026-04-11
updated: 2026-04-11
parent_issue: (to be created)
predecessor: ALP-1725
predecessor_doc: ~/.mdx/research/cx-response-payload-redesign-context-matters.md
---

# cx_* world-class retrieval

## Context

ALP-1725 shipped a YAML-projected response layer for every `cx_*` read and write tool (commit `859bc11`, released as `0.2.0`). All 16 acceptance criteria are done: BM25 normalised scores, smart snippets that strip YAML frontmatter, per-tool projected views (`browse_view`, `recall_view`, `get_view`, `stats_view`, `write_ack`), 16 KB response cap with newline-boundary clip, short ids with collision extension, relative ages, `missing: [ids]` on `cx_get`, real indented `scope_tree` on `cx_stats`, and a payload-size regression test (`crates/cm-cli/tests/payload_size_test.rs`) that locks in the 14.9 KB → <6 KB empirical win.

What ALP-1725 did **not** cover, and what this spec continues:

- `cx_recall` still fails on natural-language queries because FTS5 uses implicit AND. The ALP-1725 work improved the *rendering* of zero-result responses but not the *retrieval* path.
- Query-term matches are centred in smart snippets but not visibly marked, so a reader cannot tell at a glance why a row ranked.
- `cm-web` (the Curator/Monitor UI) bypasses the new projection layer entirely. `api/entries.rs` still returns raw `PagedResult<Entry>` JSON. The MCP surface and the web surface now show different mental models of the same data.
- Research doc §3.2 punted on dedup hints and relation-count annotations as "less urgent." They are the next class of row-level signal worth surfacing.
- Research doc §6.1 explicitly deferred the MCP 2025-06-18 `structuredContent` / `outputSchema` path. It is the "most correct" protocol move and now makes sense to plan.
- The payload-size test is one bench; real perf infra around `smart_snippet`, `normalise_bm25`, and the hoisting reductions does not exist.

## Locked decisions

1. **Single parent, granular sub-issues.** 1-level workflow. All work is backend-engineer territory (one small cm-web frontend touch). No role parents.
2. **FTS5 query robustness lives in `cm-core/src/query.rs` + `cm-capabilities/src/recall.rs`, not the store.** `cm-store` stays thin; query-rewrite/fallback logic is a capability concern.
3. **Tiered fallback order for natural-language queries**: exact → prefix → split-OR. No trigram/fuzzy layer yet (deferred as post-follow-on). Each tier is tried in order; the first non-empty result set wins. The rendered response notes which tier was used.
4. **Highlighting uses `«term»` YAML-safe brackets**, applied only in `Search`-routed recall, never in browse. No markdown bold, no ANSI. Both sides of the bracket are ASCII so any renderer can read it.
5. **cm-web parity is achieved by having `api/entries.rs` delegate to the same projection views the MCP adapter uses.** The frontend already handles JSON rows; we keep JSON on the HTTP wire but inject the projection fields (short_id, smart_snippet, age, aggregates). No YAML-text envelope on the web surface.
6. **Dedup detection is a post-fetch pass** over the result set that compares `content_hash` prefixes (first 16 hex chars). No index, no cross-query persistence. Flags duplicates within a single recall/browse response only.
7. **Relation counts use a single batch query** (`SELECT entry_id, COUNT(*) FROM entry_relations WHERE entry_id IN (...)`) run once per response, never per row. Zero N+1.
8. **Faceted drill-down hints** surface only when a dominant kind or tag covers ≥60% of a multi-kind result set. Below that threshold, no hint.
9. **MCP 2025-06-18 upgrade keeps text rendering as the primary channel**; `structuredContent` is emitted as a sibling with per-tool `outputSchema`. No removal of the YAML text. Dual-channel for one release cycle, then the text channel can shrink if structured adoption proves out.
10. **Benchmarks use `criterion`**, live in `crates/cm-capabilities/benches/`, and run against in-memory fixtures. No DB, no IO. Targets: `smart_snippet`, `normalise_bm25`, `hoist_uniform`, `compute_histograms`, end-to-end `format_browse_view` / `format_recall_view`.
11. **Breaking wire changes are allowed for `cx_*` MCP consumers** because Stuart owns every known caller and the LLM-facing side adapts automatically. Breaking HTTP changes on `cm-web` must be coordinated with the frontend in the same PR.
12. **Nothing in this spec bumps `cm-cli` to 1.0.** Each natural grouping ships as a minor bump (`0.3.0`, `0.4.0`, ...) via release-please and `feat:` / `feat!:` conventional commits.

---

## Section 1 — Query robustness

### Problem

`crates/cm-core/src/query.rs::FtsQuery::new` sanitises input into a space-joined token list. SQLite FTS5 treats space-joined tokens as implicit AND. A natural-language query like `"context-matters recent work"` becomes `context matters recent work` and demands all four terms appear in one entry, which almost never happens. The tool docs warn against this, the inline zero-result hint warns against it, but the underlying retrieval path never tries a fallback. An LLM caller that ignores the warning (or a fresh session that has not yet learned) burns a round trip and gets zero results.

The relevant call chain:

- `cm_cli::mcp::tools::recall` → `cm_capabilities::recall::recall` → `store.search(query, scope, limit)`
- `cm_store::sqlite::query::do_search` → `FtsQuery::new(query).as_str()` → SQLite FTS5 `MATCH` → `ScoredEntry` rows

### Decision

Introduce a tiered search strategy inside `cm-capabilities::recall::recall`. The capability layer is the right home because `cm-store` is intentionally thin and `cm-core` owns the sanitiser but not the retry loop.

Tier order:

1. **Exact tier** — current behaviour. `FtsQuery::new(user_query)` → AND semantics. If result count > 0, return.
2. **Prefix tier** — `FtsQuery::prefix_query(user_query)` (already exists in `cm-core`). Appends `*` to each token, which FTS5 treats as prefix-match. Catches `rust*` matching `rustaceans`, `routi*` matching `routing`, and gives AND semantics with looser token matches. If result count > 0, return.
3. **Split-OR tier** — rewrite the sanitised tokens as `token1 OR token2 OR token3 ...`, deduplicated, max 8 terms (FTS5 query plan cost). Returns entries that match any one term. Recovers the "I typed a sentence" case where exactly one word is the real signal.

Each tier records its name in a new `SearchTier` enum on `RecallResult`:

```rust
pub enum SearchTier {
    Exact,         // FTS5 implicit AND
    Prefix,        // FTS5 prefix match
    SplitOr,       // OR-joined tokens
    None,          // no tier hit — true zero-result
}
```

The rendered recall response advertises the tier in its header:

```
---
query: context-matters recent work
routing: search  # FTS5 ranking, tier: prefix
candidates: 12 -> 12 shown
...
```

When the tier is not `Exact`, a trailing advisory teaches the caller about the rewrite:

```
# tier: prefix — original query had zero exact hits, tried prefix match
# tier: split-or — original query had zero prefix hits, OR-joined tokens
```

When all three tiers fall to zero, the routing stays `Search` and tier is `None`; the existing zero-result hint applies.

### Files touched

- `crates/cm-core/src/query.rs` — add `split_or_query(input: &str) -> FtsQuery`, extend unit tests
- `crates/cm-capabilities/src/recall.rs` — introduce `SearchTier` enum, wire tier cascade, add `tier: Option<SearchTier>` field to `RecallResult`
- `crates/cm-capabilities/src/projection/recall_view.rs` — render tier in header, emit tier advisory when non-exact
- `crates/cm-capabilities/tests/recall_tests.rs` — new cases: multi-word natural-language query → prefix tier → hits; single-word exact → exact tier; gibberish → all three tiers exhausted → tier=None
- `crates/cm-capabilities/tests/recall_format_tests.rs` — snapshot tier in header and advisory

### Acceptance criteria

- [ ] `SearchTier::{Exact, Prefix, SplitOr, None}` enum exists in `cm-capabilities::recall`
- [ ] `recall::recall` runs Exact → Prefix → SplitOr in order, stops at first non-empty
- [ ] `RecallResult` carries `tier: Option<SearchTier>` populated only on `Search` routing
- [ ] Recall YAML header includes `tier: <name>` when routing is `Search`
- [ ] Non-exact tiers emit a trailing `# tier: ... — original query had zero ...` advisory
- [ ] Unit test: `"context-matters recent work"` at an empty-for-exact store returns prefix hits
- [ ] Unit test: single-word exact query still uses Exact tier
- [ ] Unit test: all-gibberish query yields tier=None, routing=Search, zero results, existing zero-result hint still fires
- [ ] Snapshot test updated for the tier advisory line

### Out of scope

- Trigram/fuzzy similarity as a fourth tier (deferred; `sqlite-vec` or `simsimd` adds a dep that needs its own decision)
- Query-rewrite driven by an LLM
- Cross-query tier statistics / telemetry

---

## Section 2 — Query-match highlighting

### Problem

`smart_snippet` in `projection/text.rs` centres the snippet window on the first query-term match. The match position drives the window but is never surfaced to the reader. An LLM that sees a 200-byte snippet cannot tell which substring the FTS ranker actually matched — it has to re-scan the snippet for any of the query terms.

### Decision

Extend `smart_snippet` to accept a highlight style:

```rust
pub enum HighlightStyle {
    None,                 // used by browse (no query context)
    Bracketed,            // used by recall — wraps matches in «term»
}
```

The `«` and `»` characters are Unicode U+00AB / U+00BB, YAML-safe, single-width, and distinct from any character in a typical code or prose body. They do not conflict with YAML quoting, markdown emphasis, or JSON escape sequences.

`smart_snippet(body, query, style, max_bytes)`:

1. Compute the snippet window as today.
2. If `style == Bracketed` and `query.is_some()`, tokenize the query using the same splitter that `first_query_match_position` already uses.
3. For each matched token, do a case-insensitive walk over the snippet window and insert `«` / `»` around each occurrence. Preserve the original casing of the body.
4. Budget: bracket insertions count against the snippet byte cap. If insertions would overflow `max_bytes`, start trimming from the right of the original window until the bracketed result fits. Never trim brackets themselves.

Only `recall_view` invokes `Bracketed`. `browse_view` passes `HighlightStyle::None`. `get_view` does not use snippets at all (it renders full bodies).

### Files touched

- `crates/cm-capabilities/src/projection/text.rs` — new `HighlightStyle` enum, extend `smart_snippet` signature, add `insert_highlights` helper
- `crates/cm-capabilities/src/projection/recall_view.rs` — pass `HighlightStyle::Bracketed` and propagate query terms
- `crates/cm-capabilities/src/projection/browse_view.rs` — pass `HighlightStyle::None` (no-op at call site)
- `crates/cm-capabilities/tests/recall_format_tests.rs` — snapshot a bracketed snippet
- `crates/cm-capabilities/tests/recall_tests.rs` — unit cases: single token match, multi-token match, no match (no brackets emitted), overflow budget (original snippet shrinks to fit brackets)

### Acceptance criteria

- [ ] `HighlightStyle::{None, Bracketed}` enum exists
- [ ] `smart_snippet` accepts `HighlightStyle` parameter
- [ ] Recall snippets wrap FTS query matches in `«...»` brackets
- [ ] Browse snippets contain no brackets
- [ ] Snippet byte budget still honoured after bracket insertion (integration test)
- [ ] Case-insensitive match, case-preserving body rendering
- [ ] Unit test: multi-occurrence match gets every occurrence bracketed
- [ ] Unit test: zero-match tokens produce no brackets (no crash, no spurious insertions)

### Out of scope

- Markdown bold / italic / ANSI colour
- Per-term different bracket styles
- Highlighting in full `cx_get` bodies (only snippets)

---

## Section 3 — cm-web surface parity

### Problem

`crates/cm-web/src/api/entries.rs` returns raw `PagedResult<Entry>` and `RecallResponse { results: Vec<RecallEntryView>, ... }` JSON. The web UI shows a different view of the same data than the MCP tools: no short ids, no smart snippets, no relative ages, no aggregate hints, no hoisted uniforms. A user who uses both the Claude Code MCP tools and the cm-web Curator sees two visually different mental models of the store.

### Decision

Introduce a `WebView` projection that mirrors the MCP projection output at the data level but serialises as JSON instead of YAML text. The frontend keeps consuming JSON; what it consumes becomes structurally identical to what the MCP projection produces.

New structs in `cm-capabilities/src/projection/web_view.rs`:

```rust
pub struct WebBrowseView {
    pub header: WebBrowseHeader,       // hoisted uniforms, sort, aggregates
    pub entries: Vec<WebBrowseRow>,     // short_id, title, smart_snippet, age, tags, scope (when not hoisted)
    pub pagination: WebPagination,
}

pub struct WebRecallView {
    pub header: WebRecallHeader,       // routing, tier, candidates, scope_chain, scope_hits, kinds, tags
    pub entries: Vec<WebRecallRow>,     // short_id, score, title, smart_snippet (bracketed), age
    pub advisories: Vec<String>,        // tier hint, truncation hint, etc.
}
```

The HTTP handlers (`browse`, `search`, `recall`) switch from `Json<PagedResult<Entry>>` to `Json<WebBrowseView>` / `Json<WebRecallView>`.

The existing frontend TypeScript types are regenerated via `ts-rs` (already set up in `cm-capabilities`). The frontend components that render rows get updated to consume the new shape.

### Files touched

- `crates/cm-capabilities/src/projection/web_view.rs` — new module
- `crates/cm-capabilities/src/projection/mod.rs` — re-export `WebBrowseView`, `WebRecallView`
- `crates/cm-web/src/api/entries.rs` — swap handler return types, delegate to `project_web_browse` / `project_web_recall`
- `crates/cm-web/frontend/src/api/types.ts` — regenerated from `ts-rs`
- `crates/cm-web/frontend/src/components/EntryList/*` — consume the new shape
- `crates/cm-web/tests/parity.rs` — new integration test asserting that for a fixed fixture store, the web projection and the MCP projection produce structurally equivalent row data (same short_ids, same snippets, same ages, same hoist decisions)

### Acceptance criteria

- [ ] `WebBrowseView` and `WebRecallView` exist in `cm-capabilities::projection`
- [ ] `ts-rs` generates matching TypeScript types
- [ ] `/api/entries` (browse), `/api/entries/search`, `/api/entries/recall` return the new shape
- [ ] Frontend renders short ids, smart snippets, relative ages, hoisted header constants
- [ ] Frontend displays `«...»` query-match highlights on recall rows (decide rendering: bracket visible or styled span)
- [ ] `crates/cm-web/tests/parity.rs` asserts MCP-vs-web row equivalence
- [ ] `just check && just test` green, including frontend `tsc -b --noEmit`

### Out of scope

- Rewriting the cm-web UI beyond row/list components (no dashboard redesign, no new pages)
- Moving the HTTP wire to YAML text (JSON stays)
- Deprecating any existing HTTP endpoints

---

## Section 4 — Result enrichment

This is one parent section covering three related row/aggregate annotations. Each is small on its own; grouped here because they share the same projection touch points.

### 4.1 Dedup hints via content_hash

**Problem.** Research doc §3.2 #9: "I stored the same lesson three times" is a known pattern. The store has BLAKE3 content hashes and they are deterministic, but the projection never surfaces duplicates.

**Decision.** In the recall and browse view builders, after the entries are fetched and projected but before rendering, run a single pass that indexes rows by the first 16 hex chars of `content_hash` and flags any row whose hash prefix collides with an earlier row in the same result set. Flagged rows get a `dup_of: <short_id>` field in their trailing comment. The leader (first occurrence) is unmarked.

**Files touched.**

- `crates/cm-capabilities/src/projection/aggregation.rs` — new `compute_dedup_hints(rows: &[ProjectedRow]) -> HashMap<EntryId, EntryId>` helper
- `crates/cm-capabilities/src/projection/recall_view.rs` + `browse_view.rs` — call the helper, thread dup-of into row formatting
- `crates/cm-capabilities/src/projection/text.rs` — extend the trailing comment format to include `dup-of: <short>` when present

**Acceptance criteria.**

- [ ] Within a single browse or recall response, duplicate `content_hash` rows carry a `dup_of: <short_id>` annotation
- [ ] The first occurrence (lowest row index) is the unmarked leader
- [ ] Cross-response dedup is not attempted (explicitly single-response scope)
- [ ] Unit test: three rows with same hash → rows 2 and 3 carry `dup_of`, row 1 is clean

### 4.2 Relation-count annotations

**Problem.** Research doc §3.2 #10: entries with `EntryRelation::Elaborates` edges are more load-bearing than orphans. The projection never surfaces the edge count.

**Decision.** Add a single batch query that aggregates relation counts for the set of entry ids in a response:

```sql
SELECT from_id, COUNT(*) FROM entry_relations
WHERE from_id IN (?, ?, ?, ...)
GROUP BY from_id
```

One query per projection call, populated into a `HashMap<EntryId, u32>`. Rows with non-zero counts get `rels: N` in their trailing comment.

**Files touched.**

- `crates/cm-core/src/store.rs` — new `count_relations_for(ids: &[Uuid]) -> HashMap<Uuid, u32>` trait method
- `crates/cm-store/src/sqlite/query.rs` — implementation
- `crates/cm-capabilities/src/recall.rs` + `browse.rs` — call the new method after fetching
- `crates/cm-capabilities/src/projection/{recall_view, browse_view}.rs` — thread relation count into row formatting
- `crates/cm-cli/src/mcp/tools/*.rs` — no changes (projection absorbs it)

**Acceptance criteria.**

- [ ] `ContextStore::count_relations_for` trait method exists and is implemented on `CmStore`
- [ ] At most one relation-count query per response, regardless of row count
- [ ] Rows with relations render `rels: N` in trailing comment; rows with zero relations omit it
- [ ] Unit test: fixture with deposited exchanges carries `rels: N` on the summary row

### 4.3 Faceted drill-down hints

**Problem.** A caller gets a 20-row recall with 12 session-log entries and 8 decisions but has no instant signal that narrowing by `kinds=[decision]` would fit their actual need. The aggregates are already in the header; the drill-down suggestion is not.

**Decision.** After computing `kinds` and `tags` histograms for the header, check the dominance threshold (≥60% of the returned slice). If one kind or tag dominates, emit a trailing advisory:

```
# narrow: cx_recall(query="...", kinds=["decision"]) — 12 of 20 results are session-log
```

The threshold is configurable via a `const DRILL_DOWN_THRESHOLD: f32 = 0.60` in the projection module.

**Files touched.**

- `crates/cm-capabilities/src/projection/aggregation.rs` — new `compute_drill_down_hint(counts: &HashMap<_,_>, total: usize) -> Option<DrillDownHint>`
- `crates/cm-capabilities/src/projection/recall_view.rs` — render the advisory when present
- `crates/cm-capabilities/src/projection/browse_view.rs` — same for browse (where `tag=` filter is already applied, so the drill-down is usually kind-dominance)

**Acceptance criteria.**

- [ ] `compute_drill_down_hint` returns Some only when one kind or tag ≥60% of total
- [ ] Advisory renders with the exact tool call to narrow
- [ ] Unit test: 12/20 one-kind → hint; 5/20 → no hint; 1/20 → no hint
- [ ] Snapshot test: recall response with dominant kind emits hint

### Out of scope for section 4

- Cross-response dedup (requires persistence layer)
- Similarity-based dedup (content_hash only; no near-duplicate detection)
- Relation-type filtering on the count (all relation kinds counted together)
- Multi-dominance hints (one hint per response max)

---

## Section 5 — MCP 2025-06-18 protocol upgrade

### Problem

Research doc §6.1 explicitly deferred the move from `2024-11-05` to `2025-06-18`. The newer version supports `structuredContent` as a sibling to `content`, and `outputSchema` on every tool. The YAML text we emit today lives entirely in `content[0].text`; a caller that wants machine-parseable structure has to parse YAML.

### Decision

Dual-channel output for one release cycle:

1. Bump `PROTOCOL_VERSION` in `crates/cm-cli/src/mcp/mod.rs:29` from `"2024-11-05"` to `"2025-06-18"`.
2. Declare an `outputSchema` for every `cx_*` tool in `crates/cm-cli/src/mcp/schema.rs`. Schemas are JSON Schema for the *structured* representation of each view, derived from `ts-rs` or hand-written.
3. Build the `CallToolResult` with both `content` (unchanged — YAML text) and `structuredContent` (new — the JSON structural form of the same data).
4. `structuredContent` goes through a *separate* projection path that emits a `serde_json::Value` matching the declared schema. This is effectively the `WebBrowseView` / `WebRecallView` shape from section 3, reused.
5. `cx_export` emits `structuredContent` but no text (the JSON *is* the canonical output for export).

The text channel remains the default for LLM consumption (fmm parity, zero-escape win preserved). The structured channel exists for any future consumer that wants JSON-schema-verified data without parsing YAML.

### Interaction with section 3

Section 3 adds `WebBrowseView` / `WebRecallView` structs for the HTTP API. Section 5 reuses the *same* structs for MCP `structuredContent`. The section-3 work creates the data types; the section-5 work wires them into the MCP envelope. Implementation order: section 3 first, then section 5.

### Files touched

- `crates/cm-cli/src/mcp/mod.rs` — protocol version bump, envelope construction with `structuredContent`
- `crates/cm-cli/src/mcp/schema.rs` — per-tool `outputSchema` declarations
- `crates/cm-cli/src/mcp/tools/*.rs` — each read tool emits both text and structured projections
- `crates/cm-cli/tests/mcp_protocol_test.rs` — assert `initialize` response advertises `2025-06-18` and every tool in `tools/list` carries an `outputSchema`
- `crates/cm-cli/tests/response_wire_tests.rs` — snapshot a dual-channel response for `cx_browse`, `cx_recall`, `cx_get`, `cx_stats`

### Acceptance criteria

- [ ] `PROTOCOL_VERSION = "2025-06-18"` in `mcp/mod.rs`
- [ ] Every `cx_*` tool declares a JSON Schema `outputSchema` in `tools/list`
- [ ] Read-tool responses contain both `content[0].text` (YAML) and `structuredContent` (JSON)
- [ ] `structuredContent` shape exactly matches the declared `outputSchema` (runtime validation in tests)
- [ ] `cx_export` emits `structuredContent` and an empty `content` array
- [ ] `cx_store`, `cx_deposit`, `cx_update`, `cx_forget` stay text-only (no structured needed for write acks)
- [ ] Integration test: real LLM-style caller can parse `structuredContent` without YAML parsing
- [ ] `just check && just test` green
- [ ] No backwards-compat flag — clean break at the protocol layer

### Risk and fallback

If the structured channel turns out to be unused in practice (Claude Code continues to read the text), the `outputSchema` declarations still serve as documentation and cost nothing at runtime. Zero-risk addition, even if no caller consumes it yet.

### Out of scope

- `inputSchema` refinement (already exists, works fine)
- Streaming tool output (MCP supports it in 2025-06-18, not needed here)
- Notification/progress updates during long tool calls

---

## Section 6 — Performance benchmarks

### Problem

The payload-size regression test (`crates/cm-cli/tests/payload_size_test.rs`) locks in the wire-bytes win. There is no coverage on the *compute* side: if `smart_snippet` silently regresses from O(n) to O(n²), no test fails until someone notices the MCP tool feeling slow.

### Decision

Introduce `criterion` benchmarks in `crates/cm-capabilities/benches/`. All benches run against in-memory fixtures, no DB, no IO. Targets:

1. `smart_snippet_bench.rs` — three cases: no frontmatter, short YAML frontmatter, long YAML frontmatter. Measures the hot path from the projection layer.
2. `normalise_bm25_bench.rs` — one case: 20 raw BM25 scores, normalised once. Cheap but exercises the float path.
3. `aggregation_bench.rs` — `compute_histograms`, `compute_dedup_hints`, `compute_drill_down_hint` against 20-row and 200-row fixtures.
4. `format_views_bench.rs` — end-to-end `format_browse_view` and `format_recall_view` with 20-row fixtures. Captures the "total time to format" number that anyone debugging slowness actually cares about.

Results land in `target/criterion/`. A CI-time check is out of scope for this spec (benches run on demand).

### Files touched

- `crates/cm-capabilities/Cargo.toml` — add `criterion = { version = "0.5", features = ["html_reports"] }` as a dev-dependency, declare `[[bench]]` entries
- `crates/cm-capabilities/benches/smart_snippet_bench.rs`
- `crates/cm-capabilities/benches/normalise_bm25_bench.rs`
- `crates/cm-capabilities/benches/aggregation_bench.rs`
- `crates/cm-capabilities/benches/format_views_bench.rs`
- `justfile` — new `just bench` recipe that runs all `cm-capabilities` benches

### Acceptance criteria

- [ ] `cargo bench -p cm-capabilities` runs all four benchmark files successfully
- [ ] `just bench` recipe exists and delegates
- [ ] Each benchmark file has at least one `criterion_group!` + `criterion_main!`
- [ ] Benchmarks use deterministic fixtures (no `rand`, no wall clock)
- [ ] README.md in `crates/cm-capabilities/benches/` documents baseline numbers as of the introducing commit

### Out of scope

- CI-time regression gating on bench numbers (future work; flaky without dedicated hardware)
- Memory allocation profiling (requires `dhat` or `heaptrack`; separate concern)
- Compare-against-master tooling (out of scope)

---

## Dependency graph between sections

```
[1] Query robustness         ── independent, ships first
[2] Match highlighting       ── depends on [1] for tier-aware query terms
[3] cm-web surface parity    ── independent, shares types with [5]
[4] Result enrichment        ── independent, touches projection
[5] MCP 2025-06-18           ── depends on [3] for shared view types
[6] Benchmarks               ── independent, but most useful after [1][2][4]
```

Suggested execution order for Nancy (if autonomous execution is planned): 1 → 2 → 4 → 3 → 5 → 6. Each section is small enough to complete in one or two sub-issues' worth of work per module it touches.

## Appendix A — verification checklist per section

| Section | `just check` | `just test` | Manual verify |
|---|---|---|---|
| 1 Query robustness | required | required | recall a natural-language query, observe prefix tier firing |
| 2 Match highlighting | required | required | recall a search, observe `«term»` in snippet |
| 3 cm-web parity | required | required | open cm-web UI, verify short ids + snippets + ages render |
| 4.1 Dedup | required | required | store two entries with identical bodies, recall, verify `dup_of:` |
| 4.2 Relation counts | required | required | deposit exchanges, recall, verify `rels: N` |
| 4.3 Drill-down | required | required | recall with dominant kind, verify advisory |
| 5 Protocol upgrade | required | required | inspect `tools/list` JSON-RPC, verify `outputSchema` |
| 6 Benchmarks | n/a | `cargo bench` | inspect `target/criterion/report/index.html` |

## Appendix B — predecessor reference

Full context for the ALP-1725 baseline redesign:

`~/.mdx/research/cx-response-payload-redesign-context-matters.md`

Key sections relevant to this follow-on:

- §3.1 — intelligence gaps (covered: BM25, routing, histograms, snippets, two-phase hints)
- §3.2 — "less urgent but worth considering" (this spec pulls #9 dedup and #10 relations forward)
- §6.1 — wire format open question (this spec takes the 2025-06-18 path)
- §6.7 — smart snippet aggressiveness (this spec extends with highlighting)
