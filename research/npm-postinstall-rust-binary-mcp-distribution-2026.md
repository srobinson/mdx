---
title: "npm postinstall binary download pattern for Rust MCP servers: 2026 assessment"
type: research
tags: [npm, rust, mcp, binary-distribution, supply-chain-security, devtools]
summary: "The npm postinstall pattern remains viable but is increasingly hostile territory; the esbuild-style optionalDependencies pattern is strictly superior for npm distribution, while MCPB bundles represent the emerging MCP-native alternative."
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

The "npm wrapper + postinstall binary download" pattern for distributing Rust CLI tools remains functional in 2026 but faces three compounding headwinds: (1) pnpm 10 blocks lifecycle scripts by default, (2) npm CLI v12 will default to stricter script controls, and (3) the security community consensus has shifted firmly toward treating postinstall scripts as a threat vector rather than a convenience. The esbuild-style `optionalDependencies` pattern with platform-specific scoped packages is the current best practice for npm-based distribution. For MCP servers specifically, the MCPB (MCP Bundle) format, adopted into the official MCP project in November 2025, provides a purpose-built binary distribution mechanism that eliminates npm as a middleman entirely. However, for the specific use case of `npx -y` launch from `.mcp.json`, npm remains the only viable channel since MCPB targets GUI-based installation flows.

## Detailed Findings

### 1. Is npm postinstall binary download still recommended?

**No. It is functional but no longer best practice.**

The pattern works today but is on a declining trajectory:

- **pnpm 10 (late 2025)** blocks all lifecycle scripts by default. Users must explicitly allowlist packages in `pnpm.onlyBuiltDependencies`. This is a breaking change that affects any project using pnpm where your npm package is a dependency. ([Socket](https://socket.dev/blog/pnpm-10-0-0-blocks-lifecycle-scripts-by-default))

- **npm CLI v11** extended `--ignore-scripts` to cover all lifecycle scripts including `prepare`. While `ignore-scripts` is not yet the default, the trajectory is clear. ([npm docs](https://docs.npmjs.com/cli/v11/using-npm/scripts/))

- **npm CLI v12** will default `--allow-git=none`, continuing the trend of restricting execution during install. ([GitHub Blog, Feb 2026](https://github.blog/changelog/2026-02-18-npm-bulk-trusted-publishing-config-and-script-security-now-generally-available/))

- **HackerNews consensus** (thread 45263347): "packages which legitimately require a postinstall script to work correctly are very rare...esbuild is the only dependency which benefits." Community sentiment strongly favors opt-in script execution.

- **Supply chain attacks in 2025-2026** have specifically weaponized postinstall/preinstall scripts: the Shai-Hulud worm (Nov 2025, 796 packages, 132M monthly downloads), the nx hijacking (Aug 2025), and the debug/chalk compromise (Sep 2025, 2.6B weekly downloads). ([CISA](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem))

**Sentry's recommendation** (authoritative source): Use BOTH `optionalDependencies` AND postinstall as a fallback. The postinstall script serves as a backup when `optionalDependencies` resolution fails. ([Sentry Engineering](https://sentry.engineering/blog/publishing-binaries-on-npm))

### 2. Platform-specific npm packages vs. single package with postinstall

**The esbuild/optionalDependencies pattern is strictly superior for reliability.**

The pattern, pioneered by esbuild and adopted by SWC, Turbo, LightningCSS, and Biome:

1. Publish scoped platform packages (e.g., `@scope/tool-darwin-arm64`, `@scope/tool-linux-x64`)
2. Each platform package declares `os` and `cpu` fields in `package.json`
3. The main package lists all platform packages as `optionalDependencies`
4. npm/yarn/pnpm installs only the matching platform package automatically
5. A thin JS shim in the main package resolves to the correct binary via `require.resolve()`

**Advantages:**
- Works with `--ignore-scripts` enabled (the primary security mitigation)
- No network fetch during postinstall (binary is in the npm tarball)
- Integrity verified by npm's own package integrity system
- Works across npm, yarn, pnpm, and bun without special handling

**Known issues:**
- npm lockfile bug (#4828): platform-specific optional dependencies may be omitted from `package-lock.json` when reinstalling with existing `node_modules`. Can cause cross-platform failures when lockfiles are shared.
- Requires publishing N+1 packages (one per platform + the wrapper)
- More complex CI/CD pipeline than a single postinstall script

**For the helioy ecosystem**, migrating from postinstall-download to optionalDependencies would require restructuring the npm package into multiple scoped packages. The wrapper script would use `require.resolve()` instead of shelling out to a downloaded binary.

### 3. Alternative distribution channels

**cargo-binstall**: Downloads prebuilt binaries from GitHub Releases based on crates.io metadata. Excellent for Rust-ecosystem users but requires `cargo-binstall` to be installed. Not viable as a general distribution channel for MCP servers consumed by non-Rust developers. ([cargo-binstall](https://github.com/cargo-bins/cargo-binstall))

**Homebrew**: Reliable for macOS/Linux. GitHub's MCP server does not use it. Requires maintaining a tap or getting into homebrew-core. Good supplemental channel but does not integrate with `.mcp.json` launch patterns.

**Direct binary path in .mcp.json**: Claude Code fully supports `"command": "/absolute/path/to/binary"` in MCP configuration. This eliminates npm entirely but requires users to manually install the binary and maintain the path. Not suitable for team-shared `.mcp.json` files checked into version control.

**Docker (OCI)**: GitHub's official MCP server uses Docker as its primary distribution. The MCP registry supports `oci` as a `registryType`. Provides sandboxing and reproducibility but adds startup overhead and requires Docker.

**MCPB (MCP Bundles)**: The emerging MCP-native format. ZIP archives containing a manifest.json plus the server binary/code. Supports a `binary` server type with platform overrides. Adopted into the official MCP project (github.com/modelcontextprotocol/mcpb) in November 2025. Designed for GUI-based one-click installation (double-click in Claude Desktop). Does NOT integrate with `npx -y` launch patterns. Manifest spec version 0.3 as of December 2025. ([MCPB spec](https://github.com/modelcontextprotocol/mcpb))

**pkgx**: Universal package runner. Has an MCP server integration but is not widely adopted for MCP server distribution specifically.

### 4. npx cold-start penalty for MCP servers

**This is a real UX issue but bounded.**

- Gemini CLI reports 8-12 second delays when MCP servers initialize via npx on first run. ([GitHub issue #4544](https://github.com/google-gemini/gemini-cli/issues/4544))
- Claude Code defaults to a 10-second MCP startup timeout, configurable via `MCP_TIMEOUT` environment variable.
- First-run npx penalty includes: npm registry lookup, package download, postinstall execution (if applicable), then binary launch.
- Subsequent runs use the npx cache, reducing startup to package resolution + binary launch.
- Rust binaries start in under 1 second once launched; TypeScript servers take 4+ seconds. The distribution overhead dominates for Rust servers.

**Mitigation strategies:**
- Set `MCP_TIMEOUT=20000` for users with slow connections
- The optionalDependencies pattern eliminates the postinstall network fetch, reducing cold-start by the download time
- Once cached, npx overhead is primarily the Node.js process startup + shim resolution (~200-500ms)

### 5. npm postinstall security trajectory

**postinstall is not being deprecated, but the ecosystem is making it increasingly friction-laden.**

Key developments:
- npm has NOT announced plans to block postinstall scripts
- npm v11 extended `--ignore-scripts` scope but did not change the default
- pnpm 10 (the second most popular Node package manager) blocks scripts by default
- `@lavamoat/allow-scripts` provides allowlist-based script execution control
- OWASP recommends `ignore-scripts=true` in `.npmrc` as a baseline security posture

**Risk assessment for the helioy pattern:** Medium-term risk. The postinstall-only pattern will increasingly encounter environments where it silently fails (pnpm users, corporate environments with `ignore-scripts=true`, CI/CD with hardened npm configs). The dual approach (optionalDependencies + postinstall fallback) handles this gracefully.

### 6. MCP registry and Anthropic's recommended distribution

**npm is the de facto standard for MCP registry listings. Anthropic has no official recommendation for binary distribution.**

The MCP registry (`registry.modelcontextprotocol.io`) supports these `registryType` values:
- `npm` (primary, most supported)
- `pypi`
- `nuget`
- `oci` (Docker)
- `mcpb` (MCP Bundle)

Notably absent: `cargo`, `homebrew`, direct binary URLs.

The Claude Code documentation's own MCP server table generates installation commands using `npx -y <package>` for npm-distributed servers. This is the path of least resistance for discoverability. The Anthropic internal API at `api.anthropic.com/mcp-registry/` serves the same data.

Claude Code's `.mcp.json` supports three command patterns:
1. `"command": "npx", "args": ["-y", "package-name", "serve"]` (npm distribution)
2. `"command": "/absolute/path/to/binary"` (local binary)
3. `"command": "docker", "args": ["run", ...]` (Docker)

For team-shared `.mcp.json` files, only patterns 1 and 3 are portable.

## Recommendation for the Helioy Ecosystem

**Short term (now):** Migrate from postinstall-only to the dual optionalDependencies + postinstall fallback pattern. This is the Sentry-recommended approach and handles the widest range of package manager configurations.

**Structure:**
```
@helioy/cm-darwin-arm64   (os: ["darwin"], cpu: ["arm64"])
@helioy/cm-darwin-x64     (os: ["darwin"], cpu: ["x64"])
@helioy/cm-linux-arm64    (os: ["linux"], cpu: ["arm64"])
@helioy/cm-linux-x64      (os: ["linux"], cpu: ["x64"])
context-matters            (wrapper with optionalDependencies + postinstall fallback)
```

**Medium term:** Watch MCPB adoption. If Claude Code adds `npx`-equivalent support for `.mcpb` bundles (or if the MCP registry adds a `binary` registryType with GitHub Release URLs), that would be the cleaner path for Rust binary distribution.

**The `npx -y context-matters serve` launch pattern remains correct** for Claude Code MCP integration. It is the only portable, zero-setup pattern that works in shared `.mcp.json` files. The internal distribution mechanism (how the binary gets onto disk after `npm install`) should change from postinstall-download to optionalDependencies, but the external interface stays the same.

## Sources Consulted

### Engineering Blogs
- [Sentry Engineering: Publishing Binaries on npm](https://sentry.engineering/blog/publishing-binaries-on-npm) - authoritative dual-approach recommendation
- [Orhun's Blog: Packaging Rust for npm](https://blog.orhun.dev/packaging-rust-for-npm/) - optionalDependencies pattern walkthrough
- [Ivan Carvalho: Rust CLI to too many places](https://ivaniscoding.github.io/posts/rustpackaging1/) - multi-channel comparison
- [DEV.to: MCP Server Executables Explained](https://dev.to/leomarsh/mcp-server-executables-explained-npx-uvx-docker-and-beyond-1i1n)

### Official Documentation
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) - configuration patterns, timeout, scopes
- [MCP Registry server.json spec](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md) - registryType values
- [MCPB GitHub](https://github.com/modelcontextprotocol/mcpb) - bundle format specification
- [MCP Registry blog post](http://blog.modelcontextprotocol.io/posts/2025-11-20-adopting-mcpb/) - MCPB adoption announcement

### Security Sources
- [CISA: npm supply chain compromise](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem)
- [GitHub Blog: npm script security GA](https://github.blog/changelog/2026-02-18-npm-bulk-trusted-publishing-config-and-script-security-now-generally-available/)
- [Socket: pnpm 10 blocks lifecycle scripts](https://socket.dev/blog/pnpm-10-0-0-blocks-lifecycle-scripts-by-default)
- [HackerNews: npm postinstall discussion](https://news.ycombinator.com/item?id=45263347)

### GitHub
- [esbuild optionalDependencies PR #1621](https://github.com/evanw/esbuild/pull/1621)
- [esbuild issue #789: platform-specific binaries strategy](https://github.com/evanw/esbuild/issues/789)
- [npm CLI lockfile bug #4828](https://github.com/npm/cli/issues/4828)
- [GitHub MCP Server](https://github.com/github/github-mcp-server) - Docker-first distribution example
- [Gemini CLI MCP startup issue #4544](https://github.com/google-gemini/gemini-cli/issues/4544)

### Package Registries
- [cargo-binstall](https://github.com/cargo-bins/cargo-binstall)
- [MCPB bundles docs](https://www.mcpbundles.com/docs/concepts/mcpb-files)

## Source Quality Assessment

**High confidence** on: npm security trajectory (multiple independent sources including CISA, OWASP, and package manager changelogs), optionalDependencies pattern mechanics (esbuild source code + Sentry engineering blog), Claude Code MCP configuration (official docs).

**Medium confidence** on: MCPB adoption trajectory (specification is 0.3, adoption is early), cold-start timing numbers (based on Gemini CLI reports, not systematic benchmarks for Claude Code specifically).

**Low confidence** on: npm v12 timeline and whether `ignore-scripts` will become the default (signaled but not confirmed).

## Open Questions

1. Will the MCP registry add a `cargo` or `binary` registryType that supports direct GitHub Release URLs? This would be the cleanest path for Rust binary distribution.
2. Will MCPB gain CLI-based installation support (not just GUI double-click), making it viable for `.mcp.json` integration?
3. What is Claude Code's actual npx cold-start time for the helioy MCP servers? The 8-12s Gemini number may not apply.
4. Does the npm lockfile bug (#4828) affect the helioy CI/CD pipeline when building across platforms?

## Actionable Takeaways

1. **Migrate to optionalDependencies pattern** for context-matters, attention-matters, and fmm npm packages. Keep postinstall as fallback per Sentry's recommendation.
2. **Do not abandon npm** as the distribution channel for MCP servers. It remains the only portable option for `.mcp.json` configuration.
3. **Monitor MCPB spec** (currently 0.3) for CLI installation support. If added, MCPB becomes the preferred channel for Claude Desktop users while npm handles Claude Code.
4. **Test with pnpm 10** to confirm the dual-approach works when lifecycle scripts are blocked by default.
5. **Consider publishing to the MCP registry** for discoverability via `registry.modelcontextprotocol.io`.
