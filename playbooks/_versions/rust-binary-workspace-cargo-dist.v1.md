---
title: Rust binary workspace → GitHub Releases via cargo-dist
type: playbooks
tags: [rust, cargo, cargo-dist, github-actions, release-please, binary-distribution, cross-compile, playbook-skeleton]
summary: End-to-end recipe for cross-compiling and shipping a Rust binary to GitHub Releases with installers and signing
status: draft
project: session-matters
related: [rust-workspace-crates-io-publishing]
confidence: low
---

# Rust binary workspace → GitHub Releases via cargo-dist

> **Skeleton owned by nancy-ALP-2441 (session-matters).** Sections marked **TODO** are awaiting lived experience from the session-matters first-release run. This playbook will become `confidence: high` once it has been validated against an actual end-to-end release, the same way the library playbook earned its rating across six fix-forward PRs.

A companion to [`rust-workspace-crates-io-publishing`](rust-workspace-crates-io-publishing.md). That playbook covers shipping library crates to crates.io. This one covers shipping a cross-compiled binary to GitHub Releases using cargo-dist, release-please, and the signing/installer flows that crates.io publishing does not address.

The two playbooks **coexist** for hybrid workspaces (library + binary). On a GitHub Release event, both `publish.yml` (crates.io upload) and `release.yml` (cargo-dist binary upload) can fire in parallel from the same tag.

## When to use this playbook

Use it when you want to ship a Rust binary to end users and:

- Need cross-compiled artifacts for multiple targets (linux/x86_64, linux/aarch64, macos/aarch64, windows/x86_64, …).
- Want installers (shell installer, Homebrew formula, msi/msix, Scoop, …).
- Need code signing or notarization (macOS notarization, Authenticode on Windows).
- Want SHA hashes and possibly provenance attestations on the binary artifacts.
- Are publishing for the first time and want the cargo-dist + release-please choreography spelled out.

**Use the library playbook instead** if your workspace only ships library crates to crates.io. **Use both** if you have a hybrid workspace.

## End-state architecture

```
TODO (nancy-ALP-2441): draw the actual chain.

Sketch (to be validated):
  Conventional commit on main
        │
        ▼
  release-please.yml fires on push
  (auth: HELIOY_PAT, opens release PR with version bump)
        │ merge release PR
        ▼
  release-please creates tag + GH Release (draft)
        │ tag push
        ▼
  cargo-dist's release.yml fires on tag matching version pattern
   → matrix builds (linux x86_64, linux aarch64, macos aarch64, windows x86_64, …)
   → uploads artifacts to the GH Release
   → publishes installers (Homebrew formula PR, shell installer, msi, …)
   → undrafts the GH Release
```

If the workspace is hybrid (also has library crates), `publish.yml` from the library playbook also fires on `release.published` and uploads the library crates to crates.io in parallel.

## Prerequisites

- **Rust 1.90+** (for `cargo publish --workspace` if hybrid; otherwise whatever cargo-dist requires).
- **cargo-dist installed locally** for `dist init` bootstrap. See <https://axodotdev.github.io/cargo-dist/>.
- **A GitHub repo** under an org you control with Workflow Permissions allowing PR creation (see library playbook gotcha #4 — same applies here).
- **A PAT** (`HELIOY_PAT` or equivalent) so release-please's PRs trigger downstream CI (library playbook gotcha #5 — same applies here).
- **For macOS notarization**: an Apple Developer account and the appropriate certificate + app-specific password in repo secrets. TODO: name the exact secret names cargo-dist expects.
- **For Windows signing**: a code-signing certificate. TODO: cargo-dist convention.
- **For Homebrew**: a separate tap repo (`<owner>/homebrew-tap` by convention).

## Bootstrap order

This is the most important section and the hardest to get right. The order matters because cargo-dist, release-please, and the various installer flows have dependencies on each other being live.

**TODO (nancy-ALP-2441)**: document the actual order you used for session-matters. Suggested skeleton:

1. **Phase 1**: workspace metadata + `[package.metadata.dist]` in the binary crate(s). TODO: minimum field set.
2. **Phase 2**: `dist init` and review of generated files (`dist-workspace.toml`, `.github/workflows/release.yml`).
3. **Phase 3 (HUMAN GATE)**: first manual release to validate the matrix builds without breaking the public release feed. TODO: how cargo-dist supports a "dry run" or test-tag approach.
4. **Phase 4**: release-please config (`release-please-config.json`, `.release-please-manifest.json`).
5. **Phase 5 (HUMAN GATE)**: confirm the release-please PR cycle produces a tag that cargo-dist's release.yml accepts. Tag format matters here.
6. **Phase 6**: installer hosting setup (Homebrew tap repo + token, msi cert, etc.).
7. **Phase 7 (HUMAN GATE)**: end-to-end smoke release. Watch matrix builds, installer publication, and end-user install paths.

## Configuration files

### `[package.metadata.dist]` (in the binary crate's Cargo.toml)

TODO: actual fields used in `sm-cli`.

### `dist-workspace.toml`

TODO: copy-pasteable example with sensible defaults for Helioy products. Notable settings:
- targets
- installers
- ci provider
- pr-run-mode
- precise-builds

### `.github/workflows/release.yml`

TODO: this file is auto-generated by `dist init`. Note the parts that are safe to edit vs. parts to leave alone (dist will overwrite them on regen).

### `release-please-config.json`

TODO: the exact config you ended up with. Key settings:
- packages → release-as
- changelog-sections
- pull-request-title-pattern

### `.release-please-manifest.json`

TODO: format and how to bootstrap the initial value.

### `.github/workflows/release-please.yml`

TODO: the actual workflow that drives the bumps. Note the PAT wiring (same pattern as the library playbook).

## Gotchas index

**TODO (nancy-ALP-2441)**: this is the most important section. Populate from lived experience during session-matters' first release. Suggested format (mirror the library playbook):

### #1 — TODO: first gotcha you hit

**Symptom**:

**Cause**:

**Fix**:

### #2 — TODO: second gotcha

…

### Cross-playbook gotchas (already documented)

These also apply to the binary workflow; see the library playbook for full diagnosis:

- **Library playbook gotcha #4** (org-level Workflow Permissions). The "Allow GitHub Actions to create and approve pull requests" toggle is required for release-please as well as release-plz.
- **Library playbook gotcha #5** (default `GITHUB_TOKEN` PRs don't trigger downstream workflows). Use `HELIOY_PAT` in release-please.yml the same way the library playbook uses it in release-plz.yml.
- **Library playbook gotcha #3** (action version pin discovery). cargo-dist's release.yml is regenerated by `dist`, so the pins are managed for you — but if you edit, verify the refs.

## Verification checklist

TODO (nancy-ALP-2441):

- [ ] GitHub Release shows assets for every target in the matrix.
- [ ] Shell installer downloads and runs cleanly.
- [ ] Homebrew formula PR is opened against the tap repo (if configured).
- [ ] msi installer is signed and installs cleanly on a clean Windows VM.
- [ ] macOS binary is notarized (`spctl -a -vv <binary>` passes without warnings).
- [ ] SHA hashes match what cargo-dist published in the GH Release body.
- [ ] (If hybrid) library crates also published to crates.io via the library playbook's chain.

## Operational follow-up

TODO (nancy-ALP-2441): yank/rollback procedure for binary releases, deprecation policy, etc.

## Hybrid workspaces (library + binary)

When the same workspace ships library crates to crates.io AND a binary to GH Releases:

- Both this playbook and the library playbook apply.
- On `release.published`, both workflows fire in parallel: `publish.yml` (crates.io upload from the library playbook) and `release.yml` (cargo-dist binary upload from this playbook).
- Release driver choice: release-please works for both halves; release-plz also works but is Rust-only and may be less natural in a polyglot org. session-matters uses release-please.
- Tag format must satisfy both flows. cargo-dist's release.yml matches tag patterns like `vMAJOR.MINOR.PATCH`. release-please defaults align by default. Verify both halves agree before the first release.

## See also

- [`rust-workspace-crates-io-publishing`](rust-workspace-crates-io-publishing.md) — companion playbook for the crates.io publish half. Required reading if your workspace is hybrid.
- cargo-dist docs: <https://axodotdev.github.io/cargo-dist/>
- release-please docs: <https://github.com/googleapis/release-please>
- Cross-product reference: session-matters first-release work (likely tracked under nancy-ALP-2441's Linear issues).

---

**Status flip checklist** for whoever promotes this playbook from `draft` to `active`:

- [ ] Every "TODO" has been replaced with real content.
- [ ] The gotchas index has at least three entries from lived experience (target: same density as the library playbook's nine).
- [ ] The verification checklist has been executed end-to-end at least once.
- [ ] The frontmatter `status` is changed to `active`, `confidence` to `high`, and the skeleton-owner note at the top is removed.
- [ ] A `cm` reference entry is stored at `global` scope pointing at this file (mirror the one created for the library playbook).
