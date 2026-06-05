---
title: TM no-DB startup — frontend feature gating + onboarding seam (Slice C)
type: research
tags: [transport-matters, www, nodb, gating, onboarding]
summary: Canvas run panes + xterm work without Postgres; transcript/session reads need a gate. RootShell is the onboarding seam; no DB status is surfaced to www today.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# Q1 — Blast surface (feature → endpoint → no-DB behavior → gate?)

All wire calls route through `www/src/api.ts`. Two clean classes:

**DB-backed (Postgres session store) — break/empty, NEED gate:**
- Legacy browser shell `/` (`App`/`BrowserAppShell`, app.tsx). Drives the live transcript reader via `useExchanges`→`fetchExchanges` (`GET /v1/runs/{id}/exchanges`) and `useExchangeStream` (`EventSource /v1/runs/{id}/stream`). No DB → empty list, SSE `onerror`, `connected=false` forever.
- Per-exchange detail + token/inspect viewers: `fetchExchange`, `fetchTurnContent` (`useTurnContent`), `fetchPipelineTokens` (`/v1/runs/{id}/exchanges/{id}/...`). No DB → fetch errors.
- Canvas resource/transcript viewers (`www/src/session-canvas/viewers/resource/*`) consuming the same per-exchange reads.

**Not DB (process-resident `RunManager` / proxy / config) — WORK without DB:**
- Canvas run panes spawn/list/stop: `createCapturedRun` (POST /runs), `listRuns` (GET /runs), `terminateRun` (DELETE /runs/{id}) via `capturedRunStore`/`canvasStore`.
- xterm terminal: `WS /runs/{id}/terminal`.
- `fetchRuntimeTemplates`, `fetchCapabilities` (config), and proxy/run-dir state: breakpoint (`armBreakpoint`/`fetchBreakpointStatus`), overrides (`fetchOverrides`/`patchOverrides`), paused-flow (`releaseFlow`/`dropFlow`). These never touch the session store.

**Verify with backend slice:** `fetchMeta` (`/api/meta`) returns launch facts (cwd, harnesses, workspaceId, runId) — likely tier-1 run-dir, not Postgres; confirm it survives no-DB.

→ ~3 feature clusters need a "DB connection required" gate (live reader, exchange detail/token viewers, canvas resource viewers); the canvas surface itself (panes + terminal) stays usable.

# Q2 — Onboarding seam

The router entry is `RootShell` (`www/src/rootShell.tsx`): `selectRootRoute(window.location.pathname)` (`session-canvas/route.ts`) forks legacy/`canvas`/`canvas-lab`. There is **no client router** — full-page nav (`navigateToRoute`). RootShell is the single seam where every surface mounts, before any DB-backed fetch, so a "no DB detected → choose local/docker/hosted Postgres" screen belongs here (gate inside RootShell ahead of the route fork; `main.tsx` only does createRoot).

**The client learns DB status nowhere today.** No www call exposes it: `Meta` and `CapabilitiesResponse` have no db field, and `/health` is polled only by the desktop wrapper (`desktop/src/backendHealth.ts`), not www. A new bootstrap signal is required — extend `/api/meta` or `/api/capabilities`, or add `/api/health/db`, consumed once in RootShell.

**No reusable empty-state component** (no `EmptyState`/error-boundary export). Closest patterns: RootShell's `<Suspense>` fallback and the `connected` SSE badge in `RouteLayout`. The onboarding gate is net-new.
