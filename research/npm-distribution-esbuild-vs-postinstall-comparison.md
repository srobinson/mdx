---
title: "npm Binary Distribution: esbuild optionalDependencies Pattern vs attention-matters postinstall Pattern"
type: research
tags: [npm, distribution, binary, esbuild, rust, postinstall, optionalDependencies, release-please, github-actions]
summary: The esbuild pattern eliminates postinstall scripts and GitHub Release availability as a runtime dependency, at the cost of N+1 npm packages and a substantially more complex release pipeline. For helioy's current scale, the migration cost is not worth the benefit.
status: active
source: quick-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

The attention-matters npm distribution uses a postinstall-download pattern: one npm package ships a Node.js script that fetches the correct platform binary from GitHub Releases at install time. The esbuild pattern inverts this: platform-specific binaries are pre-bundled into dedicated npm packages, and the main package declares them as `optionalDependencies` so the package manager installs only the matching one automatically, with no postinstall script involved.

The esbuild pattern is more robust in production (no network call, no GitHub Releases dependency at install time, no postinstall scripts blocked by security policy), but it requires significantly more release pipeline work and multiplies the npm package count. For helioy's current scale -- 2-3 tools consumed primarily via Claude Code MCP -- the migration cost outweighs the benefit. The existing pattern is reasonable; its failure modes are known and recoverable.

---

## 1. Current attention-matters Pattern: End to End

### Package structure

```
npm/
  attention-matters/          # main installable package
    package.json              # version: 0.1.17, bin: am -> bin/am
    bin/am                    # Node.js wrapper script
    scripts/install.js        # postinstall: downloads binary from GitHub Releases
  @attention-matters/cli/     # convenience alias
    package.json              # depends on attention-matters@0.1.17
```

There are exactly two npm packages. `@attention-matters/cli` is a thin wrapper whose sole purpose is discoverability under a scoped name -- it pins a hard dependency on the exact version of `attention-matters`.

### Version management

release-please-config.json manages a single release root at `.` with `release-type: simple`. On merge to main, it bumps `$.workspace.package.version` in Cargo.toml and propagates the same version string to:

- `npm/attention-matters/package.json` ($.version)
- `npm/@attention-matters/cli/package.json` ($.version and $.dependencies['attention-matters'])

All four fields are kept in lock-step by release-please's `extra-files` mechanism. There is one version number in the entire system.

### GitHub Actions release pipeline

The `release.yml` workflow runs on every push to main and executes four sequential jobs:

1. **release-please**: Runs the googleapis/release-please-action. If a release PR was merged, it creates a GitHub Release and emits `release_created=true` plus `tag_name`.

2. **build** (matrix, conditional on `release_created`): Runs in parallel across four targets using a strategy matrix:
   - `aarch64-apple-darwin` on `macos-latest`
   - `x86_64-apple-darwin` on `macos-latest`
   - `x86_64-unknown-linux-gnu` on `ubuntu-latest`
   - `aarch64-unknown-linux-gnu` on `ubuntu-latest` (cross-compiled via `gcc-aarch64-linux-gnu`)

   Each job runs `cargo build --release --target <target> -p am-cli`, tars the binary as `am-<target>.tar.gz`, and uploads it as an Actions artifact.

3. **upload-assets**: Downloads all four artifacts, generates `sha256sums.txt`, and uploads all files to the GitHub Release via `gh release upload`.

4. **publish-npm**: Checks whether each package version is already on the registry (idempotent guard), then publishes both packages with `--provenance` (npm OIDC provenance via `id-token: write`).

### Install-time behavior (postinstall)

When a user runs `npm install attention-matters` (or `npx attention-matters`):

1. npm downloads the package from the registry.
2. npm runs `scripts/install.js` as the postinstall hook.
3. `install.js` detects platform (`process.platform` + `process.arch`), maps it to a Rust target triple, reads the version from `package.json`, constructs a GitHub Releases URL, and downloads `am-<target>.tar.gz` over HTTPS.
4. It extracts the tarball with `tar xzf`, sets `chmod 0o755`, and places the binary at `scripts/am`.
5. `bin/am` (the wrapper) checks if `scripts/am` exists, execs it with `execFileSync`, and falls back to a system `am` if the native binary is missing.

The skip condition (`stat.size > 10000`) prevents redundant downloads in CI caching scenarios.

### Failure modes

| Failure | Impact | Recovery |
|---|---|---|
| GitHub Releases unavailable at install time | Postinstall exits non-zero (but does NOT fail the install -- the `catch` block only logs) | Binary not present; `bin/am` prints install instructions |
| GitHub Release artifact missing for version | Same as above | Manual `cargo install am-cli` or Homebrew |
| Unsupported platform | `process.exit(1)` in `getTarget()` -- this DOES fail the install | Manual build |
| Binary size check bypassed by stale file | Stale binary used silently | Manual re-install |
| npm publish succeeds but binary upload fails | Package on registry points to a release with no assets | Users get the log-and-continue behavior |

The most notable design decision: the `catch` block in `install()` deliberately does not rethrow. The install succeeds even if the binary download fails, relying on the wrapper's runtime error message. This is a reasonable choice for developer tooling but surprising for users.

### pnpm 10 compatibility

pnpm 10 tightened its handling of postinstall scripts in packages not listed as direct dependencies. By default, pnpm does not run lifecycle scripts for transitive dependencies. Since `attention-matters` is typically installed as a direct dependency (or via `npx`), this is not currently a problem. However, if it were ever consumed transitively, the postinstall would silently not run.

---

## 2. The esbuild Pattern

### Structure

esbuild publishes one main package (`esbuild`) and N platform-specific packages (`@esbuild/darwin-arm64`, `@esbuild/linux-x64`, etc.). The main `package.json` lists all platform packages under `optionalDependencies`:

```json
{
  "optionalDependencies": {
    "@esbuild/darwin-arm64":  "0.x.y",
    "@esbuild/darwin-x64":    "0.x.y",
    "@esbuild/linux-x64":     "0.x.y",
    "@esbuild/linux-arm64":   "0.x.y"
  }
}
```

Each platform package contains the compiled binary as a file in the package itself (not fetched at install time). The `os` and `cpu` fields in each platform package's `package.json` tell npm/pnpm/yarn to skip installation on non-matching platforms:

```json
{
  "name": "@esbuild/darwin-arm64",
  "os": ["darwin"],
  "cpu": ["arm64"],
  "bin": { "esbuild": "bin/esbuild" }
}
```

The package manager resolves optionalDependencies, sees that `@esbuild/linux-x64` does not match the current platform, and skips it without error. No postinstall script runs. The binary is present immediately after `npm install` completes.

### What this would look like for attention-matters

The equivalent structure would be:

```
npm/
  attention-matters/                         # main package, no postinstall
    package.json                             # optionalDependencies: all 4 platform packages
  @attention-matters/darwin-arm64/           # contains am binary for aarch64-apple-darwin
    package.json                             # os: [darwin], cpu: [arm64]
    bin/am                                   # actual compiled binary committed or embedded
  @attention-matters/darwin-x64/
  @attention-matters/linux-x64/
  @attention-matters/linux-arm64/
```

That is 5 npm packages instead of 2. The `@attention-matters/cli` convenience alias becomes less necessary because the scoped namespace is already occupied by platform packages.

### Versioning under the esbuild pattern

All platform packages must be published at the same version as the main package. This is a hard constraint: the main package's `optionalDependencies` pins exact versions. release-please would need to bump all four platform package `package.json` files as `extra-files`, and the publish step must publish all five packages atomically (or in the correct order, with the platform packages first).

release-please can handle this via additional `extra-files` entries, but the manifest grows considerably.

### Binary delivery mechanism

Instead of downloading from GitHub Releases at install time, each platform binary must be embedded in its npm package tarball at publish time. This means the publish step in GitHub Actions must:

1. Build all four binaries (as it does today).
2. Copy each binary into the corresponding `npm/@attention-matters/<platform>/bin/` directory.
3. Publish each platform package.
4. Publish the main package last (after platform packages are on the registry).

The binaries are committed into the platform packages only transiently during the CI publish step -- they should not be committed to the git repository itself (binary blobs in git are an antipattern). This means the publish script must write the binary file into the npm package directory before running `npm publish`.

---

## 3. Tradeoffs

### Security

| Dimension | Postinstall (current) | optionalDependencies |
|---|---|---|
| Postinstall script execution | Yes -- runs arbitrary Node.js | No postinstall required |
| Network call at install time | Yes -- to GitHub Releases | No (binary in registry tarball) |
| Supply chain surface | GitHub Releases URL + npm registry | npm registry only |
| npm provenance | Supported (--provenance used) | Supported |
| Binary verification | sha256sums.txt available but not verified by install.js | npm verifies tarball integrity |

The postinstall pattern has a meaningful security gap: `install.js` does not verify the downloaded binary against `sha256sums.txt`. A compromised GitHub account or a DNS hijack could serve a malicious binary. The esbuild pattern eliminates this vector because npm verifies tarball checksums against the registry's stored hashes.

Additionally, some corporate environments and security-hardened CI systems disable postinstall scripts entirely (`--ignore-scripts`). Under such policies, the current pattern silently produces a broken install. The esbuild pattern works correctly with `--ignore-scripts`.

### Reliability

| Dimension | Postinstall (current) | optionalDependencies |
|---|---|---|
| GitHub Releases must be reachable at install time | Yes | No |
| npm registry must be reachable | Yes | Yes |
| Failure mode | Silent (binary missing, wrapper errors at runtime) | Hard failure at resolve time if package missing |
| Air-gapped / offline installs | Broken | Works if registry mirror is available |
| Version mismatch between npm pkg and GH release | Possible (publish can succeed before assets uploaded) | Impossible (binary is in the tarball) |

The current pipeline has a sequencing dependency that the esbuild pattern eliminates: `publish-npm` runs after `upload-assets`, but if an asset upload partially fails, a published npm package can reference a GitHub Release that lacks one or more platform tarballs.

### Complexity

| Dimension | Postinstall (current) | optionalDependencies |
|---|---|---|
| npm package count | 2 | 5 (4 platform + 1 main) |
| release-please extra-files entries | 4 | 12+ (3 per platform package + main) |
| GitHub Actions publish logic | 2 packages, sequential | 5 packages, platform packages first |
| Binary delivery in CI | Upload to GH Release | Copy binary into npm package dir before publish |
| install.js maintenance | Required | Eliminated |
| bin/am wrapper | Required | Can be replaced with direct bin entry |

The esbuild pattern is simpler at install time and more complex at release time.

### pnpm 10 compatibility

pnpm 10 fully supports `optionalDependencies` with `os`/`cpu` filtering. It does not run postinstall scripts for packages installed as optional dependencies that fail the platform check (they are not installed at all). The esbuild pattern is fully compatible with pnpm 10's stricter lifecycle script defaults.

The current postinstall pattern is compatible with pnpm 10 when `attention-matters` is a direct dependency, but would break silently if pnpm's `onlyBuiltDependencies` list were configured to exclude it.

---

## 4. Migration Effort

### release-please-config.json

The `extra-files` array would expand from 4 entries to roughly 12-14: version bump in each platform package's `package.json`, and the main package's `optionalDependencies` values for each platform package.

### GitHub Actions release.yml

Three changes:

1. **build job**: No change -- the matrix already produces four platform tarballs.

2. **publish-npm job**: Must be restructured to:
   - Copy each binary into its platform package directory (`npm/@attention-matters/<platform>/bin/am`).
   - Publish the four platform packages first.
   - Publish the main `attention-matters` package after all platform packages are confirmed live.
   - Preserve the idempotency guard (`npm view` check before publish).

3. **upload-assets job**: Remains useful for GitHub Releases as a source-of-truth and for users who install via Homebrew or direct download, but is no longer on the critical path for `npm install`.

### npm package structure

- Add four new directories under `npm/@attention-matters/`: `darwin-arm64`, `darwin-x64`, `linux-x64`, `linux-arm64`.
- Each needs a `package.json` with `os`, `cpu`, `bin`, and appropriate metadata.
- Each needs a `bin/` directory (initially empty -- populated by CI during publish).
- Add `.gitignore` to each `bin/` to exclude the binary from source control.
- Update `npm/attention-matters/package.json`: remove `scripts.postinstall`, remove `files` entry for `scripts/install.js`, add `optionalDependencies`, update `bin` to point directly at platform binary (or keep wrapper).
- Delete `npm/attention-matters/scripts/install.js` and `bin/am` wrapper.

The bin resolution with optionalDependencies requires the main package to locate which platform package was installed. esbuild does this with a small `bin.js` script that requires the platform package. This is simpler than the current wrapper but still requires a few lines of JavaScript.

Estimated effort: 1-2 days of careful work to restructure packages, update CI, and verify end-to-end on all four platforms.

---

## 5. Recommendation

**Do not migrate now.**

The rationale:

1. **Scale does not justify complexity.** helioy currently has 2-3 tools (attention-matters, fmm, mdcontext). The primary consumer is Claude Code MCP, which installs packages in a controlled environment. The failure modes of the postinstall pattern are low-probability in this context.

2. **The current failure mode is recoverable.** The `catch` block that swallows download errors is a known weakness, but the wrapper provides a clear fallback message, and `cargo install am-cli` is always available. Users are developers.

3. **The migration doubles ongoing release complexity.** Five packages instead of two means five publication steps, cross-package version synchronization, and CI that must copy binaries into npm package directories before publishing. Every release touches more moving parts.

4. **The security gap is real but tolerable at current scale.** Adding SHA-256 verification to `install.js` would close the most significant security hole without requiring full migration. This is a one-function addition.

**What to do instead:**

- Add SHA-256 verification in `install.js` against the `sha256sums.txt` file that is already generated and uploaded to GitHub Releases. This closes the binary integrity gap.
- Add a `--ignore-scripts` note to installation documentation so users in restricted environments know to use `cargo install am-cli`.
- Revisit the esbuild pattern if helioy tools acquire a broader user base where corporate firewall restrictions, air-gapped installs, or security audits become common.

**When the esbuild pattern becomes worth it:**

- The tool is consumed by non-developer end users who cannot fall back to `cargo install`.
- Security audits flag postinstall scripts as a blocker.
- pnpm `onlyBuiltDependencies` configuration starts breaking installs in practice.
- A third helioy tool needs the same distribution infrastructure, making the per-package overhead amortize across the ecosystem.

---

## Sources

- attention-matters source: `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/`
  - `npm/attention-matters/package.json`
  - `npm/attention-matters/scripts/install.js`
  - `npm/attention-matters/bin/am`
  - `npm/@attention-matters/cli/package.json`
  - `release-please-config.json`
  - `Cargo.toml`
  - `.github/workflows/release.yml`
  - `.github/workflows/ci.yml`
- esbuild pattern: knowledge of esbuild npm package structure (public npm registry, esbuild repository)
- pnpm 10 lifecycle script behavior: pnpm documentation on `onlyBuiltDependencies` and optional dependency handling

## Open Questions

- Does `install.js` need to verify against `sha256sums.txt`? The file is already published to GitHub Releases but not consulted by the installer.
- Should Windows (x86_64-pc-windows-msvc) be added as a supported platform? It is absent from both the platform map and the build matrix.
- If fmm or mdcontext adopt the same postinstall distribution pattern, does a shared npm install helper library make sense to avoid duplicating `install.js`?
- What is the behavior of the `@attention-matters/cli` package if `attention-matters` fails its postinstall? The dependency is pinned by exact version, so it installs `attention-matters` which runs postinstall -- the alias provides no additional resilience.
