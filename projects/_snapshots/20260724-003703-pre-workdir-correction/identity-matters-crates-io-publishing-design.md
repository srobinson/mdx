---
project: identity-matters
topic: crates.io publication via Trusted Publishing
status: design accepted, awaiting execution
created: 2026-05-17
author: Stuart Robinson + Claude (co-authored)
related:
  - identity-matters-iam-draft.md
  - ../session-matters/... (consumer, nancy-ALP-2441)
linear:
  master: ALP-XXXX  (to be created)
  prior: ALP-2453 (IAM v1 stub umbrella)
---

# identity-matters: publish `lilo-im-*` 0.1.0 to crates.io via Trusted Publishing

## Objective

Ship `lilo-im-core`, `lilo-im-stub`, and `lilo-im-store` to crates.io at 0.1.0, with releases driven by GitHub Actions using OIDC Trusted Publishing. No long-lived crates.io API tokens stored anywhere after bootstrap. Future releases run hands-off through release-plz + native workspace publish + provenance attestations.

End-state consumer story:

```toml
# session-matters/crates/sm-daemon/Cargo.toml
lilo-im-core  = "0.1"
lilo-im-stub  = "0.1"
lilo-im-store = "0.1"
```

```rust
use lilo_im_core::{Authorizer, Principal, Action};
use lilo_im_stub::StubAuthorizer;
use lilo_im_store::SqliteAuditSink;
```

## Why

`identity-matters` currently exposes its surface to `session-matters` through sibling path dependencies (`im-core = { path = "../../../identity-matters/crates/im-core" }`). nancy-ALP-2441 surfaced this as the wrong shape for CI and release: session-matters cannot tag a release referencing an unpublished identity-matters. The fix per her bus message:

> "make identity-matters releasable/publishable first, then session-matters can consume identity-matters through a proper dependency contract."

This work is that first step. Once `lilo-im-* 0.1.0` lives on crates.io, every Helioy product can depend on identity-matters via a versioned crate registry contract, the canonical pattern in the Rust ecosystem.

## Resolved decisions

| Decision | Choice | Rationale |
|---|---|---|
| Naming namespace | `lilo-` prefix (consumer brand, derived from `lil` + `o` of `littleorgans`) | `helioy-` is reserved for enterprise tier; `lilo-` is the consumer/dev-facing brand. Distinct namespacing avoids mixing tiers in one prefix. |
| Publication shape | Shape P: split publish per workspace member | Matches the v1→v2 swap design (`im-stub` → `im-daemon` is a single Cargo.toml dep change). Matches sm-cli's narrower consumer subset (it does not need im-stub). Matches AWS / Cloudflare / Fermyon precedent. |
| Versioning | Workspace versioning, lockstep across all three crates | Current setup. Tight coupling via trait contracts argues against independent versioning. |
| Release tooling | release-plz (Rust-native) + native `cargo publish --workspace` (Rust 1.90+, Sept 2025) + `cargo-semver-checks` gate | release-plz is the 2026 Rust-native equivalent of release-please. `cargo publish --workspace` does topological ordering + local-overlay verification + dep-ordered upload natively, removing the need for `cargo-release` shell-wrapping. |
| Auth | OIDC Trusted Publishing via `rust-lang/crates-io-auth-action@v1` | GA on crates.io since July 2025. No long-lived tokens. Standard for new Rust projects in 2026. |
| Binary distribution | None (no `cargo-dist`) | Library-only workspace. cargo-dist is for binary tarballs and adds nothing here. |
| Provenance | `actions/attest-build-provenance@v3` on each `.crate` tarball | SLSA-3 provenance, defends against compromised publish path. 2025 industry best practice. |
| Scope of this work | identity-matters only | session-matters' migration to `lilo-im-* = "0.1"` is a separate concern owned by nancy-ALP-2441. Handoff via bus message after 0.1.0 publishes. |

## Architecture: end state

After this work lands and the human-gated steps complete:

```
crates.io
├── lilo            0.0.0  (dormant defensive squat, no TP)
├── lilo-im-core    0.1.0  (Trusted Publishing → littleorgans/identity-matters/publish.yml)
├── lilo-im-stub    0.1.0  (Trusted Publishing → littleorgans/identity-matters/publish.yml)
└── lilo-im-store   0.1.0  (Trusted Publishing → littleorgans/identity-matters/publish.yml)

github.com/littleorgans/identity-matters
├── crates/
│   ├── im-core/    # [package] name = "lilo-im-core", [lib] name = "lilo_im_core"
│   ├── im-stub/    # [package] name = "lilo-im-stub", [lib] name = "lilo_im_stub"
│   └── im-store/   # [package] name = "lilo-im-store", [lib] name = "lilo_im_store"
├── .github/workflows/
│   ├── ci.yml          # PR + push: just check/build/test + cargo-semver-checks
│   ├── release-plz.yml # push to main: open release PR
│   └── publish.yml     # release.published: cargo publish --workspace via OIDC
├── release-plz.toml
├── rust-toolchain.toml
├── LICENSE
├── CHANGELOG.md        # managed by release-plz
├── Cargo.toml
└── (existing IAM stub workspace)

GitHub secrets: none required for publishing.
```

Existing 0.0.0 placeholders (`identity-matters`, `runtime-matters`, `transport-matters`) stay dormant as defensive squats. Their `repository` URLs (`srobinson/...`) are not corrected — they are placeholders only and `lilo-im-* 0.1.0`'s metadata is what consumers see.

## Source structure changes

### Cargo.toml renames

Inside `crates/im-core/Cargo.toml` (mirror for stub and store):

```diff
 [package]
-name = "im-core"
+name = "lilo-im-core"
+description = "Identity Matters core: Authorizer trait, Principal types, peer credential extraction (Helioy v1 IAM)"
+readme = "README.md"
 version.workspace = true
 edition.workspace = true
 license.workspace = true
 repository.workspace = true
+homepage.workspace = true
+authors.workspace = true
+keywords = ["iam", "authorization", "audit", "principal", "helioy"]
+categories = ["authentication"]
+
+[lib]
+name = "lilo_im_core"
+path = "src/lib.rs"
```

### Workspace metadata (root `Cargo.toml`)

```diff
 [workspace.package]
 version = "0.1.0"
 edition = "2024"
 license = "MIT"
-repository = "https://github.com/littleorgans/identity-matters"
+repository = "https://github.com/littleorgans/identity-matters"
+homepage = "https://github.com/littleorgans/identity-matters"
+authors = ["Stuart Robinson"]
+rust-version = "1.90"

 [workspace.dependencies]
-im-core = { path = "crates/im-core" }
-im-stub = { path = "crates/im-stub" }
-im-store = { path = "crates/im-store" }
+lilo-im-core  = { path = "crates/im-core",  version = "0.1.0" }
+lilo-im-stub  = { path = "crates/im-stub",  version = "0.1.0" }
+lilo-im-store = { path = "crates/im-store", version = "0.1.0" }
```

`{ path = ..., version = "0.1.0" }` is required for `cargo publish` to succeed — it lets Cargo use the path locally for development while pinning to a published version when consumers consume the published artifact.

### Cross-crate source `use` updates

Inside the workspace (im-stub and im-store import im-core):

```diff
- use im_core::{Authorizer, Principal};
+ use lilo_im_core::{Authorizer, Principal};
```

Approximately 5-10 cross-crate imports based on the existing source. Mechanical rewrite.

### New top-level files

| File | Purpose |
|---|---|
| `LICENSE` | MIT license text. Required by `cargo publish`. |
| `rust-toolchain.toml` | Pins toolchain channel (e.g. `1.92`) for reproducible CI builds. Pin MSRV at `rust-version = "1.90"` in workspace.package (required for `cargo publish --workspace`). |
| `release-plz.toml` | release-plz workspace config (see below). |
| `CHANGELOG.md` | Created and managed by release-plz. Initial empty content. |

### First-publish dev-dep trap (lesson from ALP-2479 / 2026-05-17)

`cargo publish --workspace`'s verify step does NOT extend the workspace overlay reliably to `[dev-dependencies]`. If a crate's dev-deps reference a workspace sibling at the version being currently published (e.g. `lilo-im-store = "^0.1.0"`), verify will fail during first publish because crates.io only has the 0.0.0 placeholder.

**Before first publish for every Helioy product going through this dance:**

1. Audit each crate's `[dev-dependencies]` for workspace-sibling references.
2. Where a sibling appears in dev-deps, relocate the integration test into the dependent crate so dep direction is strictly one-way through the workspace graph (`store/tests/foo.rs uses stub` is fine; `stub/tests/foo.rs uses store` is not, if both publish from the same first release).
3. Confirm with `cargo publish --workspace --dry-run --allow-dirty` before the human-gate first publish.

After the first release lands on crates.io, workspace dev-deps on siblings work normally. This is a first-publish-only trap.

Reference: cm lesson "Workspace dev-dep on a sibling at the not-yet-published version breaks `cargo publish` verify" (helioy project scope).

## Workflow files

### `.github/workflows/ci.yml`

Triggers: `pull_request`, `push: main`.

Jobs:
1. **lint+build+test**: install Rust toolchain (from `rust-toolchain.toml`), install `just` via `taiki-e/install-action@just`, cache cargo via `Swatinem/rust-cache@v2`, run `just check && just build && just test`.
2. **semver-checks** (on PRs touching `crates/*/src/**` only): `obi1kenobi/cargo-semver-checks-action@v2` against the latest published version of each affected crate. Fails on undeclared breaks.

Permissions: `contents: read` only.

### `.github/workflows/release-plz.yml`

Triggers: `push: main`.

Single job:
1. Checkout with `fetch-depth: 0` (required for commit-walk).
2. Install Rust toolchain.
3. `release-plz/action@v0`.

`release-plz` opens a PR with workspace-wide version bump, regenerated lockfile, per-crate `CHANGELOG.md` updates. When merged, action tags `v0.X.0` and creates a GitHub Release.

Permissions: `contents: write`, `pull-requests: write`.

### `.github/workflows/publish.yml`

Triggers: `release: { types: [published] }`.

Single job:
1. Checkout (tagged commit).
2. Install Rust toolchain (1.90+).
3. Install `just`.
4. **Auth**: `rust-lang/crates-io-auth-action@v1` (OIDC → 30-minute crates.io credential).
5. `cargo publish --workspace`.
6. `actions/attest-build-provenance@v3` for each generated `.crate` tarball.

Permissions: `id-token: write`, `attestations: write`, `contents: read`. **No `CRATES_IO_TOKEN` secret.**

### `release-plz.toml`

Workspace versioning, lockstep, semver-checks enabled, single tag per release:

```toml
[workspace]
git_tag_name = "v{{ version }}"
git_release_enable = true
semver_check = true
changelog_update = true
publish = false  # publish.yml owns this on release.published

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

`publish = false` on release-plz tells it NOT to publish (publish.yml owns that on `release.published` event). This decouples the two concerns: release-plz creates the GitHub Release, publish.yml uploads to crates.io.

### Action inventory verification

Before each PR merge, locally:

```bash
grep -E "uses: " .github/workflows/*.yml | sort -u
```

Expected output (Node 24 actions only, no Node 20 transitive drag-ins):

```
uses: actions/attest-build-provenance@v3
uses: actions/checkout@v6
uses: dtolnay/rust-toolchain@stable
uses: obi1kenobi/cargo-semver-checks-action@v2
uses: release-plz/action@v0
uses: rust-lang/crates-io-auth-action@v1
uses: Swatinem/rust-cache@v2
uses: taiki-e/install-action@just
```

## Bootstrap order

Sequenced in two Nancy phases with three human gates between them. The reason for the split: release-plz and publish.yml both have failure modes if they run before `lilo-im-* 0.1.0` exists on crates.io and Trusted Publishing is configured. Cleanest is to land the prerequisites first (rename + CI), then do the manual bootstrap, then add the automation.

### Phase 0 — Linear scaffolding + worktree

1. Create new master parent under identity-matters project.
2. Create `Backlog` execution parent (child of master).
3. Create 4 worker pass issues (children of `Backlog`).
4. Create 1 post execution review issue.
5. Create gate review issue (direct child of master).
6. Set gate review status to `Worker Done`.
7. Create worktree at `../identity-matters-worktrees/nancy-ALP-<pass1>`.

### Phase 1 — Pass 1 (Nancy): workspace rename

After review: PR opened, CI green, merged.

### Phase 2 — Pass 2 (Nancy): CI workflow

After review: PR opened, the new `ci.yml` runs against the PR, green, merged.

### Phase 3 — First publish + tag (human gate, one-time, local)

After Pass 1 + Pass 2 merge:

```bash
cd /Users/alphab/Dev/LLM/DEV/helioy/identity-matters
git checkout main && git pull
cargo publish --workspace
git tag v0.1.0
git push origin v0.1.0
```

Uses the existing `cargo login` API token. Expected: 0.1.0 published for `lilo-im-core`, `lilo-im-stub`, `lilo-im-store` in topological order (core first). 1-3 minutes total.

The `v0.1.0` tag is what release-plz reads as the baseline on first run — without it, release-plz on its first run might try to open a release PR for 0.1.0 again.

### Phase 4 — Configure Trusted Publishing (human gate, crates.io UI)

For each of `lilo-im-core`, `lilo-im-store`, `lilo-im-stub`:

1. `https://crates.io/crates/<name>/settings` → *Trusted Publishing* → *Add GitHub publisher*.
2. Owner: `littleorgans`. Repo: `identity-matters`. Workflow: `publish.yml`. Environment: (blank).
3. Save.

`lilo` (bare) is not configured — stays a dormant squat.

### Phase 5 — Pass 3 (Nancy): release-plz workflow

Now safe because 0.1.0 is on crates.io. release-plz on first run sees the published baseline and waits for conventional commits before opening a release PR.

### Phase 6 — Pass 4 (Nancy): publish workflow

Adds `publish.yml`. Does not trigger until a release event is fired by release-plz, which won't happen until a conventional-commit feat/fix lands.

### Phase 7 — Smoke test (human gate, validates the OIDC path)

```bash
git commit --allow-empty -m "fix: smoke test publish via OIDC"
git push
```

Expected sequence:
1. `ci.yml` passes on the empty commit's PR.
2. PR merges.
3. `release-plz.yml` opens "release v0.1.1" PR (the `fix:` conventional commit triggers it).
4. Release PR merges.
5. `release-plz/action@v0` tags v0.1.1, creates GitHub Release.
6. `publish.yml` triggers on `release.published`, exchanges OIDC, publishes 0.1.1 to all three crates.
7. crates.io shows 0.1.1 visible within ~1 minute.

If the smoke test fails: TP config typo most likely (workflow filename mismatch, owner/repo mismatch).

### Phase 8 — Credential cleanup (human gate, one-time)

```bash
cargo logout
```

In crates.io UI: API Tokens → revoke the token used in Phase 5. End state: zero long-lived crates.io credentials anywhere.

### Phase 9 — Cross-repo handoff

Send bus message to `nancy-ALP-2441:general`:

```
Topic: lilo-im-* 0.1.0 published to crates.io
Content:
lilo-im-core, lilo-im-store, lilo-im-stub are live at 0.1.0 on crates.io
with Trusted Publishing wired. You can swap sm-daemon and sm-cli path
deps for `lilo-im-* = "0.1"` when ready. Also `use im_core::` →
`use lilo_im_core::` etc. in source.
```

## Worker pass scope

### Pass 1: Rename workspace crates to lilo-im-* and complete publication metadata

**Scope:**
- Rename `[package] name` in each of `crates/im-{core,stub,store}/Cargo.toml`.
- Add `[lib] name = "lilo_im_*"` aligning with package name.
- Add per-crate `description`, `readme`, `keywords`, `categories`.
- Complete `[workspace.package]` metadata: `homepage`, `authors`, `rust-version`.
- Add `version = "0.1.0"` to each `path` dep in `[workspace.dependencies]`.
- Rewrite cross-crate source imports (`im_core` → `lilo_im_core`, etc.) — applies to im-stub and im-store only.
- Add `LICENSE` (MIT text) at repo root.
- Add `rust-toolchain.toml` pinning stable channel.
- Update workspace metadata `repository` field if needed (already `littleorgans/identity-matters`).

**Verification:**
- `just check && just build && just test` → all green.
- `cargo publish --workspace --dry-run` → succeeds for all three crates.
- `grep -rE "use im_(core|stub|store)" crates/` → returns zero matches.

**Refactor permission:** none beyond above. Do not touch CI yet.

### Pass 2: Add CI workflow with check/build/test/semver gate

**Scope:**
- `.github/workflows/ci.yml` running just check/build/test on PR + push.
- semver-checks job conditional on changes to `crates/*/src/**`, using `obi1kenobi/cargo-semver-checks-action@v2`.
- Cache cargo via `Swatinem/rust-cache@v2`.

**Verification:**
- PR opened against the worktree runs `ci.yml` → goes green.
- Action inventory grep returns only Node 24 actions (Swatinem rust-cache@v2 known Node 20 warning is acceptable per nancy's guidance — same posture as `release-please-action@v4`).

**Refactor permission:** if `just test` is slow or flaky, optimize before merging.

### Pass 3: Add release-plz workflow and config

**Prerequisite (human-gated, not Nancy's job):** Phase 3 (first publish) and Phase 4 (TP config) of bootstrap order must be complete before Pass 3 starts. Without 0.1.0 on crates.io, release-plz cannot establish a published baseline. Without TP configured, the eventual `publish.yml` (Pass 4) would fail on its first run.

Operational signal: the post-execution review of Pass 2 will note "human gate: first publish + TP config required before Pass 3 starts." Nancy waits for `Done` on Pass 2's review before picking up Pass 3.

**Scope:**
- `.github/workflows/release-plz.yml` triggering on `push: main`.
- `release-plz.toml` at repo root with workspace versioning, lockstep, semver check.
- `CHANGELOG.md` empty initial file at repo root.

**Verification:**
- After merge, release-plz job runs against main. Since no `feat:`/`fix:` conventional commits exist since 0.1.0 was published, no release PR is opened.
- `release-plz.toml` validates.

**Refactor permission:** none.

### Pass 4: Add publish workflow using OIDC Trusted Publishing

**Prerequisite:** Pass 3 complete. TP must already be configured per Phase 4 of bootstrap order.

**Scope:**
- `.github/workflows/publish.yml` triggering on `release: { types: [published] }`.
- `permissions: id-token: write`, `attestations: write`, `contents: read`.
- Uses `rust-lang/crates-io-auth-action@v1` for OIDC token exchange.
- `cargo publish --workspace` for dep-ordered upload.
- `actions/attest-build-provenance@v3` for each generated `.crate` tarball.

**Verification:**
- File syntactically valid.
- Workflow does not auto-trigger on merge (`release.published` not fired yet — that happens during the Phase 7 smoke test).
- Action inventory grep includes `rust-lang/crates-io-auth-action@v1` and `actions/attest-build-provenance@v3`.

**Refactor permission:** none.

## Post-execution review (1 issue)

Reviews each pass after `Worker Done`. Gates the next pass to `Done`. Same template as ALP-2455 for the IAM stub.

## Gate review body

```
Planning complete. Outcome: Ready for execution.
Authorized execution parent: `ALP-<backlog>`.
Execute: ALP-<pass1>, ALP-<pass2>, ALP-<pass3>, ALP-<pass4>, ALP-<review>.
Required order: ALP-<pass1> before ALP-<pass2> before ALP-<pass3> before ALP-<pass4>.
ALP-<review> (post execution review) reviews each pass after `Worker Done` and gates the next pass to `Done`.

## Interleaved human gates (not Nancy-selectable, tracked in post-execution review)

After ALP-<pass2> is reviewed `Done` and BEFORE ALP-<pass3> starts:
1. From local: `cargo publish --workspace` (existing crates.io API token).
2. In crates.io UI: configure Trusted Publishing on lilo-im-core/store/stub
   (owner: littleorgans, repo: identity-matters, workflow: publish.yml).

After ALP-<pass4> is reviewed `Done`:
3. Smoke test: trivial commit → release-plz bumps 0.1.1 → publish.yml fires → 0.1.1 on crates.io via OIDC.
4. Credential cleanup: `cargo logout`, revoke API token.
5. Bus message to nancy-ALP-2441: "lilo-im-* 0.1.0 published, swap path deps when ready."

The post-execution review issue tracks these gates as human checkpoints between pass reviews.

## Cross-product dependencies

* nancy-ALP-2441 (session-matters Pass 5 consumer wiring) currently uses path deps. After this work publishes 0.1.0, that nancy migrates from path to version deps as a follow-up. Not blocked by this gate.
```

## Future considerations (out of scope here)

- **runtime-matters, transport-matters, session-matters** will follow the same shape: rename to `lilo-<prefix>-*`, adopt release-plz + Trusted Publishing, replace cargo-dist if applicable. Each is a separate Linear gate.
- **`helioy-*` namespace** for enterprise-tier crates (when applicable) stays reserved. Not touched by this work.
- **`identity-matters` 0.0.0 squat**: leave dormant; update description to point to `lilo-im-core` at some future polish pass. Optional.
- **Yanking `helioy@0.0.0` and `runtime-matters@0.0.0` etc.** for cleaner namespace: not now. Defensive squats cost nothing.

## References

- nancy-ALP-2441 bus message (2026-05-17 08:07 UTC) — the source guidance for this work.
- Linear ALP-2453 — IAM v1 stub (prior umbrella, completed).
- Linear ALP-2447 — session-matters Pass 5 consumer wiring (waiting downstream of this).
- `cargo publish --workspace` stabilization, Rust 1.90, September 2025.
- crates.io Trusted Publishing GA for GitHub Actions, July 2025.
- release-plz: https://release-plz.dev/
- matklad — Large Rust Workspaces (workspace shape guidance).
- AWS / Cloudflare / Fermyon prefix-namespace precedents.
