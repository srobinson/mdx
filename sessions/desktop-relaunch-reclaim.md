---
title: Desktop Relaunch Reclaim
type: sessions
tags: [backend, desktop, ports, relaunch]
summary: Unified desktop relaunch reclaim across foreground, detached, and direct Electron paths.
status: active
source: backend-engineer
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

## Summary

Implemented the final desktop relaunch reclaim path for Transport Matters. Foreground launches, detached launches, and direct Electron launches now share the same liveness gate before starting a new backend. Live runtimes attach, stale records are reclaimed, wedged Transport Matters runtimes auto reclaim after the existing debounce, and foreign non Transport Matters listeners are refused.

Key decisions:

- Extracted shared desktop launch configuration helpers to keep `desktop_cmd.py` below the 700 line threshold.
- Extracted hosted liveness polling from Electron `main.ts` to keep the main process entrypoint focused and below the threshold.
- Added a hidden `_desktop-reclaim` CLI seam so the direct Electron path can invoke the same Python reclaim mechanics instead of duplicating port ownership logic in TypeScript.
- Preserved the existing liveness debounce before classifying timeout states as wedged.

## API Contract

No public API contract changed.

Internal launch surfaces changed:

```typescript
interface DesktopRuntimeReclaimCommand {
  cliPath: string;
  cwd: string;
  env: NodeJS.ProcessEnv;
}

type DesktopRuntimeReclaimer = (
  channel: DesktopRuntimeChannelSpec,
  env: NodeJS.ProcessEnv,
  cwd: string,
) => void;
```

CLI behavior changed:

- `transport-matters desktop --force-restart` now works for foreground launches.
- Hidden command `_desktop-reclaim --work-dir <path> --channel <name>` reclaims stale or wedged Transport Matters runtime records for Electron managed relaunches.

## Database Changes

No schema or migration changes.

## Security Considerations

- Foreign non Transport Matters listeners remain protected. The reclaim path refuses them instead of killing unknown processes.
- Reclaim decisions still rely on recorded runtime identity plus liveness probes.
- Unhealthy mixed probe results still refuse recovery because they can indicate channel mismatch or an unexpected process.
- The Electron path delegates ownership decisions to the Python runtime record layer instead of reimplementing process kill logic.

## Performance Notes

- Live runtime attach avoids spawning a duplicate backend.
- Stale and wedged runtime cleanup happens before bind, reducing relaunch failure loops on fixed channel ports.
- The direct Electron reclaim command has a bounded 12 second timeout.
- Existing debounce remains in place so slow but healthy startup is not killed prematurely.

## Verification

- `cd api && uv run python -m pytest src/transport_matters/cli/test_desktop_idempotent.py src/transport_matters/cli/test_desktop_runtime.py src/transport_matters/test_desktop_runtime_imports.py`
- `cd desktop && pnpm vitest run src/desktopRuntime.test.ts src/main.reclaim.test.ts src/main.test.ts`
- `cd api && just check`
- `cd desktop && just check`
- `cd api && uv run python -m pytest src/transport_matters/test_launch_seam_imports.py src/transport_matters/cli/test_desktop_idempotent.py`
- `just check`
- `just test`
- `cd api && just ci`

## Open Items

None known.
