---
title: mdm config check validation fix
type: sessions
tags: [backend, cli, config, validation]
summary: Centralized mdm config validation and made config check report effective coerced values with errors.
status: active
source: backend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

## Summary

Implemented real `mdm config check` validation while preserving runtime behavior. Runtime loading still warns and coerces invalid values to defaults. `config check` now reports parse and validation errors, exits non-zero, and displays the effective coerced configuration with per-field validity markers.

Key decisions:

- Centralized validation rules in `src/config/validation.ts`.
- Added `loadDetailed()` to expose source file, parse error, unvalidated config, effective config, file config, environment config, and validation issues.
- Suppressed duplicate warnings in `config check` because the top-level CLI config layer already loads and warns once.
- Kept invalid runtime config non-breaking by coercing invalid fields to defaults.

## API Contract

No HTTP API changes.

CLI contract:

```typescript
// mdm config check --json
interface ConfigCheckValue<T> {
  value: T | null;
  source: "default" | "file" | "env";
  valid: boolean;
  errors?: string[];
}

interface ConfigCheckResult {
  valid: boolean;
  sourceFile: string | null;
  errors?: string[];
  config: {
    index: Record<string, ConfigCheckValue<unknown>>;
    search: Record<string, ConfigCheckValue<unknown>>;
    embeddings: Record<string, ConfigCheckValue<unknown>>;
    summarization: Record<string, ConfigCheckValue<unknown>>;
    aiSummarization: Record<string, ConfigCheckValue<unknown>>;
    output: Record<string, ConfigCheckValue<unknown>>;
    paths: Record<string, ConfigCheckValue<unknown>>;
  };
}
```

Invalid configs return exit code 1. Valid configs return exit code 0.

## Database Changes

None.

## Security Considerations

- Malformed TOML is now distinguished from a missing config file and surfaced with file path plus parse message.
- Invalid enum, numeric, boolean, string, string array, and option string fields are rejected by validation and coerced to safe defaults.
- Runtime behavior remains defensive: invalid values are never trusted downstream.

## Performance Notes

- Validation is pure, deterministic, and linear in the number of config fields.
- No new I/O beyond the existing config file and environment reads.
- `config check` reuses loader diagnostics instead of maintaining a separate merge or validation path.

## Open Items

- The local environment used pnpm 11 globally, which auto-ran dependency verification and failed on pnpm build approval metadata. Verification used `npx --yes pnpm@10.28.0`, consistent with the repo documentation requiring pnpm 10+.
- CLI subprocess tests require `dist/cli/main.js`; run `pnpm build` before `pnpm test` when CLI behavior changes.

## Verification

- `npx --yes pnpm@10.28.0 check` passed.
- `npx --yes pnpm@10.28.0 build` passed.
- `npx --yes pnpm@10.28.0 test` passed: 61 files, 1409 passed, 9 skipped.
- Manual invalid provider check returned exit code 1, `valid:false`, effective provider `openai`, source `file`, field `valid:false`, and one stderr warning.


## Follow-up Review Fixes

Addressed PR #41 focused review round:

- Corrected search limit attribution: `search.defaultLimit` owns `defaultLimit <= maxLimit`; `search.maxLimit` validates positive integer independently.
- Restored runtime fallthrough from malformed local `.mdm.toml` to valid global `~/.mdm/.mdm.toml`, while `config check` still reports the local parse error and exits non-zero.
- Derived enum validation values from schema-exported arrays instead of restating unions.
- Removed `readEnvVarsMap` and its re-export.
- Replaced raw `process.exit(1)` in `config check` with `Effect.fail(new ConfigError(...))` so stdout has a chance to flush before the top-level handler exits with user error semantics.
- Tightened numeric environment parsing to strict decimal strings and rejected empty `index.fileExtensions`.
- Added drift guards for validation coverage, generated TOML emission, and config-check output fields.

## Follow-up Verification

- `npx --yes pnpm@10.28.0 check` passed.
- `npx --yes pnpm@10.28.0 build` passed.
- `npx --yes pnpm@10.28.0 test` passed: 62 files, 1415 passed, 9 skipped.
- Pushed commit `ef5cc9209e9c` to PR #41.


## Final Micro Fix

Added the final parse-warning dedupe regression for PR #41. `src/cli/commands/config-cmd.test.ts` now asserts malformed `mdm config check` stderr contains exactly one `[mdm] Failed to parse config file` warning. Manual verification also returned `exit=1 count=1`.

## Final Micro Verification

- `npx --yes pnpm@10.28.0 build` passed before the CLI subprocess test.
- `npx --yes pnpm@10.28.0 vitest run src/cli/commands/config-cmd.test.ts` passed: 1 file, 6 tests.
- `npx --yes pnpm@10.28.0 check` passed.
- `npx --yes pnpm@10.28.0 test` passed: 62 files, 1415 passed, 9 skipped.
- Pushed commit `9973c10cebef` to PR #41.

## Windows CI Test Fix

Addressed the Windows CI failure in PR #41 without changing production loader behavior. The in-process loader fallback test now stubs `HOME`, `USERPROFILE`, `HOMEDRIVE`, and `HOMEPATH` so `os.homedir()` resolves to the isolated fake home on Windows as well as Unix-like systems. The test restores those environment stubs in a `finally` block and keeps the test file below the 700 line threshold at 696 lines.

Verified no other in-process loader/global-config test still depends on `HOME` alone. The remaining `HOME` matches are CLI subprocess tests whose spawned process env already sets the Windows home variables.

## Windows CI Fix Verification

- `npx --yes pnpm@10.28.0 vitest run src/config/loader.test.ts -t "falls through from broken local TOML to valid global config"` passed: 1 test, 52 skipped.
- `npx --yes pnpm@10.28.0 check` passed.
- `npx --yes pnpm@10.28.0 test` passed: 62 files, 1415 passed, 9 skipped.
- Pushed commit `b30d762640b3` to PR #41.
- Bus reply sent to `markdown-matters:general:0:6.1` with `done: b30d762640b3` evidence.
