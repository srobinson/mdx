---
title: Strict Rust Conventions Store Client Cleanup
type: sessions
tags: [backend, rust, clippy, runtime-matters]
summary: Cleaned assigned rtm-store and lilo-rm-client Clippy findings without changing wire or storage behavior.
status: active
source: backend-engineer
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Summary

Fixed the assigned strict Clippy findings for the STORE_CLIENT lane in `runtime-matters`.

Key decisions:

- Removed needless raw string hashes from lifecycle SQL queries without changing SQL text.
- Merged identical client error match arms while preserving emitted `ErrorCode` values.
- Added `#[must_use]` to event watcher builder methods that return `Self`.
- Replaced generic default calls with explicit type defaults in assigned tests.
- Removed unnecessary async wrappers from mock client helpers and updated call sites.

## API Contract

No API contract changes. Runtime RPC wire types, response shapes, and client helper return types are unchanged.

## Database Changes

No schema or migration changes. SQL query text is semantically unchanged. Raw string delimiters were simplified only.

## Security Considerations

No authentication, authorization, or secret handling changes. The cleanup preserves existing daemon socket and test daemon behavior.

## Performance Notes

No runtime performance behavior changed. Removing unnecessary async wrappers avoids constructing unused futures in tests only.

Verification run:

```bash
cargo clippy -p rtm-store -p lilo-rm-client --all-targets --all-features -- -W clippy::pedantic -A clippy::module_name_repetitions -A clippy::missing_errors_doc -A clippy::missing_panics_doc -A clippy::must_use_candidate
cargo fmt --all -- --check
cargo test -p lilo-rm-client --test integration_event_watcher --test integration_typed_helpers --test typed_helpers
cargo test -p rtm-store
```

## Open Items

The requested Clippy command still reports warnings outside the assigned STORE_CLIENT files. They were not edited because the bus directive restricted this lane to its owned files.
