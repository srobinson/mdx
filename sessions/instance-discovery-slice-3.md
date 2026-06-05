---
title: Instance Discovery Slice 3
type: sessions
tags: [backend, transport-matters, desktop-runtime, vite, electron, instance-discovery]
summary: Electron and Vite dev consumers now use discovered or injected runtime ports instead of a fixed dev port constant.
status: active
source: backend-engineer
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Summary

Implemented slice 3 consumer cleanup on branch `feat/instance-discovery` in commit `b726630`.

Key decisions:

- Added `desktop/src/desktopRuntime.ts` as the TypeScript reader for the shared `transport-matters channel status <channel> --json` contract.
- `desktop/src/main.ts:resolveBackendStartupOptions` now prefers live discovered runtime ports while preserving explicit `TRANSPORT_MATTERS_PROXY_PORT` and `TRANSPORT_MATTERS_WEB_PORT` pins.
- `desktop/src/main.ts:registerDesktopLifecycleFromEnv` keeps Python supplied `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL` hosted behavior unchanged, and direct Electron startup can open a live discovered route without launching another backend.
- `desktop/src/window.ts:rendererUrlForPort` remains the single URL constructor for runtime ports. `DEFAULT_WEB_PORT` remains only the fallback path in `window.ts`.
- `www/vite.config.ts` now reads `TRANSPORT_MATTERS_DEV_API_BASE_URL` through `buildDevServerProxy`; no fixed dev proxy target remains there.
- `scripts/local-dev-mode.sh` sources channel ports from `api/src/transport_matters/channel-specs.json`, tries live `channel status --json` for the dev API base URL, and exports `TRANSPORT_MATTERS_DEV_API_BASE_URL` into Vite.

## API Contract

No HTTP API surface changed in this slice.

Frontend dev server contract:

```text
TRANSPORT_MATTERS_DEV_API_BASE_URL=http://127.0.0.1:<web-port> pnpm dev
```

Desktop internal runtime contract consumed by TypeScript:

```typescript
interface DesktopRuntimeStatus {
  channel: string;
  defaultRouteUrl: string | null;
  proxyPort: number | null;
  state: "absent" | "live" | "stale" | "unhealthy";
  webPort: number | null;
}
```

The contract is parsed from:

```bash
transport-matters channel status <channel> --json
```

## Database Changes

None.

## Security Considerations

- The desktop runtime reader invokes a fixed command and fixed argument shape, not a shell string.
- CLI status stderr is suppressed and failures fall back to channel defaults, so no diagnostic path prints environment values.
- The dev wrapper does not scan broad environment prefixes. It reads only `TRANSPORT_MATTERS_CHANNEL` and exports only `TRANSPORT_MATTERS_DEV_API_BASE_URL`.
- Vite accepts only HTTP or HTTPS API base URLs and normalizes to the origin.

## Performance Notes

- Desktop runtime discovery is synchronous and timeout bounded at 2 seconds.
- Normal Python launched desktop still uses the hosted route env and does not invoke the TypeScript status reader.
- Direct Electron startup reads runtime status after app readiness, avoiding import time process work in tests and startup module loading.

## Verification

Final gate run:

```bash
just check && just test
```

Observed results:

- `just check` passed.
- Desktop tests: `46 passed`.
- WWW tests: `1039 passed`.
- API tests: `1736 passed in 51.75s`.
- `bash -n scripts/local-dev-mode.sh` passed.
- Fixed dev path audit: `rg 'localhost:8788|--web-port 8788|target: "http://localhost:8788"|8788' www/vite.config.ts scripts/local-dev-mode.sh desktop/src/main.ts desktop/src/window.ts` reports only `desktop/src/window.ts:DEFAULT_WEB_PORT`.
- LOC check after formatting: touched code files remain under 700 lines.
- Final branch status before this record: clean on `feat/instance-discovery` at `b726630`.

Bus reply sent to `transport-matters:general:1:2.1` on topic `tm-build` with commit `b726630` and the passing gate summary.

## Open Items

- Manual `pnpm dev` in `www/` now needs `TRANSPORT_MATTERS_DEV_API_BASE_URL`; root `just dev` sets it through the dev wrapper.
- Future dynamic instance work can extend the same TypeScript status reader instead of reintroducing fixed client port constants.
