---
title: ALP-1403 Iteration 2 Code Review
type: sessions
tags: [review, fmm, multi-language, registry, ALP-1403]
summary: Review of iteration 2 work on multi-language architecture. Found and committed uncommitted ALP-1411 changes. All quality gates pass.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Summary

Reviewed iteration 2 of ALP-1403 (multi-language architecture: LanguageDescriptor, per-lang modules, named imports). The iteration covered 5 commits (ALP-1410 through ALP-1414):

- ALP-1410: Config default_languages registry migration
- ALP-1408+1409: Fix test hang by replacing probe parser construction with const descriptors
- ALP-1412: Migrate is_reexport_file to registry descriptors
- ALP-1413: Migrate glossary_builder.rs test detection to registry
- ALP-1414: Decompose typescript.rs into directory module (5 files)

Overall assessment: solid execution. The const descriptor approach eliminates the 18-second debug build hang. TypeScript decomposition preserved all 84 tests. Registry integration is clean.

## Issues Found and Fixed

### 1. Uncommitted ALP-1411 changes (dependency_matcher + search.rs)

**Files:** `src/manifest/dependency_matcher.rs`, `src/search.rs`, `src/manifest/mod.rs`, `src/manifest/call_site_finder/{mod.rs,tests.rs}`, `src/manifest/private_members/tests.rs`

The worker completed ALP-1411 (migrate `strip_source_ext` to use registry-derived extensions) but left the changes unstaged. These were functional changes:

- `dependency_matcher.rs`: new `builtin_source_extensions()` OnceLock helper, signature changes to `strip_source_ext`, `dep_matches`, `try_resolve_local_dep`, `build_reverse_deps` to accept `&HashSet<String>`
- `search.rs`: updated `dep_targets_file` and all call sites
- `manifest/mod.rs`: re-export of `builtin_source_extensions`
- Formatting changes from `cargo fmt` in test files

Committed as `review[ALP-1403]: Commit uncommitted ALP-1411 changes`.

## Patterns Observed

- Three separate `OnceLock<ParserRegistry>` / `OnceLock<HashSet<String>>` instances exist across the codebase (`glossary_builder.rs`, `common.rs`, `dependency_matcher.rs`). Each constructs `ParserRegistry::with_builtins()` independently. Not a bug (happens once each), but consolidation into a single shared static would reduce memory and init cost.

- The `register_descriptor_ref` function copies all fields from a const ref. Since `RegisteredLanguage` uses `&'static` slices throughout, this is effectively a memcpy of pointers. Clean design.

## Open Items

None. All quality gates pass (build, fmt, clippy, 57 unit tests + 8 integration tests).
