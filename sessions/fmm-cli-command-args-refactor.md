---
title: fmm CLI Command Args Refactor
type: sessions
tags: [backend, fmm, cli, refactor]
summary: Extracted CLI command argument structs from cli/mod.rs into command modules while preserving CLI behavior.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented the Slice 0 behavior preserving refactor for `fmm` CLI command arguments.

Key decisions:

- Moved clap argument structs from `crates/fmm-cli/src/cli/mod.rs` into command owned modules under `crates/fmm-cli/src/cli/commands/`.
- Kept `Commands` as thin tuple variants that reference CLI specific `*CommandArgs` structs.
- Named the new public CLI adapter structs with the `CommandArgs` suffix to avoid collision with existing MCP transport structs.
- Updated `crates/fmm-cli/src/main.rs` dispatch and CLI parse tests for tuple variants.
- Preserved command names, aliases, flags, defaults, and help output.

Branch and PR:

- Branch: `refactor/cli-commands-split`
- Commit: `ed3bdb7`
- PR: `https://github.com/srobinson/fmm/pull/153`

## API Contract

No HTTP API contract changes.

CLI surface contract preserved:

- `fmm --help`
- `fmm generate --help`
- `fmm search --help`
- `fmm lookup --help`
- `fmm ls --help`

Each captured help output matched the baseline with a clean byte diff.

Rust public CLI enum shape changed internally from struct variants to tuple variants containing `*CommandArgs` structs. The project is pre release, and the required user facing CLI behavior stayed unchanged.

## Database Changes

No database changes.

## Security Considerations

No authentication, authorization, secret handling, or input validation behavior changed.

## Performance Notes

No runtime performance behavior changed. This was a mechanical refactor.

Size outcome:

- `crates/fmm-cli/src/cli/mod.rs`: 719 LOC before, 447 LOC after
- New command argument modules are all well below the 700 LOC file limit

Verification performed:

- `just check`: passed
- `just test`: passed, 1276 tests passed, 3 skipped, doctests ok
- `just ci`: passed, including build
- `git diff --check`: passed
- CLI help byte comparison: passed for root help and 4 representative subcommands

## Open Items

None for Slice 0.
