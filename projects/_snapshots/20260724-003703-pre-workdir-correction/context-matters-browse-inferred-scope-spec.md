---
title: context-matters browse inferred scope spec
type: projects
tags: [context-matters, cx-browse, scope, inference, mcp]
summary: Proposal for resolving local scope candidates for cx_browse without assuming clean scope naming.
status: draft
project: context-matters
confidence: high
created: 2026-04-19
updated: 2026-04-19
related: [context-matters-spec-mcp-server-and-tools, cm-capabilities-shared-application-layer-for-context-matters]
---

# context-matters browse inferred scope spec

## Problem

`cx_browse` currently behaves like a global latest entries feed unless the caller provides an explicit scope. That breaks operator expectations. When an agent is working inside a repo, browse should start from the most plausible local scope, not from unrelated recent writes somewhere else in the store.

The challenge is that scope paths are user defined. They drift. They creep. They are not guaranteed to align cleanly with filesystem structure. Simple `cwd -> scope path` mapping will be wrong often enough to damage trust.

## Goal

Make `cx_browse` locally relevant by default without pretending scope inference is exact.

## Non Goals

- Do not solve tag quality in this design.
- Do not change `cx_recall` semantics.
- Do not require one canonical scope naming convention before browse becomes useful.

## Core Decision

`cx_browse` should default to `scope = auto`.

`auto` means resolve and rank candidate scopes from available evidence, then browse the best local scope or small local scope set. It does not mean derive one invented scope string from the current working directory.

## Design Principles

1. Infer from existing store inventory, not from path strings alone.
2. Prefer local specificity over global recency.
3. Surface uncertainty in the result metadata.
4. Fall back gradually. Do not jump straight to `global`.
5. Keep browse deterministic and inspectable.

## Proposed API Shape

### Request

```json
{
  "scope": "auto",
  "scope_mode": "resolved",
  "limit": 20,
  "kind": "decision",
  "tag": "architecture"
}
```

### Parameters

- `scope`
  - default: `"auto"`
  - accepts explicit scope path or `"auto"`
- `scope_mode`
  - `"resolved"`: browse the highest confidence resolved scope
  - `"stack"`: browse a small ranked scope set, usually repo then project
  - `"exact"`: only valid when `scope` is explicit
- `cwd`
  - optional override for transports that cannot rely on process cwd
- `include_resolution`
  - default: `true`
  - include scope inference metadata in the response

## Resolution Model

The resolver should work in four stages.

### 1. Gather signals

Signals may include:

- current working directory
- repo basename from cwd
- project basename from cwd
- current session scope, if one exists
- recent writes in this session
- recent writes by this agent
- exact matches against stored scope segments
- aliases from optional local config

### 2. Build candidate scopes

Candidates must come from scopes that already exist in the store. The resolver should not fabricate a scope path and assume it is valid.

For a cwd like `/Users/alphab/Dev/LLM/DEV/helioy/fmm`, plausible candidates might be:

- `global/project:helioy/repo:fmm`
- `global/project:helioy`
- `global`

### 3. Score candidates

Suggested scoring factors:

- exact repo segment match
- exact project segment match
- specificity, repo beats project, project beats global
- recent local activity in the candidate scope
- recent local activity in descendant or sibling scopes
- explicit alias match
- session affinity, if the current session has already written there

### 4. Choose browse strategy

- High confidence: browse the top candidate only
- Medium confidence: browse the top two local candidates as a stack
- Low confidence: browse project scope if available
- Very low confidence: browse global only with an explicit warning in metadata

## Response Metadata

When `scope = auto`, the response should include resolution metadata.

```json
{
  "entries": [...],
  "resolution": {
    "requested_scope": "auto",
    "resolved_scope": "global/project:helioy/repo:fmm",
    "scope_mode": "resolved",
    "confidence": "high",
    "candidates": [
      "global/project:helioy/repo:fmm",
      "global/project:helioy",
      "global"
    ],
    "signals": [
      "cwd repo basename matched existing repo scope",
      "cwd parent basename matched existing project scope"
    ]
  }
}
```

This metadata is important. Scope inference that cannot explain itself will not be trusted.

## Default Behavior

Recommended defaults for `cx_browse`:

- `scope = auto`
- `scope_mode = resolved`
- `include_resolution = true`
- `include_superseded = false`
- order by `updated_at desc`

This produces a local inventory view rather than a global activity feed.

## Fallback Rules

1. If there is an active session scope, prefer it.
2. If cwd maps confidently to an existing repo scope, use it.
3. Otherwise use the matching project scope.
4. Otherwise use a small stack of plausible local scopes.
5. Use `global` only as the final fallback.

## Why Not Exact CWD Mapping

Exact `cwd -> scope` mapping assumes naming hygiene that does not exist:

- projects may have multiple repos with overlapping names
- scope names may be historical or shorthand
- repo roots and scope labels may diverge
- some useful scopes are project level, not repo level

A candidate ranking model fits the real system better than a canonical mapping rule.

## Separation of Concerns

This design keeps the CM tool surface coherent:

- `cx_browse`: local inventory with inferred scope resolution
- `cx_search`: deterministic query interface, future work
- `cx_recall`: curated retrieval for agent cognition

Browse should answer: what is here?

Recall should answer: what should the agent see now?

## Implementation Sketch

Suggested internal split:

- `ScopeResolver`
  - collects signals
  - loads candidate scopes from store inventory
  - scores and ranks candidates
- `BrowseCapability`
  - accepts `scope = auto`
  - delegates to `ScopeResolver`
  - fetches entries from resolved scope or scope stack
  - returns entries plus resolution metadata

## Open Questions

1. Should `auto` consider recent agent writes across projects, or is that too sticky?
2. Should `scope_mode = stack` merge results across repo and project scopes, or show grouped sections?
3. Should explicit aliases live in config, in CM itself, or both?
4. How much of the resolution trace should be exposed by default?

## Recommendation

Ship inferred scope for `cx_browse` as a resolver with confidence and explainability. Do not ship a hidden `cwd -> scope` guess. Browse should become locally relevant by default, while remaining honest about uncertainty.
