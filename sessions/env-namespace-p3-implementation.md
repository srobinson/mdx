---
title: Env Namespace P3 Implementation
type: sessions
tags: [backend, env-vars, littleorgans, verification]
summary: Implemented P3 env namespace cleanup across runtime git sha, test sentinels, and neutral test knobs.
status: active
source: backend-engineer
confidence: high
created: 2026-06-03
updated: 2026-06-03
---

## Summary

Implemented P3 of the `chore/lilo-env-namespace` work as three commits:

1. `c4c9739` — moved runtime git sha build output from `RTM_GIT_SHA` to `LILO_GIT_SHA` through shared `lilo-build-support`.
2. `f12c4a5` — moved runtime test sentinels to `LILO_TEST_*`, deleted the dead `RTM_TEST_PRINT_CWD` env branch, and kept `.lilo-print-cwd` marker behavior.
3. `a2ad2b4` — moved neutral test knobs under `LILO_DEV_*` or `LILO_TEST_*`, cleaned an unexpected bare `SM` test literal, and isolated the doctor integration fixture from host Docker availability.

Key decision: `spawn_context.rs` was not touched. `RTM_TEST_BAD_BYTES` remains in P4 per orchestrator ruling.

## API Contract

No API endpoints or wire contracts changed. This was an environment namespace and test fixture cleanup.

Build-time contract change:

```typescript
interface RuntimeVersionBuildEnv {
  // emitted by crates/lilo-rm-core/build.rs through lilo-build-support
  LILO_GIT_SHA: string; // 7 char git sha, or "unknown"
}
```

## Database Changes

No database schema changes. No migrations added.

## Security Considerations

- Removed additional legacy `RTM_*` test sentinels from runtime test paths.
- Kept the P4 boundary intact for `spawn_context.rs`, `HELIOY_*`, fixture cleanup, and bare `RTM` compatibility fixtures.
- Preserved explicit env clearing tests for launch and shell resume paths under `LILO_TEST_*` names.

## Performance Notes

No runtime performance changes. Build script behavior now shares `lilo-build-support` git rerun logic so HEAD and git env changes invalidate correctly without duplicating bespoke build logic.

## Verification

Passed:

- `fmm generate && fmm validate`
- `just check`
- `just build`
- `just test` — 645 tests passed
- Targeted rerun before full gate: `cargo nextest run -p lilo-integration-tests doctor_reachability_probe_does_not_warn_on_bare_connect`

`python3 scripts/check-env.sh --check` still exits 1 with deferred P4 residuals only: `HELIOY_*`, `RTM_SESSION_ID`, `RTM_RUNTIME_KIND`, v0.5 fixtures, bare `RTM` compatibility sites, and `RTM_TEST_BAD_BYTES` in `spawn_context.rs`.

Additional `rg` verification found no P3 retired names outside explicitly deferred P4 paths.

## Open Items

- P4 owns `spawn_context.rs`, `HELIOY_*` cleanup, `RTM_SESSION_ID` and `RTM_RUNTIME_KIND`, v0.5 fixtures, and bare `RTM` compatibility sites.
- `scripts/check-env.sh --check` will not pass until P4 removes or intentionally relocates those residual tokens.
