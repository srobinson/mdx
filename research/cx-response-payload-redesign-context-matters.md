---
title: cx_* MCP response payload audit and redesign proposal
type: research
tags: [context-matters, mcp, protocol, cx_browse, cx_recall, payload, tokens, fmm, projection]
summary: Audits every cx_* MCP response shape, quantifies the JSON-in-text bloat, and proposes a fmm-style YAML projection with intelligence layers (relevance, smart snippets, result aggregates).
status: active
source: codebase-analyst
confidence: high
created: 2026-04-11
updated: 2026-04-11
---

# cx_* MCP response payload audit and redesign proposal

## Executive summary

Every `cx_*` tool response in context-matters is built by `serde_json::to_string_pretty` on a `serde_json::Value` tree and then stuffed into an MCP `content: [{type: "text", text: ...}]` envelope. The pretty-printed JSON is then re-escaped by the outer JSON-RPC encoder, which is where the double-quote storm comes from in Stuart's observed `cx_browse` payload. Field names are spelled out verbosely, nulls are emitted, `created_at` and `updated_at` both appear on every row with full ISO 8601 precision, `created_by` and `scope_path` repeat per row, and snippets are a naive byte-truncation of whatever happens to sit at the front of `entry.body` — which, for session logs and other YAML-fronted entries, is mechanical frontmatter.

The response is also dumb. It is a flat array of rows with a pagination blob. No relevance score, no per-scope or per-tag histogram across the result set (except the one that `cx_recall` happens to expose), no cross-entry grouping, no two-phase hints, no highlighting of which query term matched where, and no tier-by-budget fallback. `cx_browse` does not even carry the sort key that determined ordering.

`fmm`, by contrast, renders pre-formatted YAML text inside the same MCP text envelope. Short field names, column-aligned tables, grouped sections (`EXPORTS`, `FILES`, `IMPORTS`, `NAMED IMPORTS`), inline `# loc: N, exports: M` annotations in YAML comments, truncation notices with suggested next actions, and a hard 10 KB cap that clips mid-line at the nearest newline. The entire fmm design philosophy is: render in-place, omit defaults, hoist constants, and make the response readable to a model as if it were a terminal session.

This doc proposes that context-matters adopt the same rendering strategy: replace `json_response` with a `yaml_view` layer in `cm-capabilities/projection.rs`, introduce real relevance scoring + result-set aggregates in `cm-capabilities/recall.rs`, and generate snippets that skip YAML frontmatter and match around query terms. The wire format stays inside the 2024-11-05 `content: [text]` envelope — no `structuredContent`, no protocol bump — but the bytes shrink by a conservatively-estimated 55-70% on representative browse and recall payloads and the information density goes up.

---

## 1. Inventory of current cx_* response shapes

All response construction flows through `crates/cm-cli/src/shared.rs`:

- `json_response(value)` (`crates/cm-cli/src/shared.rs:8`) — `serde_json::to_string_pretty(&value)`.
- `entry_to_browse_json(entry)` — delegates to `project_browse_entry` (`crates/cm-capabilities/src/projection.rs:132`).
- `entry_to_recall_json(entry)` — delegates to `project_recall_entry` (`crates/cm-capabilities/src/projection.rs:113`).
- `entry_to_full_json(entry)` — delegates to `project_full_entry` (`crates/cm-capabilities/src/projection.rs:148`).

The text is then placed into the MCP envelope at `crates/cm-cli/src/mcp/mod.rs:254-266`:

```rust
Ok(value) => Ok(json!({
    "content": [{"type": "text", "text": value}]
})),
```

No tool declares `outputSchema`, so the MCP client never expects or parses `structuredContent`. See §2 for why this matters.

Per-tool field inventory below. File references are `file:line` for the outermost `json!` call that actually shapes the response.

### 1.1 `cx_browse` — `crates/cm-cli/src/mcp/tools/browse.rs:79-84`

```json
{
  "entries": [BrowseEntryView],
  "total": u64,
  "next_cursor": Option<String>,
  "has_more": bool
}
```

`BrowseEntryView` (`crates/cm-capabilities/src/projection.rs:61-73`) — every field **always present**, even when null or empty:

| Field             | Type              | Notes                                                              |
| ----------------- | ----------------- | ------------------------------------------------------------------ |
| `id`              | `String` (UUID v7) | 36 chars hyphenated, always present                                 |
| `scope_path`      | `String`          | Always present, high repetition (e.g. `global` on every row)        |
| `kind`            | `String`          | Always present                                                      |
| `title`           | `String`          | Always present                                                      |
| `snippet`         | `String`          | Always present, `SNIPPET_LENGTH = 200` bytes prefix of `entry.body` |
| `created_by`      | `String`          | Always present, almost always `agent:claude-code`                   |
| `created_at`      | `String` (RFC 3339)| Always present, 29-33 chars incl. ms + tz offset                    |
| `updated_at`      | `String` (RFC 3339)| Always present, typically identical to `created_at`                 |
| `superseded_by`   | `Option<String>`  | `None` serialised as `"superseded_by": null` (bytes with no info)   |
| `tags`            | `Vec<String>`     | `skip_serializing_if = "Vec::is_empty"` — omitted when empty        |

**Gap**: the sort key actually used for ordering (`BrowseSort` default from `cm-core/src/types.rs:669`) is not echoed in the response. A consumer cannot tell whether the list is ordered by `created_at DESC`, `updated_at DESC`, or something else.

### 1.2 `cx_recall` — `crates/cm-cli/src/mcp/tools/recall.rs:107-116`

```json
{
  "results": [RecallEntryView],
  "returned": usize,
  "scope_chain": [String],
  "scope_hits": { "<scope>": N, ... },
  "hint": Option<String>   // only when results.is_empty() and query has > 3 words
}
```

`RecallEntryView` (`crates/cm-capabilities/src/projection.rs:43-57`):

| Field             | Type              | Notes                                                              |
| ----------------- | ----------------- | ------------------------------------------------------------------ |
| `id`              | `String`          | Always present                                                      |
| `scope_path`      | `String`          | Always present                                                      |
| `kind`            | `String`          | Always present                                                      |
| `title`           | `String`          | Always present                                                      |
| `snippet`         | `String`          | Always present                                                      |
| `created_by`      | `String`          | Always present                                                      |
| `updated_at`      | `String`          | Only `updated_at`, not `created_at` (improvement over browse view)  |
| `tags`            | `Vec<String>`     | Omitted when empty                                                  |
| `confidence`      | `Option<Confidence>` | Omitted when None                                                |
| `token_estimate`  | `u32`             | Estimated tokens for full body (re-serialises the `FullEntryView` per row to compute — see perf note below) |

`RecallResult` (`crates/cm-capabilities/src/recall.rs:32-44`) carries fields that **never reach the wire**: `token_estimate` (total, distinct from the per-entry field), `routing` (which of `Search | TagScopeWalk | ScopeResolve | BrowseFallback` was used), `candidates_before_filter`, `fetch_limit_used`. These are high-signal observability fields the projection drops on the floor.

**Perf note on `token_estimate`**: `project_recall_entry` calls `project_full_entry(entry)` and re-serialises it inside the per-row loop (`crates/cm-capabilities/src/projection.rs:124-127`). For recall limit=20, that is 20 full-body serialisations performed twice: once to generate `token_estimate` per row, and once more inside `recall::recall` at `crates/cm-capabilities/src/recall.rs:108-111` for the budget check. Each full clone includes `meta.clone()` and `body.clone()`.

### 1.3 `cx_get` — `crates/cm-cli/src/mcp/tools/get.rs:42-46`

```json
{
  "entries": [FullEntryView],
  "found": usize,
  "missing": usize
}
```

`FullEntryView` (`crates/cm-capabilities/src/projection.rs:77-89`):

| Field           | Type              | Notes                                                                 |
| --------------- | ----------------- | --------------------------------------------------------------------- |
| `id`            | `String`          |                                                                       |
| `scope_path`    | `String`          |                                                                       |
| `kind`          | `String`          |                                                                       |
| `title`         | `String`          |                                                                       |
| `body`          | `String`          | Full body                                                             |
| `content_hash`  | `String`          | BLAKE3 hex, 64 chars — rarely useful to an LLM consumer               |
| `meta`          | `Option<EntryMeta>`| Full nested metadata                                                 |
| `created_by`    | `String`          |                                                                       |
| `created_at`    | `String`          |                                                                       |
| `updated_at`    | `String`          |                                                                       |
| `superseded_by` | `Option<String>`  | Emits `null` when None — `skip_serializing_if` is **not** set here, unlike `tags` |

**Gap**: `cx_get` does not tell the caller which requested IDs were missing. `found`/`missing` are counts only. The caller has to diff their input array against the returned `entries[*].id`.

### 1.4 `cx_store` — `crates/cm-cli/src/mcp/tools/store.rs:146-155`

```json
{
  "id": "<uuid>",
  "scope_path": "<scope>",
  "kind": "<kind>",
  "title": "<title>",
  "content_hash": "<blake3>",
  "created_at": "<rfc3339>",
  "superseded": Option<String>,
  "message": "Entry stored." | "Entry stored. Superseded entry <id>."
}
```

Echoes the inputs back. `content_hash` is visible to the caller but rarely load-bearing. `message` is a human-string duplicating what the structural fields already say.

### 1.5 `cx_deposit` — `crates/cm-cli/src/mcp/tools/deposit.rs:151-156`

```json
{
  "deposited": usize,
  "entry_ids": ["<uuid>", ...],
  "summary_id": Option<String>,
  "message": "Deposited N exchanges[ with summary]."
}
```

Again duplicates `deposited` in the human `message`.

### 1.6 `cx_stats` — `crates/cm-cli/src/mcp/tools/stats.rs:49-59`

```json
{
  "active_entries": u64,
  "superseded_entries": u64,
  "scopes": u64,
  "relations": u64,
  "entries_by_kind": { "<kind>": N, ... },
  "entries_by_scope": { "<scope>": N, ... },
  "entries_by_tag": [{"tag": "...", "count": N}, ...],
  "db_size_bytes": u64,
  "scope_tree": [{"path": "...", "kind": "...", "label": "...", "entry_count": N}, ...]
}
```

`scope_tree` is flat (it is not actually a tree). The name is misleading.

### 1.7 `cx_update` — `crates/cm-cli/src/mcp/tools/update.rs:119-129`

```json
{
  "entry": {
    "id": "...",
    "scope_path": "...",
    "kind": "...",
    "title": "...",
    "content_hash": "...",
    "updated_at": "..."
  },
  "message": "Entry updated."
}
```

Extra indirection through a nested `entry` object for a response that is already sparse.

### 1.8 `cx_forget` — `crates/cm-cli/src/mcp/tools/forget.rs:88-94`

```json
{
  "forgotten": u32,
  "already_inactive": u32,
  "not_found": u32,
  "details": [{"id": "...", "status": "forgotten|already_inactive|not_found|error", "error": "..."}, ...],
  "message": "Forgot N entries. M already inactive. K not found."
}
```

`details` repeats every ID with its status even in the happy path — redundant when `forgotten == len(input_ids)`.

### 1.9 `cx_export` — `crates/cm-cli/src/mcp/tools/export.rs:57-62`

```json
{
  "entries": [Entry],
  "scopes": [Scope],
  "exported_at": "<rfc3339>",
  "count": usize
}
```

Uses raw `Entry` and `Scope` types via blanket `serde_json::to_value` — bypasses the projection layer entirely. For an export tool that is arguably correct (you want fidelity). Flagging only because it is inconsistent with the other tools.

---

## 2. Token-bloat quantification

### 2.1 The MCP envelope double-encoding

The MCP transport is manual JSON-RPC over stdio (`crates/cm-cli/src/mcp/mod.rs:131-175`). The tool result is built as:

```rust
Ok(json!({
    "content": [{"type": "text", "text": value}]
}))
```

`value` is already a pretty-printed JSON string. When the outer `JsonRpcResponse` is serialised to the wire, that inner JSON gets string-escaped: every `"` becomes `\"`, every `\n` becomes `\\n`. A two-space-indented pretty JSON for a 20-row browse response roughly doubles its already-verbose byte count once escaped.

**This double-encoding is a local choice, not an MCP requirement.** MCP 2024-11-05 allows `content[].text` to contain any string the server wants. Putting JSON inside a text block is a convention; fmm puts YAML there instead. MCP 2025-06-18 adds `structuredContent` as a sibling to `content` so the server can deliver machine-parseable data without escaping, but neither fmm nor context-matters uses it, neither declares `outputSchema`, and both pin `PROTOCOL_VERSION = "2024-11-05"` (`crates/cm-cli/src/mcp/mod.rs:29`, `fmm/crates/fmm-cli/src/mcp/mod.rs:17`). Adopting `structuredContent` would require bumping the declared protocol version and declaring per-tool `outputSchema`, which is a much bigger surface-area change than swapping the text content.

### 2.2 Byte budget for a representative `cx_browse` payload at limit=20

Using Stuart's real `tag="session-log"` example and extrapolating to 20 rows. A typical row has:

- `id` (UUID hyphenated): 36 chars × wrapped in quotes + field name + separators ≈ 54 bytes
- `scope_path: "global"`: 22 bytes
- `kind: "observation"`: 23 bytes
- `title` (avg ~80 chars): ~95 bytes
- `snippet` (200 bytes of YAML frontmatter): ~220 bytes
- `created_by: "agent:claude-code"`: 35 bytes
- `created_at` (RFC 3339 with ms + tz): ~45 bytes
- `updated_at` (same): ~45 bytes
- `superseded_by: null`: 23 bytes
- `tags: ["session-log", "manicure"]`: ~40 bytes
- Pretty-print indentation (two-space × 4 levels) + commas + braces + newlines per row: ~90 bytes

Per-row pretty JSON ≈ **690 bytes**. For 20 rows: ~13,800 bytes. Plus envelope (`entries`, `total`, `next_cursor`, `has_more`) ~200 bytes = **~14,000 bytes pretty JSON**.

Then the JSON-RPC outer string-escape. Quotes become `\"` (1 extra byte each; ~14 per row × 20 = 280 bytes), newlines become `\n` (1 extra byte each; ~25 per row × 20 = 500 bytes). Net escape overhead: **~780 bytes**.

Add the JSON-RPC skeleton (`{"jsonrpc":"2.0","id":N,"result":{"content":[{"type":"text","text":"..."}]}}`): ~90 bytes.

**Total wire bytes for a 20-row browse: ~14,900 bytes ≈ ~3,725 tokens** at 4 chars/token.

### 2.3 Breakdown by field category (per row, pretty JSON bytes)

| Category                 | Bytes/row | × 20 rows | % of row |
| ------------------------ | --------- | --------- | -------- |
| `snippet` (200 B content + quoting) | 220 | 4,400 | 32% |
| `title` (content-dependent) | 95 | 1,900 | 14% |
| Structural overhead (indent, braces, field names × 10) | 140 | 2,800 | 20% |
| Timestamps × 2 (`created_at`, `updated_at`) | 90 | 1,800 | 13% |
| `id` (full UUID) | 54 | 1,080 | 8% |
| `created_by` | 35 | 700 | 5% |
| `scope_path` | 22 | 440 | 3% |
| `kind` | 23 | 460 | 3% |
| `superseded_by: null` | 23 | 460 | 3% |
| `tags` (when present) | 40 | 800 | 6% (not always present) |

### 2.4 ≥80% of bytes carry <20% of information

Rolling up:

- **Structural/format overhead** (indentation, field names, braces, commas, newlines, quotes): ~20% of row bytes. Zero information.
- **Redundant nulls**: `superseded_by: null` on every row = 3%. Zero information when the caller already asked for active entries (default `include_superseded = false`).
- **Repeated constants across rows**: `created_by` (identical on every row in practice), `scope_path` (often identical within a filtered browse), `kind` (often identical): ~11% combined. Each of these is near-zero marginal information once you have seen the first row.
- **Dual timestamps**: `created_at` + `updated_at`, both to millisecond precision. For entries that have never been updated, `updated_at == created_at` and the second field is pure duplicate. Sub-second precision is noise for every retrieval use case. ~13% of row bytes for ~1% of information.
- **Full-length UUID**: 36 chars. The first 8 chars (UUID v7 time prefix) + something shorter identifies the entry uniquely within a result set of 20. ~8% of row bytes that a short handle would replace.
- **Mechanical-prefix snippets**: 32% of row bytes. For session-log entries, the first 200 bytes are YAML frontmatter boilerplate — `session: ...`, `date: ...`, `agent: ...`, `---`. That is ~180 bytes of zero-information prefix around ~20 bytes of real content. Session-log-tagged browse responses are the worst case, and they are the majority of Stuart's observed usage.

The punchline: conservatively, **~70% of the ~14,900 bytes on a 20-row browse response carry <10% of the information**. The escape overhead from the JSON-in-text envelope is additive on top.

### 2.5 `cx_recall` has an additional bloat source

`token_estimate` per row is a `u32` but the computation serialises the *entire* `FullEntryView` per row (`projection.rs:124-127`). The field itself is small. The compute cost is not. At limit=20 with average body ~2 KB, each row serialises ~2.5 KB of JSON just to throw the bytes away and keep the length. That is not user-visible in the wire payload but it is silent per-request CPU.

---

## 3. Intelligence gap

The current payload is a flat list of homogeneous rows plus a pagination blob. Here is what is derivable cheaply but not surfaced:

### 3.1 Confirmed missing, high-value, cheap

1. **Relevance score on recall**. `recall::recall` at `crates/cm-capabilities/src/recall.rs:52` currently sorts entries by `scope_path.as_str().len()` (deepest scope first) and only then by whatever SQL order the store returned. When the routing path is `Search` (FTS5 keyword query), the store returns entries in FTS ranking order (BM25), but that order is preserved only as a stable-sort tiebreaker *within* each scope depth. The top-level response has no per-row score at all. Two near-misses: SQLite's FTS5 exposes `bm25()` via an auxiliary function; `cm-store` currently does not select it. Adding a `score: f32` column to the `Search` path is a ~5-line change in `cm-store/src/sqlite/entry.rs` and would propagate up.

2. **Routing and observability**. `RecallResult.routing`, `candidates_before_filter`, `fetch_limit_used` are already computed (`recall.rs:161-169`). None reach the wire. A single-line header `# routing: search, candidates: 47, returned: 20` (fmm-style YAML comment) would tell the caller whether they got an FTS hit or a browse fallback, which is load-bearing for debugging "why did my query miss?".

3. **Per-kind and per-tag histograms across the result set**. `cx_recall` already builds `scope_hits` for scope aggregation. The same reduction over `kinds` and `tags` is trivial and yields `# kinds: decision=4, fact=12, lesson=4` — an inventory hint that lets the caller decide whether to narrow by kind before fetching full bodies.

4. **Total vs returned context**. `cx_browse` carries `total: u64` but `cx_recall` does not. Callers have no way to know how many candidates the store considered. Even a simple `candidates: 47, returned: 20` line (derivable from `candidates_before_filter`) is worth surfacing.

5. **Smart snippets that skip YAML frontmatter**. The current `snippet` function (`projection.rs:15-24`) is a mechanical byte-prefix with a word-boundary break. For any entry whose body starts with a `---`-fenced YAML block (session logs, ingested markdown), the first 200 bytes are pure metadata. The fix is a small helper:

   - If body starts with `---`, find the closing `---` and start the snippet after it.
   - Skip the first blank line.
   - Start the snippet at the first real prose block (`##` heading + first paragraph, or just first paragraph).

   For session logs specifically, this would change the snippet from `session: 940f8c77-...\ndate: 2026-04-11\nagent: claude-code\n...` to the first sentence of the actual session narrative. Same 200 bytes on the wire, ~10× the information.

6. **Query-match highlights on recall**. For `Search`-routed recall, post-processing the body against the query terms (extracted by splitting on whitespace and stripping FTS operators) and picking the chunk around the first hit gives a genuinely informative snippet. `unicode-segmentation` is already in the `cm-core` dep tree transitively via `chrono`; a simple find-nearest-match is ~15 lines.

7. **Two-phase retrieval hints**. For a recall row where `token_estimate > threshold`, annotate `# truncated — use cx_get({id}) for full body`. The data is already computed.

### 3.2 Less urgent but worth considering

8. **Age-decay indicators**. `created_at` already tells the caller everything they need to compute age. A terse `# 3d old` or `# 6mo old` column would be easier to scan than a full RFC 3339 timestamp.

9. **Dedup / near-duplicate hints**. `content_hash` is BLAKE3 and deterministic. If two entries in a recall result share a hash prefix or their bodies differ only in metadata, annotate `# dup-of: <short-id>`. This catches the "I stored the same lesson three times" pattern which is known to happen.

10. **Link-density annotations**. `cx_deposit` creates `EntryRelation::Elaborates` links between summary and exchanges. Entries with non-trivial relation counts are more load-bearing than orphans. Surfacing `# 5 relations` per row is a constant-time lookup given an index join.

### 3.3 Intentionally dropped candidates

- **"Headline-only" mode for recall**. Tempting, but the caller already has `cx_get` for two-phase. A flag on recall ending up as a `--brief` equivalent would add modal complexity for marginal gains.
- **On-the-fly summarisation of bodies**. Out of scope — requires an LLM in the loop inside a tool call, which violates the store's zero-I/O architecture and adds latency that the caller's own LLM can provide more cheaply.
- **Relevance calibration against the user's historical clicks**. No behaviour signal exists in the store today, and synthesising one would require an ingestion path that does not exist.

---

## 4. What fmm does right (reference model)

The relevant formatters are `fmm/crates/fmm-core/src/format/`:

- `search_formatters.rs:10-108` — `format_bare_search`
- `list_formatters.rs:108-189` — `format_list_files`
- `yaml_formatters.rs:16-226` — `format_file_outline`
- `yaml_formatters.rs:361-388` — `format_read_symbol`
- `yaml_formatters.rs:393-438` — `format_class_redirect`

The principles extracted from these files, mapped to `cx_*` prescriptions:

### 4.1 Render once in-place; never double-encode

fmm formats its response as a YAML-ish string directly (`format_bare_search` returns `String`), and places that string straight into `content[0].text`. There is no intermediate `serde_json::Value` tree. Result bytes are readable in the raw JSON-RPC frame because there is no nested JSON to escape. This alone saves ~10% of wire bytes on any non-trivial response and eliminates the `\"` and `\\n` storms that Stuart's example shows.

**→ Prescription for cx**: replace `shared.rs:json_response` with a pair of functions — `yaml_response(String)` for text output, and `json_response(Value)` retained only for `cx_export` which legitimately needs machine-parseable data.

### 4.2 Compact tabular sections with column alignment

`format_bare_search` computes `name_width` and `file_width` dynamically (`search_formatters.rs:22-34`) and emits column-aligned rows inside grouped section headers (`EXPORTS`, `FILES`, `IMPORTS`, `NAMED IMPORTS`). The section boundaries let a reader scan by category without reading every row.

**→ Prescription**: `cx_browse` and `cx_recall` get per-kind section headers (`DECISIONS`, `FACTS`, `LESSONS`, etc.) when results span multiple kinds, or a single unsectioned block when homogeneous. Columns are id-short, title, scope, age.

### 4.3 YAML comment annotations for per-row metadata

fmm writes `- crates/cm-cli/src/mcp/tools/browse.rs  # loc: 87, exports: 1` (`list_formatters.rs:170`). The comment is not semantically YAML data, but it is visually co-located with the row and survives any downstream YAML parse. It is the trick that makes fmm responses feel dense without being structurally overloaded.

**→ Prescription**: cx per-row metadata (kind, age, score, scope) goes in a trailing YAML comment. Core identity (id-short, title) goes in the row body.

### 4.4 Aggressive omit-when-default

`format_list_files` at `list_formatters.rs:156-161` emits the `downstream` count **only if > 0** and the comment `# ↓ N = local relative-import dependents only. Cross-package importers not included.` **only if any downstream is present**. Zero values are omitted wholesale. Absent fields are not stubbed.

**→ Prescription**: cx rows never emit `superseded_by: null`, never emit empty `tags`, never emit `confidence` when absent. `created_at` and `updated_at` collapse to one line, and only when the caller asked for it (via a `verbosity` flag) or when they differ.

### 4.5 Hoist invariants into a shared header

`format_list_files` writes one summary line at the top — `summary: 13 files · 1,575 LOC · largest: ... (332 LOC)` — then lets the rows be terse. Scope and directory constants are hoisted.

**→ Prescription**: for a `cx_browse(scope_path="global", kind="observation", tag="session-log")` query, the response header carries `scope: global`, `kind: observation`, `tag: session-log` **once**, and the rows drop those fields entirely.

### 4.6 Truncation with actionable next-action

`format_bare_search` at `search_formatters.rs:98-105` appends `[{N} fuzzy matches — showing top {M} by relevance. Use a more specific term or set limit.]`. `format_list_exports_pattern` at `list_formatters.rs:29-31` appends `# next: Use offset={end} to continue.`. fmm's `cap_response` at `fmm/crates/fmm-cli/src/mcp/mod.rs:23-41` cuts at the nearest newline and emits `[Truncated — showing X/Y lines. Use truncate: false to get the full source.]`.

**→ Prescription**: cx honours a hard response cap, clips at a row boundary (never mid-row), and emits a trailing hint: `# truncated — 113 total, 20 shown; cx_browse(cursor="...", limit=50) to page` or `# use cx_recall(query="...", max_tokens=N) to tighten budget`.

### 4.7 Sectional disclosures about data provenance

`format_dependency_graph` at `yaml_formatters.rs:293-299` writes `# ℹ Cross-package imports are excluded from the downstream count.` as a trailing advisory when external imports are present. The advisory is not output-shaped metadata; it is a note telling the caller what the numbers do not include.

**→ Prescription**: `cx_recall` grows a trailing advisory for the routing path — `# routing: browse-fallback (no query provided); ordering is recency-descending, not relevance.` A caller who sees that learns when to re-query with search terms.

### 4.8 Hard byte cap with graceful mid-line clip

fmm caps every non-opt-out response at 10 KB (`fmm/crates/fmm-cli/src/mcp/mod.rs:21-41`) and trims to the last newline before the cap. `fmm_read_symbol` and `fmm_glossary` accept `truncate: false` to override. This prevents context bombs without forcing the caller to guess the right limit.

**→ Prescription**: cx introduces `MAX_MCP_RESPONSE_BYTES` (suggest 16 KB — bigger than fmm's 10 KB because cx rows carry more per-row meaning), clips at row boundary, emits `# truncated — ... ; cx_get(id=...) for full body` hint. `cx_get` and `cx_export` get the `truncate: false` escape hatch.

---

## 5. Proposed redesign

### 5.1 Wire format

**Keep** `content: [{type: "text", text: "..."}]`. **Drop** `structuredContent`. **Drop** `outputSchema`. Stay on `protocolVersion = "2024-11-05"` for now.

**Change** the text content from pretty-printed JSON to fmm-style YAML-comment-annotated text. Ship one format for all `cx_*` read tools (`cx_browse`, `cx_recall`, `cx_get`, `cx_stats`). Keep machine-parseable JSON only for `cx_export` (explicit backup tool, caller wants fidelity).

**Rationale**:
- Matches fmm's proven pattern in the same ecosystem.
- Eliminates the double-escape overhead (§2.1) at zero protocol cost.
- Humans and LLMs read it identically.
- Backwards compat: the shape inside `content[0].text` is free-form per MCP; callers that parse the string as JSON today will break, but there is no known structured caller outside `cm-web` (which goes through `cm-capabilities` directly, not the MCP adapter).

### 5.2 Per-tool projected shape

#### 5.2.1 `cx_browse` — inventory mode

Header declares query, sort, and totals. Rows are terse; repeated constants from the header are omitted per row. `created_by` collapses into the header when uniform. `scope_path` collapses into the header when uniform.

Example response for Stuart's actual query `cx_browse(tag="session-log", limit=3)`:

```
---
query: tag=session-log
sort: updated_at desc
total: 113
returned: 3
scope: (mixed)  # global=2, global/project:helioy=1
kinds: observation=3
created_by: agent:claude-code  # uniform

entries:
  - 019d79d3  Session: marketing strategy + lazy tool loading design sketch for manicure
              ## Task\nBrief session on marketing copy refinements for the manicure...
              # scope: global  tags: session-log, manicure  age: 2h
  - 019d6f22  Session: cx_recall FTS operator regression
              Repro: queries with hyphens now fail with "fts5: syntax error near '-'"...
              # scope: global/project:helioy  tags: session-log, cm  age: 1d
  - 019d5af1  Session: warroom orchestration design
              Decided on Rust-native orchestrator with bus-backed message passing...
              # scope: global  tags: session-log, warroom  age: 3d

# 110 more — cx_browse(cursor="eyJzb3J0...", limit=50) to page
```

**Design notes**:

- **Id-short**: 8-char prefix of the UUID v7 (time-sortable, hex). Collisions within a single result set are essentially impossible; if they occur, lengthen to 12 and emit `# id-collision-extended` as a header advisory. Full UUIDs are fetched via `cx_get` (which needs them anyway).
- **Title on first line, snippet on second**. Snippet is indented to visually subordinate it to the title. Leading `##` or `---` in the body is stripped before the snippet is rendered (see §5.3).
- **Trailing `# ...` comment carries per-row metadata**: scope (omitted when header declares uniform scope), tags, age (relative `2h`/`3d`/`6mo`, always), and only-when-present fields like `confidence: low`, `superseded: 019d...`, `score: 0.87`.
- **Age** is computed from `created_at` as a human-relative string. Precision: `<1m`, `Xm`, `Xh`, `Xd`, `Xw`, `Xmo`, `Xy`. This is ~6 bytes vs ~45 bytes for the current RFC 3339 timestamp.
- **Scope and `created_by` hoisting**: the projection layer walks rows once, checks for uniform values, and decides whether to hoist. Mixed rows keep the per-row annotation.
- **Pagination hint**: single trailing line with the actionable next-action, not a `next_cursor` field. Cursors are opaque to the caller but recognisable in the hint.

**Estimated wire bytes for 20 rows**: ~4,200 bytes pretty text (≈1,050 tokens). **~70% reduction vs ~14,900 bytes today**.

#### 5.2.2 `cx_recall` — minimal mode

Header declares query, routing, candidates, totals, and aggregate hints. Rows carry score when available, short id, title, snippet, and a trailing comment.

Example response for `cx_recall(query="snippet strategy", limit=5)`:

```
---
query: snippet strategy
routing: search  # FTS5 ranking
candidates: 47 → 5 shown
scope_chain: [global/project:helioy, global]
scope_hits: global/project:helioy=3, global=2
kinds: decision=2, lesson=2, observation=1
tokens: 3,420 of 8,000 budget

entries:
  - 019d8a01  0.91  How to snippet-truncate at word boundaries
                    The byte-prefix snippet drops mid-word; floor_char_boundary + rfind(' ') handles...
                    # scope: global/project:helioy  kind: decision  tags: projection, snippet  age: 1d
  - 019d7f3e  0.74  Lesson: YAML frontmatter pollutes session-log snippets
                    Session-tagged entries start with `---\nsession: ...\n---` which chews the snippet budget...
                    # scope: global/project:helioy  kind: lesson  tags: session-log  age: 4d
  ...

# routing: search — re-query with OR between synonyms if you need more breadth
# cx_get(id="019d8a01", "019d7f3e", ...) for full bodies
```

**Design notes**:
- **Score column**: 2-decimal float. Populated only when routing is `Search` (FTS5 BM25 via `bm25(entries_fts)`). For non-search routings, column is omitted entirely, not replaced with `-` or `null`.
- **Header `routing`** is an inline YAML comment because it is observability, not data. The same pattern is used by fmm for advisories.
- **Aggregate reductions**: `scope_hits` and `kinds` histograms are trivial reductions over the returned slice. Stuart gets "113 total, 98 session-log, 40 global" for free.
- **Candidates-before-filter** is surfaced: `candidates: 47 → 5 shown` tells the caller the store had 47 candidates and post-filtering kept 5.
- **Trailing advisories**: both the routing note and the two-phase `cx_get` suggestion are rendered only when actionable. `cx_get` suggestion is emitted only when ≥1 row has `token_estimate > threshold`.

#### 5.2.3 `cx_get` — full body with diagnostics

Section per requested id. Includes a `missing:` block enumerating any ids the caller asked for that do not exist.

```
---
requested: 3
found: 2
missing: [019d8a99]

entries:
  - id: 019d8a01-9c4f-...-000000000000
    title: How to snippet-truncate at word boundaries
    scope: global/project:helioy
    kind: decision
    tags: [projection, snippet]
    confidence: high
    age: 1d
    body: |
      The byte-prefix snippet drops mid-word, which is fine for ASCII but
      panics on multi-byte UTF-8 boundaries. Use `floor_char_boundary` (stable
      since Rust 1.82) and break at the nearest preceding space.
      ...
  - id: 019d7f3e-...
    ...

# 1 missing — ids: 019d8a99
```

**Design notes**:
- Full body in a YAML block-literal `|`. No escaping, no double-encoding. The outer JSON-RPC still string-escapes the whole thing, but only once.
- **`missing` is explicit**, not a count. Caller sees exactly which ids vanished.
- `content_hash` is dropped from default output. Include a `--verbose` flag if Stuart wants it back.

#### 5.2.4 `cx_stats` — scope rollup

```
---
active: 1,342
superseded: 89
scopes: 17
relations: 201
db_size: 4.2 MB

kinds:
  observation    748
  fact           201
  decision        87
  lesson          81
  preference      34
  feedback        12
  pattern          8
  reference        3

top_tags:
  session-log    113
  helioy          98
  cm              41
  projection      28
  ...

scope_tree:
  global                                1,042
    project:helioy                        203
      repo:context-matters                 78
      repo:fmm                             45
    project:nancyr                         97
```

Scope tree is **actually indented** rather than flat with a `path` field. `entries_by_kind` is sorted and column-aligned. `db_size_bytes` becomes `db_size: 4.2 MB`.

#### 5.2.5 Write-tool responses (`cx_store`, `cx_deposit`, `cx_update`, `cx_forget`)

These can remain JSON-ish but should drop the `message` field (redundant with the structural data) and move to the same YAML-text envelope for consistency:

```
---
stored: 019d8a01-9c4f-...-000000000000
scope: global/project:helioy
kind: decision
content_hash: b4c2a9...  # first 8 chars of BLAKE3
```

```
---
deposited: 5 exchanges
summary: 019d8b01-...
scope: global
# cx_get(id="019d8b01-...") to read summary
```

```
---
updated: 019d8a01-...
content_hash: c5d3b8...
```

```
---
forgotten: 3
already_inactive: 1
not_found: 0
# all requested ids handled — no further action required
```

Note how the `cx_forget` response omits `details` entirely when every row is in a clean state. It reappears only when there is at least one `error` row.

### 5.3 Snippet strategy

A new helper in `crates/cm-capabilities/src/projection.rs`:

```rust
pub fn smart_snippet(body: &str, query: Option<&str>, max_bytes: usize) -> String {
    let body = strip_yaml_frontmatter(body);
    let body = strip_leading_markdown_heading(body);
    let start = match query {
        Some(q) => first_query_match_position(body, q).unwrap_or(0),
        None => 0,
    };
    snippet_around(body, start, max_bytes)
}
```

Three sub-behaviours:

1. **`strip_yaml_frontmatter`** — if `body.starts_with("---\n")`, find the second `---\n` or `---\r\n` and return the slice after it. O(n) scan bounded by ~2 KB in practice.
2. **`strip_leading_markdown_heading`** — if the post-frontmatter content starts with `# ` or `## `, skip to the next `\n\n` and start from there. Heading content can go in `title`; the snippet should show the body.
3. **`first_query_match_position`** — for `Search`-routed recall, split the query on whitespace, strip FTS5 operators (`AND`, `OR`, `NOT`, `(`, `)`, `"`, `*`), lowercase-fold, and return the first byte offset where any term is found. If no match, default to 0.

`snippet_around` does the current `floor_char_boundary` + `rfind(' ')` logic but centred on `start` instead of at position 0.

**Expected effect on the session-log case**: a 200-byte snippet that shows the first real sentence of the session narrative instead of `session: ...\ndate: ...\nagent: ...`. Same bytes, 10× information.

### 5.4 Where each intelligence addition lives

| Addition                                        | Layer                                      | Effort      |
| ------------------------------------------------ | ------------------------------------------ | ----------- |
| Relevance score (BM25)                           | `cm-store/src/sqlite/entry.rs`             | 5-line SQL change + plumb through `Entry` (needs a transient score field) |
| Routing / candidates / fetch_limit surface       | `cm-capabilities/src/recall.rs`            | Already computed; new projection step |
| Per-kind / per-tag histograms                    | New function in `cm-capabilities/src/projection.rs` | ~25 lines |
| Smart snippet (strip frontmatter, match-centred) | `cm-capabilities/src/projection.rs`        | ~50 lines + tests |
| Sort key echoed in browse header                 | `cm-capabilities/src/browse.rs` (`BrowseResult` → add `sort_used: BrowseSort`) | 1 field + projection |
| Hoisted constants (scope / created_by uniformity)| New `hoist_uniform` helper in `projection.rs` | ~20 lines |
| Short id                                         | `projection.rs` (new `short_id` helper)   | 3 lines    |
| Relative age                                     | `projection.rs` (new `relative_age`)      | ~20 lines  |
| Missing ids on `cx_get`                          | `cm-cli/src/mcp/tools/get.rs`             | ~10 lines  |
| Response byte cap with newline clip              | `cm-cli/src/mcp/mod.rs`                    | Copy fmm's `cap_response` |
| Actionable trailing advisories                   | New `format_advisory` helpers in `projection.rs` | ~30 lines |

The work is concentrated in `cm-capabilities/src/projection.rs` (currently 188 LOC; post-redesign estimated ~400 LOC — still well under the 700 LOC refactor-first threshold from CLAUDE.md). `cm-cli/src/shared.rs` shrinks because it no longer needs per-tool JSON projection wrappers. The adapter-layer tool files stay mostly unchanged in shape, only swapping `json_response(json!(...))` for `yaml_response(format_browse_view(...))`.

### 5.5 Backwards compatibility

**This is a breaking wire change** for any caller that parses the inner `content[0].text` as JSON. Known callers:

- **Claude Code LLM consumption**: no impact — the LLM reads the text either way and adapts instantly.
- **`cm-web`** (`crates/cm-web/*`): does not consume MCP responses. It calls `cm-capabilities` directly via HTTP handlers in `crates/cm-web/src/api/entries.rs`. Unaffected.
- **Tests**: `crates/cm-cli/tests/mcp_protocol_test.rs`, `snapshot_tests.rs`, `tools_integration.rs` will break on the JSON-parse path. These are the tests that need to be updated as part of the migration.
- **External downstream callers**: none known. Stuart's primary usage is via Claude Code.

**Migration path options**, ranked by preference:

1. **Clean break** (preferred): bump `cm-cli` to 0.2.0, ship the redesign, update the three test files, call it done. No compat flag. The justification is: Stuart owns every known consumer, the LLM-facing side is automatic, and a compat flag would preserve the bloat path and double the test surface.

2. **Feature flag via MCP tool param**: each read tool accepts an optional `format: "yaml" | "json"` param, defaulting to `yaml`. Kept for one release cycle, then dropped. Adds surface area. Not recommended unless Stuart wants a graceful-degradation period.

3. **Env var toggle**: `CM_MCP_LEGACY_JSON=1`. Even more hidden, even worse ergonomics. Only mentioned for completeness.

### 5.6 On-the-wire byte comparison (20-row `cx_browse`)

| Variant                             | Body bytes | Envelope escape overhead | Total wire bytes | Tokens |
| ----------------------------------- | ---------- | ------------------------ | ---------------- | ------ |
| Current (pretty JSON in text block) | ~14,000    | ~780                     | ~14,900          | ~3,725 |
| Proposed (YAML text)                | ~4,100     | ~110                     | ~4,300           | ~1,075 |
| **Saving**                          | **−71%**   | **−86%**                 | **−71%**         | **−71%** |

Similar ratios (55-70%) apply to `cx_recall` at limit=20 and `cx_get` at 3 full entries.

---

## 6. Open questions / decisions for Stuart

1. **Wire format gate — YAML text or MCP `structuredContent`?** The proposal above keeps `content: [text]` because that matches fmm and requires zero protocol bump. The alternative is to bump `PROTOCOL_VERSION` to `2025-06-18`, declare per-tool `outputSchema`, and return `structuredContent` as JSON. That path is "more correct" by the 2025 spec but costs a protocol version bump across every cm install, every test, and the declared fmm/cm parity that currently both pin 2024-11-05. **Default recommendation: YAML text. Decision needed if you disagree.**

2. **Break wire compat cleanly or ship a `format` flag?** §5.5 option 1 vs option 2. Recommendation: clean break at 0.2.0. Ship release-please as usual.

3. **Should `cx_store` / `cx_update` / `cx_deposit` / `cx_forget` move to the YAML text envelope, or stay as JSON-in-text?** They are write tools, caller typically just checks for success. Proposal moves them for consistency. Low-risk either way.

4. **Relevance score: BM25 from FTS5, or defer?** Adding `bm25(entries_fts)` to the `store.search()` SQL is a ~5-line change but it requires deciding whether to expose the raw BM25 value or a normalised 0-1 score. Normalisation is cheap (divide by the max in the result set) but makes cross-query score comparison meaningless. BM25-raw is meaningful per-query but visually weird (`-3.47` vs `-1.12`). **Suggest: normalised 0-1 per query, shown to 2 decimals.**

5. **Response byte cap value.** fmm uses 10 KB. cx rows carry more per-row meaning (titles, snippets). Suggest 16 KB for cx, but this should be measured against real traffic. What is the p95 useful response size Stuart wants before a truncate kicks in?

6. **Short-id length: 8 or 12?** Option: start at 8, extend to 12 only on detected collision within a result set. Extends the lifetime of the terse row format.

7. **How aggressive should "smart snippet" be for non-session-log entries?** The proposal strips YAML frontmatter and leading markdown headings unconditionally. That changes the snippet for every entry, not just session logs. Is there a class of entries where the current byte-prefix behaviour is preferable?

8. **Keep `content_hash` in `cx_get` default output, or hide behind a verbose flag?** It is 64 chars of hex that only matters for dedup debugging. Proposal hides it. Confirm.

9. **`cx_stats.scope_tree` — render as actually-indented tree or keep flat?** The current "flat list with `path` field" is not a tree. Proposal renders a real indented tree using the `/` separator in scope paths. Any caller that parses the current shape breaks.

10. **Migration of `cx_export`?** Proposal keeps `cx_export` as JSON for fidelity. But that means `cx_export` is now the only tool returning JSON-in-text, which is inconsistent. Alternative: emit a `---`-separated YAML multi-document stream for exports too. Export durability is more important than wire compactness here, so JSON is probably correct, but flagging for confirmation.

---

## Appendices

### A. File paths touched

- `crates/cm-capabilities/src/projection.rs` (188 LOC → ~400 LOC) — new view types, smart snippets, histograms, format helpers
- `crates/cm-capabilities/src/browse.rs` (62 LOC) — add `sort_used` to `BrowseResult`
- `crates/cm-capabilities/src/recall.rs` (298 LOC) — expose routing/candidates in response, not just `RecallResult`
- `crates/cm-cli/src/shared.rs` (56 LOC → ~20 LOC) — delete `entry_to_*_json` wrappers; add `yaml_response(String)`
- `crates/cm-cli/src/mcp/mod.rs` (268 LOC) — add `cap_response` helper copied from fmm
- `crates/cm-cli/src/mcp/tools/browse.rs` (87 LOC) — call `format_browse_view` instead of per-row JSON projection
- `crates/cm-cli/src/mcp/tools/recall.rs` (119 LOC) — same
- `crates/cm-cli/src/mcp/tools/get.rs` (49 LOC) — same + missing-ids enumeration
- `crates/cm-cli/src/mcp/tools/stats.rs` (62 LOC) — render indented tree
- `crates/cm-cli/src/mcp/tools/{store,deposit,update,forget}.rs` — thin YAML emitters
- `crates/cm-store/src/sqlite/entry.rs` (492 LOC) — add BM25 column to search query
- `crates/cm-cli/tests/{mcp_protocol_test,snapshot_tests,tools_integration}.rs` — update expected shapes
- `crates/cm-capabilities/tests/{recall_tests,browse_tests}.rs` — update expected shapes

### B. Reference: fmm response construction call graph

```
McpServer::handle_tool_call (fmm/crates/fmm-cli/src/mcp/mod.rs:275)
  └─ tools::tool_search (fmm/crates/fmm-cli/src/mcp/tools/search.rs:7)
       ├─ fmm_core::search::bare_search (returns BareSearchResult)
       └─ fmm_core::format::format_bare_search (returns String)
            ├─ section: EXPORTS (column-aligned)
            ├─ section: FILES
            ├─ section: IMPORTS
            ├─ section: NAMED IMPORTS
            └─ optional truncation notice
  └─ cap_response(text, truncate)  (10 KB cap, newline clip)
  └─ json!({"content": [{"type": "text", "text": text}]})
```

### C. Reference: current cx response construction call graph

```
McpServer::handle_tool_call (crates/cm-cli/src/mcp/mod.rs:223)
  └─ tools::cx_browse (crates/cm-cli/src/mcp/tools/browse.rs:44)
       ├─ cm_capabilities::browse::browse (returns BrowseResult { entries, total, ... })
       ├─ entries.iter().map(entry_to_browse_json) → Vec<serde_json::Value>
       │    └─ project_browse_entry (projection.rs:132)
       │         ├─ format_uuid
       │         ├─ format_time (×2)
       │         ├─ snippet (byte-prefix)
       │         └─ extract_tags
       ├─ json!({"entries": ..., "total": ..., "next_cursor": ..., "has_more": ...})
       └─ json_response (shared.rs:8) → serde_json::to_string_pretty → String
  └─ json!({"content": [{"type": "text", "text": value}]})
  └─ JsonRpcResponse serialises → inner string gets double-escaped
```

The extra hops (`entry_to_browse_json` wrapping `project_browse_entry` wrapping nothing) are pure indirection — removing them is a side benefit of the redesign.
