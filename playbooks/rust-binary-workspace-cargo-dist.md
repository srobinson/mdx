---
title: Rust binary workspace → GitHub Releases via cargo-dist
type: playbooks
tags: [rust, cargo, cargo-dist, github-actions, release-please, binary-distribution, cross-compile]
summary: Recipe for shipping a Rust workspace binary to GitHub Releases with cargo-dist and release-please
status: active
project: session-matters
related: [rust-workspace-crates-io-publishing]
confidence: medium
---

# Rust binary workspace → GitHub Releases via cargo-dist

Use this playbook when a Rust workspace ships an executable to end users through GitHub Releases. It covers the release-please handoff, cargo-dist artifact matrix, generated release workflow, provenance attestations, and installer checks.

Companion playbook: [`rust-workspace-crates-io-publishing`](rust-workspace-crates-io-publishing.md). That playbook covers library crates on crates.io. This playbook covers binary artifacts on GitHub Releases. Hybrid workspaces can use both from the same version tag.

Validation basis: session-matters PR #1 on 2026-05-17 reached green macOS and Ubuntu CI at `cfb3568`, with a local cargo-dist archive smoke. The first live tag, `v0.1.1`, created a public GitHub Release, and all non-Windows build jobs passed. The configured Windows target failed because `sm-driver` still compiles Unix-only process and pty code on Windows; the host upload job skipped, so the release currently has no cargo-dist assets. Keep `confidence: medium` until a live tag completes every configured target and publishes assets.

## End-state architecture

```text
Conventional commits land on main
  ↓
.github/workflows/release-please.yml runs on main push
  ↓
release-please opens or updates a release PR
  - bumps workspace version in Cargo.toml
  - updates CHANGELOG.md
  - syncs Cargo.lock on the release PR branch
  - auto-merges the release PR when checks allow it
  ↓
release-please creates the version tag and a draft GitHub Release
  ↓
.github/workflows/release.yml runs on the version tag
  ↓
cargo-dist builds the full artifact matrix
  - per-target archives
  - shell and PowerShell installers
  - checksums
  - GitHub provenance attestations
  ↓
cargo-dist uploads artifacts into the existing GitHub Release
  ↓
cargo-dist undrafts the GitHub Release
```

Division of responsibility:

- release-please owns version bumps, changelog, tag creation, and the GitHub Release object.
- cargo-dist owns the dist build profile, target matrix, installers, checksums, attestations, artifact upload, and undrafting.

## Session-matters decisions

- The user-facing binary name stays `sm`. The package can remain `sm-cli`; cargo-dist installs the binary declared by `[[bin]] name = "sm"`.
- The `sm-*` crates stay workspace path crates for the first binary release. If any crate becomes a public library API, publish it through the library playbook with crates.io package names like `lilo-sm-core` and Rust module names like `lilo_sm_core`.
- External workspace dependencies must be registry crates, git dependencies, or vendored code. Do not clone sibling repos in CI to satisfy path dependencies.

## Prerequisites

- Rust toolchain that can build the workspace.
- `cargo-dist` installed locally at the version pinned in workspace metadata.
- GitHub Actions workflow permissions that allow release-please to create and update PRs.
- `HELIOY_PAT` as an org or repo secret. Use it for release-please API calls and checkout pushes so release PR checks are triggered.
- If the repo also publishes library crates, `CARGO_REGISTRY_TOKEN` from the library playbook.
- Optional signing assets only when enabled: Apple Developer credentials for notarization, Windows code signing certificate, and a Homebrew tap token if cargo-dist is configured to publish formula PRs.

## Bootstrap order

1. Add the binary crate metadata in the crate that declares `[[bin]]`.
2. Add `[profile.dist]` and `[workspace.metadata.dist]` in the workspace root.
3. Run `cargo dist generate --mode=ci` and review the generated `.github/workflows/release.yml`.
4. Add `release-please-config.json`, `.release-please-manifest.json`, and `.github/workflows/release-please.yml`.
5. Run the pre-merge checks below before pushing.
6. Merge a conventional commit to main and confirm release-please opens a release PR.
7. Merge the release PR only when the repo gate is green.
8. Watch the tag workflow. The release.yml workflow must build artifacts, upload them into the draft release, then undraft it.
9. Run the live-release checklist before telling users to install it.

## Configuration files

### Binary crate `Cargo.toml`

```toml
[package.metadata.dist]
dist = true

[[bin]]
name = "sm"
path = "src/main.rs"
```

Only the package that should produce release artifacts needs `dist = true`.

### Workspace `Cargo.toml`

```toml
[profile.dist]
inherits = "release"
lto = "thin"

[workspace.metadata.dist]
cargo-dist-version = "0.31.0"
ci = "github"
targets = [
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-unknown-linux-musl",
    "aarch64-unknown-linux-musl",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
    "x86_64-pc-windows-msvc",
]
installers = ["shell", "powershell"]
github-attestations = true
# release-please creates the GitHub Release; cargo-dist only uploads into it.
create-release = false
unix-archive = ".tar.gz"
windows-archive = ".zip"
include = ["LICENSE", "README.md"]
auto-includes = false
pr-run-mode = "skip"
```

Do not keep `allow-dirty = ["ci"]` for the generated workflow. It can hide release.yml drift.

### Generated `.github/workflows/release.yml`

Treat this file as generated. Change cargo-dist config, then regenerate:

```bash
cargo dist generate --mode=ci
cargo dist generate --mode=ci --check
```

Expected Node 24 compatible action majors from cargo-dist 0.31.0:

- `actions/checkout@v6`
- `actions/upload-artifact@v6`
- `actions/download-artifact@v7`
- `actions/attest-build-provenance@v3`

The generated host job should upload into the existing release:

```bash
gh release upload "${{ needs.plan.outputs.tag }}" artifacts/*
gh release edit "${{ needs.plan.outputs.tag }}" --target "$RELEASE_COMMIT" $PRERELEASE_FLAG --draft=false
```

If the workflow calls `gh release create`, verify `create-release = false` and regenerate.

### `release-please-config.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "packages": {
    ".": {
      "release-type": "simple",
      "component": "session-matters",
      "include-component-in-tag": false,
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": true,
      "extra-files": [
        {
          "type": "toml",
          "path": "Cargo.toml",
          "jsonpath": "$.workspace.package.version"
        }
      ],
      "changelog-sections": [
        { "type": "feat", "section": "Features" },
        { "type": "fix", "section": "Bug Fixes" },
        { "type": "perf", "section": "Performance" },
        { "type": "refactor", "section": "Refactoring", "hidden": true },
        { "type": "docs", "section": "Documentation", "hidden": true },
        { "type": "chore", "section": "Miscellaneous", "hidden": true },
        { "type": "test", "section": "Tests", "hidden": true },
        { "type": "ci", "section": "CI", "hidden": true }
      ]
    }
  }
}
```

Use `release-type: "simple"` for workspaces where member crates inherit `version.workspace = true`. Let `extra-files` update the workspace package version.

### `.release-please-manifest.json`

```json
{
  ".": "0.1.0"
}
```

Bootstrap this with the current workspace version before enabling the workflow.

### `.github/workflows/release-please.yml`

```yaml
name: Release Please

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
          token: ${{ secrets.HELIOY_PAT }}

      - name: Update Cargo.lock on release PR
        if: steps.release.outputs.pr
        uses: actions/checkout@v5
        with:
          ref: ${{ fromJSON(steps.release.outputs.pr).headBranchName }}
          token: ${{ secrets.HELIOY_PAT }}

      - name: Install Rust toolchain
        if: steps.release.outputs.pr
        uses: dtolnay/rust-toolchain@stable

      - name: Sync Cargo.lock
        if: steps.release.outputs.pr
        run: |
          cargo update --workspace
          if git diff --quiet Cargo.lock; then
            echo "Cargo.lock already up to date"
          else
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git add Cargo.lock
            git commit -m "chore: update Cargo.lock"
            git push
          fi

      - name: Auto-merge release PR
        if: steps.release.outputs.pr
        env:
          GH_TOKEN: ${{ secrets.HELIOY_PAT }}
          PR_NUMBER: ${{ steps.release.outputs.pr && fromJSON(steps.release.outputs.pr).number || '' }}
        run: gh pr merge --auto --squash "$PR_NUMBER" --repo "${{ github.repository }}"
```

`googleapis/release-please-action@v4` still emits a Node 20 warning until upstream ships a Node 24 major. Keep the warning scoped to this workflow and revisit when v5 exists.

## Gotchas index

### #1: Generated release.yml can drift from dist config

**Symptom**: Release workflow builds only a subset of targets, uses stale action majors, or lacks attestation despite `github-attestations = true`.

**Cause**: The generated release workflow was hand-edited or copied from another repo.

**Fix**: Regenerate from cargo-dist 0.31.0 and keep `cargo dist generate --mode=ci --check` in the review gate.

### #2: Node 20 action warnings hide inside transitive actions

**Symptom**: CI warns about Node 20 deprecation even after bumping first-party actions.

**Cause**: Helper actions can wrap older JavaScript actions. `extractions/setup-just@v3` pulled a Node 20 setup-crate dependency.

**Fix**: Use `taiki-e/install-action@just` and verify inventory:

```bash
grep -E "uses: " .github/workflows/*.yml | sort -u
```

### #3: Missing `[profile.dist]` breaks every release target

**Symptom**: Tag workflow fails with `profile dist is not defined`.

**Cause**: `[workspace.metadata.dist]` was added without the dist build profile.

**Fix**: Add:

```toml
[profile.dist]
inherits = "release"
lto = "thin"
```

### #4: Both tools can try to create the same GitHub Release

**Symptom**: cargo-dist host step fails because a release with the same tag already exists.

**Cause**: release-please created the GitHub Release and cargo-dist was still configured to create one.

**Fix**: Set `create-release = false`, regenerate release.yml, and verify the host step uses `gh release upload` followed by `gh release edit --draft=false`.

### #5: `release-type: "rust"` does not fit workspace inherited versions

**Symptom**: release-please fails parsing member crates that use `version.workspace = true`.

**Cause**: The Rust release type expects package-local versions in every crate.

**Fix**: Use `release-type: "simple"` and update `$.workspace.package.version` with `extra-files`.

### #6: Default-token release PRs do not trigger CI

**Symptom**: release-please opens a release PR but required checks never run.

**Cause**: GitHub suppresses workflow recursion from the default `GITHUB_TOKEN`.

**Fix**: Use `HELIOY_PAT` in the release-please action and checkout step.

### #7: Sibling path dependencies break clean checkout releases

**Symptom**: CI fails during cargo metadata with a missing `../identity-matters` or similar path.

**Cause**: The local developer layout leaked into Cargo.toml.

**Fix**: Publish or consume the sibling contract properly. For session-matters, `im-*` path deps became crates.io dependencies on `lilo-im-core`, `lilo-im-store`, and `lilo-im-stub` 0.1.

### #8: Protocol tests must not rely on runner-installed runtimes

**Symptom**: MCP integration tests pass locally but fail on GitHub with a session no longer running.

**Cause**: The test launched the real `codex` binary from the runner. Its lifecycle differed from the expected long-lived runtime.

**Fix**: Put a fake executable ahead of PATH in the test fixture and keep the runtime alive until the daemon deletes it.

### #9: Attestation settings need workflow permissions

**Symptom**: `actions/attest-build-provenance` cannot sign artifacts.

**Cause**: `github-attestations = true` requires generated job permissions for `attestations: write`, `id-token: write`, and `contents: read`.

**Fix**: Regenerate release.yml with cargo-dist and verify the build job permissions include those fields.

### #10: Configured targets must match platform support

**Symptom**: The live tag release passes plan and non-Windows builds, but `x86_64-pc-windows-msvc` fails. The GitHub Release exists with no assets because cargo-dist skips the host upload job after any matrix failure.

**Cause**: The target matrix included Windows before the workspace had a Windows driver implementation. In session-matters `v0.1.1`, `sm-driver` compiled Unix-only APIs such as `std::os::fd`, `nix::pty`, `nix::sys::signal`, `nix::sys::wait`, and `nix::unistd` on the Windows target.

**Fix**: Either remove unsupported targets from `[workspace.metadata.dist].targets` for the first release, or gate the platform-specific driver behind `cfg(unix)` and provide a Windows implementation or a clean unsupported-runtime error behind `cfg(windows)`. Re-run `cargo dist plan` after changing targets and verify the expected artifact count.

## Verification checklist

Before merge:

- [ ] `cargo metadata --format-version 1` resolves every dependency from a clean checkout.
- [ ] `cargo dist generate --mode=ci --check` passes.
- [ ] `cargo dist plan --output-format=json` shows the expected target matrix and artifact count.
- [ ] `cargo dist plan --output-format=json | jq -e '.github_attestations == true'` passes when attestations are required.
- [ ] `grep -E "uses: " .github/workflows/*.yml | sort -u` contains only accepted action refs.
- [ ] `git diff --check` passes.
- [ ] Repo gate passes, for example `just check && just build && just test --profile ci && just test-doc`.
- [ ] Local host smoke produces an archive and checksum:

```bash
cargo dist build --target "$(rustc -vV | awk '/host:/ {print $2}')" --artifacts=local --output-format=json
```

For session-matters, the PR gate also checked:

```bash
cargo dist plan --output-format=json \
  | jq -e '.github_attestations == true
    and (.ci.github.artifacts_matrix.include | length == 7)
    and (.releases[0].artifacts | length == 19)'
```

Live release:

- [ ] `gh release view <tag> --json isDraft,isPrerelease,assets` shows `isDraft: false`.
- [ ] Assets exist for every target in the cargo-dist matrix.
- [ ] `.sha256` files match downloaded artifacts.
- [ ] `gh attestation list --repo <owner>/<repo>` shows build provenance for released artifacts.
- [ ] Shell installer downloads and installs the binary.
- [ ] PowerShell installer downloads and installs the binary on a clean Windows host.
- [ ] Homebrew formula PR opens against the tap repo if Homebrew is configured.
- [ ] Windows artifacts are signed if Windows signing is configured.
- [ ] macOS binaries pass `spctl -a -vv <binary>` if notarization is configured.
- [ ] Hybrid workspaces also finish crates.io publication via the library playbook.

## Operational follow-up

- If a release is still draft and assets are wrong, delete the draft release and tag, fix the workflow, then recreate the tag.
- If a release is public, prefer a patch release. GitHub binary releases have no crates.io-style yank that cleanly protects existing installers.
- If a public asset must be removed, update the release body with the reason and publish a replacement version immediately.
- Rotate `HELIOY_PAT` on the same cadence as the library publish token.
- Recheck `googleapis/release-please-action@v4` periodically. Move to the first Node 24 major after upstream ships it.
- After the first full session-matters cargo-dist tag succeeds, update this playbook with the actual tag, asset count, installer result, and raise `confidence` to `high`.

## Hybrid workspaces

When the same repo ships library crates and a binary:

- Use the library playbook for crates.io package names, token scope, publish workflow, and crate attestations.
- Use this playbook for cargo-dist binary artifacts and installers.
- Both workflows can fire from the same GitHub Release event.
- Tag format must satisfy both flows. release-please defaults to `vMAJOR.MINOR.PATCH`; cargo-dist accepts that pattern.
- Decide public package names separately from executable names. A crate may be `lilo-sm-cli` while the installed binary remains `sm`.

## See also

- [`rust-workspace-crates-io-publishing`](rust-workspace-crates-io-publishing.md)
- cargo-dist docs: <https://axodotdev.github.io/cargo-dist/>
- release-please docs: <https://github.com/googleapis/release-please>
- Reference repo state: `session-matters` PR #1, head `cfb3568`.
