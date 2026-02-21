---
title: Cargo.lock Orphan Entries (Weak Deps) and rustsec/audit-check Ignore Config
type: research
tags: [rust, cargo, cargo-lock, sqlx, rustsec, cargo-audit, github-actions, security]
summary: Cargo.lock orphans from disabled weak optional dependencies are a known unfixed Cargo bug (#10801); rustsec/audit-check@v2 supports an `ignore` input and .cargo/audit.toml for suppressing specific advisories.
status: active
source: quick-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

### Question 1: Cargo.lock Orphan Entries

The orphan entries (sqlx-mysql, rsa) are not a bug in your configuration. They are a known, unfixed defect in Cargo itself: **Cargo issue #10801** ("Disabled optional weak dependencies end up in `Cargo.lock`"), open since late 2022 and still unmerged as of March 2026.

### Question 2: rustsec/audit-check@v2 Ignore Config

The action has a first-class `ignore` input. Specific advisories can also be suppressed project-wide via `.cargo/audit.toml`. Both approaches are stable and documented.

---

## Details: Cargo.lock Orphan Entries

### Root Cause

Cargo uses **weak dependency syntax** in feature declarations, e.g.:

```toml
[features]
postgres = ["dep:sqlx-postgres", "sqlx-core/runtime-tokio"]
mysql    = ["dep:sqlx-mysql",    "sqlx-core/runtime-tokio"]
tls-rustls = ["sqlx-core?/tls-rustls", "rsa"]
```

When a crate (sqlx, in this case) uses `dep_name?/feature` syntax, Cargo's feature resolver registers the weak dependency edge during resolution. Even when the downstream consumer never enables the feature that would activate it, **Cargo's lockfile generator includes the crate** because it uses a resolver pass that activates features before determining whether the dependency is truly reachable.

This is distinct from how `cargo build` operates: the compiler correctly ignores the unused crates. The problem is isolated to the lockfile and `cargo metadata` output.

### Why `cargo update` and `rm Cargo.lock && cargo generate-lockfile` Do Not Help

Both commands invoke the same broken resolver. The resolver re-resolves and re-writes the same entries. There is no "clean" state achievable with current stable Cargo because the root cause is in the resolver logic, not in cached state.

### Current Status

- **Issue**: https://github.com/rust-lang/cargo/issues/10801 (open, labeled `C-bug`, `S-needs-design`)
- **Fix PR**: https://github.com/rust-lang/cargo/pull/16424 (targets `ResolveVersion::V5`, open as of January 2026, under active review by `@Eh2406`)
- **No stable workaround exists** for eliminating the entries from `Cargo.lock` while still using the affected upstream crate (sqlx) with weak dep features in its own manifest.

### Practical Implications

- The entries in `Cargo.lock` are inert: the affected crates are never compiled into your binary.
- `cargo audit` and other tools that read `Cargo.lock` will flag advisories against these phantom entries. This is the most disruptive consequence.
- The correct mitigation for audit false positives is to ignore the affected advisories explicitly (see Question 2 below).

---

## Details: rustsec/audit-check@v2 Ignore Config

### Option 1: Action `ignore` Input (workflow-level)

The `ignore` input accepts a comma-separated list of advisory IDs. The action splits this list and passes each as a separate `--ignore <ID>` flag to `cargo audit`.

```yaml
- uses: rustsec/audit-check@v2.0.0
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    ignore: RUSTSEC-2023-0071
```

Multiple advisories:

```yaml
- uses: rustsec/audit-check@v2.0.0
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    ignore: RUSTSEC-2023-0071,RUSTSEC-2022-0093
```

Source: `action.yml` and `src/input.ts` in https://github.com/rustsec/audit-check — the `ignore` field is parsed via `getInputList`, which splits on commas and newlines.

### Option 2: `.cargo/audit.toml` (project-level, checked into repo)

Place this file at `.cargo/audit.toml` in the project root. The `rustsec/audit-check` action respects it automatically because it delegates to `cargo-audit`, which reads this file.

```toml
[advisories]
ignore = ["RUSTSEC-2023-0071"]
```

Full example config (from https://github.com/rustsec/rustsec/blob/main/cargo-audit/audit.toml.example):

```toml
[advisories]
ignore = ["RUSTSEC-2023-0071"]           # advisory IDs to ignore
informational_warnings = ["unmaintained"]
severity_threshold = "low"

[database]
path = "~/.cargo/advisory-db"
url = "https://github.com/RustSec/advisory-db.git"
fetch = true
stale = false

[output]
deny = ["unmaintained"]
format = "terminal"
quiet = false
show_tree = true

[yanked]
enabled = true
update_index = true
```

Config file can live at:
- `.cargo/audit.toml` (project root, recommended for team consistency)
- `~/.cargo/audit.toml` (user home, affects all projects)

### Which Approach to Use

Use `.cargo/audit.toml` when the suppression should be permanent and visible to all contributors and CI runs. Use the action `ignore` input when the suppression is environment-specific or you want it declared in the workflow file rather than the codebase.

For the sqlx weak-dep false positive scenario, `.cargo/audit.toml` is the correct choice: the false positive is structural (not environment-dependent) and you want it documented in source control with a comment explaining why.

```toml
[advisories]
# RUSTSEC-2023-0071: affects rsa crate, which appears in Cargo.lock as an orphan
# from sqlx's weak optional dependency. Not compiled into this binary.
# See: https://github.com/rust-lang/cargo/issues/10801
ignore = ["RUSTSEC-2023-0071"]
```

---

## Sources

- Cargo issue #10801: https://github.com/rust-lang/cargo/issues/10801
- Cargo fix PR #16424: https://github.com/rust-lang/cargo/pull/16424
- rustsec/audit-check action.yml: https://github.com/rustsec/audit-check/blob/main/action.yml
- rustsec/audit-check src/input.ts: https://github.com/rustsec/audit-check/blob/main/src/input.ts
- cargo-audit audit.toml.example: https://github.com/rustsec/rustsec/blob/main/cargo-audit/audit.toml.example

## Open Questions

- PR #16424 targets `ResolveVersion::V5`. It is unclear when V5 will ship in stable Rust or what the migration path looks like for existing lockfiles.
- The `ignore` field in `audit.toml` suppresses the advisory globally. There is no per-package scoping in `audit.toml` (as of cargo-audit ~0.21). If scoping is needed, the `--ignore` flag is the only option.
