---
title: EAS Build in Monorepo - eas.json Location and Project Root Resolution
type: research
tags: [expo, eas, monorepo, ci, eas-build, eas.json]
summary: eas build resolves projectDir via pkg-dir from cwd, then looks for eas.json in that exact directory. There is no --config flag. The only correct approach is to place eas.json inside each app directory and run from there.
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

`eas build` determines the project directory by running `pkg-dir(process.cwd())`, which walks up from the current working directory to find the nearest `package.json`. It then looks for `eas.json` at exactly that directory using `path.join(projectDir, 'eas.json')`. There is no parent-directory traversal for `eas.json`, no `--config` flag, no `EAS_PROJECT_ROOT` override that affects eas.json lookup, and no `--root` or `--project-dir` flag.

**Canonical monorepo approach per official Expo docs:**

> "All files related to EAS Build, such as eas.json and credentials.json, should be in the root of the app directory."
> "Run all EAS CLI commands from the root of the app directory."

Each app in the monorepo must have its own `eas.json`.

## Details

### How project root is resolved (source: eas-cli source code)

File: `packages/eas-cli/src/commandUtils/context/contextUtils/findProjectDirAndVerifyProjectSetupAsync.ts`

```typescript
export async function findProjectRootAsync({ cwd }: { cwd?: string } = {}): Promise<string> {
  const projectRootDir = await pkgDir(cwd);  // cwd defaults to process.cwd()
  // ...
  return projectRootDir;
}
```

`ProjectDirContextField` calls `findProjectDirAndVerifyProjectSetupAsync()` with no arguments, so `cwd` is always `process.cwd()`.

### How eas.json is located (source: `packages/eas-json/src/accessor.ts`)

```typescript
public static formatEasJsonPath(projectDir: string): string {
  return path.join(projectDir, 'eas.json');
}
```

No traversal. No fallback to parent directories. If `eas.json` is not at `projectDir/eas.json`, you get `MissingEasJsonError`.

### Available flags (confirmed absent)

- `--config`: NOT valid
- `--root`: does not exist
- `--project-dir`: does not exist
- `--app-dir`: does not exist
- `EAS_PROJECT_ROOT`: only affects VCS root for file upload (noVcs.ts), NOT eas.json resolution

### What `EAS_PROJECT_ROOT` actually does

`EAS_PROJECT_ROOT` is used in `noVcs.ts` to set the root path for the VCS shallow copy (what files get uploaded). It does NOT affect project directory resolution or eas.json lookup. It is only relevant when using `EAS_NO_VCS=1`.

### pkg-dir traversal behavior

When you `cd apps/admin && eas build`, pkg-dir walks up from `apps/admin/`, finds `apps/admin/package.json`, and stops there. It does NOT continue up to the repo root. This is the desired behavior: `projectDir = apps/admin/`, so EAS looks for `apps/admin/eas.json`.

## Correct CI Setup

**Option 1 (canonical): eas.json per app directory**

Place a complete `eas.json` inside each app:
- `apps/admin/eas.json` - contains `preview-admin` profile
- `apps/student/eas.json` - contains `preview-student` profile

CI workflow:
```yaml
- name: Build admin
  working-directory: apps/admin
  run: eas build --profile preview-admin --platform ios --non-interactive
```

**Option 2: Symlink (not recommended for CI)**

Symlink `apps/admin/eas.json -> ../../eas.json`. This works locally but symlinks behave inconsistently across CI file upload steps and OS environments.

**Option 3: Copy eas.json during CI**

Before the build step, copy the root `eas.json` into the app directory:
```yaml
- run: cp eas.json apps/admin/eas.json
- working-directory: apps/admin
  run: eas build --profile preview-admin --non-interactive
```

This works but creates drift risk if eas.json is modified in one place and not the other.

## Recommendation

**Option 1 is canonical and correct.** Each app directory should own its `eas.json`. Profiles that are app-specific (e.g., `preview-admin`) belong in `apps/admin/eas.json`. Profiles can share build settings via JSON object references within the file if needed. The root-level `eas.json` should either be deleted or left only as a reference artifact.

## Sources

- Official Expo docs: https://docs.expo.dev/build-reference/build-with-monorepos/
- eas-cli source - project root resolution: https://github.com/expo/eas-cli/blob/main/packages/eas-cli/src/commandUtils/context/contextUtils/findProjectDirAndVerifyProjectSetupAsync.ts
- eas-cli source - eas.json path: https://github.com/expo/eas-cli/blob/main/packages/eas-json/src/accessor.ts
- eas-cli source - ProjectDirContextField: https://github.com/expo/eas-cli/blob/main/packages/eas-cli/src/commandUtils/context/ProjectDirContextField.ts

## Open Questions

- Whether `eas.json` profiles can be shared via a base file using YAML-style anchors or JSON extends (JSON does not support this natively; would require tooling).
- Whether EAS Workflows (the newer CI product) has a mechanism to specify eas.json path differently than the CLI.
