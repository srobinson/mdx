---
title: Handling False Positive cargo-audit Advisories in CI
type: research
tags: [rust, cargo-audit, cargo-deny, ci, security, github-actions]
summary: Complete guide to suppressing false positive RUSTSEC advisories in CI, covering audit.toml, GitHub Actions inputs, CLI flags, and cargo-deny as an alternative.
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

False positive `cargo audit` advisories from orphan transitive dependencies (like `rsa` via `sqlx-mysql` when only using `sqlx-sqlite`) can be suppressed through three mechanisms: the `.cargo/audit.toml` config file, CLI `--ignore` flags, or GitHub Action `ignore` inputs. For projects wanting finer control over dependency graph linting, `cargo-deny` provides a superset of `cargo-audit` functionality with richer ignore semantics. The `audit.toml` approach is the recommended path because it is declarative, version-controlled, and works identically across local development, CI, and all GitHub Action variants.

## 1. The `.cargo/audit.toml` Config File

**Location:** `.cargo/audit.toml` (project-local) or `~/.cargo/audit.toml` (user-global). Project-local takes precedence.

**Recommended configuration for ignoring RUSTSEC-2023-0071:**

```toml
[advisories]
ignore = ["RUSTSEC-2023-0071"]
```

**Full schema (all optional fields):**

```toml
[advisories]
# Advisory IDs to ignore. Treated as "note" severity instead of warning/error.
ignore = ["RUSTSEC-2023-0071"]

# Categories of informational advisories to warn about.
# Options: "unmaintained", "unsound", "notice"
informational_warnings = ["unmaintained"]

# Minimum severity to report. Options: "none", "low", "medium", "high", "critical"
severity_threshold = "none"

[database]
path = "~/.cargo/advisory-db"
url = "https://github.com/rustsec/advisory-db.git"
fetch = true
stale = false

[output]
# Advisory types that cause non-zero exit. Options: "unmaintained", "unsound", "yanked"
deny = ["unmaintained"]
format = "terminal"  # or "json"
quiet = false
show_tree = true  # Show dependency tree for flagged crates

[target]
arch = "x86_64"
os = ["linux", "windows", "macos"]

[yanked]
enabled = true
update_index = true
```

**Key behavior:** Adding an advisory ID to `ignore` downgrades it from warning/error to a "note." It does not suppress it entirely from output, but it will not cause a non-zero exit code.

## 2. GitHub Actions for cargo-audit

### 2a. `rustsec/audit-check@v2.0.0`

The official RustSec GitHub Action. Creates GitHub Check annotations and can auto-create issues for vulnerabilities.

**Inputs:**

| Input | Required | Description | Default |
|-------|----------|-------------|---------|
| `token` | Yes | GitHub token (`${{ secrets.GITHUB_TOKEN }}`) | none |
| `ignore` | No | Comma-separated list of RUSTSEC IDs to ignore | empty |
| `working-directory` | No | Path to Cargo.toml / Cargo.lock | `.` |

**Example workflow:**

```yaml
- uses: rustsec/audit-check@v2.0.0
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    ignore: RUSTSEC-2023-0071
```

**Config file support:** The action runs `cargo audit` under the hood, which reads `.cargo/audit.toml` automatically. Both the `ignore` input and the `audit.toml` file work; using `audit.toml` is preferred because it also applies to local `cargo audit` runs.

### 2b. `actions-rust-lang/audit@v1` (community alternative)

A community-maintained alternative with slightly different input naming and additional features.

**Inputs:**

| Input | Required | Description | Default |
|-------|----------|-------------|---------|
| `TOKEN` | No | GitHub token for issue creation | `github.token` |
| `denyWarnings` | No | Treat warnings as errors | `false` |
| `file` | No | Path to Cargo.lock | auto |
| `ignore` | No | Comma-separated RUSTSEC IDs | empty |
| `createIssues` | No | Auto-create issues per vulnerability | main/master only |
| `workingDirectory` | No | Working directory for cargo audit | repo root |

**Example:**

```yaml
- uses: actions-rust-lang/audit@v1
  with:
    ignore: RUSTSEC-2023-0071
```

This action also reads `.cargo/audit.toml` automatically.

### Choosing between them

Both run `cargo audit` underneath and both read `audit.toml`. The `rustsec/audit-check` action is the official one maintained by the RustSec team. The `actions-rust-lang/audit` action has a cleaner summary output and more granular configuration. Either works; pick based on existing CI patterns.

## 3. `cargo audit` CLI Flags

```bash
# Ignore a single advisory
cargo audit --ignore RUSTSEC-2023-0071

# Ignore multiple advisories
cargo audit --ignore RUSTSEC-2023-0071 --ignore RUSTSEC-2024-0001

# Specify a custom config path
cargo audit --config-path ./my-audit.toml

# JSON output (useful for CI parsing)
cargo audit --json

# Show dependency tree for flagged crates
cargo audit --show-tree
```

The `--ignore` flag and the `audit.toml` `ignore` array have the same effect: the advisory is downgraded to a "note."

## 4. `cargo-deny` as an Alternative

`cargo-deny` is a superset dependency linter that covers advisories, licenses, bans, and source restrictions. It uses its own config file (`deny.toml`).

### Advisory configuration in `deny.toml`

```toml
[advisories]
# Ignore specific advisories with optional reasons
ignore = [
    { id = "RUSTSEC-2023-0071", reason = "rsa is an orphan transitive dep from sqlx-mysql; not compiled when using sqlx-sqlite only" },
]

# How to handle unmaintained crates:
# "all" = fail for any, "workspace" = only direct deps, "transitive" = only indirect, "none" = ignore
unmaintained = "workspace"

# How to handle unsound advisories
unsound = "all"

# Warn when an ignored advisory doesn't match anything in the graph
# Options: "warn", "deny", "allow"
unused-ignored-advisory = "warn"
```

### Advantages over `cargo-audit`

1. **Structured ignore with reasons.** Each suppression can carry a `reason` string, creating a self-documenting audit trail.
2. **Granular scope control.** The `unmaintained`/`unsound` fields accept `"workspace"` or `"transitive"` to apply different policies to direct vs. transitive dependencies.
3. **Unused ignore detection.** The `unused-ignored-advisory` field warns (or errors) when a suppression no longer matches anything in the dependency graph, preventing stale ignores from accumulating.
4. **License and ban checks.** A single tool covers advisories, license compliance, duplicate crate detection, and source restrictions.
5. **Better CI ergonomics.** The `EmbarkStudios/cargo-deny-action` GitHub Action is well maintained.

### Disadvantages

1. **Separate config file.** If you already have `audit.toml`, adding `deny.toml` means two places to maintain advisory ignores.
2. **Heavier tool.** `cargo-deny` resolves the full dependency graph itself; slower than `cargo-audit` on large workspaces.
3. **Different advisory semantics.** `cargo-deny` and `cargo-audit` can produce slightly different results because they resolve the crate graph differently. If you use both, you need to ignore advisories in both configs.

## 5. The RUSTSEC-2023-0071 / sqlx Situation Specifically

This is a well-known false positive pattern. The facts:

- **RUSTSEC-2023-0071** flags the `rsa` crate for the Marvin Attack (timing side-channel in RSA PKCS#1 v1.5 decryption).
- The `rsa` crate is pulled in as a transitive dependency through `sqlx-mysql`, even when only the `sqlx-sqlite` feature is enabled.
- This happens because of a Cargo bug with weak optional dependency syntax (`dep?/feature`). Enabling certain cross-cutting features like `chrono` or `uuid` on sqlx causes `sqlx-mysql` (and `sqlx-sqlite`, `sqlx-postgres`) to appear in `Cargo.lock` despite not being feature-activated. See [sqlx#2911](https://github.com/launchbadge/sqlx/issues/2911) and [sqlx#3538](https://github.com/launchbadge/sqlx/issues/3538).
- The SQLx maintainers closed these issues as "not planned" because the root cause is in Cargo itself ([rust-lang/cargo#10801](https://github.com/rust-lang/cargo/issues/10801)).
- `cargo tree` does not show `sqlx-mysql` as an actual dependency, confirming the crate is not compiled. The advisory is a pure false positive in this scenario.

**Recommended fix:**

```toml
# .cargo/audit.toml
[advisories]
ignore = ["RUSTSEC-2023-0071"]  # rsa is orphan transitive dep from sqlx-mysql; not compiled (sqlx#2911)
```

This is the simplest, most portable solution. The ignore persists across local dev, CI, and all GitHub Action variants.

## Sources Consulted

### GitHub Repositories
- [rustsec/audit-check (v2 branch)](https://github.com/rustsec/audit-check/tree/v2) -- official RustSec GitHub Action
- [actions-rust-lang/audit](https://github.com/actions-rust-lang/audit) -- community cargo-audit GitHub Action
- [cargo-audit audit.toml.example](https://github.com/rustsec/rustsec/blob/main/cargo-audit/audit.toml.example) -- official example config
- [cargo-audit README](https://github.com/rustsec/rustsec/blob/main/cargo-audit/README.md) -- CLI documentation
- [rustsec .cargo/audit.toml](https://github.com/RustSec/rustsec/blob/main/.cargo/audit.toml) -- real-world usage in the rustsec project itself

### SQLx Issues
- [sqlx#2911: Optional features enabled when not activated](https://github.com/launchbadge/sqlx/issues/2911) -- root cause of phantom sqlx-mysql dependency
- [sqlx#3538: chrono makes sqlx-mysql part of Cargo.lock](https://github.com/launchbadge/sqlx/issues/3538) -- additional confirmation

### cargo-deny Documentation
- [cargo-deny advisories config](https://embarkstudios.github.io/cargo-deny/checks/advisories/cfg.html) -- ignore format with reasons
- [cargo-deny vs cargo-audit discussion](https://github.com/EmbarkStudios/cargo-deny/issues/386) -- when to use which

### Advisory Database
- [RUSTSEC-2023-0071](https://rustsec.org/advisories/RUSTSEC-2023-0071) -- the Marvin Attack advisory

## Source Quality Assessment

**Confidence: High.** All findings come from primary sources (official repos, maintainer comments, official documentation). The sqlx false positive pattern is confirmed by multiple independent issue reporters and the SQLx maintainers themselves. The `audit.toml` format is documented with an official example file in the rustsec repo.

## Open Questions

1. **Will Cargo fix the phantom dependency bug?** [rust-lang/cargo#10801](https://github.com/rust-lang/cargo/issues/10801) tracks the weak optional dependency resolution issue. If fixed, `rsa` would no longer appear in `Cargo.lock` and the ignore entry would become unnecessary. The `unused-ignored-advisory` feature in `cargo-deny` would catch this automatically.
2. **Will sqlx restructure to avoid the pattern?** The maintainers closed the issue as "not planned," so this is unlikely without the Cargo-level fix.

## Actionable Takeaways

1. **Immediate fix:** Add `.cargo/audit.toml` with `ignore = ["RUSTSEC-2023-0071"]` and a comment explaining why. This works with both `rustsec/audit-check@v2` and `actions-rust-lang/audit@v1` with zero workflow changes.
2. **If using the Action's `ignore` input:** Pass `ignore: RUSTSEC-2023-0071` in the workflow YAML. This works but is less discoverable than the config file approach.
3. **For long-term maintenance:** Consider migrating to `cargo-deny` with its structured `{ id = "...", reason = "..." }` ignore format. The `unused-ignored-advisory = "warn"` setting will alert you when the ignore becomes stale.
4. **Do not attempt to exclude sqlx-mysql via feature flags.** The phantom dependency is a Cargo resolver bug, not a feature configuration issue. Feature flags will not prevent it from appearing in `Cargo.lock`.
