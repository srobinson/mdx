---
title: Transport Matters Channels Slice 4 Desktop Identity and Badge
type: sessions
tags: [backend, transport-matters, channels, desktop, api, web, badge]
summary: Added desktop channel identity, packaged channel specs, meta channel fields, and the preview badge.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented slice 4 of the Transport Matters channels build on `feat/channels`.

Commit: `d8f839a2603ed804124e436b05a7fee7938933ec`.

Key decisions:

- `desktop/scripts/copy-channel-specs.mjs` copies the package owned `api/src/transport_matters/channel-specs.json` into `desktop/dist/channel-specs.json` during `pnpm build`.
- `desktop/src/env.ts` reads the runtime JSON through `new URL("./channel-specs.json", import.meta.url)` and resolves stable or preview channel specs without generated TypeScript constants.
- `registerDesktopLifecycleFromEnv` resolves the channel spec and applies Electron identity before smoke, hosted route, direct backend, and `app.whenReady()` paths.
- Preview identity returns a shared icon path so both dock and BrowserWindow icon configuration flow from `applyChannelIdentity`.
- `/api/meta` now returns additive channel fields consumed by `www/src/api.ts` and `www/src/components/ChannelBadge.tsx`.
- The package smoke path now assembles the smoke app via `desktop/scripts/package-smoke-build.mjs`, because `electron-packager` returned before producing `dist/package-smoke` under the current Node 24 runtime. The script copies Electron.app with `/bin/cp -R` to preserve framework symlinks.

## API Contract

```typescript
interface ChannelBadgeResponse {
  text: string;
  color: "amber";
  hex: string;
}

interface MetaResponse {
  cwd: string;
  workspace_id: string;
  run_id: string | null;
  channel: string;
  channel_label: string;
  channel_badge: ChannelBadgeResponse | null;
  harnesses: HarnessDescriptorResponse[];
}

interface ChannelBadgeMeta {
  text: string;
  color: "amber";
  hex: string;
}

interface Meta {
  channel: string;
  channelLabel: string;
  channelBadge: ChannelBadgeMeta | null;
  cwd: string;
  harnesses: HarnessDescriptor[];
  workspaceId: string;
  runId?: string | null;
}
```

## Database Changes

No database schema changes.

## Security Considerations

- Channel selection remains allow list based through `channel-specs.json` and existing Python channel resolution.
- Desktop channel resolution validates JSON shape, non-empty strings, allowed dock icon values, and port ranges before use.
- The frontend badge is display only and does not accept user input.
- The meta fields are additive and do not expose credentials or filesystem secrets.

## Performance Notes

- Desktop channel spec JSON is small and read during process startup.
- `/api/meta` remains lightweight. It adds one cached channel spec resolution and no database access.
- `ChannelBadge` uses the existing infinitely cached `useMeta` query.

## Verification

Observed gates:

- `cd desktop && just package-smoke && just check`
  - Package smoke returned `status":"main-window-created"`.
  - Desktop typecheck passed.
  - Desktop Vitest reported `8 passed (8)` files and `33 passed (33)` tests.
- `cd www && just check && just test`
  - Biome format, lint, and TypeScript check passed. Biome reported two existing `!important` warnings in `src/session-canvas/components/pane-dock.css`.
  - Vitest reported `140 passed (140)` files and `989 passed (989)` tests.
- `cd api && just test src/transport_matters/api/v1/test_meta.py && just check`
  - Meta endpoint tests reported `8 passed`.
  - Ruff format and lint passed.
  - Mypy reported `Success: no issues found in 413 source files`.
- `git diff --cached --check` exited 0 before commit.
- `fmm validate` reported all `851` files indexed and up to date.

## Open Items

- Slice 5 still needs live stable and preview smoke plus channel promotion work.
- The current package smoke builder is a local deterministic replacement for the previous `electron-packager` CLI path under Node 24. If the packager dependency is retained long term, revisit once the upstream CLI produces `dist/package-smoke` reliably in this runtime.
