---
title: "context-matters v0.1.0 iteration 1 review"
type: sessions
tags: [review, context-matters, cm-core, rust]
summary: "Fixed FTS sanitization bypass, ScopePath allocation waste, redundant dep. 3 issues resolved, 3 tests added."
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

Reviewed iteration 1 of ALP-1367 (context-matters v0.1.0). Five commits implementing cm-core domain types, ContextStore trait, query helpers, unit tests, project scaffolding, and npm distribution package. Overall quality is high. Found and fixed 3 issues.

## Issues Found and Fixed

### 1. FTS sanitization bypass (query.rs)

`sanitize_fts_input` had a code path where balanced quotes caused the entire input to pass through without sanitization. Non-quoted portions containing FTS5 syntax characters (parens, carets, NEAR operators) would reach the MATCH expression and cause runtime SQL errors.

**Fix:** Rewrote the balanced-quote path to parse quoted vs non-quoted segments independently. Quoted phrases are preserved verbatim; non-quoted text is sanitized word by word. Added `sanitize_unquoted_words` helper.

**Tests added:** 3 new tests covering balanced-quote edge cases.

### 2. Unnecessary allocation in ScopePath::TryFrom<String> (types.rs)

`TryFrom<String>` took an owned `String`, borrowed it for validation via `parse(&s)`, which then cloned it with `input.to_string()`. The original owned string was dropped.

**Fix:** Extracted `validate(&str) -> Result<(), ScopePathError>` from `parse`. `TryFrom<String>` now calls `validate` then wraps the original owned string directly, avoiding the clone.

### 3. Redundant dev-dependency (cm-core/Cargo.toml)

`serde_json` appeared in both `[dependencies]` and `[dev-dependencies]`. The dev-dependency entry was redundant.

**Fix:** Removed the `[dev-dependencies]` section.

## Patterns Observed

- Code quality across the iteration is consistently good. Types are well-documented, error handling is thorough, serde attributes are correct.
- The FTS sanitization pattern of "trust user input when quotes look balanced" is a recurring footgun. Any sanitization function with an early-return "looks safe" path deserves scrutiny.
- The worker agent consistently produces clean clippy output and well-structured tests.

## Open Items

None. All issues resolved.
