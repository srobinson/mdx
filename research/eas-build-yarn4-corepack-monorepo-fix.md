---
title: EAS Build Yarn 4 / Corepack Fix for Yarn Workspaces Monorepo
type: research
tags: [eas, expo, yarn4, corepack, monorepo, build]
summary: corepack:true in eas.json is the correct fix; eas-build-pre-install runs AFTER corepack enable when using that flag. The script workaround must use npm run (EAS does this automatically) and must be in the app's package.json, not root.
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

Two definitive fixes exist for the `"packageManager": "yarn@4.x"` / Corepack error on EAS Build. The cleaner one is `corepack: true` in `eas.json`. The `eas-build-pre-install` script approach works but has important constraints in a monorepo context. A third option (committing a Yarn binary via `yarnPath`) avoids Corepack entirely.

## Exact Error

```
error This project's package.json defines "packageManager": "yarn@4.9.1". However the current global version of Yarn is 1.22.22.
Corepack must currently be enabled by running corepack enable in your terminal.
yarn install --inline-builds --no-immutable exited with non-zero code: 1
```

---

## Research Questions Answered

### 1. Does `eas-build-pre-install` run before `yarn install`?

**Yes, it does run before `yarn install`.** The execution order is confirmed from source code in `packages/worker/src/build.ts` and `packages/build-tools/src/common/setup.ts`:

```
BuildPhase.INSTALL_CUSTOM_TOOLS  →  prepareRuntimeEnvironment() [corepack: true runs here]
  └─ androidBuilder / iosBuilder
       └─ setupAsync()
            ├─ BuildPhase.PRE_INSTALL_HOOK  →  eas-build-pre-install [hook runs here]
            ├─ BuildPhase.INSTALL_DEPENDENCIES  →  yarn install [runs here]
            └─ BuildPhase.POST_INSTALL_HOOK
```

**Critical caveat for YARN monorepos:** When the package manager is detected as Yarn, EAS intentionally runs the pre-install hook using **`npm run eas-build-pre-install`** instead of `yarn run`. This is documented in source (`packages/build-tools/src/utils/hooks.ts`):

```typescript
// both yarn v2+ and yarn v1 seem to have issues with running preinstall script
// in some cases like doing corepack enable
const packageManager =
  ctx.packageManager === PackageManager.YARN && hook === Hook.PRE_INSTALL
    ? PackageManager.NPM
    : ctx.packageManager;
```

This means the script is always run with `npm run` for Yarn projects. That is intentional and correct.

**The script must live in the `package.json` at `ctx.getReactNativeProjectDirectory()`** -- which in a monorepo is the app subdirectory (e.g. `apps/admin/package.json`), not the monorepo root. EAS resolves the hook from the project root directory as detected from the build profile's `projectRootDirectory`.

**Why `eas-build-pre-install` at the root wasn't working:** The hook is looked up in `ctx.getReactNativeProjectDirectory()` -- the app directory -- not the monorepo root. If the script was only in the monorepo root `package.json`, EAS never found it.

### 2. Correct, documented way to enable Corepack / Yarn 4

**Option A: `corepack: true` in `eas.json` (recommended)**

Add to each build profile in `eas.json`:

```json
{
  "build": {
    "preview": {
      "corepack": true,
      "env": {
        "YARN_ENABLE_IMMUTABLE_INSTALLS": "false"
      }
    },
    "production": {
      "corepack": true
    }
  }
}
```

This is processed in `BuildPhase.INSTALL_CUSTOM_TOOLS` before anything else. The worker calls `corepack enable` via spawn, which installs Corepack shims globally. Yarn then reads `packageManager` from `package.json` and uses version 4.x.

Source: `packages/worker/src/runtimeEnvironment.ts`:
```typescript
if (builderConfig.corepack) {
  ctx.logger.info(`Enabling corepack`);
  await spawn('corepack', ['enable'], { logger: ctx.logger, env: ctx.env });
}
```

**This was merged in expo/eas-build PR #520 (March 25, 2025).** It is available in current EAS CLI.

**Option B: `eas-build-pre-install` hook (works, but placement matters)**

From Expo docs at `https://docs.expo.dev/more/create-expo/`:

```json
{
  "scripts": {
    "eas-build-pre-install": "corepack enable && yarn set version 4"
  }
}
```

This script must be in the **app's** `package.json` (e.g. `apps/admin/package.json`), not the monorepo root. In a Yarn workspaces monorepo, EAS detects the workspace and runs `yarn install` from the monorepo root, but it reads the hook from the app directory.

The `yarn set version 4` is redundant if `.yarnrc.yml` already has `yarnPath` set -- but harmless.

**Option C: Commit Yarn binary via `yarnPath` (avoids Corepack entirely)**

Reported as working for both cloud and local builds (expo/eas-cli issue #2679):

```bash
mkdir -p .yarn/releases
curl -L https://github.com/yarnpkg/berry/releases/download/yarn%404.9.1/yarn-4.9.1.cjs \
  -o .yarn/releases/yarn-4.9.1.cjs
yarn config set yarnPath .yarn/releases/yarn-4.9.1.cjs
```

Commit `.yarn/releases/yarn-4.9.1.cjs` and the updated `.yarnrc.yml`. EAS picks up `yarnPath` from `.yarnrc.yml` and uses the checked-in binary directly, bypassing Corepack entirely.

This approach does NOT require `corepack: true` and works with local builds (`eas build --local`), which skip `eas-build-pre-install`.

### 3. EAS Build image / Node version with Corepack enabled by default

**No EAS Build image ships with Corepack enabled by default.** The SDK 52 images use Node.js 20.18.3 and Yarn 1.22.22. Corepack is available on Node 16.9+ but is not enabled.

Node versions per image (as of March 2026):
- SDK 52: Node 20.18.3, Yarn 1.22.22 (Corepack not enabled)
- SDK 53: Node 20.19.2, Yarn 1.22.22 (Corepack not enabled)
- SDK 54/55: Node 20.19.4, Yarn 1.22.22 (Corepack not enabled)

You must explicitly opt in via `corepack: true` in `eas.json`.

### 4. Known working examples (Expo SDK 52 + Yarn 4 + EAS Build)

Yes. Community reports from expo/eas-cli issues #2679 and #3132 confirm both Option A (`corepack: true`) and Option C (`yarnPath`) work as of 2025. The `eas-build-pre-install` + Corepack approach (Option B) has more fragility but works when placed correctly.

Known broken approach: `"yarn": "4.x"` field in `eas.json` builderEnvironment. This installs Yarn 4.x via `npm -g install yarn@4.x`, which installs the wrong package (yarn 1.x is on npm; Yarn 4 is published as `@yarnpkg/cli-dist`). Do not use this field for Yarn 4.

---

## Definitive Fix for This Specific Setup

Given: monorepo root has `"packageManager": "yarn@4.9.1"`, app is at `apps/admin`.

**Add `corepack: true` to all build profiles in `eas.json`:**

```json
{
  "build": {
    "preview": {
      "corepack": true,
      "env": {
        "YARN_ENABLE_IMMUTABLE_INSTALLS": "false"
      }
    },
    "production": {
      "corepack": true
    }
  }
}
```

**Optionally add `eas-build-pre-install` to `apps/admin/package.json` (not the root):**

```json
{
  "scripts": {
    "eas-build-pre-install": "corepack enable"
  }
}
```

With `corepack: true`, the hook is redundant but harmless.

**Also set `YARN_ENABLE_IMMUTABLE_INSTALLS: "false"`** in `env` if the lockfile will not be frozen at build time (EAS runs `--no-immutable` for Yarn Modern by default based on SDK version detection, but this env var overrides if needed).

---

## Why `eas-build-pre-install` in the Root Didn't Work

EAS resolves `eas-build-pre-install` from `ctx.getReactNativeProjectDirectory()` which is the app directory detected from `projectRootDirectory` in the job spec. The monorepo root `package.json` script is never read because the hook lookup is scoped to the app.

---

## Sources

- `packages/worker/src/build.ts` -- execution order (INSTALL_CUSTOM_TOOLS → androidBuilder)
- `packages/worker/src/runtimeEnvironment.ts` -- `corepack enable` implementation
- `packages/build-tools/src/common/setup.ts` -- PRE_INSTALL_HOOK order
- `packages/build-tools/src/utils/hooks.ts` -- npm-instead-of-yarn for pre-install
- `packages/build-tools/src/android/prepareJob.ts` -- `corepack: buildProfile.corepack`
- expo/eas-build PR #520 -- merged March 25, 2025 (corepack field added to schema)
- expo/eas-cli issue #2679 -- Yarn 4 monorepo + local build failures, `yarnPath` workaround
- expo/eas-cli issue #3132 -- Yarn v4 defaults to v1, community workarounds
- https://docs.expo.dev/more/create-expo/ -- official eas-build-pre-install guidance
- https://docs.expo.dev/build-reference/infrastructure/ -- Node/Yarn versions per image

## Open Questions

- Whether `corepack: true` propagates correctly to the `yarn` shim when used in combination with Yarn 4's own `.yarnrc.yml` `yarnPath` setting (no conflict reported in issues, but not explicitly tested together).
- Whether the hook placement issue (root vs app) is documented officially -- it is not, only derivable from source code.
