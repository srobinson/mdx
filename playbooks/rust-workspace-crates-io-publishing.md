---
title: Rust workspace to crates.io with release-plz and a scoped org token
type: playbooks
tags: [rust, cargo, crates-io, github-actions, release-plz, publishing]
summary: Publish selected crates from a Rust workspace to crates.io using release-plz, conventional commits, and a scoped CARGO_REGISTRY_TOKEN.
status: active
project: helioy
related: [rust-binary-workspace-cargo-dist, identity-matters-crates-io-publishing-design]
confidence: high
---

# Rust workspace to crates.io with release-plz and a scoped org token

Use this playbook to publish one or more library crates from a Rust workspace to crates.io. It supports mixed workspaces where some crates are public API crates and the rest are private implementation crates.

The default path uses release-plz for release PRs, version bumps, changelogs, GitHub Releases, git tags, and crates.io publishing. Authentication uses a scoped crates.io token stored as `CARGO_REGISTRY_TOKEN`.

## When To Use

Use this when a Rust workspace has public library crates that should be consumed by other repos.

This playbook is a good fit when:

- You own a crate prefix such as `lilo-*` or `helioy-*`.
- You want release PRs from conventional commits.
- You want the tool that bumps versions to also publish the crates.
- You need first publish and later updates to run without per-crate UI setup.
- Some workspace crates may remain private.

For binary artifacts, use the cargo-dist playbook. A hybrid repo can use release-plz for library crates and cargo-dist for binaries.

## End State

```text
commit on main
  -> release-plz release publishes any unpublished public package versions
  -> release-plz release-pr opens or updates the next release PR
  -> release PR merge bumps versions and changelogs
  -> next main run publishes the bumped crate versions
```

Do not add a separate `publish.yml` unless release-plz cannot own publishing for the repo. A separate publisher creates a second release authority and is easy to race in workspaces with interdependent crates.

## Prerequisites

- Rust stable. Use Rust 1.90 or newer if you rely on native workspace publish dry runs.
- A GitHub repo with Actions enabled.
- A crates.io token named `CARGO_REGISTRY_TOKEN` in repo or org Actions secrets.
- For Helioy repos, a `HELIOY_PAT` Actions secret with `Contents: write` and `Pull requests: write`.
- A crate naming decision. Use `lilo-*` for consumer tier crates and reserve `helioy-*` for enterprise tier crates.

Create the crates.io token at <https://crates.io/settings/tokens>. For a prefix owned by the org, scope it to:

- `publish-new`
- `publish-update`
- crate name pattern such as `lilo-*`

The token must allow both first publish and later updates. A token with only one of those endpoint scopes will fail in one of the two phases.

## Phase 1: Prepare The Workspace

Add or confirm `rust-toolchain.toml`:

```toml
[toolchain]
channel = "stable"
components = ["rustfmt", "clippy"]
```

Add a root `LICENSE`.

Set shared package metadata in the root `Cargo.toml`:

```toml
[workspace.package]
version = "0.1.0"
edition = "2024"
license = "MIT"
repository = "https://github.com/littleorgans/<repo>"
homepage = "https://github.com/littleorgans/<repo>"
authors = ["Your Name"]
rust-version = "1.90"
```

Use path plus version for workspace crate dependencies that will be published:

```toml
[workspace.dependencies]
lilo-foo = { path = "crates/foo", version = "0.1.0" }
lilo-bar = { path = "crates/bar", version = "0.1.0" }
```

For each public crate, include crates.io metadata in `crates/<name>/Cargo.toml`:

```toml
[package]
name = "lilo-foo"
description = "One sentence description shown on crates.io"
readme = "README.md"
version.workspace = true
edition.workspace = true
license.workspace = true
repository.workspace = true
homepage.workspace = true
authors.workspace = true
rust-version.workspace = true
keywords = ["runtime", "agents"]
categories = ["development-tools"]

[lib]
name = "lilo_foo"
path = "src/lib.rs"
```

For each private crate, set `publish = false` in that crate's `Cargo.toml`:

```toml
[package]
name = "internal-helper"
publish = false
```

Add a crate level rustdoc line to each public crate's `src/lib.rs`:

```rust
//! Public API for ...
```

Run a local package check for the crates you plan to publish:

```bash
cargo publish -p lilo-foo -p lilo-bar --dry-run --allow-dirty
```

Fix all packaging failures before wiring automation. Cargo publish verifies the packaged tarball, so files loaded with `include_str!` and crate READMEs must exist inside the package.

## Phase 2: Add The CI Gate

Add `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  local-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: dtolnay/rust-toolchain@stable
      - uses: taiki-e/install-action@just
      - uses: Swatinem/rust-cache@v2
      - run: just check
      - run: just build
      - run: just test

  semver-checks:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - name: Detect public crate source changes
        id: public-crate-changes
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          if git diff --name-only "$BASE_SHA" "$HEAD_SHA" | grep -Eq '^(crates/foo|crates/bar)/(src/|Cargo.toml)|^Cargo.toml$'; then
            echo "changed=true" >> "$GITHUB_OUTPUT"
          else
            echo "changed=false" >> "$GITHUB_OUTPUT"
          fi
      - if: steps.public-crate-changes.outputs.changed == 'true'
        uses: dtolnay/rust-toolchain@stable
      - if: steps.public-crate-changes.outputs.changed == 'true'
        uses: obi1kenobi/cargo-semver-checks-action@v2
        with:
          package: lilo-foo, lilo-bar
```

Adjust runner OS and `just` recipes to match the repo. Keep `cargo-semver-checks` focused on public crates.

## Phase 3: Configure release-plz

Add `release-plz.toml` at the repo root.

For a mixed workspace, default to private and opt public packages in:

```toml
[workspace]
release = false
publish = false
semver_check = true
changelog_update = true
git_tag_name = "{{ package }}-v{{ version }}"
git_release_name = "{{ package }}-v{{ version }}"
release_always = false

[[package]]
name = "lilo-foo"
release = true
publish = true
version_group = "public-api"

[[package]]
name = "lilo-bar"
release = true
publish = true
version_group = "public-api"

[changelog]
header = """# Changelog\n\nAll notable changes documented here.\n"""
commit_parsers = [
  { message = "^feat", group = "Features" },
  { message = "^fix", group = "Bug Fixes" },
  { message = "^perf", group = "Performance" },
  { message = "^refactor", group = "Refactoring", default_scope = "internal" },
  { message = "^doc", group = "Documentation", default_scope = "internal" },
  { message = "^chore", group = "Miscellaneous", default_scope = "internal" },
  { message = "^test", group = "Tests", default_scope = "internal" },
  { message = "^ci", group = "CI", default_scope = "internal" },
]
```

Use the same `version_group` for crates that must release together. This is important when one public crate depends on another at the same version.

Add a `CHANGELOG.md` beside each public crate's `Cargo.toml`, unless you intentionally configure another changelog path:

```markdown
# Changelog

All notable changes documented here.
```

## Phase 4: Add The release-plz Workflow

Add `.github/workflows/release-plz.yml`:

```yaml
name: Release-plz

on:
  push:
    branches:
      - main

permissions:
  contents: write
  pull-requests: write

jobs:
  release-plz-release:
    name: Release-plz release
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0
          token: ${{ secrets.HELIOY_PAT }}

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Run release-plz
        uses: release-plz/action@v0.5
        with:
          command: release
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.HELIOY_PAT }}

  release-plz-pr:
    name: Release-plz PR
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    concurrency:
      group: release-plz-${{ github.ref }}
      cancel-in-progress: false

    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0
          token: ${{ secrets.HELIOY_PAT }}

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Run release-plz
        uses: release-plz/action@v0.5
        with:
          command: release-pr
        env:
          GITHUB_TOKEN: ${{ secrets.HELIOY_PAT }}
```

If the repo does not use a PAT, replace `secrets.HELIOY_PAT` with `secrets.GITHUB_TOKEN`. Keep in mind that PRs opened with the default `GITHUB_TOKEN` usually do not trigger downstream workflows. For Helioy repos, use the PAT.

## Phase 5: First Publish

1. Merge the setup PR to `main`.
2. Watch the `Release-plz release` job.
3. Confirm it publishes every public crate whose current version is missing on crates.io.
4. Confirm `Release-plz PR` opens the next release PR only when package files have relevant commits.

For the first publish, the crates.io token claims the new crate names. No manual `cargo login` and no per-crate crates.io UI setup is required.

## Phase 6: Normal Release Flow

1. Merge a real `feat:`, `fix:`, or `perf:` change that touches files owned by a public crate.
2. release-plz opens or updates a release PR with version and changelog changes.
3. CI runs on the release PR.
4. Merge the release PR.
5. release-plz publishes the new crate version, creates the git tag, and creates the GitHub Release.

Empty conventional commits do not produce release PRs because release-plz attributes changes to packages by touched files.

## Verification Checklist

After setup or release, verify:

- `cargo publish -p <crate> --dry-run --allow-dirty` passes for each public crate.
- `gh run list --workflow Release-plz` shows a green latest run.
- `https://crates.io/crates/<crate>` shows the expected version.
- `https://docs.rs/<crate>` renders useful crate docs.
- `git ls-remote --tags origin '<crate>-v*'` shows the expected tag.
- GitHub Releases contains one release per public crate version.
- No private crate was published.

## Gotchas

### Sibling dev dependencies can break first publish

If a public crate has a `[dev-dependencies]` edge to a sibling public crate at a version that is not on crates.io yet, `cargo publish --dry-run` may fail during verify.

Fix the test layout so dependency direction is one way, or publish the lower level crate first. Prefer moving integration tests to the higher level crate.

### Private crates need two protections

Set `publish = false` in private crate `Cargo.toml` files, and keep `[workspace] release = false` plus `publish = false` in `release-plz.toml`. Then opt in public packages explicitly.

### Package metadata must be inside each published crate

crates.io packages from `crates/foo` cannot rely on repo root files unless Cargo includes them in the package. If a crate has `readme = "README.md"`, that README must live beside that crate's `Cargo.toml` or be included correctly.

Run:

```bash
cargo package -p lilo-foo --list
```

### Version groups only apply to changed packages

release-plz uses `version_group` when packages in the group need to move. If one package depends on another, release-plz can move both to keep the dependency valid. Still verify lockstep packages in the release PR before merging.

### Per crate tags avoid collisions

Do not use `git_tag_name = "v{{ version }}"` for a multi-crate workspace. Multiple crates at the same version will collide. Use:

```toml
git_tag_name = "{{ package }}-v{{ version }}"
git_release_name = "{{ package }}-v{{ version }}"
```

### Token scope has to cover first publish and updates

A new crate needs `publish-new`. A later version needs `publish-update`. The token also needs a name pattern that matches the crate.

### release-plz release does not edit files

`release-plz release` publishes versions already present in the repo. It does not bump `Cargo.toml`. Version and changelog edits come from `release-plz release-pr`.

### Attestations are not part of the default token flow

This playbook does not add SLSA provenance attestations. If you need attestations for `.crate` files, add a separate design for packaging and attesting the exact uploaded artifact. Do not reintroduce a second publisher just to get attestations.

## Operational Notes

- Consumers can depend on pre-1.0 crates with `crate = "0.x"` when they accept compatible patch updates.
- Yank a bad version with `cargo yank --version <version> <crate>` from a logged in maintainer machine.
- Rotate the scoped token on a regular schedule and immediately after any suspected leak.
- If a release partially publishes, fix the root cause and rerun release-plz. It releases unpublished package versions and skips versions already present on the registry.

## Appendix: Trusted Publishing Variant

release-plz also supports crates.io Trusted Publishing.

Use that path when security policy forbids long lived tokens and the per-crate setup cost is acceptable.

Differences from the token path:

1. Do not set `CARGO_REGISTRY_TOKEN` in the workflow.
2. Give the `release-plz release` job `id-token: write`.
3. Configure Trusted Publishing on crates.io for every crate.
4. New crates cannot be first published with Trusted Publishing. Publish each crate once by another approved path, then switch future releases to Trusted Publishing.

## References

- [release-plz GitHub quickstart](https://release-plz.dev/docs/github/quickstart)
- [release-plz release command](https://release-plz.dev/docs/usage/release)
- [release-plz configuration](https://release-plz.dev/docs/config)
- [Cargo publish command](https://doc.rust-lang.org/cargo/commands/cargo-publish.html)
- [crates.io token scopes RFC](https://rust-lang.github.io/rfcs/2947-crates-io-token-scopes.html)
