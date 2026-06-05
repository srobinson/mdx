---
title: F6 Seam Lint Implementation
type: sessions
tags: [backend, littleorgans, lilo-sys, seam-lint, ci]
summary: Added the platform seam guardian lint and wired it into Moon CI, just, and workspace cfg hygiene.
status: active
source: backend-engineer
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Summary

Implemented F6 of the `refactor/lilo-sys-platform-seam` batch in commit `71bd699`.

The change adds `scripts/check-seam.sh`, a CI guardian that blocks raw platform seam tokens outside `crates/lilo-sys`. It strips inline test gated Rust items before scanning, prunes test and support paths, and keeps the single approved `libc::SIG*` mapping in `internal/runtime/daemon/src/signal.rs` scoped to that token class only.

The lint is wired into root `moon.yml`, the `justfile`, and workspace Rust lint configuration.

## API Contract

No API endpoints or wire schemas changed.

Operational contract:

```text
just check-seam
moon run littleorgans:check-seam
moon ci
```

`check-seam` fails when production Rust outside `crates/lilo-sys` contains any forbidden OS seam token. It exits cleanly for inline `#[cfg(test)]` and `#[cfg(all(test, ...))]` items, test paths, bench paths, and `*test_support*` paths.

## Database Changes

No schema, migration, or index changes.

## Security Considerations

The lint enforces platform seam centralization. This reduces accidental raw OS access outside the system boundary and keeps future credential, signal, socket, and process primitives behind the reviewed `lilo-sys` surface.

Workspace cfg hygiene now denies `unexpected_cfgs`, so accidental custom cfg names fail during Cargo checks.

## Performance Notes

The lint is file based and completed inside `moon ci` in about three seconds on the current tree. It prunes large generated and build directories through `find` and scans only candidate Rust source files.

## Verification

Completed before commit:

- `bash scripts/check-seam.sh`, passed.
- Temporary inline `#[cfg(test)]` and `#[cfg(all(test, unix))]` seam tokens, passed after stripping.
- Temporary production `UnixStream` outside `crates/lilo-sys`, failed as expected.
- Temporary production `libc::SIGTERM` outside `crates/lilo-sys`, failed as expected.
- Temporary non SIG seam token in `internal/runtime/daemon/src/signal.rs`, failed as expected.
- `bash -n scripts/check-seam.sh`, passed.
- `cargo check --workspace`, passed.
- `moon ci`, passed with 7 tasks completed and 632 tests passed.

## Open Items

Reviewer `S|B` sign off was received for commit `71bd699` after independent adversarial verification and `moon ci`. No push was performed.
