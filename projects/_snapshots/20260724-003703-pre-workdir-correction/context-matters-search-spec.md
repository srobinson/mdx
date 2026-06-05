---
title: context-matters search spec
type: projects
tags: [context-matters, cx-search, search, retrieval, mcp]
summary: Proposal for a deterministic cx_search surface that separates search semantics from browse and recall.
status: draft
project: context-matters
confidence: high
created: 2026-04-19
updated: 2026-04-19
related: [context-matters-browse-inferred-scope-spec, context-matters-spec-mcp-server-and-tools, context-matters-spec-world-class-retrieval]
---

# context-matters search spec

## Problem

`context-matters` currently has:

- `cx_browse` for inventory and pagination
- `cx_recall` for curated agent facing retrieval

What is missing is a clean deterministic search surface.

That creates semantic overload:

- `cx_browse` is not search, so callers cannot use it to answer "what matches this query?"
- `cx_recall` is more than search, so callers cannot trust it as a transparent query interface

This weakens operator trust and makes debugging retrieval harder than it should be.

## Goal

Add `cx_search` as the explicit query interface for CM.

`cx_search` should answer:

"What entries match this query under these filters and sort rules?"

It should not answer:

"What context should the agent probably see now?"

## Non Goals

- Do not replace `cx_recall`
- Do not turn `cx_search` into a summarizer or curator
- Do not solve tag quality in this design
- Do not require LLM involvement on the read path

## Core Decision

`cx_search` should be deterministic, inspectable, and minimally opinionated.

That means:

- explicit query semantics
- explicit scope behavior
- explicit sort behavior
- explicit match metadata
- no hidden synthesis
- no token budget trimming

## Tool Surface

### Request

```json
{
  "query": "helix context",
  "mode": "fts",
  "scope": "auto",
  "scope_mode": "stack",
  "kinds": ["decision", "fact"],
  "tags": ["architecture"],
  "sort": "relevance",
  "limit": 20
}
```

### Parameters

- `query`
  - required
  - text query string
- `mode`
  - `"fts"` default
  - `"phrase"`
  - `"prefix"`
  - `"exact"`
- `scope`
  - default: `"auto"`
  - explicit scope path or `"auto"`
- `scope_mode`
  - `"resolved"` default when `scope = auto`
  - `"stack"`
  - `"exact"`
  - `"ancestors"`
- `kinds`
  - optional entry kind filter
- `tags`
  - optional tag filter
- `created_by`
  - optional creator filter
- `include_superseded`
  - default: `false`
- `sort`
  - `"relevance"` default for FTS like modes
  - `"updated_at"`
  - `"created_at"`
  - `"priority"`
- `limit`
  - default: `20`
- `cursor`
  - optional pagination cursor
- `include_resolution`
  - default: `true` when `scope = auto`
- `include_matches`
  - default: `true`

## Search Semantics

### Deterministic, not curated

`cx_search` must return entries because they matched the query and filters, not because a capability layer judged them useful for the current conversation.

### Mode behavior

- `fts`
  - FTS5 query using the existing search backend
  - best default mode for most callers
- `phrase`
  - exact phrase match semantics over the indexed text
- `prefix`
  - prefix query over tokenized terms
- `exact`
  - exact text match over stable fields such as title, tags, and body substring

The point is not to expose every possible SQLite trick. The point is to give operators a small set of stable and understandable query modes.

## Scope Behavior

`cx_search` should reuse the same inferred scope resolver proposed for `cx_browse`.

That means:

- `scope = auto` resolves candidate local scopes from actual store inventory
- uncertainty is exposed in response metadata
- `global` is a last resort, not the first move

Recommended defaults:

- if `scope = auto`, use `scope_mode = resolved`
- if the caller wants wider discovery, use `scope_mode = stack` or `ancestors`

This keeps search locally relevant without hiding what scope was actually searched.

## Ranking and Sorting

Search should not blend ranking heuristics with curation heuristics.

### Default behavior

- `fts`, `phrase`, `prefix` default to `sort = relevance`
- `exact` defaults to `sort = updated_at`

### Allowed explicit sorts

- `relevance`
- `updated_at`
- `created_at`
- `priority`

If the requested sort is incompatible with the mode, the tool should either reject it clearly or document the fallback in metadata. Silent fallback is a bad design here.

## Response Shape

```json
{
  "entries": [
    {
      "id": "019da1c9-318f-7083-bc8f-4d779769f9cd",
      "kind": "decision",
      "title": "Helix and littleorgans are distinct layers of one cognitive system",
      "scope": "global/project:helioy",
      "tags": ["helix", "littleorgans", "architecture"],
      "updated_at": "2026-04-19T10:12:00Z",
      "score": 0.87,
      "snippet": "Helix and littleorgans are separate layers of the same architecture...",
      "matches": {
        "mode": "fts",
        "fields": ["title", "body", "tags"],
        "terms": ["helix", "context"]
      }
    }
  ],
  "search": {
    "query": "helix context",
    "mode": "fts",
    "sort": "relevance",
    "returned": 1
  },
  "resolution": {
    "requested_scope": "auto",
    "resolved_scope": "global/project:helioy",
    "confidence": "high"
  },
  "pagination": {
    "next_cursor": null
  }
}
```

## Match Metadata

Search results should explain why an entry matched.

Useful match metadata:

- matched fields
- normalized query mode
- matched terms
- score when relevance ranking applies

This matters for trust. Search that cannot explain its match basis becomes hard to debug.

## Separation of Concerns

The CM read surface should become:

- `cx_browse`
  - inventory
  - latest or filtered entries
  - local scope by default
- `cx_search`
  - deterministic query interface
  - explicit matching and sorting semantics
- `cx_recall`
  - curated retrieval for agent cognition
  - token budget aware
  - allowed to fuse and shape results for usefulness

This separation is important. Search is about evidence. Recall is about delivery.

## Why Search Should Exist Even If Recall Exists

`cx_recall` is optimized for agent usefulness:

- ancestor walk
- ranking
- token budgeting
- trimmed result sets
- context oriented response shaping

Those are all good features for runtime cognition. They are poor features for debugging, operator trust, and user facing query UX.

A caller often wants:

- "show me all matching decisions about Helix"
- not "show me what the system thinks is probably enough"

That is what `cx_search` should provide.

## Implementation Sketch

Suggested internal split:

- `ScopeResolver`
  - shared with browse
  - resolves `scope = auto`
- `SearchCapability`
  - validates query and mode
  - resolves scope
  - delegates to store search primitives
  - applies explicit filters
  - applies explicit sort
  - returns entries plus search metadata

Likely module shape:

- `cm-capabilities/src/search.rs`
- `cm-capabilities/src/projection/search_view.rs`
- MCP handler `cx_search`
- optional web parity route later

## Open Questions

1. Should `cx_search` support `scope_mode = descendants`, or is that too broad for the first version?
2. Should `exact` search touch full body text, or remain limited to stable fields?
3. Should tag filtering remain strict OR semantics, or allow an `all_tags` mode later?
4. Should `cx_search` expose raw FTS syntax, or keep the mode surface small and hide backend details?

## Recommendation

Add `cx_search` as a first class tool.

Make it deterministic, scope aware, and explainable. Do not overload `cx_recall` with search responsibilities, and do not stretch `cx_browse` into a weak search substitute.
