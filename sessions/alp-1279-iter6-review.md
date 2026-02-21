---
title: "ALP-1279 Iter 6 Review: Performance & Type Safety"
type: sessions
tags: [review, mdcontext, ALP-1279, performance, type-safety]
summary: "Reviewed 5 commits (ALP-1221-1225): parallel I/O, delta embedding, changedPaths watcher, Effect Schema validation, RootContent typing. All clean."
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

Reviewed iteration 6 of ALP-1279 (mdcontext review feedback). Five commits covering performance improvements and type safety enhancements. All 1263 tests pass, typecheck clean, lint clean.

## Commits Reviewed

1. **ALP-1221**: Parallelize file I/O in buildIndex (Phase 1 concurrent read+parse, Phase 2 sequential merge)
2. **ALP-1222**: Delta embedding with `getEmbeddedIds()` and `removeEntries()` on HnswVectorStore
3. **ALP-1223**: Pass `changedPaths` from watcher to buildIndex, skip full directory walk
4. **ALP-1224**: Effect Schema validation for all 7 MCP handler argument sets
5. **ALP-1225**: Type `RawSection.contentNodes` as `RootContent[]`, remove 4 unsafe casts

## Issues Found and Fixed

None. Code is clean.

## Observations

- **Fixture regeneration**: Test suite regenerates `tests/fixtures/cli/.mdcontext/indexes/*.json` with absolute machine-specific paths. Reset to committed state. This is a recurring side effect; the fixtures aren't consumed by any test but get rewritten when the indexer runs against the fixture directory.
- **changedPaths ignoring ignore filter**: The `changedPaths` path in the indexer skips the ignore filter, relying on chokidar's own ignore patterns in the watcher. Acceptable since `changedPaths` is an internal API only used by the watcher, which applies ignore patterns at the chokidar level.
- **Duplicated save/invalidate blocks**: The delta embedding code has two identical save + `invalidateHnswCache` blocks (empty sectionsByDoc and empty sectionsToEmbed paths). Functional duplication, not a bug. Could be extracted but not worth a change.
- **`as string[]` cast on filter result**: `options.changedPaths.filter(...) as string[]` is redundant since `filter` on `readonly string[]` returns `string[]`. Harmless.

## Open Items

None.
