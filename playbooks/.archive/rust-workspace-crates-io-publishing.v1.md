---
title: Rust workspace → crates.io with release-plz and a scoped org token
type: playbooks
tags: [rust, cargo, crates-io, github-actions, release-plz, publishing, provenance]
summary: Recipe for publishing a Rust workspace to crates.io using release-plz, a scoped org-level CARGO_REGISTRY_TOKEN, and SLSA-3 provenance attestations
status: active
project: identity-matters
related: [rust-binary-workspace-cargo-dist, identity-matters-crates-io-publishing-design]
confidence: high
---

# Rust workspace → crates.io with release-plz and a scoped org token

Take a Rust workspace from "path-dep only" to "0.1.0 on crates.io", with all subsequent releases driven by conventional commits and zero per-crate manual setup. Battle-tested on `identity-matters` (lilo-im-core/stub/store, May 2026).

> The original version of this playbook used OIDC Trusted Publishing with per-crate UI configuration. We switched to a scoped org-level `CARGO_REGISTRY_TOKEN` after the second product onboarding, because the per-crate Trusted Publishing dance does not scale across products. The OIDC path still works and remains documented in [Appendix A](#appendix-a-oidc-trusted-publishing-variant) for higher-security needs.

## When to use

Use this when you want to ship one or more Rust library crates to crates.io and:

- Have an org that owns a crate-name prefix (`lilo-*`, `helioy-*`, etc.).
- Want zero manual UI steps per crate.
- Want releases driven by conventional commits (`feat:`, `fix:`, `perf:`).
- Want SLSA-3 provenance attestations on every `.crate` tarball.

**See also**: [`rust-binary-workspace-cargo-dist`](rust-binary-workspace-cargo-dist.md) for shipping a binary via cargo-dist. The two playbooks coexist for hybrid workspaces — both workflows can fire from the same GH Release event.

## End-state architecture

```
  Conventional commit on main (feat/fix/perf)
        │
        ▼
  release-plz.yml fires (auth: HELIOY_PAT)
        │ opens release PR with version bump + CHANGELOG
        ▼
  PR merged (CI green, auto-merge if you wire it)
        │
        ▼
  release-plz creates tag(s) + GH Release(s)
        │ release.published
        ▼
  publish.yml fires
        │ cargo publish --workspace
        │   env: CARGO_REGISTRY_TOKEN (org-level, scoped to <prefix>-* + publish-new + publish-update)
        ▼
  cargo package --workspace --allow-dirty   # rematerialize .crate files
        │
        ▼
  attest-build-provenance signs each .crate (uses GitHub OIDC, separate from crates.io)
```

## Prerequisites

- **Rust 1.90+** — `cargo publish --workspace` was stabilized September 2025.
- **GitHub org** with Workflow Permissions set to "Read and write" + "Allow GitHub Actions to create and approve pull requests" (see [Gotcha #4](#4--org-level-workflow-permissions-block-github_token-from-creating-prs)).
- **Two org-level secrets** (Settings → Secrets and variables → Actions → New organization secret, visible to the relevant repos):
  - `CARGO_REGISTRY_TOKEN` — crates.io API token, scoped to `publish-new` + `publish-update` + crate-name pattern `<prefix>-*` (e.g., `lilo-*`). Generate at <https://crates.io/settings/tokens> with both endpoint scopes and a pattern. Allows the workflow to claim new names AND publish updates, within the namespace, and nothing else.
  - `HELIOY_PAT` — fine-grained PAT with `Contents: write` + `Pull requests: write` on each repo release-plz operates on. Used so release-plz PRs trigger downstream CI (see [Gotcha #5](#5--default-github_token-prs-dont-trigger-downstream-workflows)).
- **Helioy naming**: `lilo-` prefix for consumer-tier crates, `helioy-` reserved for enterprise. Match the prefix to the token's pattern scope.

## Bootstrap order

### Phase 1: workspace metadata

Goal: `cargo publish --workspace --dry-run --allow-dirty` succeeds locally.

1. Add `rust-toolchain.toml` at repo root:

   ```toml
   [toolchain]
   channel = "stable"
   components = ["rustfmt", "clippy"]
   ```

2. Add `LICENSE` at repo root.

3. Fill `[workspace.package]` in root `Cargo.toml`:

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

4. For each workspace member (`crates/<name>/Cargo.toml`):

   ```toml
   [package]
   name = "lilo-<name>"
   description = "One-line crate-specific description, shown on crates.io"
   readme = "README.md"
   version.workspace = true
   edition.workspace = true
   license.workspace = true
   repository.workspace = true
   homepage.workspace = true
   authors.workspace = true
   keywords = ["..."]      # max 5, lowercase, hyphenated
   categories = ["..."]

   [lib]
   name = "lilo_<name>"
   path = "src/lib.rs"
   ```

5. `[workspace.dependencies]` uses path + version form:

   ```toml
   [workspace.dependencies]
   lilo-foo  = { path = "crates/foo",  version = "0.1.0" }
   lilo-bar  = { path = "crates/bar",  version = "0.1.0" }
   ```

6. Add a `//!` crate-level doc to each `src/lib.rs`. docs.rs renders a blank landing page otherwise.

7. **Audit `[dev-dependencies]` for workspace-sibling references.** See [Gotcha #1](#1--cargo-publish---workspace-verify-fails-on-dev-dep-cycles). Relocate integration tests so dep direction is one-way.

8. Run `cargo publish --workspace --dry-run --allow-dirty`. Iterate until clean.

### Phase 2: CI quality gate

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
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: dtolnay/rust-toolchain@stable
      - uses: taiki-e/install-action@just
      - uses: taiki-e/install-action@nextest    # if you use nextest
      - uses: Swatinem/rust-cache@v2
      - run: just check
      - run: just build
      - run: just test

  semver-checks:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 0 }
      - name: Detect public crate source changes
        id: crate-src-changes
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          if git diff --name-only "$BASE_SHA" "$HEAD_SHA" | grep -Eq '^crates/[^/]+/src/'; then
            echo "changed=true" >> "$GITHUB_OUTPUT"
          else
            echo "changed=false" >> "$GITHUB_OUTPUT"
          fi
      - if: steps.crate-src-changes.outputs.changed == 'true'
        uses: dtolnay/rust-toolchain@stable
      - if: steps.crate-src-changes.outputs.changed == 'true'
        uses: obi1kenobi/cargo-semver-checks-action@v2
```

**Don't use `extractions/setup-just@v3`** — drags Node 20 transitives. `taiki-e/install-action@just` is fine.

### Phase 3: release-plz automation

`release-plz.toml`:

```toml
[workspace]
git_tag_name = "{{ package }}-v{{ version }}"   # per-crate tag, see Gotcha #6
git_release_enable = true
semver_check = true
changelog_update = true
publish = false                                  # publish.yml owns crates.io upload

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

`.github/workflows/release-plz.yml`:

```yaml
name: Release-plz

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-plz:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
          token: ${{ secrets.HELIOY_PAT }}
      - uses: dtolnay/rust-toolchain@stable
      - uses: release-plz/action@v0.5
        env:
          GITHUB_TOKEN: ${{ secrets.HELIOY_PAT }}
```

`CHANGELOG.md`:

```markdown
# Changelog

All notable changes documented here.
```

### Phase 4: publish workflow

`.github/workflows/publish.yml`:

```yaml
name: Publish to crates.io

on:
  release:
    types: [published]

permissions:
  id-token: write          # for attestation signing (GitHub's OIDC, not crates.io's)
  attestations: write
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: dtolnay/rust-toolchain@stable

      - name: Publish workspace
        run: cargo publish --workspace
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}

      - name: Repackage for attestation
        run: cargo package --workspace --allow-dirty

      - name: Attest crate packages
        uses: actions/attest-build-provenance@v3
        with:
          subject-path: target/package/*.crate
```

The token is scoped to your namespace + `publish-new` + `publish-update`. The first release of a brand-new crate is just a release in this model — the token claims the name on first publish, updates it on subsequent publishes. Zero per-crate UI configuration on crates.io.

### Phase 5 (HUMAN GATE): smoke test

1. Push a real `fix:`/`feat:`/`perf:` commit that touches at least one file under `crates/<name>/`. **Empty commits will NOT trigger a release** — see [Gotcha #8](#8--empty-fix-commits-dont-trigger-release-plz).
2. Watch: CI → PR merge → release-plz opens release PR → CI on release PR → merge → tag + GH Release → publish.yml fires → cargo publish → attestation → new version on crates.io within ~1 minute.

That's it. No `cargo login`, no manual first publish, no crates.io UI clicks.

## Gotchas index

### #1 — `cargo publish --workspace` verify fails on dev-dep cycles

**Symptom**: `--dry-run` fails for `crate-A` with "could not find crate-B in registry crates-io".

**Cause**: `crate-A` has `[dev-dependencies] crate-B = "0.1.0"`. Workspace overlay does NOT reliably extend to dev-deps during verify; cargo looks `crate-B` up on crates.io, which doesn't have it yet.

**Fix**: relocate the integration test so dep direction is one-way. If `crate-A` (smaller) dev-deps on `crate-B` (larger), move the test to `crate-B/tests/` and import `crate-A` from there.

### #2 — Library-only workspaces don't need cargo-dist

Non-issue, common confusion. `cargo publish` ships `.crate` tarballs to crates.io. Binaries are a separate concern handled by [the binary playbook](rust-binary-workspace-cargo-dist.md).

### #3 — Action version pins: `@v0` and `@v1` are not universal

**Symptom**: `Unable to resolve action <repo>@<version>`.

**Cause**: Not every action publishes floating major tags. `release-plz/action` floats minor (`@v0.5`). `rust-lang/crates-io-auth-action` ships only patch tags.

**Fix**: verify before pinning:

```bash
gh api repos/<owner>/<repo>/git/ref/tags/<ref>   # 404 = doesn't exist
gh api repos/<owner>/<repo>/git/refs/tags --jq '.[] | .ref' | head -20   # list available
```

### #4 — Org-level Workflow Permissions block `GITHUB_TOKEN` from creating PRs

**Symptom**: release-plz logs `release-plz release-pr failed with HTTP 422; continuing with no PRs created`. The branch is pushed but no PR appears.

**Cause**: "Allow GitHub Actions to create and approve pull requests" is disabled. The repo radio is on "Read repository contents and packages permissions" instead of "Read and write permissions", which grays out the checkbox. If the repo's radio is itself grayed out, an **org-level policy** is locking it.

**Fix**:
1. Org Settings → Actions → General → "Read and write" + check the PR-creation box.
2. Same at repo Settings (now interactive).
3. Per-workflow `permissions:` blocks remain the security floor — default-write at the org is just an upper bound.

API field name is misleading: `can_approve_pull_request_reviews` controls both PR creation AND approval.

### #5 — Default `GITHUB_TOKEN` PRs don't trigger downstream workflows

**Symptom**: release-plz successfully opens a release PR (after fixing #4), but no CI runs on it.

**Cause**: GitHub deliberately suppresses workflow runs from default-token actions to prevent recursive loops.

**Fix**: use a PAT in two places:

```yaml
- uses: actions/checkout@v6
  with:
    fetch-depth: 0
    token: ${{ secrets.HELIOY_PAT }}        # for git push

- uses: release-plz/action@v0.5
  env:
    GITHUB_TOKEN: ${{ secrets.HELIOY_PAT }}  # for REST API calls
```

publish.yml is unaffected — `release.published` events fire regardless of token used to create the release.

### #6 — Workspace tag collision in release-plz

**Symptom**: release-plz exits non-zero with `failed to create ref refs/tags/v0.1.1 ... Reference already exists`.

**Cause**: `git_tag_name = "v{{ version }}"` forces all workspace members to share one tag; release-plz creates it for crate 1, collides for crate 2.

**Fix**: per-crate template:

```toml
git_tag_name = "{{ package }}-v{{ version }}"
git_release_name = "{{ package }}-v{{ version }}"
```

Trade-off: one tag + GH Release per crate → publish.yml fires N times per release. Runs 2..N are near-noops (cargo skips already-published versions). Acceptable noise; matches release-plz's data model.

### #7 — Attestation step can't find `.crate` files

**Symptom**: `actions/attest-build-provenance` fails with `Could not find subject at path target/package/*.crate`.

**Cause**: cargo deletes `target/package/*.crate` after a successful upload ([rust-lang/cargo#14994](https://github.com/rust-lang/cargo/issues/14994)) to prevent re-uploading stale artifacts.

**Fix**: `cargo package --workspace --allow-dirty` after publish to rematerialize byte-identical tarballs.

### #8 — Empty `fix:` commits don't trigger release-plz

**Symptom**: `git commit --allow-empty -m "fix: smoke"` pushed to main, release-plz runs, no release PR opens.

**Cause**: release-plz attributes commits to packages by file path. An empty commit touches no package files → no bumps.

**Fix**: touch real files under `crates/<name>/`. Crate-level rustdoc additions (`//! ...`) are a defensible real change that also improves docs.rs.

### #9 — Token scope mismatch

**Symptom**: publish.yml fails with `403 Forbidden: this token does not have the required permissions` on either the first publish of a new crate (claim) or a subsequent publish (update).

**Cause**: token scope is too narrow. `publish-new` alone covers first publish but blocks updates. `publish-update` alone covers updates but blocks claim.

**Fix**: token scope must include both endpoint scopes (`publish-new` + `publish-update`) and a name-pattern scope matching your namespace (e.g., `lilo-*`). Regenerate at <https://crates.io/settings/tokens> if needed.

## Verification checklist

- [ ] All target crates show the bumped version on `https://crates.io/crates/<name>`.
- [ ] docs.rs renders each crate's landing page with the `//!` doc.
- [ ] `git ls-remote --tags origin` shows new tag(s).
- [ ] GH Releases page shows new release(s).
- [ ] Latest release-plz and publish.yml runs are green.
- [ ] `gh attestation list --repo <owner>/<repo>` shows attestations for published artifacts.
- [ ] No per-crate UI configuration was needed on crates.io.

## Operational follow-up

- Consumers can pin to `<name> = "0.x"` (pre-1.0) or `<name> = "x"` (1.0+).
- The CHANGELOG diff in the release PR is the source of truth — link to it from bus messages.
- **Yank** a bad version: `cargo yank --version <ver> <crate>` from a logged-in local machine, or add it to the token's allowed scopes and add a `cargo yank` step to a manually-triggered workflow.
- Token rotation: low cadence (annual is fine). The narrow scope means a leak can only claim sibling names in your namespace; no existing crate is at risk.

## Future: composite GitHub Action

The publish.yml job body (`publish → repackage → attest`) is stable enough to extract as a Helioy-owned composite action. **Defer until a second Rust workspace ships through this same pattern** — pre-extracting from one data point is premature.

Proposed shape:

```yaml
# helioy/rust-publish-workspace-action/action.yml
name: Rust publish workspace
inputs:
  token:
    description: crates.io token (typically org-scoped CARGO_REGISTRY_TOKEN)
    required: true
runs:
  using: composite
  steps:
    - shell: bash
      env:
        CARGO_REGISTRY_TOKEN: ${{ inputs.token }}
      run: cargo publish --workspace
    - shell: bash
      run: cargo package --workspace --allow-dirty
    - uses: actions/attest-build-provenance@v3
      with:
        subject-path: target/package/*.crate
```

Consumer publish.yml collapses to one step. release-plz.yml is already abstracted upstream by `release-plz/action`.

## Appendix A: OIDC Trusted Publishing variant

Higher-security alternative to the org-scoped token. Per-crate UI configuration on crates.io, no long-lived credentials anywhere.

When to choose this:

- You cannot use an org-level long-lived token (security policy).
- You're publishing fewer crates and the per-crate UI cost is acceptable.
- You want the strongest possible supply-chain posture.

Differences from the main playbook:

1. **Extra prerequisite**: nothing in `CARGO_REGISTRY_TOKEN`; you'll configure Trusted Publishing per crate.
2. **First publish is manual** ([crates.io does not support pending publishers](https://simonwillison.net/2025/Jul/12/cratesio-trusted-publishing/)). From a logged-in local machine:
   ```bash
   cargo publish --workspace
   git tag v0.1.0 && git push origin v0.1.0
   cargo logout                # immediately
   ```
3. **Configure Trusted Publishing per crate**: <https://crates.io/crates/<name>/settings> → Trusted Publishing → Add GitHub publisher. Owner `<github-org>`, Repo `<repo>`, Workflow `publish.yml`, Environment **blank**.
4. **publish.yml uses `rust-lang/crates-io-auth-action@v1.0.4`**:

   ```yaml
   - name: Authenticate with crates.io
     id: auth
     uses: rust-lang/crates-io-auth-action@v1.0.4

   - name: Publish workspace
     run: cargo publish --workspace
     env:
       CARGO_REGISTRY_TOKEN: ${{ steps.auth.outputs.token }}
   ```

5. **Skip Gotcha #9** (no scope to worry about; OIDC handles auth per-step).

identity-matters' lilo-im-core/stub/store currently use this variant. Both variants can coexist in the same org; choose per-product based on security posture.

## References

- Distilled from `identity-matters`, May 2026. Six fix-forward PRs in the first run; all captured in the gotchas index.
- Design rationale: `~/.mdx/projects/identity-matters-crates-io-publishing-design.md`
- [`cargo publish --workspace` stabilization (Rust 1.90, Sept 2025)](https://blog.rust-lang.org/2025/09/18/Rust-1.90.0/)
- [crates.io Trusted Publishing GA (July 2025)](https://simonwillison.net/2025/Jul/12/cratesio-trusted-publishing/)
- [crates.io token scopes (RFC 2947)](https://rust-lang.github.io/rfcs/2947-crates-io-token-scopes.html)
- [release-plz docs](https://release-plz.dev/)
- [Cargo #14994: .crate files deleted after publish](https://github.com/rust-lang/cargo/issues/14994)
- Linear master: ALP-2477. Follow-up: ALP-2488 (tag collision migration).
