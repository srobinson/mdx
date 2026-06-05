---
title: Transport Matters www/ Separation — Architecture Review (Composer, v3)
type: research
tags: [transport-matters, www, separation, monorepo, architecture-review, canvas, inspector, shell, host]
summary: Adversarial review of tm-sep-proposal.md v3 — v2 blockers largely closed via @tm/host, lib map, stream port, P3 CI checklist. New blocker: keybinding split contradicts live inspector→engine imports (useFullscreen). gestureModifier and route.ts split incomplete.
status: active
source: composer
confidence: high
created: 2026-07-01
updated: 2026-07-02
reviewed_proposal: ~/.mdx/projects/tm-sep-proposal.md
supersedes: v2 review (same file)
---

# Adversarial architecture review: TM www/ separation proposal (v3)

Reviewed `tm-sep-proposal.md` v3 (changelog §0), v2 Composer review, and re-verified live code: `exchangeStreamEvents.ts`, `keybindings/{engine,registry,platform,gestureModifier}.ts`, `hooks/useFullscreen.ts`, `stores/keymapStore.ts`, `session-canvas/route.ts`, `ChannelBadge.tsx`, `main.tsx`, `browserIdentity.test.ts`, `desktop/package.json`.

**Verdict shift:** v3 is the first version I would sign off for execution **after one design fix** (keybinding/engine split). It closes v2 blockers (`lib/` map, stream port, P3 CI/scripts, `@tm/host`, reviewer corrections on route/icons). The topology is right. What remains is one internal contradiction in the keybindings plan and a few thin seams, not a wrong package model.

---

## 1. Verdict: workspace vs full monorepo

**Agree. Correctly closed, correctly hardened.**

Repo-root workspace + `desktop` as member + root `onlyBuiltDependencies: [electron]` addresses v2's CI lockfile gap explicitly. Keeping `api/` on `uv`/`just` and skipping Turborepo/Nx is still right.

**Nit:** P3 must also update `desktop/package.json` `clean` (today `rimraf ... pnpm-lock.yaml`) and any `pnpm/action-setup` `package_json_file` in `release.yml`, not only `ci.yml`. v3 mentions `release.yml`; ensure desktop job install path is root too.

---

## 2. Stress-test: `core` / `host` / `inspector` / `canvas` / `shell`

### Does the split prevent ExchangeDetail-style leaks?

**Yes, if P5 enforcement lands as written.**

v3 keeps the right invariant: `inspector ⊥ canvas`, reachable only from own entry/tests + `@tm/shell`. `exports` exposing `"."` only is the correct minimal guard. Downgrading `dependency-cruiser` to optional is acceptable **only if** the Vitest import-graph test:

- resolves imports by **package name** (`@tm/inspector`, not filesystem paths),
- fails on deep imports and relative cross-package `../../packages/inspector/...` during migration,
- runs in CI `pnpm test`, not a manual gate.

Optional cruiser can come later; do not ship P5 without the graph test enforcing the peer ban.

### Is `@tm/core`'s public API right?

**Much improved. `lib/` table is evidence-based.**

Verified alignments:

- `exchangeStreamEvents.ts`: five `useUIStore.getState()` sites — stream port in P4 is the right seam.
- `formatting.ts`, `agentPalette.ts`: cross-product importers match the table.
- `persistence` split (helper in core, keys per product): fixes v2's registry-in-core mistake.
- Canvas Tailwind-free claim still holds (ExchangeDetail breach excepted).

**`@tm/host` is the right extraction.** v2 putting chrome in core violated core's no-CSS contract. `mountWindowChrome()` + Tailwind-free `ChannelBadge`/`WindowDragRegion` consumed by both production `main.tsx` files is clean. `ChannelBadge` → `useMeta` implies **`@tm/host` depends on `@tm/core`**; state that in §4 deps (minor doc gap).

### Keybindings plan — internal contradiction (Blocker)

v3 §4 says:

- **Core IN:** keybinding primitive (`platform`, `format`, registry/command **types**)
- **Canvas OUT:** `engine`, `gestures`, `gestureModifier`, `registry`
- **Inspector:** `keymapStore`, `useFullscreen` bound to core primitive, **never** the canvas engine

**Live code refutes the inspector line.** `hooks/useFullscreen.ts` imports `useFullscreenKeybindings` from `keybindings/engine.ts`. `ExchangeDetail` uses `useFullscreen`. Inspector fullscreen escape is wired through `registry.ts` command `ui.exitFullscreen` inside the same `engine.ts` that powers canvas launcher/dock.

Also:

| Symbol | v3 home | Actual importers | Fix |
|---|---|---|---|
| `gestureModifier.ts` | canvas engine | **inspector** `keymapStore` + canvas launcher | **Core IN** (shared types/constants), not canvas-only |
| `platform.ts` | core primitive | imports `desktopHost` | Core → host dep, **or** `platform` lives in `@tm/host` |
| `registry.ts` `COMMANDS` | split unclear | launcher+dock+fullscreen in one array | Split command lists: canvas registry vs inspector registry; shared `Command` **types** in core |
| `engine.ts` | canvas | inspector `useFullscreenKeybindings` | Split engine: inspector owns `useFullscreenKeybindings` (+ fullscreen slice of registry); canvas owns `KeybindingEngineProvider` + launcher/dock hooks |

Until this is designed, P5's "inspector never imports canvas keybinding engine" will fail the import-graph gate or force a smuggled dependency.

### `route.ts` split — mostly right, incomplete list

v3 correction (Codex): `parseCanvasLaunchContext`/`defaultCanvasId` → canvas, `selectRootRoute` → shell. **Verified.**

Also canvas-only and should move with the same file split: `CanvasLaunchContext`, `worktreeSwitchUrl`, `isStressCanvas`. `RootRoute` type stays with shell (`selectRootRoute`). Not a blocker if P5 moves the whole `route.ts` body except `selectRootRoute`, but the plan should say so to avoid half-split churn.

### Peer graph + shell + host

**Correct and production-shaped.**

```
core ← host ← {inspector, canvas}
core ← inspector
core ← canvas
{core, host, inspector, canvas} ← shell (dev only)
```

P1 factoring `mountWindowChrome()` before scaffold is smart: exercises neutral chrome early, reduces P3 move surprise. P6 each product calls `@tm/host` — good.

**Shell zero-Tailwind claim:** depends on P1 neutralizing `rootShell` Suspense fallback (`min-h-screen bg-canvas text-txt` today). Plan says so; gate it.

### Separate tokens + fork viewer?

**Unchanged and still correct.** Phase 2 render contract + tab-mapping test + snapshot is the right bar. Locked separate-token policy is coherent.

---

## 3. Findings by severity

### Blocker

**B1 — Keybinding/engine split contradicts inspector imports (§4, §5 P5)**

`useFullscreen` → `engine.useFullscreenKeybindings` today. v3 cannot put `engine.ts` entirely in canvas while claiming inspector never touches canvas keybinding code. Design the split before P5:

- Core: `platform` (with host dep), `format`, `Command` types, `gestureModifier` constants
- Inspector: `useFullscreenKeybindings`, fullscreen `COMMANDS` slice, `useRouteHotkeys`, `keymapStore`
- Canvas: `KeybindingEngineProvider`, launcher/dock hooks, `gestures`, gesture surface attrs

**Gate:** import graph shows zero `inspector → canvas` and zero `canvas → inspector`; inspector does not import canvas `engine.ts`.

### Major

**M1 — `lib/domFocus.ts` unmapped (§4 lib table)**

Used by `keybindings/engine`, `keybindings/gestures`, `hooks/useRouteHotkeys` (inspector). Neutral DOM helper → **core IN** or inspector if only inspector after engine split. Omitting it guarantees a P4/P5 stall.

**M2 — `@tm/core/keybindings/platform` ↔ `@tm/host` dependency (§4)**

`platform.ts` imports `DESKTOP_BRIDGE_KEY` from `desktopHost`. If platform lands in core, core depends on host. That is fine (host is neutral), but it must be explicit in package.json deps and the import graph rules. Alternative: platform in host, format/types in core.

**M3 — P3 remains the highest mechanical risk (§5 P3, §6)**

v3 checklist is comprehensive (workspace-root `outDir`, every CI job, scripts, desktop membership). **Hold the line on fresh-clone gate.** One missed `working-directory: www` in a secondary job breaks main.

**M4 — P6 two-dir static test (§5 P6)**

Correctly upgraded from v2. Adversarial minimum unchanged: real built `www/` + `canvas/` directories, `/canvas/assets/*` resolves under canvas mount, `/assets/*` on inspector mount, cross-mount 404 regression.

**M5 — Enforcement without dependency-cruiser (§4)**

Acceptable if Vitest graph is strict. **Failure mode:** a dev adds `"@tm/inspector": "workspace:*"` to canvas `package.json` during debugging and the graph test does not run on that config. Add a package.json dep lint: canvas and inspector `dependencies` must not list each other.

### Minor

**m1 — `browserIdentity.ts` dropped but `browserIdentity.test.ts` exists**

Rename/migrate the slug-guard test in P3 or it references wrong paths after scaffold.

**m2 — `queryClient` singleton (§4)**

Shared instance across P6 entries is fine for same-origin desktop+web. Document that inspector and canvas SPAs on different mounts still share one module singleton when both load (they will not simultaneously in prod; OK).

**m3 — `useRouteHotkeys` (inspector `app.tsx`)**

Not named in §4. Belongs inspector with `domFocus`. Trivial but add to move-map.

**m4 — Drift/onboarding (§1)**

Honest call: canvas-local, no modules yet. Prevents premature core promotion. Good.

**m5 — v3 self-corrections validated**

- `TransportMattersIcon`/`icons` → inspector only (grep confirms)
- `route.ts` launch fns → canvas only (grep confirms)
- Codex keybindings rationale wrong; real split driver is inspector `keymapStore` + `useFullscreen` (confirmed)

---

## 4. What v3 still misses / structure opinion

### Closed since v2

- `@tm/host` (fixes chrome-in-core mistake)
- Complete `lib/` disposition (minus `domFocus`)
- `StreamSideEffects` port + P4 zero-`stores/` gate
- P3 CI/scripts/desktop checklist
- P6 two-bundle test story
- `Toggle`/icons/route corrections
- P3/P4 separate commits
- Shell peer composition (no `inspector → canvas`)

### Still thin

1. **Keybinding split spec** (B1) — the only remaining design doc gap worth blocking on.
2. **`route.ts` full canvas export list** — include `worktreeSwitchUrl`, `isStressCanvas`, `CanvasLaunchContext`.
3. **`@tm/host` package.json deps** — `{ "@tm/core": "workspace:*" }` at minimum.
4. **Shell P6 dev Vite** — one sentence is not a spec; need: shell `vite.config` aliases `@tm/inspector` and `@tm/canvas` lazy entrypoints, `server.fs.allow` to workspace root. Acceptable as "write before P6" if it is actually written before P6.

### Structure opinion

**Do not redesign.** v3 package model is the right end state:

| Package | Role |
|---|---|
| `@tm/core` | Data + transport + neutral utils |
| `@tm/host` | Tailwind-free chrome + desktop bridge |
| `@tm/inspector` | Web reactive product |
| `@tm/canvas` | Desktop proactive product |
| `@tm/shell` | Dev composer only |

Fix B1 in §4 before starting P4/P5 keybinding moves. Everything else is execution discipline.

---

## 5. Bottom line

| Question | v2 answer | v3 answer |
|---|---|---|
| Workspace | Agree, closed | **Agree; hardened** |
| Package split clean? | Yes with stream + lib fixes | **Yes after keybinding split fix** |
| Prevents ExchangeDetail leak? | Yes with strict exports | **Yes** |
| `@tm/host` | (missing) | **Correct addition** |
| Execute? | Yes with B1 stream port | **Yes with B1 keybinding port** |

v3 incorporated the prior review seriously — the changelog even catches wrong peer rationales. That is rare and good.

**Approve v3 for execution with one precondition:** write the keybinding/engine/registry split (B1) into §4 before Phase 5, including `gestureModifier` → core and an explicit `core → host` edge for `platform`. Then run P1→P6 as written.