---
title: "temp_env crate: scoped env var overrides for Rust tests"
type: research
tags: [rust, testing, env-vars, temp-env, nextest, edition-2024]
summary: temp_env wraps unsafe set_var/remove_var behind a ReentrantMutex; works with nextest but has known data race edge cases; edition 2024 unsafety is encapsulated because the crate compiles as edition 2021
status: active
source: quick-research
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Summary

`temp_env` v0.3.6 provides scoped environment variable overrides for tests via closure-based APIs. It calls `std::env::set_var`/`remove_var` internally (no avoidance), wrapping them behind a `parking_lot::ReentrantMutex` to serialize access. The crate compiles as edition 2021, so the unsafe boundary does not propagate to callers even if the consuming crate uses edition 2024. It is compatible with `cargo nextest` (process-per-test isolation makes the mutex largely redundant). There are open issues about data races in threaded scenarios and no concrete plan yet for edition 2024 migration.

## 1. API

| Function | Signature (simplified) | Purpose |
|----------|----------------------|---------|
| `with_var` | `(key, Option<value>, closure) -> R` | Set or unset a single var for the closure's duration |
| `with_var_unset` | `(key, closure) -> R` | Unset a single var for the closure's duration |
| `with_vars` | `([(key, Option<value>)], closure) -> R` | Set/unset multiple vars |
| `with_vars_unset` | `([key], closure) -> R` | Unset multiple vars |

All functions:
- Return the closure's return value (`-> R`)
- Restore original values on drop (RAII via `RestoreEnv` struct)
- Restore even on panic (Drop runs during unwind)
- Support async closures via the `async_closure` feature flag (requires Rust 1.64+)

Usage for the HOME-unset case:

```rust
temp_env::with_vars(
    [("HOME", None::<&str>), ("USERPROFILE", None::<&str>)],
    || {
        let result = expand_tilde("~/foo/bar");
        assert!(result.is_err());
    },
);
```

## 2. Internal unsafe handling

The crate **does** call `std::env::set_var` and `std::env::remove_var` directly:

```rust
fn update_env<K, V>(key: K, value: Option<V>)
where K: AsRef<OsStr>, V: AsRef<OsStr>
{
    match value {
        Some(v) => env::set_var(key, v),
        None => env::remove_var(key),
    }
}
```

No `unsafe` blocks in the crate source. This works because temp_env declares `edition = "2021"` in its own Cargo.toml. In edition 2021, `set_var`/`remove_var` are safe functions. Each crate in a workspace compiles under its own declared edition, so a top-level edition 2024 crate can depend on temp_env without any unsafe propagation.

Serialization: a static `ReentrantMutex<()>` (from `parking_lot`) guards all env modifications. Tests that use temp_env run serially with respect to each other. However, this only protects against other temp_env callers; it does not protect against direct `env::var` reads on other threads.

## 3. nextest compatibility

Fully compatible. nextest runs each test as a separate process, providing natural isolation. Under nextest:

- Each test process gets its own copy of the environment
- Mutations in one test cannot affect another
- The ReentrantMutex is largely unnecessary (but harmless)
- No data race risk between tests

This makes temp_env + nextest the safest combination for env var testing.

## 4. Version and maintenance

- **Latest version**: 0.3.6
- **Rust edition**: 2021
- **MSRV**: 1.63.0
- **License**: MIT OR Apache-2.0
- **Dependencies**: `parking_lot ^0.12.3` (required), `futures ^0.3.31` (optional, for async)
- **Last commit**: January 2025
- **Stars**: 44
- **Open issues**: 4 (including #34 about edition 2024 migration, #36 about data races)

Maintenance is moderate. The crate is small and focused, so low commit frequency is expected. No edition 2024 migration planned yet (would bump MSRV to 1.85).

## 5. Known issues

**Issue #34 - Edition 2024 unsafe migration**: No action taken. Maintainer's position: they intentionally hide the unsafety for test ergonomics. Not upgrading to edition 2024 until forced.

**Issue #36 - Data races**: A user reported that `with_var` modifications can leak across tests when using the default `cargo test` runner (which runs tests as threads in a single process). The mutex serializes temp_env callers, but a test that reads `env::var("X")` without going through temp_env can still observe stale/modified values if timing aligns. This is a fundamental limitation of in-process env mutation, not a temp_env bug.

## 6. Alternatives

### Option A: cargo nextest (process isolation)
- Run each test in its own process
- Use `unsafe { env::set_var(...) }` / `unsafe { env::remove_var(...) }` directly in tests
- Complete isolation, no mutex overhead
- You already use nextest (`just test` runs `cargo nextest run`)
- Downside: `cargo test --doc` still runs in-process, so doc tests with env mutation need care

### Option B: `Command::env` / `Command::env_remove` (for CLI integration tests)
- Already used in am-cli integration tests
- Spawns a child process with modified env
- Completely safe, no mutation of the parent process
- Only works for subprocess-based tests

### Option C: `serial_test` crate
- Provides `#[serial]` and `#[parallel]` attributes
- Serializes tests that share global state (env, filesystem)
- Does not handle env var mutation itself; you still call set_var/remove_var
- Useful with `cargo test` (thread-based) but redundant with nextest

### Option D: Direct `unsafe` blocks (edition 2024)
- Write `unsafe { env::set_var(...) }` with a SAFETY comment
- Honest about what is happening
- Requires manual restore-on-drop logic (or combine with a small RAII wrapper)
- Most transparent option

## Recommendation for this project

The project already uses temp_env in `am-store/src/config.rs` tests and nextest as the test runner. This is a sound combination:

1. temp_env handles the `set_var`/`remove_var` calls internally (edition 2021, no unsafe needed at your call site)
2. nextest provides process isolation, eliminating cross-test data race risk
3. CLI integration tests already use `Command::env_remove("HOME")`, which is the safest approach

No changes needed. temp_env is appropriate for unit tests that need to verify behavior with HOME unset. The edition mismatch (your crate: 2024, temp_env: 2021) is by design in Rust's edition system - each crate compiles under its own edition.

## Sources

- https://docs.rs/temp-env/latest/temp_env/
- https://github.com/vmx/temp-env (README, src/lib.rs, issues #34, #36)
- https://doc.rust-lang.org/edition-guide/rust-2024/newly-unsafe-functions.html
- https://nexte.st/docs/design/how-it-works/
- https://docs.rs/serial_test/latest/serial_test/

## Open questions

- Will temp_env ever migrate to edition 2024? If so, they would need to add `unsafe` blocks internally, which is a cosmetic change (the actual safety story does not change).
- Issue #39 proposes an RAII-style API (guard-based instead of closure-based). Could be more ergonomic if adopted.
