---
title: ALP-1279 Iter 1 Review - mdcontext CLI flag and schema fixes
type: sessions
tags: [review, mdcontext, cli, flag-schemas]
summary: "Review of 5 commits (ALP-1200 through ALP-1204). Found and fixed 2 issues in flag-schemas.ts: missing --provider flag and missing duplicates command schema."
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

Reviewed iteration 1 of ALP-1279 (Review Feedback Mar 13 2026) covering 5 commits across 6 files in the mdcontext project. The work addressed security (API key redaction, schema validation), CLI completeness (help registry, flag schemas, TTY checks).

## Issues Found and Fixed

### 1. Missing `--provider` flag in searchSchema (flag-schemas.ts)

The `--provider` option is defined in `search.ts` (line 222) as `Options.choice('provider', ['openai', 'ollama', 'lm-studio', 'openrouter', 'voyage'])` but was absent from `searchSchema` in `flag-schemas.ts`. Same bug class as ALP-1203: the argv preprocessor rejects unknown flags before Effect CLI processes them.

**Fix:** Added `{ name: 'provider', type: 'string', description: '...' }` to `searchSchema.flags`.

### 2. Missing `duplicates` command schema (flag-schemas.ts)

ALP-1202 added duplicates to the help registry and main help listing but did not add a `duplicatesSchema` to the `commandSchemas` map. Running `mdcontext duplicates --min-length 100` would fail because the preprocessor has no schema for the command's flags.

**Fix:** Added `duplicatesSchema` with `--min-length`, `-p/--path`, `--json`, `--pretty` flags and registered it in `commandSchemas`.

## Patterns Observed

- The argv preprocessor / flag-schemas.ts is a parallel source of truth for CLI flags alongside the Effect CLI command definitions. Any new command or flag added to a command must be mirrored in both places. This is a recurring gap.
- The 5 commits under review were well structured: correct schemas matching TypeScript types, proper Effect error handling patterns, clean sensitive field redaction logic.

## Verification

- `just check`: clean (typecheck + lint + format)
- `just test`: 1133 passed, 9 skipped, 0 failed

## Open Items

None. All fixes committed.
