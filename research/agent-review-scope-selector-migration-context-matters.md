---
title: Agent review for context-matters scope selector migration
type: research
tags: [context-matters, scope, review, linear]
summary: Agent review requested changes, then the scope selector spec and Linear issues were tightened.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

The Agent Review Step found the scope selector migration direction architecturally correct, but not tight enough for a breaking public API change. The spec and Linear issues were updated to explicitly reject removed public inputs, remove public `scope_mode`, cover cm-web write request DTOs, define strict inferred write policy, and strengthen vertical tests and verification.

## Project Metadata

- Project: context-matters
- Parent Linear issue: `ALP-2054`
- Spec: `~/.mdx/projects/context-matters-spec-scope-selector-migration.md`
- Review artifacts:
  - `~/.mdx/research/scope-selector-migration-architecture-review-context-matters.md`
  - `~/.mdx/research/coverage-review-scope-selector-migration-context-matters.md`

## Architecture

Review confirmed the intended boundary:

- `cm-core` keeps exact durable `ScopePath` and does not own cwd inference.
- `cm-capabilities` owns unresolved `ScopeSelector` and cwd inference.
- `cm-cli` and `cm-web` parse public wire inputs, reject removed fields, and delegate typed requests to capabilities.

## Key Patterns

- Removing a public field from docs or schemas is insufficient. Serde and web query parsing can silently ignore unknown fields unless strict rejection is implemented.
- For breaking API migrations, tests must assert both the accepted new path and the rejected old path.
- Public request terms and persisted output terms can differ, but the compatibility boundary must be explicit.

## Detailed Findings

### Changes requested by review

- Explicitly reject public `scope_path`, `auto`, and public input `scope_mode`.
- Remove `scope_mode` from public request inputs. It may remain output metadata only.
- Add cm-web dedicated create and merge request DTOs so public write bodies use `scope`, not `cm_core::NewEntry.scope_path`.
- Define inferred write policy exactly: writes require one unique high confidence candidate.
- Require rejected inferred writes to create no entries and no scope rows.
- Add linked worktree fixture where source repo name differs from worktree directory name.
- Add MCP schema scans, protocol rejection tests, CLI flag tests, cm-web search/export coverage, frontend serialization tests, feed URL migration tests, generated artifact scans, doc tests, and clean diff verification.

### Actions taken

- Updated `~/.mdx/projects/context-matters-spec-scope-selector-migration.md` with all review decisions.
- Updated Linear issues `ALP-2054` through `ALP-2065` with stricter acceptance criteria and file targets.
- Closed the third review agent after repeated waits because it did not return.

## Dependencies

- Linear project: `context-matters`
- Parent issue: `ALP-2054`
- Updated subissues: `ALP-2055` through `ALP-2065`

## Relevance to Helioy

This review protects the memory system from another silent scope placement bug. The updated plan forces public API rejection tests and worktree-aware inference before implementation begins.

## Open Questions

No blocking questions remain for planning. Implementation still needs to decide the concrete test seam for git metadata detection.
