---
title: Runtime Matters CLI Verb Split
type: sessions
tags: [backend, rust, cli, refactor, runtime-matters]
summary: Split rtm CLI verb handlers out of cli/mod.rs into per-verb modules without changing CLI surface.
status: active
source: backend-engineer
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Summary

Implemented Refactor 2 on `refactor/post-review-cleanup`: split `crates/rtm-cli/src/cli/mod.rs` into per-verb modules while preserving CLI behavior. Commit `7060844` was pushed to `origin/refactor/post-review-cleanup` after Phase B reviewer signoff.

Key decisions:

- Kept `cli/mod.rs` focused on module declarations, `Cli`, private `Command`, out-of-scope `VersionArgs` and `DoctorArgs`, and dispatch.
- Moved each verb handler and its private helper cluster to a verb module.
- Left existing `mcp.rs`, `version.rs`, `doctor.rs`, `daemon.rs`, `initdb.rs`, and `shim.rs` patterns intact.
- Preserved all clap attributes and public argument struct visibility.

## API Contract

No API, RPC, or CLI contract changes were intended or made.

CLI surface preservation was verified byte for byte for these help outputs against baseline commit `70f7ed6`:

- `rtm --help`
- `rtm spawn --help`
- `rtm kill --help`
- `rtm nudge --help`
- `rtm capture --help`
- `rtm validate-target --help`
- `rtm status --help`
- `rtm mcp --help`
- `rtm version --help`
- `rtm doctor --help`
- `rtm events --help`
- `rtm initdb --help`
- `rtm daemon --help`

## Database Changes

None.

## Security Considerations

No auth, persistence, or process isolation behavior changed. The refactor preserved existing validation and error handling. No new `unwrap()` or `expect(` calls were introduced in the new verb files.

## Performance Notes

No runtime performance changes expected. This was a source organization refactor only. File sizes after split:

- `cli/mod.rs`: 94 LOC
- largest new verb file, `spawn.rs`: 128 LOC
- all new verb files are well below the 700 LOC project ceiling

## Verification

Commands run:

```bash
just check
just build
just test
```

Results:

- `just check` passed.
- `just build` passed.
- `just test` passed: 249 tests.
- `cargo test -p rtm-cli --test cli_flags` passed under reviewer verification.
- `cargo test -p rtm-cli --test generated_snapshots` passed under reviewer verification.
- `cargo test -p rtm-cli --test surface_snapshots` passed under reviewer verification.
- `git diff 70f7ed6 HEAD -- crates/rtm-cli/tests/surface_snapshots.rs crates/rtm-cli/tests/cli_flags.rs` was empty under reviewer verification.

## Open Items

None for Refactor 2. Reviewer signed off with: `I sign off on the CLI verb split as currently filed`.
