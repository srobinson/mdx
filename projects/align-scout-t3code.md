---
title: t3code Upstream Scout — Whole-App Alignment Analysis for transport-matters
type: research
tags: [t3code, transport-matters, electron, effect-ts, monorepo, backend-lifecycle, alignment, scout]
summary: t3code is an Effect-ts pnpm monorepo whose apps/desktop Electron skeleton tears down its backend via Effect Scope finalizers (SIGTERM + 2s grace, force-kill) driven by a DesktopShutdown coordinator; the whole codebase is orphan-aware by design.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-04
updated: 2026-07-04
---

# t3code Upstream Scout — Alignment Analysis for transport-matters

**Scope:** Read-only reconnaissance of t3code current `main` (HEAD `cabc93bad`), for a fork (`transport-matters`) that copied and evolved t3code's `apps/desktop` Electron skeleton. Goal: what to adopt from upstream. Structure/hygiene lens applied.

**Tooling note:** repo was not fmm-indexed on arrival (`.fmm.db` absent). I ran `fmm generate` (1938 files, 4.9s) then used fmm for structural orientation. Citations are **file + symbol**, no line numbers.

---

## 0. Headline Answer (backend teardown — the active fork bug)

t3code's desktop **does not orphan its backend**, and does so by construction, not by ad-hoc signal wiring:

- Each backend run is spawned inside a per-run **Effect `Scope`** using `effect/unstable/process` `ChildProcess.make` with `killSignal: "SIGTERM"` and `forceKillAfter: DEFAULT_BACKEND_TERMINATE_GRACE` (2s). See `DesktopBackendManager.runBackendProcess`. Closing the scope sends SIGTERM, waits the grace, then SIGKILLs — platform-native, no manual `.kill()`.
- `DesktopBackendManager.makeBackendInstance` registers `Effect.addFinalizer(() => stop())`; `stop` → `closeRun` → `Scope.close(run.scope)`. So the child is bound to a scope that is guaranteed to close.
- `DesktopBackendPool.layer` **anchors every instance's scope to the pool's layer scope** (`const layerScope = yield* Scope.Scope`). Its header comment states the exact failure mode the fork is hitting: *"Without this, instance scopes are orphaned … on app shutdown the WSL backend child process gets hard-killed by the OS instead of receiving the graceful SIGTERM + grace period."*
- `DesktopApp.program` (the `scopedProgram`) blocks on `shutdown.awaitRequest`, and registers a **top-level finalizer that explicitly iterates `pool.list` and `instance.stop()`s every backend concurrently** before quit — comment: *"The electronApp.quit() path can race ahead of the layer-scope cascade, so leaving the WSL instance for its parent scope finalizer means it gets hard-killed by the OS instead of receiving SIGTERM + grace."*
- Quit/signals funnel through a single coordinator, `DesktopShutdown` (a `Deferred`-based request/awaitComplete service). `DesktopLifecycle.register` wires `before-quit`, `window-all-closed`, and (non-Windows) `SIGINT`/`SIGTERM` → `shutdown.request` + `shutdown.awaitComplete` → `electronApp.quit`.

**One-phrase teardown:** *per-run Effect Scope finalizer (SIGTERM + 2s grace, then force-kill), pool anchored to layer scope, driven by a DesktopShutdown Deferred that a top-level app finalizer stops every pool instance through before electronApp.quit.*

The adoptable lesson for transport-matters: **never let the child process outlive an Effect scope, and never let `electronApp.quit()` win the race against backend teardown.** t3code solves both explicitly.

---

## 1. Monorepo Map

pnpm@10.24.0 workspace; build orchestrated by **`vite-plus` (`vp`)**, not turbo/nx. `pnpm-workspace.yaml` members: `apps/*`, `infra/*`, `oxlint-plugin-t3code`, `packages/*`, `scripts`. Notable: `supportedArchitectures` installs both Windows + Linux (glibc) native binaries into one `node_modules` so the WSL Linux backend and Windows desktop share deps.

### apps/*
| App | Package | Role (why it matters for the fork) |
|-----|---------|-----|
| `apps/desktop` | `@t3tools/desktop` | **Direct inheritance.** Electron main-process shell (114 src files, ~30.5k LOC). Effect-based. |
| `apps/server` | `t3` | Node WebSocket backend the desktop spawns; wraps Codex app-server (JSON-RPC over stdio), serves the web app, manages provider sessions. This is *the backend* the desktop lifecycle manages. |
| `apps/web` | `@t3tools/web` | React/Vite renderer UI (session UX, event rendering, client state). |
| `apps/mobile` | `@t3tools/mobile` | Expo/React Native client (shares `packages/client-runtime`). |
| `apps/marketing` | `@t3tools/marketing` | Marketing site (separate `vp`/vite build). |

### packages/* (109k LOC total)
| Package | Role |
|---------|------|
| `packages/contracts` (`@t3tools/contracts`) | **Schema-only** effect/Schema contracts: provider events, WS protocol, model/session types, and the **`DesktopBridge`** IPC contract type. AGENTS.md rule: keep runtime-logic-free. |
| `packages/shared` (`@t3tools/shared`) | Runtime utilities for server + client. **Explicit subpath exports, no barrel index** (`@t3tools/shared/git`, `/Net`, `/httpReadiness`, `/hostProcess`, `/shell`). |
| `packages/client-runtime` (`@t3tools/client-runtime`) | Shared client code across web + mobile (125 files, largest package by file count). |
| `packages/effect-codex-app-server` | Effect binding for Codex app-server JSON-RPC (42k LOC, mostly generated — see `scripts/generate.ts`). |
| `packages/effect-acp` | Effect binding for the Agent Client Protocol (ACP) over stdio. |
| `packages/ssh` (`@t3tools/ssh`) | Remote/SSH runner + tunnel (`command.ts`, `tunnel.ts`) — desktop uses it for remote backend spawns. |
| `packages/tailscale` (`@t3tools/tailscale`) | Tailscale integration for network-accessible server exposure. |

### infra / scripts / tooling
- `infra/relay` (`t3code-relay`): relay infrastructure (Alchemy-effect based per AGENTS.md).
- `scripts/`: a **full Effect CLI toolchain**, each script paired with a `.test.ts`: `dev-runner.ts` (dev orchestration, PR #3662), `build-desktop-artifact.ts` (electron-builder driver, all `dist:desktop:*` targets), `merge-update-manifests.ts`, `resolve-nightly-release.ts`, `sync-reference-repos.ts`, `mock-update-server.ts`, `notify-discord-release.ts`. Shared helpers in `scripts/lib` (`public-config.ts`, `build-target-arch.ts`, `electron-launcher.mjs`).
- `oxlint-plugin-t3code`: **custom oxlint plugin** enforcing house Effect conventions (see §4).
- `vite.config.ts` (root) + per-app `vite.config.ts` using `vite-plus` `defineConfig`; `tsconfig.base.json` sets the strict TS baseline.

---

## 2. apps/desktop Deep Dive (highest priority)

`apps/desktop/src` = 12 subsystems. Entire desktop is an **Effect application**: `main.ts` builds a large `Layer` graph and runs `DesktopApp.program` via `@effect/platform-node` `NodeRuntime.runMain`. Services use `Context.Service`; errors are `Schema.TaggedErrorClass`; everything is span-instrumented.

### 2a. Electron main / window / preload / IPC surface

- **Main entry:** `apps/desktop/src/main.ts` — pure Layer composition (`electronLayer`, `desktopFoundationLayer`, `desktopBackendLayer`, `desktopWslBackendLayer`, `desktopRuntimeLayer`) then `DesktopApp.program.pipe(Effect.provide(desktopRuntimeLayer), NodeRuntime.runMain)`. Clean, declarative wiring; no imperative bootstrap in main.
- **Electron adapters** (`src/electron/`, 9 files, thin wrappers around Electron APIs as Effect services): `ElectronApp` (app lifecycle/metadata/quit), `ElectronWindow`, `ElectronMenu`, `ElectronProtocol` (custom scheme registration for renderer + backend origins), `ElectronDialog`, `ElectronUpdater`, `ElectronSafeStorage`, `ElectronTheme`, `ElectronShell`. Each `↓`-depended-on by many app modules — clean boundary between "Electron the platform" and "desktop the app."
- **Window management:** `src/window/DesktopWindow.ts` (`handleBackendReady`, `showConnectingSplash`, `syncAppearance`, `activate`) — window creation is gated on backend readiness, and a "Connecting to WSL" splash shows in wsl-only mode.
- **Preload:** `src/preload.ts` uses `contextBridge.exposeInMainWorld("desktopBridge", …)`, typed against `@t3tools/contracts` `DesktopBridge`, dispatching to channel constants from `src/ipc/channels.ts`. Also composes `@clerk/electron/preload` `exposeClerkBridge`. Preload is bundled as a separate `cjs` pack target with `alwaysBundle` for `@clerk/electron` (sandboxed preloads can't resolve ASAR package imports).
- **IPC surface** (`src/ipc/`, 11 files): the core abstraction is `DesktopIpc` — a typed IPC service. `makeIpcMethod`/`makeSyncIpcMethod` wrap each handler with **`Schema.decodeUnknownEffect` payload validation → handler → `Schema.encodeUnknownEffect` result encoding**, all span-wrapped and acquire/release-registered (auto-unregister on scope close). Channel names centralized in `channels.ts` (73 exports). Method groups in `src/ipc/methods/`: `preview` (34 exports — largest), `window`, `sshEnvironment`, `wsl`, `serverExposure`, `updates`, `connectionCatalog`, `clientSettings`. Handlers installed via `DesktopIpcHandlers.installDesktopIpcHandlers`. **Adoptable pattern:** schema-validated, self-registering, observable IPC beats hand-rolled `ipcMain.handle` string channels.

### 2b. Backend process lifecycle (the fork's active bug — deepest dive)

Files: `src/backend/` (7 source files, 2831 LOC). Key modules:
- **`DesktopBackendManager.ts`** (819 LOC) — factory `makeBackendInstance` returns an instance with `start`/`stop`/`snapshot`/`waitForReady`/`currentConfig`. Owns per-instance state `Ref`, a `Semaphore` mutex, the restart loop, and the active child process. `runBackendProcess` does the actual spawn (see §0). Health-check: `waitForHttpReady` polls a readiness path (`@t3tools/shared/httpReadiness` `waitForHttpReadyShared`), 1-min timeout, 100ms interval; on ready fires `onReady(httpBaseUrl)` → opens the window.
- **`DesktopBackendPool.ts`** (470 LOC) — `DesktopBackendPool` service registry: `get`/`list`/`primary`/`register`/`unregister`. Anchors instance scopes to the layer scope (orphan prevention, §0). Handles WSL→Windows preflight fallback (`handlePrimaryPreflightFailure`: dialog + persist Windows fallback + in-memory fallback if the persist write fails).
- **`DesktopBackendConfiguration.ts`** (686 LOC) — resolves entry path, args, env, bootstrap envelope; primary label resolution kept lazy (see comment: resolving eagerly would capture default settings and mislabel wsl-only primaries).
- **`DesktopServerExposure.ts`** (563 LOC) — local-only vs network-accessible exposure, port config from settings.
- Support: `tailscaleEndpointProvider.ts`, `DesktopLocalEnvironmentAuth.ts`, `DesktopNetworkInterfaces.ts`.

**Spawn → health-check → teardown flow:**
1. `DesktopApp.bootstrap`: `resolveDesktopBackendPort` (sequential scan from 3773 across hosts `127.0.0.1`/`0.0.0.0`/`::`), configure protocol + server exposure, `installDesktopIpcHandlers`, then `primaryBackend.start` and `Effect.forkScoped(wslBackend.reconcile)`.
2. `makeBackendInstance.start`: mutex-guarded; resolves config, checks entry exists, handles **preflight failures** (transient WSL cold-start → retry; fatal/bounded → `MAX_PREFLIGHT_FAILURE_ATTEMPTS` then surface + Windows fallback), then opens `runScope` and spawns.
3. Restart loop with exponential backoff (`calculateRestartDelay`: `INITIAL_RESTART_DELAY * 2^attempt` capped at `MAX_RESTART_DELAY`), cancellable restart fibers.
4. **Teardown** (see §0): `stop` flips state under mutex (so a racing `start` can't spawn a second backend on top), interrupts the restart fiber, `closeRun` → `Scope.close` → SIGTERM+grace via `forceKillAfter`.

**Dev vs packaged / signal handling / parent-death:**
- SIGINT/SIGTERM registered **only on non-Windows** (`DesktopLifecycle.register`, `if environment.platform !== "win32"`), via `addScopedListener` (auto-removed on scope close).
- Dev launcher `scripts/start-electron.mjs` re-signals **itself** on child exit (`process.kill(process.pid, signal)`) so the parent inherits the child's fate — a clean launcher-level orphan guard.
- Fatal startup errors (`DesktopApp.handleFatalStartupError`) route to `shutdown.request` + `electronApp.quit` + an error dialog, so a failed boot still tears down cleanly.

### 2c. Dev launch (PR #3662), .electron-runtime, packaging, WSL

- **`.electron-runtime`**: `apps/desktop/scripts/ensure-electron-runtime.mjs` downloads a pinned Electron zip from GitHub releases (`electron-v${version}-${platform}-${arch}.zip`) into a local runtime dir and chmods the binary — decouples the Electron binary from the npm dep for dev. `start-electron.mjs`/`smoke-test.mjs` resolve the launch command via `scripts/lib/electron-launcher.mjs`.
- **Dev launch (PR #3662):** `scripts/dev-runner.ts` is an Effect CLI (`effect/unstable/cli`) that hash-derives dev ports (base server 13773 / web 5733) per repo path, probes host availability, and orchestrates `vp run --filter … dev` for each mode (`dev`, `dev:server`, `dev:web`, `dev:desktop`). Desktop dev build: `apps/desktop/vite.config.ts` `pack --watch` with `onSuccess: node scripts/dev-electron.mjs` gated on `T3CODE_DESKTOP_DEV=1`. Has a companion `dev-runner.test.ts`.
- **Packaging (`dist-electron`):** `apps/desktop/vite.config.ts` uses `vite-plus` `pack` to emit **three CJS bundles** to `dist-electron/`: `main.cjs` (entry `src/main.ts`, `alwaysBundle` all `@t3tools/*`), `preload.cjs` (bundles `@clerk/electron`), and `preview-pick-preload.cjs` (bundles `react-grab`). `apps/desktop/package.json` `main: dist-electron/main.cjs`. Artifact build via `scripts/build-desktop-artifact.ts` (electron-builder driver; dmg/nsis/AppImage per arch; mac passkey signing config).
- **WSL modes (PR #3588):** `src/wsl/` — `DesktopWslEnvironment.ts` (849 LOC, the largest desktop file — WSL distro detection, `wslpath` translation, env warm-up) and `DesktopWslBackend.ts` (`reconcile` — brings up the WSL backend if enabled, in parallel with the Windows primary). `wslPathParsing.ts` is a small pure module with its own tests. The "warm WSL before preflight" fix lives in this env warm-up path. Dual-mode (parallel WSL + Windows backends) landed in PR #2751 and is why the pool/`list`-based teardown exists.

### 2d. Shared packages the desktop depends on
`@t3tools/contracts` (`DesktopBridge` IPC contract + provider/session schemas), `@t3tools/shared` subpaths (`/Net` for port probing, `/httpReadiness` for backend health, `/hostProcess` for platform/arch, `/shell` for spawn command resolution), `@t3tools/ssh` (remote runner for SSH-hosted backends), plus `apps/server/package.json` imported for the server's node engine range.

---

## 3. Recent main Themes (last ~40 commits)

Not a commit log — the themes relevant to the desktop skeleton and cross-cutting conventions:

1. **Backend lifecycle / multi-backend orchestration** — parallel WSL + Windows backends with mode picker (#2751), warm WSL before preflight in wsl-only mode (#3588). This is the live area for the fork's orphan bug; upstream's pool + scope model is the reference.
2. **Electron dev/packaged startup hardening** — "Fix electron dev launch and add test" (#3662), "Fix Electron dev and packaged renderer startup" (#3557). Upstream is actively de-flaking exactly the launch path a fork inherits.
3. **Preview/automation subsystem stabilization** — `src/preview/` (largest desktop subsystem, 6930 LOC): preview browser surfaces/automation/recording (#3565), live owner streams (#3548), element-pick context (#3527, #a4964b3b3). Heavy webview/CDP automation area.
4. **Effect error-handling conventions** — "Enforce Effect error handling conventions" (#3380), structured tagged errors for archive/auth/credential failures (#3451, #3471, #3349). Systematic move to `Schema.TaggedErrorClass`.
5. **`[codex]`-prefixed hardening commits** — a large share of recent commits are small, targeted defensive fixes (guard clipboard copy, guard DPoP fallback URL, reject unsupported pairing protocols, ignore stale reducer events). Signals a mature "many small guarded fixes" cadence.
6. **Chat/composer UX + model defaults** — composer liquid-glass (#3668), revision-gated native composer updates (#3574), Claude Sonnet 5 as default (#3620). Renderer-side, less relevant to the skeleton.

---

## 4. Conventions Worth Adopting

**Effect-ts as the app architecture (highest-leverage):** services via `Context.Service`, dependency wiring via `Layer`, lifecycle/teardown via `Scope` + `addFinalizer`, errors via `Schema.TaggedErrorClass`, tracing via `Effect.withSpan`/`annotateCurrentSpan`. The orphan-prevention story only works *because* processes are scope-bound. If the fork is still using ad-hoc `child_process` + manual `.kill()`, the single biggest adoptable change is moving backend spawning onto `effect/unstable/process` `ChildProcess.make` with `killSignal` + `forceKillAfter`.

**Custom oxlint plugin (`oxlint-plugin-t3code`)** — house rules that encode Effect discipline, each with a `.test.ts`:
- `namespace-node-imports`: require `import * as NodeFS from "node:fs"` canonical namespace form for all node builtins.
- `no-global-process-runtime`: forbid referencing global `process` in Effect-runtime files (use a HostProcess service); standalone repair scripts opt out with an inline disable + reason.
- `no-inline-schema-compile`: hoist `Schema.decode*/encode*` compilers out of function bodies so hot paths don't rebuild compilers per call.
- `no-manual-effect-runtime-in-tests`: forbid manual `Effect.runPromise`/`runSync` in tests; require `@effect/vitest` `it.effect(...)` + test layers.

**Testing:** `@effect/vitest` with `it.effect(...)` and test layers; **co-located `*.test.ts`** beside every non-trivial source and script (e.g. `DesktopBackendManager.test.ts` 716 LOC, `DesktopBackendConfiguration.test.ts` 799 LOC, `dev-runner.test.ts`). Command: `vp test` / `vp run test`. A separate `smoke-test.mjs` boots the packaged `main.cjs` under Electron.

**Strict TS baseline (`tsconfig.base.json`):** `module`/`moduleResolution: NodeNext`, `target: ESNext`, `strict`, `verbatimModuleSyntax`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `allowImportingTsExtensions` (imports use explicit `.ts`), `erasableSyntaxOnly`. Per-package `tsconfig.json` extends it; typecheck via `tsgo` (effect-tsgo).

**Package boundaries (from `AGENTS.md`):** `contracts` = schema-only, no runtime logic; `shared` = explicit subpath exports, **no barrel index**; extract shared logic before duplicating (stated as a hard rule). Core priorities stated as performance + reliability + predictable-under-failure.

**Process/error handling:** single `DesktopShutdown` `Deferred` coordinator instead of scattered quit logic; all teardown paths (signals, before-quit, window-all-closed, fatal startup) converge on it. Every IPC method and backend operation is span-wrapped and log-annotated with a component logger (`makeComponentLogger`).

---

## 5. Structure / Hygiene Lens

**Clean boundaries (adopt as-is):** `src/electron/*` (platform adapters) vs `src/app/*` (application logic) vs `src/backend/*` (process management) vs `src/ipc/*` (typed transport) is a genuinely clean layering. The `DesktopBackendPool` → `DesktopBackendManager` split (registry vs single-instance factory) is a good seam that the fork should preserve if it adds backend variants.

**Large files to watch (upstream already at/over the fork's own 700-LOC threshold):**
- `src/preview/Manager.ts` — **2973 LOC, 30 exports** (with a 1119-LOC test and a 1263-LOC `PickPreload.ts`). Far past any refactor threshold; the preview subsystem is the least-decomposed area. If the fork inherits preview, treat this as a decomposition target, not a template.
- `src/wsl/DesktopWslEnvironment.ts` — 849 LOC.
- `src/updates/DesktopUpdates.ts` — 841 LOC.
- `src/backend/DesktopBackendManager.ts` — 819 LOC, and `makeBackendInstance` is a **~432-line single function** (start/stop/restart/finalize all inlined). Correct and well-commented, but the largest function in the desktop and a candidate to split (extract the restart loop and `finalizeRun`).

**Reusable patterns:** the `makeIpcMethod` schema-validation wrapper, the `DesktopShutdown` Deferred coordinator, the scope-anchored process pool, and the per-run `Scope` + `forceKillAfter` idiom are the four highest-value things to lift into `transport-matters`.

---

## 6. Open Questions / For Follow-up

- Does `transport-matters` still spawn its backend with raw `child_process` (the likely orphan root cause), or has it partially adopted the Effect pool? A diff of the fork's `backend/` against upstream's would localize the regression.
- Windows has **no** SIGINT/SIGTERM handler upstream (relies on `before-quit`/`window-all-closed`). If the fork runs on Windows and orphans there, the gap may be the missing Windows-specific quit path rather than the kill mechanism.
- `forceKillAfter: 2s` grace — confirm the fork's backend actually exits within 2s of SIGTERM (flush/close ordering), else force-kill still drops in-flight work.
