---
title: ALP-2103 backend review (recall/search split)
type: projects
tags: [context-matters, review, alp-2103, backend]
summary: Pre-Nancy review of the Rust/web slice of the recall/search split epic. Flags layering, file-size, and DRY risks before implementation kicks off.
status: active
source: backend-engineer
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

# Summary

Top risks to address before kicking off Nancy:

1. **Layering violation in ALP-2113**. ALP-2108 adds a new `search()` capability that takes a `ScopeSelector` and pushes it to the store. `ScopeSelector` lives in `cm-capabilities`, but `cm-store` cannot depend on `cm-capabilities`. ALP-2113 names the constraint but does not specify the resolution. Decide where the scope-predicate type lives (almost certainly `cm-core`) before any sub-issue ships, or every sub-issue will block on this.
2. **`EntryFilter` widening is unowned.** ALP-2110 widens browse to accept `Subtree`/`Set`/`All`. Today `EntryFilter.scope_path: Option<ScopePath>` (cm-core) is the only thing the SQL layer sees. Either ALP-2110 changes that to a richer scope predicate, or ALP-2104 must add the predicate to `cm-core` up front. ALP-2104 explicitly says it "does not widen `EntryFilter`". This is a hard gap.
3. **No single shared scope-predicate builder.** ALP-2104 says add SQL builders for `Subtree`/`Set`/`All` to `query.rs`. ALP-2108 builds a new search SQL path. ALP-2110 adds them to browse. ALP-2113 says "if a shared scope predicate is needed, define it in `cm-core`". Three writers, no owner, no shape. Pick: a single `fn push_scope_predicate(qb, &ScopeFilter)` in `cm-store` that browse and search both call. Decide which issue owns it.
4. **`do_search` ancestor-walk preservation is fragile**. ALP-2108 says replace `do_search`. ALP-2113 says don't. Today `cx_recall` with a query calls `ContextStore::search(scope, ...)` and gets target+ancestors via `WHERE scope_path IN (ancestors)`. If `ContextStore::search` takes a `ScopeSelector::Path` going forward, it must mean exact (cx_search semantics), so recall's ancestor-walk path needs a separate trait method. ALP-2113 hints at this but doesn't pick. Pick now: `ContextStore::search_ancestor_walk(&ScopePath, ...)` for recall, `ContextStore::search(ScopeFilter, ...)` for cx_search. Otherwise the work serialises.
5. **ALP-2104's recall-guard error variant is half-specified**. The issue says "introduce `RecallScopeNotSingular`" but the existing `CmError` taxonomy in `cm-core/src/error.rs` is generic (`Validation`, `EntryNotFound`, etc.). ALP-2104 mentions it "also covers the empty-query rejection in ALP-2108". ALP-2108 currently says `cx_search` rejects empty queries. Define the variant in cm-core, not cm-capabilities, and name it for the rule (e.g. `InvalidScopeForOp { op, expected }`) so it is reusable. Two hands, one error type.

# Per-issue findings

## ALP-2104 — Grow ScopeSelector vocabulary
**Status: needs revision.**

Concerns:
- The `Deserialize` rewrite (`#[serde(tag = "kind", rename_all = "snake_case")]`) means a new wire shape. The wire format was already breaking, but check that **every** caller uses `ScopeSelector::parse(&str)` today (used in `agent.rs:114`, `entries.rs:259`) so the swap from string to JSON requires touching call sites in `cm-web` and tests, not just the type. Issue body should call this out as part of its scope.
- Pins line numbers (`recall.rs:23`, `recall.rs:81`, `query.rs:27-31`, `migrations/001_initial_schema.sql:39`, `tools.toml:134`). Drop these or replace with stable references (function names, headings). They will rot the moment any unrelated PR shifts a line.
- "Resolver lives in `scope/resolution.rs`" — `Subtree`/`Set`/`All` should not pass through `resolve_scope_selection`. Issue should say: resolver is only called for `Path`/`CwdInferred` (the only variants that need a `ScopePath`); non-singular variants bypass resolution and go straight to the SQL builder. State this explicitly so an implementer doesn't try to "resolve" `All`.
- `EntryFilter` is a cm-core struct. ALP-2104 says "this issue does not widen `EntryFilter`" but ALP-2110 will need that shape. Either push the widening into ALP-2104 (preferred — keeps the type/serde change in one place) or define a separate `ScopeFilter` enum in cm-core in ALP-2104 that browse can opt into in ALP-2110.
- "Single shared error type also covers the empty-query rejection in ALP-2108" — the variant name should not be `RecallScopeNotSingular` because it is reused for the empty-query case. Rename or split. `op: Op, reason: ...` is one option.

Recommended edits to issue:
- Strip line numbers; cite functions and headings.
- Add the `cm-core` scope-predicate type (or widened `EntryFilter`) explicitly to the file list.
- Rename the new error variant to a name that fits both rejections, or split into two.
- Add: "non-singular variants bypass `resolve_scope_selection` and go directly to SQL".

## ALP-2105 — cx_search capability + MCP tool (parent)
**Status: good.**

Reasonable split into capability/store (ALP-2108) and MCP wiring (ALP-2109). No edits needed; this is a tracking parent.

## ALP-2110 — Widen browse to accept ScopeSelector
**Status: needs revision.**

Concerns:
- Depends on ALP-2104 widening `EntryFilter` (or adding a new scope predicate type). ALP-2104 disclaims that work. Either ALP-2110 absorbs it, or ALP-2104 adds it. Resolve before either issue starts.
- `BrowseRequest.scope: Option<ScopeSelector>` already exists in `cm-capabilities/src/browse.rs`. The capability change is small; the lift is at the cm-core/cm-store layer. Issue body should clarify that the `cm-capabilities` plumbing is mostly already there.
- "HTTP browse routes should use the structured scope parser from ALP-2115" — OK, but `BrowseQuery` in `agent.rs:252` currently uses `Option<String>` for `scope` and gets parsed via `ScopeSelector::from_optional_scope`. With structured JSON in the query string, that parser changes shape. Note that ALP-2115 owns the parser change; ALP-2110 does not need to specify it.
- "Subtree browse keeps using the scope index" — verify with EXPLAIN QUERY PLAN per ALP-2104; cite that requirement.

Recommended edits to issue:
- Explicitly state which crate carries the `EntryFilter` widening and that ALP-2110 inherits it from ALP-2104.
- Drop "/api/agent/browse" wording since both `/api/entries` and `/api/agent/browse` share `BrowseQuery` via `agent::execute_browse`.

## ALP-2113 — Preserve recall ancestor search when adding cx_search
**Status: blocker.**

Concerns:
- This is the most important coordinating issue, and the most underspecified. It correctly identifies the seam (recall.search-with-ancestors vs cx_search.flat) but does not decide the contract.
- Two viable shapes:
  - **(A)** Keep `ContextStore::search(query, Option<&ScopePath>, limit) -> ScoredEntry` for recall (target+ancestors) and add `ContextStore::content_search(req: ContentSearchRequest) -> ...` for cx_search.
  - **(B)** Generalise: `ContextStore::search(ScopeFilter, query, ...)` where `ScopeFilter::AncestorWalk(p)` is one variant alongside `Exact(p)`, `Subtree(p)`, `Set(...)`, `All`.
  - (B) is cleaner long-term but more scope. (A) is faster, safer, and matches the file-size budget. Recommend (A).
- `cm-store` cannot depend on `cm-capabilities`. The new request type lives in `cm-core`. ALP-2113 says this; it just doesn't pick a name.
- ALP-2108 currently says "replace `do_search`". ALP-2113 says don't. **These two issues directly contradict each other** until ALP-2113 is locked. Resolve ALP-2113 first, then update ALP-2108 wording.

Recommended edits to issue:
- Pick (A) or (B). Name the new trait method. Name the cm-core types (`ScopeFilter`, `ContentSearchRequest`).
- Update ALP-2108 to match. Specifically: `do_search` becomes `do_search_ancestor_walk` (recall path stays) and a new `do_content_search` is added (cx_search path).

## ALP-2114 — Apply cx_search filters before pagination
**Status: good with caveats.**

Concerns:
- "Reuse the existing `json_each` tag predicate from browse" is feasible: it lives at `crates/cm-store/src/sqlite/query.rs` lines 45-50 inside `push_browse_filters`. To reuse it, extract it into a free function `push_tag_predicate(qb, tag)` so both browse and search call it. This is a one-line ask in the issue body.
- Browse takes a single `tag: Option<String>`. cx_search takes `tags: Option<Vec<String>>` (per ALP-2108). The reuse helper must accept a slice and use `OR` semantics consistent with recall (`entry_has_any_tag` in `projection`), or the contract diverges. Decide tag semantics (any-of vs all-of) and make it explicit in ALP-2114 and ALP-2108.
- Kind filter: ALP-2108 says `kinds: Option<Vec<EntryKind>>` (multi). Browse takes `Option<EntryKind>` (single). Reuse needs a multi-kind helper too, or browse keeps single and search has its own multi.

Recommended edits to issue:
- State explicitly: tag semantics is "any-of" (matches recall).
- Note that the json_each helper must be extracted to a free function for reuse. Browse stays single-tag at the API boundary.

## ALP-2112 — Structured logging for recall and search
**Status: good.**

Concerns:
- "Adopt `tracing` (or whatever the broader Helioy stack settles on; check `nancyr` for prior art)". cm-web already uses `tracing::info!` directly (`entries.rs:210`). cm-cli `entries.rs` mutations log via `tracing::info!`. So `tracing` is already in. Drop the "check nancyr" hedge; just say "use `tracing`, consistent with cm-web mutations".
- `crates/cm-cli/src/main.rs` for subscriber init — verify path; the existing CLI init may live under `cm-cli/src/cli/` or `cm-cli/src/mcp/`. Don't pin path in issue body.

Recommended edits to issue:
- Drop the "or whatever the broader stack settles on" hedge.
- Drop the file path for subscriber init.

## ALP-2115 — cm-web API: parse structured ScopeSelector query params
**Status: good.**

Concerns:
- Today `agent.rs::parse_scope_selector` handles `(Option<String>, Option<String>)` for `(scope, cwd)`. Moving to structured JSON in `?scope=` means the wire shape becomes JSON-in-querystring, which is awkward (URL-encoded JSON). Confirm ergonomics with frontend; alternative is moving these reads to POST bodies. ALP-2103 commits to "structured JSON, not glob" so the URL-encoded route is intentional, but the issue should explicitly call out that callers will URL-encode.
- "Apply the shared parser to `/api/agent/recall`, `/api/entries/recall`, `/api/agent/browse`, `/api/entries`, `/api/entries/search`, and `/api/export`". `/api/export` is not on the file list of ALP-2103. Verify it has a scope query param (it does: `crates/cm-web/src/api/export.rs`). Add it to ALP-2103's surface list.

Recommended edits to issue:
- Note URL-encoding burden on callers; this is a design tradeoff worth surfacing.

## ALP-2117 — cm-web API: define the cx_search web response contract
**Status: needs revision.**

Concerns:
- This is the right question to ask but the issue avoids answering it. Pick now: new `WebSearchView` projection or compatibility with `WebRecallView`. They have meaningfully different contracts (recall has `routing`, `tier`, `scope_chain`, `scope_hits`; search has `next_cursor`).
- Recommended: new `WebSearchView`. The whole point of ALP-2103 is that recall and search are different operations. Pretending they have the same response shape re-introduces the conflation at the web layer.
- `crates/cm-capabilities/src/projection/web_view/recall.rs` is 200 lines. Adding `web_view/search.rs` is the natural shape.
- "A search request with a cursor is either supported end to end or rejected at the type boundary, not only by the backend parser" — this is a contract bug in current code (`SearchQuery` has no cursor). Worth flagging that the current `/api/entries/search` parser accepts no cursor at all (verified at `entries.rs:65-73`).

Recommended edits to issue:
- Pick: new `WebSearchView`.
- Drop the "or compatibility view" branch unless there is a strong reason to keep it.
- Add: cursor support is a hard requirement once `cx_search` paginates (per ALP-2108).

## ALP-2111 — Docs/SKILL update
**Status: good.**

Concerns:
- Pins `tools.toml:134`. Drop. Cite `[[tools.cx_recall.params]] name = "scope"` block instead.
- "`CLAUDE.md` (root), the architecture table currently lists `cm-core`, `cm-store`, `cm-cli` only. Sync with reality (`cm-capabilities`, `cm-web` exist)" — verified, this is real. Good catch.
- SKILL template at `crates/cm-cli/templates/SKILL.md` is 209 lines. Adding cx_search takes it to ~250-280; well under budget.

Recommended edits to issue: drop line numbers.

# Cross-cutting concerns

## File size projections

| File | Current | Projected post-edit | Risk |
|---|---|---|---|
| `crates/cm-capabilities/src/scope/types.rs` | 227 | ~280-310 (3 new variants + structured serde) | safe |
| `crates/cm-capabilities/src/scope/resolution.rs` | 574 | 574 (touched, not grown) | **already over 500; do not grow** |
| `crates/cm-capabilities/src/recall.rs` | 143 | ~170 (guard + tracing) | safe |
| `crates/cm-capabilities/src/recall/routing.rs` | 235 | 235 | safe |
| `crates/cm-capabilities/src/search.rs` (new) | 0 | ~250-300 (request, response, cursor, executor, tests) | safe |
| `crates/cm-capabilities/src/projection/web_view/recall.rs` | 200 | 200 | safe |
| `crates/cm-capabilities/src/projection/web_view/search.rs` (new) | 0 | ~150-200 | safe |
| `crates/cm-store/src/sqlite/query.rs` | 245 | ~400-500 (3 scope-predicate builders + new search SQL + extracted helpers) | **watch** |
| `crates/cm-web/src/api/agent.rs` | 361 | ~430-480 (structured scope parser, kept shared) | **watch** |
| `crates/cm-web/src/api/entries.rs` | 334 | ~390-420 (cursor support + new search shape) | **watch** |
| `crates/cm-cli/templates/SKILL.md` | 209 | ~280 | safe |
| `tools.toml` | 690 | ~810-850 (cx_search block) | safe (TOML, not Rust) |

Decompositions to plan now (before any code is written):
- `crates/cm-store/src/sqlite/query.rs` should split. Recommended: keep `query.rs` for browse, add `crates/cm-store/src/sqlite/search.rs` for `do_content_search` (cx_search) and `do_search_ancestor_walk` (recall). Move shared scope-predicate helpers to `crates/cm-store/src/sqlite/predicates.rs` (new). This contains scope variant builders, the `json_each` tag predicate, and kind-IN builder — used by browse and search.
- `crates/cm-web/src/api/agent.rs` is approaching the budget. The shared structured-scope parser from ALP-2115 should land in a sibling `crates/cm-web/src/api/scope_query.rs` (new). ALP-2115 already says "Keep it near `agent.rs` only if that file stays readable; otherwise move it". Decide upfront: move it.

## Shared code to extract before any sub-issue lands

1. **Scope predicate builder** in `cm-store/src/sqlite/predicates.rs`: `fn push_scope_predicate(qb, &ScopeFilter)` — handles all five variants. Browse, recall ancestor-walk, and cx_search all call this. Owner: ALP-2104 (defines the type), ALP-2110 (calls from browse), ALP-2108 (calls from search), ALP-2113 (calls from recall ancestor-walk).
2. **Tag predicate**: extract `push_tag_predicate(qb, &[String])` from `push_browse_filters`. Owner: ALP-2114.
3. **Kind-IN predicate**: extract `push_kind_predicate(qb, &[EntryKind])`. Owner: ALP-2114 (or ALP-2110).
4. **FTS rank+order helper**: `do_search` already orders by `f.rank` then no tiebreaker. cx_search needs `ORDER BY f.rank ASC, e.updated_at DESC, e.id ASC`. Extract `fn order_by_fts_rank()`. Owner: ALP-2108.
5. **Web scope query parser**: `crates/cm-web/src/api/scope_query.rs::parse_scope_selector_from_query`. Owner: ALP-2115.

## Seam risks

- **Recall vs cx_search**: ALP-2113 + ALP-2108 jointly own this seam. Today both go through `ContextStore::search`. After the split, recall keeps ancestor-walk semantics on a new method; cx_search uses the new `ScopeFilter`-driven method. Resolve before any work starts.
- **Browse vs cx_search scope predicates**: Both want the same builders. Without a shared builder (item 1 above), three implementers will write three copies. Mandate the predicate module up front.
- **Web `WebRecallView` vs `WebSearchView`**: ALP-2117 must pick. `WebRecallView` carries recall-only fields. Pretending they're the same conflates again. New view.
- **Recall scope guard vs cm-web policy**: ALP-2115 correctly says "let the recall capability reject" and cm-web should not duplicate. Verify in implementation that the typed error from the capability surfaces cleanly through `ApiError`.

## DRY violations to prevent

- Three scope-predicate builders (browse, recall ancestor, search) would all do `WHERE scope_path = ?` and similar. Extract once.
- Two FTS query builders (existing `do_search`, new `do_content_search`) would duplicate the JOIN to `entries_fts`. Extract a query stub helper or share the FTS-MATCH skeleton.
- Three web scope parsers (`agent.rs::parse_scope_query`, `agent.rs::parse_scope_selector`, `entries.rs::parse_search_query`) already exist; ALP-2115 collapses them. Make sure ALP-2115 actually deletes the duplicates rather than adding a fourth.

# Suggested issue changes

## Reorder dependencies

Current implicit order is: ALP-2104 → ALP-2110/2113/2108 → ALP-2114 → ALP-2109 → ALP-2117 → ALP-2115 → ALP-2112 → ALP-2111.

Recommended explicit order:
1. **ALP-2113 first** (decides trait shape, blocks 2104 + 2108).
2. **ALP-2104** (vocab + cm-core types + recall guard).
3. **Parallel: ALP-2110, ALP-2108** (browse + cx_search both consume cm-core types from 2104).
4. **ALP-2114** (filters before pagination — depends on 2108).
5. **ALP-2117** (web response contract — depends on 2108 result type).
6. **ALP-2115** (web scope parser — depends on 2104 wire shape).
7. **ALP-2109** (MCP tool — depends on 2108).
8. **ALP-2112** (logging — depends on 2108 spans existing).
9. **ALP-2111** (docs — last).

Mark ALP-2113 as **blocker** for ALP-2104 and ALP-2108. Today it is a sibling.

## Splits/merges

- **Split ALP-2110**: pull the `EntryFilter` widening (cm-core type change) into ALP-2104, leave ALP-2110 as the wiring change in cm-capabilities + cm-web only. Type changes in core are dangerous-by-default; quarantine them in one issue.
- **Merge ALP-2113 into a clarification on ALP-2108**: ALP-2113 is currently a parent/sibling that must run first. If ALP-2108's body is updated to specify the new trait method names and the no-replace-of-do_search policy, ALP-2113 collapses into 2-3 acceptance bullets on ALP-2108. Either upgrade ALP-2113 to a real issue with named types, or fold it.
- **Don't split** ALP-2114; it's already minimal.

## Stable references to fix

Issue bodies pin the following lines/symbols that will rot:
- ALP-2104: `recall.rs:23`, `recall.rs:81`, `query.rs:27-31`, `migrations/001_initial_schema.sql:39`, `tools.toml:134`.
- ALP-2108: `cm-store/src/sqlite/query.rs:114-181`, `tools.toml:134`.
- ALP-2111: `tools.toml:134`.

Replace with: "function `push_browse_filters` in `cm-store/src/sqlite/query.rs`", "the `idx_entries_scope` index in migration 001", "the `[[tools.cx_recall.params]]` block where `name = \"scope\"`".

# Open questions

1. **Is `ScopeFilter` a new cm-core type or does `EntryFilter.scope_path` get widened to `EntryFilter.scope: Option<ScopeFilter>`?** The latter is breaking for `EntryFilter` consumers. The former is cleaner. I lean toward a new `ScopeFilter` enum in cm-core with `EntryFilter.scope: Option<ScopeFilter>` (rename) or keep `scope_path` for back-compat and add `scope_filter: Option<ScopeFilter>` (ugly). Ask Stuart.
2. **cx_search tag semantics**: any-of (matches recall and most search engines) or all-of? ALP-2108 doesn't say. Lock in any-of.
3. **Cursor encoding for cx_search**: existing `cm-store/src/sqlite/cursor.rs` patterns — does that module support a `(rank, updated_at, id)` triple cursor today, or only the browse `(updated_at, id)` shape? If only browse, ALP-2108 needs a cursor extension and the file-size projection on `cursor.rs` needs to be checked.
4. **`/api/export` scope param**: in ALP-2115's list. Confirm it accepts the new structured shape, since export today is more permissive (cross-scope by design).
5. **Frontend impact of structured JSON in querystring**: URL-encoded JSON is awkward. Should some of these read endpoints move to POST? Out of scope here, but worth raising before frontend agent picks up the work.
