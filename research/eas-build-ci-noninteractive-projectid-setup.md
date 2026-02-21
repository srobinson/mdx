---
title: EAS Build CI Non-Interactive Setup - Project ID and eas.json Requirements
type: research
tags: [expo, eas, ci, github-actions, monorepo, react-native]
summary: extra.eas.projectId in app.json is the single field that bypasses the "EAS project not configured" error in non-interactive CI builds. Set appVersionSource to "remote" to silence the cli warning.
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

The "EAS project not configured" error in non-interactive mode is thrown from a single code path in `fetchOrCreateProjectIDForWriteToConfigWithConfirmationAsync.ts`:

```ts
if (options.nonInteractive) {
  throw new Error(
    `Must configure EAS project by running 'eas init' before this command can be run in non-interactive mode.`
  );
}
```

This branch is reached **only when `exp.extra?.eas?.projectId` is absent** from app.json. Setting that field statically in app.json, before CI runs, is the complete fix.

## What `eas init` Does

Source: `packages/eas-cli/src/commands/project/init.ts`

1. Looks up `extra.eas.projectId` in app.json.
2. If absent, queries the EAS API for an existing project matching `@{owner}/{slug}`.
3. If found in non-interactive + force mode, writes the ID back to app.json.
4. If not found in non-interactive mode (without --force), throws the error above.
5. Also writes/validates `owner` and `slug` fields in app.json.

The only file modified is **app.json** (or app.config.js). The only field written is:
```json
{ "expo": { "extra": { "eas": { "projectId": "<uuid>" } } } }
```

## Required Fields in app.json

| Field | Required | Notes |
|---|---|---|
| `expo.extra.eas.projectId` | Yes | UUID from expo.dev dashboard. This is the only field that gates non-interactive mode. |
| `expo.owner` | Required for SDK < 53 when using robot tokens | Account name (e.g. `"stuartjohnson"`) |
| `expo.slug` | Yes | Must match the slug registered on expo.dev |

### How to get the project ID

1. Go to [expo.dev](https://expo.dev) and log in.
2. Navigate to your project (or create one via "New Project").
3. The project ID is the UUID in the URL: `https://expo.dev/accounts/{owner}/projects/{slug}` — or visible on the project overview page.
4. Alternatively: run `eas init` once locally (interactive), which writes the ID to app.json, then commit it.

## Exact app.json Changes Required

Add to each app's `app.json`:

```json
{
  "expo": {
    "owner": "your-expo-account-name",
    "slug": "your-app-slug",
    "extra": {
      "eas": {
        "projectId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      }
    }
  }
}
```

The `owner` field is required when using a robot/CI token (EAS_TOKEN) for SDK < 53 because the CLI cannot infer which account the robot token belongs to from the app config alone.

## Exact eas.json Changes Required

Add `cli.appVersionSource` to silence the warning:

```json
{
  "cli": {
    "version": ">= 12.0.0",
    "appVersionSource": "remote"
  },
  "build": {
    "preview-admin": {
      "distribution": "internal",
      "channel": "preview",
      "android": { "buildType": "apk" }
    }
  }
}
```

### `appVersionSource` values

- `"remote"` — EAS servers own the `versionCode`/`buildNumber`. Enables `autoIncrement: true`. Recommended for CI because no commits are needed to bump versions.
- `"local"` — Your app.json/native files own the version numbers. Requires committing bumps.

For a CI pipeline that just needs to build without auto-incrementing, either value works. `"remote"` is the recommended default as of EAS CLI 12.

## Monorepo: Does Each App Need Its Own EAS Project?

**Yes.** Each app (`apps/admin`, `apps/student`) must be a separate EAS project with its own:
- `projectId` (different UUID for each)
- `slug` (e.g. `echoecho-admin`, `echoecho-student`)
- `eas.json` (scoped to that app's build profiles)

The `eas build` command resolves `projectId` from the `app.json` in the current working directory. Since CI runs from `working-directory: apps/admin`, the admin app.json is read. The student app has its own entirely separate project on expo.dev.

## Working CI Configuration (GitHub Actions)

```yaml
- name: Build admin app
  working-directory: apps/admin
  env:
    EAS_TOKEN: ${{ secrets.EAS_TOKEN }}
  run: npx eas-cli build --profile preview-admin --platform all --non-interactive --no-wait
```

No `eas init` step needed in CI once `extra.eas.projectId` is committed to app.json.

## Sources

- `packages/eas-cli/src/commands/project/init.ts` — full init command source
- `packages/eas-cli/src/commandUtils/context/contextUtils/getProjectIdAsync.ts` — exact error throw location
- `packages/eas-cli/src/project/fetchOrCreateProjectIDForWriteToConfigWithConfirmationAsync.ts` — non-interactive guard
- `packages/eas-json/src/types.ts` — AppVersionSource enum (`local | remote`)
- `packages/eas-json/src/schema.ts` — eas.json Joi schema
- https://docs.expo.dev/build/building-on-ci/
- https://docs.expo.dev/build-reference/app-versions/

## Open Questions

- SDK version of this project: if >= 53, `owner` field may not be required even with robot tokens. Verify by checking the semver guard in `getProjectIdAsync.ts`.
