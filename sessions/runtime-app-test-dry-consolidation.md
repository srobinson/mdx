---
title: Runtime app test DRY consolidation
type: sessions
tags: [backend, rust, tests, dry, runtime-app]
summary: Consolidated duplicated lilo-runtime-app test and bench helpers under tests/common.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Consolidated duplicated test and bench helpers in `lilo-runtime-app` while staying inside the `internal/runtime/app/tests/**` and `internal/runtime/app/benches/**` lane. The change promotes shared command construction, headless spawn request construction, polling helpers, child exit polling, SIGKILL scenario setup, Docker E2E daemon setup, and benchmark sample parsing through `tests/common`.

## API Contract

N/A. Test and benchmark helper refactor only. No public API, CLI contract, or wire schema changed.

## Database Changes

None.

## Security Considerations

No authentication, authorization, or production runtime behavior changed. The refactor preserved existing test assertions around lifecycle status, Docker isolation rejection, tmux behavior, and runtime event reporting.

## Performance Notes

No production performance change. Benchmark helper parsing now reuses `common::bench_sample_count` in both runtime app benches.

Verification completed:

- `cargo clippy -p lilo-runtime-app --all-targets -- -D warnings`
- `cargo test -p lilo-runtime-app`

## Open Items

The research note also listed a production duplicate in `internal/runtime/app/src/cli/version.rs` and `internal/runtime/app/src/cli/doctor.rs`. That was intentionally left untouched because the assigned lane allowed only runtime app tests and benches.
