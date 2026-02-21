---
title: FMM bare Rust test module classification
type: sessions
tags: [backend, fmm, rust, test-classification]
summary: Added precise classification for bare Rust tests.rs and test.rs submodule files.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented and shipped commit `d627dcf` on `nancy/ALP-2707`: `fix: classify bare tests.rs and test.rs Rust submodule files as tests`.

The fix classifies idiomatic Rust submodule test files named `tests.rs` and `test.rs` without overmatching names like `wrtests.rs` or `protest.rs`. The change was reviewed through the Phase A and Phase B mail workflow, then pushed to `origin/nancy/ALP-2707`.

## API Contract

No API endpoints were added or changed.

Classifier contract affected:

```rust
Config::default().is_test_file("crates/fmm-core/src/manifest/private_members/tests.rs") == true
Config::default().is_test_file("crates/fmm-core/src/manifest/private_members/test.rs") == true
Config::default().is_test_file("crates/whatever/wrtests.rs") == false
Config::default().is_test_file("crates/whatever/protest.rs") == false
```

Convention layer contract affected:

```rust
ConventionRegistry::with_builtin_conventions(&parser_registry).is_test_file("src/tests.rs") == true
ConventionRegistry::with_builtin_conventions(&parser_registry).is_test_file("src/test.rs") == true
ConventionRegistry::with_builtin_conventions(&parser_registry).is_test_file("src/wrtests.rs") == false
ConventionRegistry::with_builtin_conventions(&parser_registry).is_test_file("src/protest.rs") == false
```

## Database Changes

No database schema changes.

The file classification logic is read time logic over file paths. No index migration or regeneration is required for the classifier predicate itself. Existing local `.fmm.db` state can still report stale schema mismatches through MCP, which is separate from this fix.

## Security Considerations

No authentication, authorization, or data mutation surfaces changed.

The implementation avoids overbroad filename suffix matching. It uses path boundary patterns `"/tests.rs"` and `"/test.rs"` rather than raw suffixes `"tests.rs"` or `"test.rs"`, preventing false positives for source files whose names merely end in those strings.

## Performance Notes

The fix adds two short string checks to the existing `path_contains` vectors in config defaults and convention defaults. Runtime impact is negligible.

Verification performed:

- `just check` passed.
- `just test` passed: 1217 tests passed, 3 skipped, doctests ok.
- `./target/debug/fmm ls --filter source --limit 1` reported 180 files and 33,914 LOC after the fix.
- `./target/debug/fmm ls --filter source --pattern 'tests.rs'` reported 0 files.
- `./target/debug/fmm ls --filter tests --pattern 'tests.rs'` reported the 10 bare `tests.rs` files.

## Open Items

- The Rust parser descriptor cannot precisely express bare `tests.rs` and `test.rs` today because `LanguageTestPatterns` has no `path_contains` field and `ParserRegistry::is_language_test_file` compares only basenames against suffixes and prefixes.
- The convention layer was updated as the correct mirror for glossary filtering without expanding scope into a parser descriptor matcher redesign.
- A pre-existing top level edge case remains in `path_pattern_matches`: leading slash patterns also match top level paths through `starts_with(root_pattern)`. This was reviewed and accepted as non blocking for this change.
