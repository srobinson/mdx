---
title: Runtime matters crate releases with release-plz
type: playbooks
tags: [runtime-matters, rust, cargo, crates-io, release-plz, conventional-commits]
summary: Release lilo-rm-core and lilo-rm-client through release-plz owned version bumps, changelogs, crate tags, GitHub Releases, and crates.io publishing.
status: active
project: helioy
related: [rust-workspace-crates-io-publishing, rust-binary-workspace-cargo-dist]
confidence: high
---

# Runtime matters crate releases with release-plz

Use this runbook for `lilo-rm-core` and `lilo-rm-client` releases from `littleorgans/runtime-matters`.

Release-plz owns the crate release lane:

- `Cargo.toml` package versions
- package changelogs
- crate tags such as `lilo-rm-core-v0.7.0`
- crate GitHub Releases
- crates.io publish

Do not manually edit package versions or changelog release headers in feature PRs. Conventional commit messages describe intent. Release-plz turns that intent into a release PR.

## Source Of Truth

Runtime matters currently configures release-plz with:

```toml
[workspace]
semver_check = true
git_tag_name = "{{ package }}-v{{ version }}"
git_release_name = "{{ package }}-v{{ version }}"
release_always = false

[[package]]
name = "lilo-rm-core"
release = true
publish = true
version_group = "rm-contract"

[[package]]
name = "lilo-rm-client"
release = true
publish = true
version_group = "rm-contract"
```

The two packages share `version_group = "rm-contract"`, so they release together as one contract pair.

Because `release_always = false`, publishing happens from the release-plz release path after a release-plz PR merge. A manual version bump on an ordinary feature PR can leave the repo with updated versions and changelogs but no release-plz publish event.

## Commit Syntax

Use Conventional Commits.

Patch:

```text
fix(rtm-core): handle missing runtime socket
```

Feature:

```text
feat(rtm-client): add spawn status polling
```

Breaking public contract change:

```text
feat(rtm-core)!: add spawn request mounts

BREAKING CHANGE: SpawnRequest now includes mounts and RuntimeCapability now includes SpawnRequestMounts.
```

The `!` belongs after the type or scope and immediately before the colon:

- Correct: `feat!: change public API`
- Correct: `feat(rtm-core)!: change public API`
- Incorrect: `! feat: change public API`

The `BREAKING CHANGE:` footer is optional when `!` is present, but use both for public contract changes. The footer gives reviewers and downstream users the concrete migration note.

## Version Bump Rules

With the default release-plz behavior used here:

- `fix:` bumps patch.
- `feat:` bumps patch while the crate major version is `0`.
- `feat!:` or `feat(scope)!:` bumps minor while the crate major version is `0`.
- `feat!:` or `feat(scope)!:` bumps major once the crate is `1.x`.
- cargo-semver-checks can also force a breaking bump when `semver_check = true`.

For the current `0.x` crates, a breaking change should move `0.6.3 -> 0.7.0`, not `1.0.0`.

Verification basis:

- Conventional Commits 1.0.0 defines `!` after type or scope as a breaking change marker: <https://www.conventionalcommits.org/en/v1.0.0/>
- Release-plz changelog docs say `<prefix>!:` represents a breaking change: <https://release-plz.dev/docs/changelog/format>
- Local release-plz `0.3.158` tests include `feat!: breaking API change` and assert a `0.x` minor bump.
- Local `next_version 0.3.2` tests assert `feat!: break user` moves `0.2.3 -> 0.3.0`.

## Normal Release Flow

1. Land the feature or fix with the correct conventional commit title.
2. For public contract breaks, use `feat(scope)!:` and a `BREAKING CHANGE:` footer.
3. Wait for release-plz to open or update the crate release PR.
4. Review the release-plz PR. Confirm:
   - both `lilo-rm-core` and `lilo-rm-client` are included when the contract changes
   - versions are changed only by release-plz
   - changelogs describe the public change
   - `Cargo.lock` is synced
5. Merge the release-plz PR only after the repo gate is green.
6. Watch the next main run. Confirm release-plz publishes both crates, creates both tags, and creates both GitHub Releases.

## Do Not Do

Do not land a feature PR that manually edits:

- `crates/rtm-core/Cargo.toml` version
- `crates/rtm-client/Cargo.toml` version
- package changelog release headers
- release-plz generated release metadata

Those edits belong in the release-plz PR.

Do not use release-please for the crate lane. Release-please can own binary or workspace application releases, while release-plz owns public Rust library crates.

## 0.7.0 Incident

The `0.7.0` crate versions existed in `Cargo.toml` and the changelogs, but release-plz did not publish them because the version bump landed outside a release-plz PR. The release-plz run reported:

```text
skipping release: current commit is not from a release PR
```

Manual recovery was required because the crates were then published by hand:

```bash
cargo publish -p lilo-rm-core
cargo publish -p lilo-rm-client
```

After crates.io accepted `0.7.0`, the missing crate tags and GitHub Releases were manually created at commit `edc385e934f6bbfc07ad7a4edaa5f8f136884300`:

```bash
git tag -a lilo-rm-core-v0.7.0 edc385e934f6bbfc07ad7a4edaa5f8f136884300 \
  -m "chore: Release package lilo-rm-core version 0.7.0"

git tag -a lilo-rm-client-v0.7.0 edc385e934f6bbfc07ad7a4edaa5f8f136884300 \
  -m "chore: Release package lilo-rm-client version 0.7.0"

git push origin lilo-rm-core-v0.7.0 lilo-rm-client-v0.7.0
```

Manual recovery is an exception path. The forward path is release-plz owned.

## Verification Commands

Check the release-plz version used locally:

```bash
release-plz --version
```

Confirm runtime-matters release-plz config:

```bash
sed -n '1,40p' release-plz.toml
```

Confirm the conventional commit parser behavior in the installed release-plz sources:

```bash
rg -n "feat!:|breaking API change|features_always_increment_minor" \
  ~/.cargo/registry/src/index.crates.io-*/release-plz-* \
  ~/.cargo/registry/src/index.crates.io-*/release_plz_core-* \
  ~/.cargo/registry/src/index.crates.io-*/next_version-*
```

Check crates.io for published versions:

```bash
curl -s https://crates.io/api/v1/crates/lilo-rm-core | jq -r '.versions[].num' | head
curl -s https://crates.io/api/v1/crates/lilo-rm-client | jq -r '.versions[].num' | head
```

Check GitHub tags and releases:

```bash
git ls-remote --tags origin 'lilo-rm-*-v*'
gh release view lilo-rm-core-v0.7.0 --repo littleorgans/runtime-matters
gh release view lilo-rm-client-v0.7.0 --repo littleorgans/runtime-matters
```

