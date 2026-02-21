---
title: Rust Code Coverage - cargo-llvm-cov vs cargo-tarpaulin (2025-2026)
type: research
tags: [rust, coverage, testing, cargo-llvm-cov, tarpaulin, nextest]
summary: cargo-llvm-cov is the clear winner for Rust workspaces using nextest - native nextest subcommand, cross-platform, LLVM-precision coverage.
status: active
source: quick-research
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Summary

**cargo-llvm-cov** is the recommended tool. It has first-class nextest integration via a dedicated `nextest` subcommand, cross-platform support, LLVM-precision instrumentation (line, region, and branch coverage), and robust workspace handling. Tarpaulin remains viable for simple Linux-only projects but falls short on nextest integration and macOS support.

## Comparison

| Criterion                  | cargo-llvm-cov                          | cargo-tarpaulin                      |
|----------------------------|-----------------------------------------|--------------------------------------|
| Coverage engine            | LLVM instrumentation (`-C instrument-coverage`) | Ptrace (x86_64 Linux) or LLVM       |
| Precision                  | Line, region, branch, MC/DC (unstable)  | Line coverage                        |
| nextest integration        | Native `cargo llvm-cov nextest` subcommand | None documented                    |
| macOS support              | Full                                    | LLVM backend only, limited           |
| Workspace support          | `--workspace`, `--exclude`, `--exclude-from-report`, `--exclude-from-test` | `--workspace`, `--exclude` |
| Doctest coverage           | Yes (nightly required)                  | Yes                                  |
| Output formats             | HTML, LCOV, JSON, Cobertura XML, Codecov, text | HTML, LCOV, JSON, XML, stdout   |
| Proc-macro coverage        | Yes (with caveats around `--target`)    | Limited                              |
| Maintenance                | taiki-e (prolific Rust ecosystem maintainer) | xd009642                          |

## Recommended Setup

### Installation

```sh
# Install cargo-llvm-cov
cargo install cargo-llvm-cov

# The llvm-tools component is installed automatically by cargo-llvm-cov,
# but you can also install it manually:
rustup component add llvm-tools-preview
```

### Basic usage with nextest

```sh
# Run tests with coverage via nextest
cargo llvm-cov nextest --workspace

# Generate HTML report
cargo llvm-cov nextest --workspace --html --output-dir coverage/

# Generate LCOV for CI upload (Codecov, Coveralls)
cargo llvm-cov nextest --workspace --lcov --output-path lcov.info
```

### Including doctests (requires separate merge)

nextest does not run doctests. To get full coverage including docs:

```sh
# Clean previous coverage artifacts
cargo llvm-cov clean --workspace

# Run nextest (collects profraw but does not report yet)
cargo llvm-cov nextest --workspace --no-report

# Run doctests (nightly only, collects additional profraw)
cargo llvm-cov --doctests --no-report

# Merge and produce final report
cargo llvm-cov report --lcov --output-path lcov.info
```

### Justfile recipe

For the attention-matters project (which already uses `cargo nextest run --workspace`):

```just
# Quick text summary
coverage:
    cargo llvm-cov nextest --workspace

# HTML report in coverage/
coverage-html:
    cargo llvm-cov nextest --workspace --html --output-dir coverage/

# LCOV for CI upload
coverage-lcov:
    cargo llvm-cov nextest --workspace --lcov --output-path lcov.info

# Full coverage including doctests (nightly)
coverage-full:
    cargo llvm-cov clean --workspace
    cargo llvm-cov nextest --workspace --no-report
    cargo +nightly llvm-cov --doctests --no-report
    cargo llvm-cov report --html --output-dir coverage/
```

## Workspace Gotchas

1. **Exclude build-only crates from reports**: If a crate has no tests (e.g., a proc-macro crate), use `--exclude-from-report <crate>` to avoid 0% coverage noise.
2. **Proc-macro coverage**: When using `--target`, proc-macro and build script coverage will not display unless `--no-rustc-wrapper` is also passed.
3. **Branch coverage**: Still marked unstable in cargo-llvm-cov. Enable with `--branch` flag but expect rough edges.
4. **MC/DC coverage**: Experimental. Requires nightly.
5. **Binary size**: Instrumented binaries are larger. The tool only instruments necessary crates, but workspace builds will be slower than normal test runs.
6. **profraw conflicts**: Since Rust 1.65+, the default profile filename pattern is `default_%m_%p.profraw` which prevents test binaries from overwriting each other's data. This is handled automatically.
7. **Nightly for doctests**: Doctest coverage requires nightly. The `--doctests` flag will fail on stable.

## GitHub Actions Integration

```yaml
- uses: dtolnay/rust-toolchain@stable
  with:
    components: llvm-tools-preview

- uses: taiki-e/install-action@cargo-llvm-cov
- uses: taiki-e/install-action@nextest

- run: cargo llvm-cov nextest --workspace --lcov --output-path lcov.info

- uses: codecov/codecov-action@v4
  with:
    files: lcov.info
```

## Why Not Tarpaulin

- No native nextest integration. You would need to fall back to `cargo test`.
- Ptrace backend is Linux x86_64 only. macOS requires the LLVM backend, at which point you are using the same underlying mechanism as cargo-llvm-cov but with a less mature wrapper.
- Less granular coverage (line only vs. line + region + branch).
- Less active maintenance trajectory relative to cargo-llvm-cov.
- Historical thread-safety issues with the LLVM backend.

Tarpaulin's one advantage: doctest coverage works on stable (no nightly needed). If that is a hard requirement and you do not use nextest, Tarpaulin is acceptable.

## Sources

- https://github.com/taiki-e/cargo-llvm-cov (README, feature list, workspace flags)
- https://github.com/xd009642/tarpaulin (README, platform support, limitations)
- https://doc.rust-lang.org/rustc/instrument-coverage.html (underlying LLVM instrumentation)
- https://nexte.st/book/test-coverage.html (nextest coverage integration docs)

## Open Questions

- Branch coverage stability: track https://github.com/taiki-e/cargo-llvm-cov/issues/8
- Whether `cargo llvm-cov` will eventually support stable doctest coverage (blocked on rustc stabilization)
