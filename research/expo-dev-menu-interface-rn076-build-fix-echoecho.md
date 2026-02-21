---
title: expo-dev-menu-interface Build Failure with RN 0.76 - Root Cause and Fix
type: research
tags: [expo, react-native, android, gradle, yarn-patch, build]
summary: yarn patch created locally but neither committed nor reflected in yarn.lock — CI and fresh clones build against unpatched expo-dev-menu-interface@1.8.4 and hit the jsEngineResolutionAlgorithm removal
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

The build failure is **not a version mismatch requiring an upgrade**. It is a yarn patch that was applied locally but never committed to git. The fix is already written and sitting in the working tree — it just needs to be committed.

## Findings

### Environment

| Package | Pinned (package.json) | Installed (node_modules) |
|---|---|---|
| `expo` | `~52.0.0` | `52.0.49` |
| `react-native` | `0.76.7` | `0.76.7` |
| `expo-dev-client` | `~4.0.0` | `4.0.29` |
| `expo-dev-menu` | (transitive) | `5.0.23` |
| `expo-dev-menu-interface` | (transitive) | `1.8.4` |

Note: the problem statement says "RN 0.76.9" but the installed version is `0.76.7`. The root cause is the same either way — `jsEngineResolutionAlgorithm` was removed from `ReactHost` in RN 0.76.x.

### What `expo-dev-menu-interface@1.8.4` ships

The published npm package at `1.8.4` contains the OLD code that calls the removed API:

```kotlin
// OLD (buggy for RN 0.76+)
return if (reactHost.jsEngineResolutionAlgorithm == JSEngineResolutionAlgorithm.JSC) {
  "JSC"
} else {
  "Hermes"
}
```

### The patch — exists but uncommitted

A correct fix was authored as a yarn patch:

**File:** `.yarn/patches/expo-dev-menu-interface-npm-1.8.4-5236be8358.patch`

The patch removes the `JSEngineResolutionAlgorithm` import and replaces the `jsExecutorName` getter with:

```kotlin
// RN 0.76.7 removed jsEngineResolutionAlgorithm from ReactHost.
// Bridgeless mode in RN 0.76+ exclusively uses Hermes.
return "Hermes"
```

This is correct — RN 0.76 bridgeless mode is Hermes-only.

### Why the build fails on CI / fresh clones

Three things must all land in git together for the patch to take effect:

1. `.yarn/patches/expo-dev-menu-interface-npm-1.8.4-5236be8358.patch` — the patch file itself
2. `package.json` `resolutions` entry pointing to the patch
3. `yarn.lock` updated to reflect the patch resolution

**Current state:**

| Artifact | Local disk | Committed to git |
|---|---|---|
| Patch file | YES | NO — never `git add`ed |
| `package.json` resolutions | YES (unstaged) | NO — unstaged modification |
| `yarn.lock` patch entry | NO — still shows `npm:1.8.4` raw | NO |

The local `node_modules` has the patched file because `yarn install` was run after the patch was written, but the `yarn.lock` was never updated to write the `patch:` resolution entry. On a fresh clone, `yarn install` resolves from the committed `yarn.lock`, which has no patch entry, and installs the unpatched `1.8.4` from npm — producing the build error.

## Exact Fix Required

Three steps, all in one commit:

### Step 1: Run `yarn install` to update yarn.lock with the patch resolution

```bash
cd /path/to/echoecho
yarn install
```

After this, `yarn.lock` should contain an entry like:

```
"expo-dev-menu-interface@patch:expo-dev-menu-interface@npm%3A1.8.4#~/.yarn/patches/expo-dev-menu-interface-npm-1.8.4-5236be8358.patch":
  version: 1.8.4
  resolution: "expo-dev-menu-interface@patch:..."
  checksum: <new-hash>
  ...
```

### Step 2: Commit all three artifacts together

```bash
git add .yarn/patches/expo-dev-menu-interface-npm-1.8.4-5236be8358.patch
git add package.json
git add yarn.lock
git commit -m "fix(android): yarn patch expo-dev-menu-interface for RN 0.76 jsEngineResolutionAlgorithm removal"
```

### What NOT to do

- Do not upgrade `expo-dev-client` or `react-native`. The existing packages are correct for SDK 52; the issue is purely the uncommitted patch.
- Do not run `npx expo install --fix`. That would attempt to upgrade `expo-dev-client` to a version aligned with the latest Expo SDK, not SDK 52.
- The `expo-dev-menu-interface` npm `latest` tag is `55.0.1` (SDK 55). There is no `sdk-52` dist-tag, and `1.8.4` is the correct version for SDK 52.

## Sources

- Inspected `.yarn/patches/expo-dev-menu-interface-npm-1.8.4-5236be8358.patch` directly
- Inspected `node_modules/expo-dev-menu-interface/android/src/main/java/expo/interfaces/devmenu/ReactHostWrapper.kt`
- `git diff package.json` — resolutions field is unstaged
- `git ls-files .yarn/` — returns empty; patch file is untracked
- `git show HEAD:yarn.lock | grep expo-dev-menu-interface` — no patch resolution in committed lock

## Open Questions

- Was `yarn install` ever run in this worktree after the patch was authored? (node_modules is patched, but yarn.lock is not — unusual, possibly the patch file was copied from another location and `yarn install` was not re-run properly.)
