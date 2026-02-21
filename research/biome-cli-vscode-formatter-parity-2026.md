---
title: "Biome CLI vs VS Code Extension Formatter Parity (2026)"
type: research
tags: [biome, formatter, vscode, lsp, json, tooling]
summary: "CLI and VS Code extension use identical formatter code via lsp-proxy, but config resolution bugs and VS Code per-language override behavior cause real-world discrepancies"
status: active
source: deep-research
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

## Executive Summary

Biome's CLI and VS Code extension share the same Rust formatter binary via the `lsp-proxy` daemon architecture. There is no separate formatting pipeline in the extension. When CLI and extension produce different output, the root cause is always config resolution: the LSP loading the wrong config (or falling back to defaults), VS Code silently assigning a non-Biome formatter to specific file types, or workspace nesting creating competing LSP instances.

## 1. CLI/Extension Formatter Architecture

The VS Code extension does NOT contain its own formatter. It spawns the Biome binary as an LSP server using the `lsp-proxy` command, which creates two processes: a daemon that executes operations and a proxy server mediating JSON-RPC between the editor and daemon.

**Source**: Biome docs "Integrate Biome in an editor extension" (biomejs.dev/guides/editors/create-an-extension/)

The `biome.lsp.bin` setting overrides which binary the extension spawns. It accepts a string path or a platform-keyed object. When omitted, the extension resolves the binary from `node_modules/@biomejs/biome` or `@biomejs/cli-*` packages.

**Implication**: pointing `biome.lsp.bin` to `./node_modules/.bin/biome` guarantees the extension uses the exact same binary version as the CLI. The formatter code path is identical because it IS the same binary.

## 2. Known Config Resolution Bugs Causing Discrepancies

### 2a. Relative `configurationPath` broken in 2.4.0+ (fixed 2.4.8+)

Issue #9217: Starting with Biome 2.4.0, `biome.configurationPath` set to a relative path caused the LSP to fail to load config. The LSP would silently fall back to defaults, producing different formatting than CLI.

**Fix**: PR #9392 (merged 2026-03-12) corrected project directory resolution when configurationPath points outside workspace. PR #9441 (merged 2026-03-30) fixed most-specific project root selection in multi-root workspaces.

**Status as of 2.4.11**: Fixed for most cases. Use absolute paths for `configurationPath` if you encounter issues.

### 2b. Monorepo/nested workspace config loading

Issue #7138 (recurring since 2025-08, still referenced 2026-03): In monorepos where `biome.json` lives in a subdirectory, the extension frequently loads the wrong config or falls back to defaults. Symptoms: tabs vs spaces, wrong line width, wrong quote style.

**Workaround**: Place a root-level `biome.json` that `extends` the subdirectory config. Remove `biome.configurationPath` from VS Code settings.

### 2c. Multi-root workspace causes competing LSP instances

Issue #817 (biome-vscode): When VS Code workspace includes a root folder AND subfolders, the extension spawns one LSP per workspace folder. The root LSP's document selector matches files in subfolders too, producing duplicate formatting passes that can corrupt files.

**Fix as of v3.5.0+**: The extension now warns about overlapping workspace roots. The workaround is `"biome.enabled": false` in root `.vscode/settings.json`, while enabling it per subfolder. This is still an active pain point (April 2026).

## 3. JSON Array Expand Behavior

### The `json.formatter.expand` option

- `"auto"` (default): Objects expand if first property has a newline. **Arrays collapse to single line if they fit within `lineWidth`**.
- `"always"`: Always expand to multiple lines regardless of length.
- `"never"`: Collapse to single line if it fits within `lineWidth`.

For `package.json` specifically, Biome defaults to `"always"` unless configured otherwise (Biome v2 breaking change).

### The specific discrepancy pattern (short arrays)

When the CLI collapses short arrays onto one line but the extension expands them, the root cause is the extension not loading the `biome.json` config. Without config:
- Default `lineWidth` is 80 (same for both)
- Default `expand` is `"auto"`

If the extension falls back to defaults and uses a different `lineWidth` or if the file is `package.json` (where `"always"` is the default), the behavior diverges.

**Issue #701 (biome-vscode)**: Exact reproduction of this pattern. User reports arrays expanded by extension, collapsed by CLI. Same config, same version. Closed 2026-03-14 as could not reproduce. This suggests it is intermittent and config-resolution-dependent.

### Auto vs Never for arrays

Discussion #8364 confirms: `"auto"` behaves identically to `"never"` for arrays. The `"auto"` "object first property newline" heuristic only applies to object literals. For arrays, the only distinction is between `"always"` (force expand) and the line-width-based collapse.

## 4. VS Code Per-Language Formatter Override Trap

Issue #451 (biome-vscode): Setting `"editor.defaultFormatter": "biomejs.biome"` at the top level is NOT sufficient. VS Code allows per-language formatter overrides that take precedence. If another extension (Prettier, TypeScript built-in, etc.) has been assigned as the formatter for `[json]`, `[typescript]`, etc., it will silently override Biome.

**This is a VS Code platform limitation, not a Biome bug.** Confirmed by ematipico (Biome maintainer).

## 5. Recommended VS Code Configuration for Parity

```jsonc
// .vscode/settings.json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "biomejs.biome",
  "biome.enabled": true,
  "biome.requireConfiguration": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports.biome": "explicit",
    "source.fixAll.biome": "explicit"
  },
  // REQUIRED: explicit per-language overrides to prevent VS Code from
  // silently assigning another formatter
  "[javascript]": { "editor.defaultFormatter": "biomejs.biome" },
  "[typescript]": { "editor.defaultFormatter": "biomejs.biome" },
  "[javascriptreact]": { "editor.defaultFormatter": "biomejs.biome" },
  "[typescriptreact]": { "editor.defaultFormatter": "biomejs.biome" },
  "[json]": { "editor.defaultFormatter": "biomejs.biome" },
  "[jsonc]": { "editor.defaultFormatter": "biomejs.biome" },
  "[css]": { "editor.defaultFormatter": "biomejs.biome" }
}
```

Additional steps:
1. Set `biome.lsp.bin` to the project binary only if you need to override the auto-resolved version.
2. Place `biome.json` at the workspace root. If it must live in a subdirectory, use an absolute path for `biome.configurationPath` or use the `extends` pattern with a root-level config.
3. For monorepos with multi-root workspaces: set `"biome.enabled": false` at the root level and `"biome.enabled": true` per subfolder.
4. Set `"biome.requireConfiguration": true` to prevent the extension from formatting with defaults when it cannot find config.

## 6. Biome vs Prettier Hybrid Setup (2026 Status)

The community consensus for 2026:
- **New projects**: Use Biome for both formatting and linting. No Prettier needed.
- **Existing projects**: Migrate incrementally. Biome for formatting + most linting, ESLint only for rules Biome lacks (react-hooks, type-aware rules expected late 2026).
- **Hybrid Biome+Prettier is no longer commonly recommended**. Biome's formatter is Prettier-compatible for JS/TS/JSON/CSS. The remaining gaps are HTML, Markdown (formatter just landed in v2.4), and embedded languages (GraphQL in template literals).

Biome is 10-25x faster than ESLint+Prettier combined. On 10k files: format in 0.3s vs Prettier's 12.1s.

## Sources Consulted

### GitHub Issues (biomejs/biome)
- #1100: VSCode extension format disagrees with CLI (2023-12, closed as PEBKAC)
- #504: lsp-proxy --config-path not working during formatting (2023-10, fixed)
- #4383: Formatter produces different output on 2nd run (2024-10, fixed)
- #7138: VS Code extension config issue format on save (2025-08, config resolution)
- #9217: configurationPath relative path broken in 2.4.0 (2026-02, fixed PR #9392)
- #9741: LSP organizeImports filtered out in 2.4.10 (2026-03, fixed)
- #8635: Extension crashes with 2.3.10 server (2025-12, fixed)

### GitHub Issues (biomejs/biome-vscode)
- #451: CLI & VS Code format on save behavior different (2024-12, VS Code limitation)
- #701: JSON formatted differently between CLI and extension (2025-07, could not reproduce)
- #817: Multiple biome entries from workspace causes corrupted formatting (2025-10, warning added)
- #721: biome.lsp.bin does not expand VS Code variables (2025-07, open)
- #230: Discussion on recommended VS Code settings (active)

### GitHub Discussions
- #8364: formatter.expand and attributePosition rework proposal (2025-12)
- #3493: Biome formatter without auto-wrapping

### Documentation
- biomejs.dev/reference/vscode/
- biomejs.dev/formatter/
- biomejs.dev/reference/configuration/
- biomejs.dev/guides/editors/create-an-extension/
- biomejs.dev/formatter/differences-with-prettier/

### Community
- HN: news.ycombinator.com/item?id=43913950 (May 2025 migration discussion)
- dev.to: Biome migration guide for 2026
- pkgpulse.com: Biome vs ESLint+Prettier comparison

## Source Quality Assessment

**High confidence** on the architecture claim (CLI and LSP share the same binary). This is confirmed by official docs, the lsp-proxy command structure, and multiple maintainer comments (ematipico).

**High confidence** on config resolution as the root cause of discrepancies. Every reported case of CLI/extension disagreement traces back to either: wrong config loaded, config not found, or VS Code per-language override.

**Medium confidence** on the JSON array expand behavior specifically. Issue #701 was closed as "cannot reproduce," suggesting it is intermittent and environment-dependent. The theoretical explanation (defaults vs loaded config) is sound but lacks a confirmed fix.

**Low signal from Reddit/HN** for this specific topic. Reddit has essentially no Biome-specific discussions. HN has general migration experience reports but nothing on CLI/LSP formatter parity.

## Open Questions

1. Is there a race condition in the LSP where the extension sometimes formats before the config file is fully loaded? The intermittent nature of issue #701 suggests this.
2. Will the `expand` option rework (discussion #8364) add per-type control over array expansion? Currently `"auto"` treats arrays identically to `"never"`.
3. Will the extension eventually respect VS Code path variables in `biome.lsp.bin`? Issue #721 is still open.
