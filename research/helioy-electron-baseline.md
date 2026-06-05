---
title: Helioy Electron + Web App Baseline (v0 Spec)
type: spec
tags: [helioy-baseline, electron, baseline, template, transport-matters, runtime-matters, littleorgans, effect, effect-schema, effect-rpc, effect-atom, tailwind4, base-ui, design-system, monorepo, ipc, rpc]
summary: 'Spec for `@helioy/baseline` — the three-app + three-package shape for every Helioy desktop+web product surface. Three consumers: transport-matters, runtime-matters, littleorgans. 35 numbered patterns sourced from pingdotgg/t3code v0.0.24 plus 12 locked baseline parameters (Effect Schema across all boundaries, atom-first renderer, WebSocket + Effect RPC, single Electron shell with three packaged identities, file-based routing, Geist vendored, Lucide everywhere, Header + StatusBar primitives).'
status: active
source: four parallel codebase-analyst agents against /Users/alphab/Dev/LLM/DEV/helioy/t3code @ review/pingdotgg-main d1e85c4e v0.0.24; twelve decisions resolved interactively with Stuart on 2026-05-16
confidence: high
created: 2026-05-15
updated: 2026-05-16
---

# Helioy Electron + Web App Baseline

## Purpose

This document specifies `@helioy/baseline` — the shape every Helioy desktop+web product surface inherits. Three apps (`desktop`, `server`, `web`), three packages (`contracts`, `shared`, `client-runtime`), one wire contract, one design surface, one Electron shell shape, twelve locked baseline parameters.

Three consumers ship from this baseline: **transport-matters** (immediate, has existing Manicure v2 canvas work), **runtime-matters** (next, the brain of the Little Organs system), **littleorgans** (parallel, the dashboard that observes and operates the organs). The baseline exists so all three move at the same velocity, share visual identity, and never re-solve a problem one of the others already solved.

## Source and provenance

Every pattern in §2–§5 is sourced from `pingdotgg/t3code` at v0.0.24 (`review/pingdotgg-main` at `d1e85c4e`, reviewed 2026-05-15). Patterns are documented with file paths and line numbers so each can be lifted independently. The twelve baseline parameters in §7 were resolved interactively with Stuart on 2026-05-16.

T3 Code is a credible source because two things in it had to be true to make this baseline cheap: an Effect-ported Electron layer with a typed IPC contract (`apps/desktop/src/ipc/`), and a renderer-server seam decoupled enough that the React app can run as a web page or as an Electron renderer from the same bundle. Both shipped in the six weeks between the prior t3code product-foundation eval (`t3code-product-evaluation.md`, 2026-04-06) and this spec. The previous eval's "fork-and-rebrand the product" framing is no longer the right read; the right read is "extract the baseline, design the products on top."

The local clone was tracking `srobinson/t3code` (a personal fork) and was 260 commits behind. The review was done on a fresh branch cut from `pingdotgg/main`.

## Executive summary

```
helioy app baseline (extracted shape)
├── apps/
│   ├── desktop/      Electron 40+ shell, Effect runtime in main process
│   ├── server/       Effect backbone (Bun + Node dual), the brain
│   └── web/          React 19 + Vite, single bundle for both web and desktop renderer
└── packages/
    ├── contracts/    Schema-only: Effect Schema + WS_METHODS + RpcGroup
    ├── shared/       Stateless utilities, explicit subpath exports, no barrel
    └── client-runtime/  UI-agnostic renderer state primitives, Effect Atoms, no React
```

Three apps that ship as one. One wire contract typechecked on both sides. A renderer-side runtime that holds atoms and the RPC client without React in scope. A design system built on Tailwind 4 + base-ui with a single `--radius` knob and a pre-React inline theme bootstrap that eliminates FOUC.

**The single most copy-worthy thing in the codebase**: the `apps/web/index.html` + `apps/web/src/index.css` trinity. It is the smallest amount of code that gives a Helioy product a production-feeling first paint. See §5.1.

## 1. The Helioy app baseline blueprint

Three product surfaces, one baseline. Each surface gets its own monorepo cloned from the same baseline, with three apps and three packages preconfigured.

### What every Helioy app gets out of the box

```
helioy-{surface}/
├── apps/
│   ├── desktop/
│   │   ├── src/
│   │   │   ├── main.ts                  Bootstrap: Effect Layer composition, scoped finalizers
│   │   │   ├── preload.ts               Single DesktopBridge interface, `satisfies` at expose
│   │   │   ├── app/                     Domain services: lifecycle, env, identity, observability
│   │   │   ├── backend/                 Server-as-child-process: spawn, restart mutex, fd3 bootstrap
│   │   │   ├── electron/                Effect wrappers around every Electron API touchpoint
│   │   │   ├── ipc/                     makeIpcMethod codec brackets, channels.ts, methods/
│   │   │   ├── settings/                Persisted JSON state on disk
│   │   │   ├── shell/                   PATH/locale shell-env capture (macOS GUI fix)
│   │   │   ├── updates/                 Pure reducer + electron-updater orchestration
│   │   │   └── window/                  Window orchestration, native menus, context menus
│   │   ├── scripts/                     dev-electron, start-electron, smoke-test
│   │   └── tsdown.config.ts             CJS, noExternal @helioy/*, two outputs
│   ├── server/
│   │   └── src/                         Effect Layer composition, sqlite, OTLP, schema-driven settings
│   └── web/
│       ├── index.html                   Pre-React inline theme bootstrap + boot splash
│       └── src/
│           ├── main.tsx                 26 LOC: createHistory + getRouter + render
│           ├── router.ts                getRouter wires QueryClient + RegistryContext + route tree
│           ├── routes/                  File-based, __root.tsx is the auth gate
│           ├── rpc/                     wsTransport, wsRpcClient, atomRegistry, serverState
│           ├── environments/            EnvironmentConnection per backend (optional)
│           ├── store.ts                 Zustand primary; ONE per domain, not god-store
│           ├── components/
│           │   └── ui/                  All primitives: button, dialog, sheet, popover, toast, ...
│           ├── lib/                     Per-resource ReactQuery keys, per-entity Atom.family
│           └── index.css                Tailwind 4 @theme inline, semantic tokens, --radius
└── packages/
    ├── contracts/                       Schema-only, Effect Schema, WS_METHODS, RpcGroup
    ├── shared/                          Explicit subpath exports, no barrel
    └── client-runtime/                  Effect Atoms, scoped-ref helpers, KnownEnvironment shape
```

Top-level: root `package.json` with `workspaces.catalog` (pin every Effect/TypeScript/Vitest version), `turbo.json` with four tasks (`build`, `dev`, `typecheck`, `test`), `scripts/dev-runner.ts` (port-hash, multi-host probe, turbo orchestrator), `tsconfig.base.json` with `@effect/language-service` strictness plugin enabled.

That is the template. Sections 2–5 explain why each piece earns its place. Section 9 maps it onto the three target Helioy surfaces.

## 2. The Electron shell layer

`apps/desktop/src` is the most surprising thing in the repo. It is not a thin Electron wrapper. It is a structured Effect program that happens to run inside an Electron main process. Every cross-cutting concern is a `Context.Service` with a `Layer.effect` adapter. The whole bootstrap is one `Effect.gen` whose `Scope.close` is the shutdown path.

### 2.1 The nine subdirs, what each holds

- **`app/`** — domain of the desktop layer. `DesktopApp.ts` is the program entry. `DesktopEnvironment` holds the read-only record (paths, version, branding, runtime info — `app/DesktopEnvironment.ts:33-77`). `DesktopLifecycle`, `DesktopState`, `DesktopAppIdentity` (single-instance lock), `DesktopAssets`, `DesktopConfig`, `DesktopObservability`. None of these import Electron globals.
- **`backend/`** — server-as-child-process. `DesktopBackendManager.ts:280-596` is a spawn/restart state machine with mutex. `DesktopBackendConfiguration` assembles env + bootstrap payload. `DesktopServerExposure` resolves bind host across local-only / LAN / Tailscale modes.
- **`electron/`** — thin Effect wrappers around every Electron API touchpoint: `ElectronApp`, `ElectronDialog`, `ElectronMenu`, `ElectronProtocol`, `ElectronSafeStorage`, `ElectronShell`, `ElectronTheme`, `ElectronUpdater`, `ElectronWindow`. Each exposes a `Context.Service` with effectful methods. **This is the seam between Effect-world and the imperative Electron globals.** Nothing else in the codebase touches `app`, `BrowserWindow`, `ipcMain`, etc. directly.
- **`ipc/`** — typed main/renderer boundary. `channels.ts:1-36` is the string constant registry. `DesktopIpc.ts:130-219` exposes a `makeIpcMethod` factory that wraps `{ channel, payload: Schema.Codec, result: Schema.Codec, handler }`. `DesktopIpcHandlers.ts:45-84` is the registration manifest. One file per concern under `methods/`.
- **`settings/`** — `DesktopAppSettings`, `DesktopClientSettings`, `DesktopSavedEnvironments`. Persisted JSON state.
- **`shell/`** — `DesktopShellEnvironment.installIntoProcess` captures the user's login shell PATH so spawned subprocesses see the same `node`/`bun`/`git` the user sees in their terminal. Load-bearing on macOS where GUI apps inherit a stripped environment.
- **`ssh/`** — remote-host pairing (product-specific to t3code). Skip in the baseline.
- **`updates/`** — auto-update state machine. `updateMachine.ts` is pure reducer functions over `DesktopUpdateState`. `DesktopUpdates.ts:188-664` wires `electron-updater` events into those reducers. State is broadcast to all renderers via `electronWindow.sendAll(UPDATE_STATE_CHANNEL, state)` (line 213).
- **`window/`** — `DesktopWindow.ts:147-368` (create-main-window orchestration, native context menus, `did-fail-load` handling) and `DesktopApplicationMenu` (per-platform native menu template).

### 2.2 Patterns to copy verbatim

**P1 · Effect Layer composition as the desktop bootstrap.** `apps/desktop/src/main.ts:48-154` builds five concentric layers and provides them to `DesktopApp.program`. The whole runtime closes cleanly on `scopedProgram` finalizers (`app/DesktopApp.ts:222-238` registers backend stop + `shutdown.markComplete` as scope finalizers). For Helioy: every desktop concern becomes a Service, the main process is one Effect program, and shutdown is `Scope.close`.

**P2 · `makeIpcMethod` codec-bracketed handlers.** `ipc/DesktopIpc.ts:130-170` wraps a registration `{ channel, payload, result, handler }` so every handler decodes inputs and encodes outputs at the wire boundary. The preload side imports a single `DesktopBridge` interface from `@t3tools/contracts` (`packages/contracts/src/ipc.ts:372`) and applies `satisfies DesktopBridge` on the exposed object (`preload.ts:127`). Type drift between main and renderer is caught at build time. **This is the most important pattern in `apps/desktop/`. Adopt verbatim, using Effect Schema both directions.**

**P3 · Server-as-child-process with bootstrap on fd3.** `backend/DesktopBackendManager.ts:236-257` spawns the server using `process.execPath` + `ELECTRON_RUN_AS_NODE=1` (`DesktopBackendConfiguration.ts:117-120`) and passes the bootstrap JSON as a one-shot stream on **file descriptor 3** (`--bootstrap-fd 3`). The child reads structured config without env-var stringification or argv hell. Readiness is HTTP-polled at `/.well-known/t3/environment` with `HttpClient.retry(Schedule.spaced(100ms))` and a 1-minute timeout. Restart is exponential-backoff with mutex. For Helioy: fd3 bootstrap as the desktop→backend contract works identically for Node, Bun, or a Rust server that reads fd3.

**P4 · Sequential port scan with multi-host probe.** `app/DesktopApp.ts:59-93` walks ports from a base upward, probing each on `["127.0.0.1", "0.0.0.0", "::"]` before accepting. Single-host probe hands back a "free" port that fails on bind. Triple-host probe is the difference between "works on my machine" and "works on every machine".

**P5 · Pure reducer for cross-process UI state, effectful orchestration on top.** `updates/updateMachine.ts` exports `reduceDesktopUpdateStateOnCheckStart`, `…OnDownloadProgress`, etc. as pure functions over `DesktopUpdateState`. The Effect-layer wraps electron-updater events into those reducers, calls `setState` which broadcasts to all renderers. Reducer testability decoupled from Electron. Apply to any long-lived UI state that flows from main to renderer (updates, backend health, exposure mode).

**P6 · Two-file build with tsdown, CJS output, `@helioy/*` bundled in.** `apps/desktop/tsdown.config.ts` produces `dist-electron/main.cjs` and `dist-electron/preload.cjs`. `noExternal: (id) => id.startsWith("@t3tools/")` bundles every workspace package into the main bundle. Electron's CJS loader does not need workspace resolution at runtime. Dev loop is `bun run --parallel dev:bundle dev:electron`; `scripts/dev-electron.mjs:163-179` watches the two emitted bundles + the server output and restarts Electron with a 120 ms debounce, force-kills the child tree after 1.5 s.

**P7 · Stage-then-build packaging.** `scripts/build-desktop-artifact.ts:651-891` creates a temp directory, copies `dist-electron/`, `server/dist/`, `resources/` into it, writes a synthetic `package.json` containing resolved (catalog-flattened) production deps plus electron-builder build config, runs `bun install --production --omit optional` inside the stage, then `electron-builder` against that stage. **The actual workspace is never seen by electron-builder.** `resolveGitHubPublishConfig` (line 505) reads `T3CODE_DESKTOP_UPDATE_REPOSITORY` or `GITHUB_REPOSITORY` so the same script targets any fork's releases. mac generates `.icns` on the fly from PNG via `sips` + `iconutil`. This is the cleanest desktop packaging recipe I have seen.

### 2.3 Patterns to skip in the Helioy baseline

The entire `ssh/` subtree (724 LOC) is t3code's remote-dev pairing flow. `DesktopSavedEnvironments` + safeStorage secret indirection is right for an app that lists remote hosts, wrong for an app with zero or one local credential. The `branding`/`stageLabel` machinery (`app/DesktopEnvironment.ts:83-106`) staged-label apparatus is for shipping three release channels of *one* product. Helioy's three surfaces are three different products, not channels.

### 2.4 Inspirational but not yet

`DesktopServerExposure` with Tailscale Serve (548 LOC) — eventually Helioy will want "expose this desktop instance to my phone" semantics. Adopt the *shape* (an `exposure` service that resolves bind host + advertised URL from settings) without the Tailscale wiring. `ELECTRON_RUN_AS_NODE=1` is brilliant if the runtime is JS, irrelevant if a Helioy surface ships a Rust backend.

## 3. The monorepo and contracts spine

### 3.1 Topology

| Path | Bedrock? | Role |
| --- | --- | --- |
| `apps/server` | yes | Bun/Node CLI; the brain. tsdown-bundled. |
| `apps/web` | yes | Vite + React 19 + TanStack Router renderer. Same bundle for browser and Electron. |
| `apps/desktop` | yes | Electron 40 main process. |
| `apps/marketing` | no | Astro site. Out of baseline scope. |
| `packages/contracts` | yes | Wire-format schema spine. |
| `packages/shared` | yes | Stateless utilities, 21 explicit subpath exports. |
| `packages/client-runtime` | yes | UI-agnostic renderer state primitives. Effect Atoms. No React dep. |
| `packages/effect-acp` | inspiration | Wraps Zed's Agent Client Protocol. Generated bindings under `_generated/`. |
| `packages/effect-codex-app-server` | inspiration | Wraps Codex CLI's JSON-RPC. Same shape as effect-acp. |
| `packages/ssh` | product-specific | Effect-wrapped `ssh` CLI. Skip. |
| `packages/tailscale` | product-specific | Effect-wrapped `tailscale` CLI. Skip. |

`oxlint-plugin-t3code` is also a workspace package. Skip — t3code-specific lint rules.

### 3.2 The contract spine, end to end

`packages/contracts` is the single source of truth for the WebSocket wire format. The flow:

1. **Branded ID primitives** at `packages/contracts/src/baseSchemas.ts:30-60` define `ThreadId`, `ProjectId`, `EnvironmentId`, `CommandId`, `MessageId`, etc. via `Schema.brand`. `TrimmedNonEmptyString` is the base. `makeEntityId = <Brand>(brand) => TrimmedNonEmptyString.pipe(Schema.brand(brand))` is the factory at lines 26-28. **One helper, sixteen branded IDs.**
2. **Domain shapes and tagged errors** in per-concern files (`server.ts`, `git.ts`, `terminal.ts`, `orchestration.ts`). Each defines `XxxInput` / `XxxResult` Structs and `XxxError` tagged unions.
3. **Method-name registry** at `rpc.ts:102-164`: a single `WS_METHODS` const object pins every RPC string id. Forty-five methods.
4. **One `Rpc.make` per method** at `rpc.ts:166-473`, each binding `payload`, `success`, `error`, and `stream: true` for subscriptions. Pattern is uniform.
5. **One `RpcGroup.make` aggregating everything** at `rpc.ts:475-524` (`WsRpcGroup`).
6. **Server consumes** at `apps/server/src/ws.ts` (handler implementations bound to `WsRpcGroup`).
7. **Client consumes** at `apps/web/src/rpc/protocol.ts` (typed RPC client from the same group).

Both ends get full type-checking from the same file. Adding an RPC method is: add to `WS_METHODS`, write `Rpc.make`, register in `WsRpcGroup`, then both sides refuse to compile until handler and call-site exist. **This is the contract spine to copy verbatim.**

### 3.3 `packages/client-runtime`: the missing third package

This package did not exist six weeks ago. It is the renderer-side state primitive layer, between `contracts` (wire types) and the React app (hooks). It imports `type` only from `contracts` and uses `effect/unstable/reactivity` `Atom.family` to expose UI-shaped state. `sourceControlDiscoveryState.ts:38-48` shows the idiomatic shape: an `Atom.family` keyed by string, a frozen initial state, and a manager factory that takes `getRegistry` and `getClient` as **injected** functions (line 76). The package has **no `react` dependency.** React glue stays in the web app.

For Helioy, this is the package every product needs. It is where atoms, scoped-ref helpers, environment descriptors, and refresh managers live. The web app composes them. If Helioy ever runs the same logic in a non-React surface (CLI dashboard, Tauri Solid app, server-rendered admin), `client-runtime` ports unchanged.

### 3.4 Patterns to copy verbatim

**P8 · Catalog-pinned Effect ecosystem.** Root `package.json:11-27` pins every `effect`, `@effect/*`, `vitest`, `tsdown`, `typescript`, `@types/*` to a single version via `workspaces.catalog`. `overrides` (lines 73-82) repeat the same for transitive resolution. Every package writes `"effect": "catalog:"`. Pin once.

**P9 · Schema-only contracts package.** `packages/contracts` has zero runtime side effects: `dependencies: { "effect": "catalog:" }` only. Adopt as-is.

**P10 · `WS_METHODS` const + `Rpc.make` + single `RpcGroup`.** The triple-binding at `rpc.ts:102-524`. Adding an RPC is three lines plus a group registration. Streaming uses `stream: true` (lines 294, 313, 437, 450-471) so push channels share the same registry.

**P11 · Branded entity-ID factory.** `baseSchemas.ts:26-28`. Centralise branding here, not ad hoc per file.

**P12 · Explicit subpath exports, no barrel.** `packages/shared/package.json:5-94` lists 21 explicit `./model`, `./git`, `./Net`, etc. with `types` + `import` pointing at the `.ts` source. Zero barrel `index.ts`. Tree-shaking by file path. `allowImportingTsExtensions` + `rewriteRelativeImportExtensions` (tsconfig.base.json:7-8) makes `.ts` source imports work directly without a build step in dev. **For any utility kitchen package in Helioy.**

**P13 · `client-runtime` as the renderer state primitive package.** `Atom.family` keyed by composite string. Manager factories that accept injected `getRegistry`/`getClient`. No React dependency.

**P14 · `scripts/dev-runner.ts` orchestrator.** A 540-line Effect CLI that resolves deterministic port offsets from `T3CODE_PORT_OFFSET` or hashed `T3CODE_DEV_INSTANCE` (line 87-112) so multiple worktrees do not collide, probes four hostnames per port (line 233-308), sets `VITE_DEV_SERVER_URL`/`VITE_HTTP_URL`/`VITE_WS_URL`/`T3CODE_PORT`/`T3CODE_HOME` per mode (lines 141-221), and spawns a single `turbo run dev --filter=... --parallel` child (line 441-458) with `detached: false` so Ctrl+C propagates. **The port-hash trick alone is worth the entire file.** Copy verbatim, rename env vars.

**P15 · `turbo.json` discipline.** Four task entries: `build` cached with `^build` chain, `dev` non-cached and persistent with `@helioy/contracts#build` as a one-time prerequisite, `typecheck` and `test` both with `^build`. `globalEnv` declares every env var Turbo's cache should consider.

### 3.5 Patterns to study before adopting

**`@effect/language-service` strictness plugin.** `tsconfig.base.json:21-53` enables 24 Effect-specific diagnostics as errors: `importFromBarrel`, `anyUnknownInErrorContext`, `unsafeEffectTypeAssertion`, `instanceOfSchema`, `missingEffectServiceDependency`, `leakingRequirements`, `globalDate`, `globalConsole`, `cryptoRandomUUID`, `nodeBuiltinImport`. The `prepare: effect-language-service patch` script in root `package.json:31` patches `effect` itself. Install once, audit the resulting errors, ratchet.

**External CLI wrapped as Effect Service.** `packages/tailscale/src/tailscale.ts:14-27` and `packages/ssh/src/tunnel.ts:1-40` show the canonical shape: three `Data.TaggedError`s, `ChildProcessSpawner` + `HttpClient`, output parsed with `Schema.Struct` (using `Schema.Unknown` for fields we do not validate), Service interface, Layer. **Use when wrapping `git`, `gh`, `fmm`, or any tool.**

**Generated bindings under `_generated/`.** `effect-acp` and `effect-codex-app-server` both wrap an external JSON-RPC protocol by generating Effect Schema types from a published JSON schema, then writing hand-curated `client.ts`/`protocol.ts` on top. Pattern: external protocol → generated schema → Effect-Schema wrapper → Effect Service interface.

## 4. The web client architecture

The prior eval claimed atom-first state. **That was wrong.** The web client is **Zustand-primary, atom-secondary**. Atoms are used for cross-cutting reactive state where imperative `.get()`/`.set()` matters (RPC connection phase, push-driven server state, per-entity reactive families). Domain state (projects, threads, messages) lives in Zustand slices.

### 4.1 Boot sequence

Three statements in `apps/web/src/main.tsx:15-28`:

```ts
const history = isElectron ? createHashHistory() : createBrowserHistory();
const router = getRouter(history);              // router.ts:8
ReactDOM.createRoot(...).render(<RouterProvider router={router}/>);
```

`getRouter` (`router.ts:8-24`) wires three concerns into TanStack Router via its `Wrap` prop: a fresh `QueryClient`, a `RegistryContext.Provider` for the shared `appAtomRegistry`, and the route tree. **The WS transport is not created here.**

The root route (`routes/__root.tsx:67-100`) is the actual app gate. Its `beforeLoad` runs `ensurePrimaryEnvironmentReady()` (descriptor) plus `resolveInitialServerAuthGateState()` (auth probe) in parallel. The gate result is exposed through `Route.useRouteContext()` as `authGateState`. Nested routes (`_chat.tsx:110-116`, `settings.tsx:106`) redirect on `status !== "authenticated"` via their own `beforeLoad`. **This is the pattern.** Any product that needs an auth/setup gate before mounting the shell maps directly onto this. No Suspense flicker. No top-level `if (loading)` ladder.

### 4.2 The renderer-server seam

The WS client is constructed lazily in `environments/runtime/service.ts:1124-1142` (`createPrimaryEnvironmentClient`) and reused per `EnvironmentId`. The stack:

- `WsTransport` (`rpc/wsTransport.ts:240-276`) owns **one `ManagedRuntime` per session**, creates a Layer from `createWsRpcProtocolLayer(url, lifecycleHandlers)`, returns a typed facade.
- **Reconnect creates a new session + new runtime, then closes the previous one** (`wsTransport.ts:199-218`). All Effect resources tear down deterministically.
- `WsRpcClient` (`rpc/wsRpcClient.ts:56-156`) groups methods by domain (`terminal`, `vcs`, `git`, `server`, `orchestration`), each typed off `WS_METHODS` constants from `@t3tools/contracts`. Renaming a contract method fails at compile time at every call site.

The contract for Helioy: `packages/client-runtime` exports the target descriptor (`KnownEnvironment` with `wsBaseUrl`/`httpBaseUrl`) and scoped-ref helpers. `apps/web/src/rpc/*` owns transport. Components only see an `EnvironmentConnection` value: `{ kind, environmentId, knownEnvironment, client, ensureBootstrapped, reconnect, dispose }`.

### 4.3 Server-pushed state lands in two sinks

Structured app state (project list, thread snapshots) goes to the Zustand `store.ts` via handlers in `createEnvironmentConnectionHandlers` (`service.ts:1084`). Cross-cutting connection/config status (WS phase, server config, latency, providers) goes to Atoms in `rpc/serverState.ts` and `rpc/wsConnectionState.ts`, read with `useAtomValue`. The `__root.tsx` `EventRouter` (line 281) is the single dispatcher for server `welcome` and `serverConfigUpdated` lifecycle events.

### 4.4 Patterns to copy verbatim

**P16 · Auth gate via `beforeLoad` on `__root` returning context.** `__root.tsx:69-94`. Parallel-fires bootstrap + auth probe, stores `authGateState` in route context. Nested routes redirect.

**P17 · `ManagedRuntime` per WebSocket session, reconnect = new session.** Each `WsTransport` keeps a `nextSessionId`/`activeSessionId` pair. Reconnect swaps `this.session`, awaits the new client, closes the old `Scope`. **Never try to keep a single client and "reset" it. Build a session abstraction.**

**P18 · Domain-grouped typed facade over the transport.** `client.terminal.open()`, `client.git.runStackedAction()`, each generated from `WS_METHODS.foo`. The contracts package is the single source of method names. The facade is a thin per-domain map.

**P19 · `AtomRegistry` provided once via `RegistryContext`, atoms colocated with their concern.** `rpc/atomRegistry.ts:5-9`, used in `router.ts:20-22`. Registry exported as a mutable binding so tests can reset it (`resetAppAtomRegistryForTests`). Atoms for cross-cutting "global" reactive state where imperative `.get()`/`.set()` without a hook matters.

**P20 · `Atom.family` keyed by composite string for per-entity reactive state.** `gitStatusState.ts:51-70`. `gitStatusStateAtom(environmentId + ':' + cwd)` mints a new atom per target lazily. `Atom.keepAlive` retains it. Ref-counted subscriptions in `watchedGitStatuses` drive subscribe/unsubscribe. Right primitive for "one observable per entity" without exploding store shape.

**P21 · Component split: `Foo.tsx` + `Foo.logic.ts` + `Foo.logic.test.ts`.** Pure derive functions in `.logic.ts`, thin glue in `.tsx`. `MessagesTimeline.logic.ts` exports `deriveMessagesTimelineRows()` plus `isRowUnchanged()` for identity-stable lists. Readable tests on render logic without spinning up DOM.

**P22 · Push per-row state into precomputed row objects, read via context only what is genuinely shared.** Commit `a41f4895`: removed `activeTurnInProgress`, `activeTurnId`, `completionSummary` from `TimelineRowActivityCtx`, folded them into `MessagesTimelineRow` fields. Rationale: `activeTurnId` ticks every turn, invalidating context on every assistant turn and rerendering every row. Once moved into row identity, only the row that actually changes rerenders. The `isRowUnchanged` shallow comparator preserves identity across derivation calls. **Apply to virtualised lists, sidebar trees, anything mapping over hundreds of items.**

**P23 · `useStore.getState()` inside event handlers; subscribe only when display state needs reactivity.** Commit `7455472c` removed `useStore(s => s.size)` and replaced with `useThreadSelectionStore.getState().hasSelection()` inside handlers. Component no longer rerenders on every selection change. **Codify: if a value is only read in callbacks, do not subscribe to it.**

### 4.5 Patterns to skip

The monolithic `store.ts` (1987 LOC) and `service.ts` (1824 LOC) violate the 700-LOC threshold by 2.5x. Hand-rolled domain-specific patches conflate projects, threads, messages, sessions, turn state into one Zustand instance. Connection lifecycle + saved environment catalog + SSH bearer flow + projection version reconciliation in one file. **Do not copy this shape. Start with per-domain Zustand slices.** The `EventRouter` god-component (`__root.tsx:281-428`, 147 LOC of `useEffectEvent`) should be split per concern.

Pair-route auth flow (`pair.tsx`) is specific to Pierre's hosted-static distribution model. Skip.

## 5. The design system (UI emphasis)

This is the load-bearing section for the Helioy baseline. t3code's UI surface is unusually production-grade for v0.0.24. **Stack**: Tailwind 4 CSS-only-config, base-ui as the primitive library, DM Sans, **zero motion library** (all animation is CSS data-attr transitions on base-ui state), shadcn-flavored component shells with `data-slot` attributes everywhere.

### 5.1 The single most copy-worthy thing

The trinity of `apps/web/index.html` + `apps/web/src/index.css` plus the boot splash. Two files. Production-feeling first paint. No FOUC.

**Pre-React inline theme bootstrap** (`index.html:14-37`): a synchronous IIFE that reads `localStorage["t3code:theme"]`, applies the `.dark` class to `<html>`, sets `<html style="background-color">`, and updates `<meta name="theme-color">`. All before React mounts. All before the first paint.

**Boot splash** (`index.html:94-101`): `#boot-shell` renders the app icon centered. Replaced when React hydrates `#root`. Cheap perceived-performance win.

**Tailwind 4 `@theme inline` token bridge** (`index.css:7-46`): semantic vars defined in `:root`, bridged to Tailwind utilities. Gives `bg-popover`, `text-muted-foreground`, etc. without a JS config. There is **no `tailwind.config.*` file in the repo.**

Drop these into every Helioy product. Swap the palette and the font import. You have visual coherence before writing a single component.

### 5.2 The token system

```css
/* index.css:7-46 — what's in @theme inline */
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-card: var(--card);
  --color-popover: var(--popover);
  --color-muted: var(--muted);
  --color-accent: var(--accent);
  --color-destructive: var(--destructive);
  --color-success: var(--success);
  --color-warning: var(--warning);
  --color-info: var(--info);
  --color-border: var(--border);
  --color-ring: var(--ring);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --animate-skeleton: skeleton 2s -1s infinite linear;
}
```

Values are OKLCH from Tailwind 4's built-in palette plus alpha-mix:

```css
:root {
  --radius: 0.625rem;
  --background: var(--color-white);
  --foreground: var(--color-neutral-800);
  --primary: oklch(0.488 0.217 264);    /* indigo-ish */
  --ring: oklch(0.488 0.217 264);
  --secondary: --alpha(var(--color-black) / 4%);
  --muted: --alpha(var(--color-black) / 4%);
  --border: --alpha(var(--color-black) / 8%);
  --success: var(--color-emerald-500);
  --success-foreground: var(--color-emerald-700);
}

@variant dark {
  --background: color-mix(in srgb, var(--color-neutral-950) 95%, var(--color-white));
  --primary: oklch(0.588 0.217 264);
  --border: --alpha(var(--color-white) / 6%);
}
```

Two things to call out. First, the background in dark is **not pure black**. It is `color-mix(in srgb, var(--color-neutral-950) 95%, var(--color-white))` — a 5% white tint on near-black. Reads softer than `#000`. Second, every radius derives from a single `--radius` knob. Recalibrate the whole product by changing one number.

**Theme selection** is class-based on `<html>`. Three-way `light | dark | system`. Stored at `localStorage["t3code:theme"]` (`useTheme.ts:9`). A `.no-transitions` class is toggled during theme swaps to suppress transitions globally (`index.css:78-84`).

**Typography**: DM Sans variable, 300-800. Google-hosted. Fallback `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif`. Mono is `"SF Mono", "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace`. No size scale defined as tokens — Tailwind defaults. Sub-`sm` breakpoint downshifts most components one step (`button.tsx:11` — `text-base sm:text-sm`).

**Motion**: zero library dependency. All animation is CSS transitions on base-ui `data-starting-style` / `data-ending-style` / `data-instant` attributes. Durations are inline (`200ms ease-in-out` for dialog/sheet, `120ms ease` for chrome hovers, `300ms` delay for scrollbar fade). Massively cheaper than a motion library and feels right.

### 5.3 Layout primitives

- **Root shell** (`__root.tsx:124-130`): `ToastProvider > AnchoredToastProvider > [bootstraps] > WebSocketConnectionSurface > CommandPalette > AppSidebarLayout > Outlet`. Toast and CommandPalette wrap everything, including offline states.
- **`apps/web/src/components/ui/sidebar.tsx`** (1001 LOC): the most reusable single file in the repo. Full `SidebarProvider`/`Sidebar`/`SidebarRail`/`SidebarInset`/`SidebarTrigger`/`SidebarMenu(Item|Sub|Button|Action)` tree. Mobile sheet fallback via `useIsMobile`. Cookie + localStorage persistence. Hand-rolled pointer-based resize with a `shouldAcceptWidth` callback (lines 400-558).
- **`AppSidebarLayout.tsx`** (76 LOC): wires the resizable left sidebar with min/max constraints (`THREAD_SIDEBAR_WIDTH_STORAGE_KEY`, min 208px, requires ≥640px of remaining main content). Width persisted with Effect `Schema.Finite` validation.
- **`RightPanelSheet.tsx`** (30 LOC): uses `Sheet` `side="right"` with `keepMounted` so content state survives close.

### 5.4 The component primitive table

All under `apps/web/src/components/ui/`. All wrap `@base-ui/react/*`. All use `cn` from `~/lib/utils` and CSS vars from `index.css`. Every primitive sets a `data-slot` attribute, enabling CSS like `in-[[data-slot=dialog-popup]:has([data-slot=dialog-panel])]:pb-3` — container queries via attribute selectors, no JS context.

| Component | Path | base-ui | Notes |
| --- | --- | --- | --- |
| Button | `ui/button.tsx` (75) | `merge-props` + `use-render` | cva, 7 variants × 9 sizes |
| Badge | `ui/badge.tsx` (57) | `use-render` | cva, 7 variants (success/warning/info/error subtle) |
| Dialog | `ui/dialog.tsx` (182) | `dialog` | Nested-dialog scale via `--nested-dialogs` |
| Sheet | `ui/sheet.tsx` (201) | `dialog` | `side="right\|left\|top\|bottom"`, `variant="default\|inset"` |
| Popover | `ui/popover.tsx` (109) | `popover` | Includes `tooltipStyle` flag |
| Tooltip | `ui/tooltip.tsx` (60) | `tooltip` | |
| Menu | `ui/menu.tsx` (311) | `menu` | Re-exported as DropdownMenu; includes `MenuShortcut` (kbd) |
| Toast | `ui/toast.tsx` (777) | `toast` | Stacked + Anchored providers; iOS-style corner dismiss orb |
| CommandPalette | `ui/command.tsx` (235) | `dialog` + Autocomplete | Built on Autocomplete primitive |
| Autocomplete / Combobox / Select | `ui/*.tsx` | base-ui | |
| AlertDialog / Checkbox / Switch / Toggle / RadioGroup / NumberField | `ui/*.tsx` | base-ui | |
| Form / Field / Fieldset / Label / Input / Textarea / InputGroup / DraftInput | `ui/*.tsx` | base-ui form primitives | |
| ScrollArea | `ui/scroll-area.tsx` (75) | `scroll-area` | `scrollFade`, `scrollbarGutter`, `hideScrollbars` |
| Collapsible | `ui/collapsible.tsx` | base-ui | |
| Skeleton | `ui/skeleton.tsx` (17) | none | linear-gradient shimmer with `[--skeleton-highlight]` |
| Spinner | `ui/spinner.tsx` | none | |
| Empty | `ui/empty.tsx` (115) | none | Stacked icon cards variant — see below |
| Kbd / KbdGroup | `ui/kbd.tsx` (29) | none | `<kbd>` shell for shortcut labels |
| Card / Alert / Separator / Group | `ui/*.tsx` | none | |
| Sidebar | `ui/sidebar.tsx` (1001) | sheet + tooltip composed | Full resizable persisted shell |

### 5.5 Patterns to copy verbatim

**P24 · Pre-React inline theme bootstrap.** `index.html:14-37`. The single most important UI pattern in the codebase.

**P25 · Tailwind 4 `@theme inline` token bridge.** `index.css:7-46`. Drop into every Helioy product, swap palette and font.

**P26 · OKLCH primary + neutral-grounded surfaces.** `--primary: oklch(0.488 0.217 264)` light / `oklch(0.588 0.217 264)` dark. `--background: color-mix(in srgb, var(--color-neutral-950) 95%, var(--color-white))` in dark. The slight white-tint on near-black is unusually pleasant. Copy the formula, pick the hue.

**P27 · Single `--radius` knob with derived scale.** `index.css:34-39`. One value, six derived. One knob to recalibrate the whole product.

**P28 · base-ui `data-starting-style` / `data-ending-style` motion contract.** No `framer-motion`. CSS transitions + base-ui state attributes. Includes nested-dialog scale via `--nested-dialogs` counter (`dialog.tsx:67`).

**P29 · Resizable persisted sidebar with `shouldAcceptWidth`.** `sidebar.tsx:400-558` + `AppSidebarLayout.tsx:62-67`. Pointer-based resize, RAF-throttled, with a predicate callback that enforces min content width. localStorage backed. **Adopt for all three Helioy surfaces.**

**P30 · `KeybindingShortcut` + `KeybindingWhenNode` AST.** `apps/web/src/keybindings.ts:119-209` + `packages/contracts/src/keybindings.ts`. Resolver evaluates a parsed `when` AST (`identifier|not|and|or`). Conflict-key dedup. `mod`-key cross-platform aliasing. Last-rule-wins precedence. Formatter emits macOS symbol glyphs (⌃⌥⇧⌘). **The keyboard-UX contract everything else builds on.**

**P31 · Stacked toast manager + AnchoredToastProvider pair.** `ui/toast.tsx`. Two managers — one viewport-stacked (iOS-notification style, peek heights via `--toast-peek`, swipe-aware), one anchored to a trigger. Both reuse `ToastBodyContent`. Expandable details + "Copy error" + line-clamp pattern (lines 114-247) is what an agent app needs.

**P32 · `Empty` component with stacked icon cards.** `ui/empty.tsx:43-76`. `variant="icon"` renders three offset cards (10° rotation each direction + center). Excellent empty-state visual without illustrations.

**P33 · `scrollFade` mask on ScrollArea.** `scroll-area.tsx:30-31`. `mask-t-from-[calc(100%-min(var(--fade-size),var(--scroll-area-overflow-y-start)))]` fades only when content overflows that edge. Base-ui exposes the overflow-distance var. Tailwind's mask utilities consume it. Tiny and gorgeous.

**P34 · `data-slot` on every primitive.** Container queries via attribute selectors. Zero JS context.

**P35 · `useRender` + `mergeProps` from base-ui.** `button.tsx:67-71`. Replaces Radix `asChild`. `<DialogClose render={<Button variant="ghost" />}>` without prop drilling.

### 5.6 Patterns to skip

`JetBrainsIcons.tsx`, `vscode-icons.ts`, `vscode-icons-manifest.json` — editor/file-type iconography. Custom SVG editor logos in `Icons.tsx` (686 LOC) — GitHub/GitLab/Jujutsu/JetBrains/Cursor brand glyphs. Use `lucide-react` for everything generic; vendor SVGs only when shipping integrations. `xterm.js` and `ThreadTerminalDrawer` — agent-IDE chrome. `Lexical` editor wrapper (`ComposerPromptEditor`) — heavy editor stack; adopt only for rich composers with mentions and slash commands. `provider-update-pill-countdown` and `ultrathink-*` animations — workspace-IDE flavour. Tailwind `wco` variant — only with Electron Window Controls Overlay.

## 6. Patterns to copy verbatim, consolidated

Thirty-five numbered patterns across four layers. Treat as a checklist.

**Electron shell** (§2.2): P1 Effect Layer bootstrap • P2 `makeIpcMethod` codec brackets + `satisfies` preload • P3 server-as-child-process with fd3 bootstrap • P4 multi-host port probe • P5 pure reducer + effectful orchestration for cross-process state • P6 tsdown CJS with `noExternal @helioy/*` and debounced restart • P7 stage-then-build packaging.

**Monorepo + contracts** (§3.4): P8 catalog-pinned Effect • P9 schema-only contracts • P10 WS_METHODS + Rpc.make + RpcGroup • P11 branded entity-ID factory • P12 explicit subpath exports, no barrel • P13 client-runtime package shape • P14 dev-runner.ts orchestrator • P15 turbo.json discipline.

**Web client** (§4.4): P16 auth gate via `beforeLoad` on `__root` • P17 ManagedRuntime per session • P18 domain-grouped typed facade • P19 AtomRegistry + RegistryContext • P20 Atom.family for per-entity reactive state • P21 component split (Foo.tsx + Foo.logic.ts + Foo.logic.test.ts) • P22 push per-row state into row objects • P23 `useStore.getState()` inside handlers.

**Design system** (§5.5): P24 pre-React inline theme bootstrap • P25 Tailwind 4 `@theme inline` token bridge • P26 OKLCH primary + neutral-grounded surfaces • P27 single `--radius` knob • P28 base-ui data-starting-style motion • P29 resizable persisted sidebar with `shouldAcceptWidth` • P30 KeybindingShortcut AST • P31 stacked + anchored toast managers • P32 stacked-icon-cards empty state • P33 scrollFade mask • P34 `data-slot` on every primitive • P35 base-ui `useRender` + `mergeProps`.

## 7. Baseline parameters (resolved 2026-05-16)

The twelve open questions were walked through with Stuart on 2026-05-16. Locked answers below. Each one is a load-bearing constraint on the `@helioy/baseline` scaffold.

| # | Question | Decision |
| --- | --- | --- |
| 1 | Schema library across all boundaries | **Effect Schema everywhere.** Contracts, IPC, settings, RPC, persistence, bootstrap. `makeIpcMethod` and `WsRpcGroup` adopted verbatim. |
| 2 | Desktop→server bootstrap channel | **fd3 primary, stdin-JSON fallback.** Baseline supports both via a `--bootstrap-via=fd3\|stdin` flag so JS and Rust runtimes each pick their lane. |
| 3 | Shell topology | **One shell codebase, three packaged identities.** Single `apps/desktop` in baseline. Build script emits three artifacts per platform with their own `productName`, `bundleId`, icon, userData path, and auto-update channel. All three coexist on disk. |
| 4 | Auto-update target | **GitHub Releases per surface.** `electron-updater` GitHub provider out of the box. Static-host migration path preserved (build script knob, not architecture). |
| 5 | Renderer-server transport | **WebSocket + Effect RPC.** `WsRpcGroup` + `WsTransport` + `WsRpcClient` adopted verbatim. One connection per session, `ManagedRuntime` reconstructed on reconnect. |
| 6 | Renderer state model | **Atom-first.** `@effect/atom-react` everywhere. `Atom.family` for per-entity, `Atom.keepAlive` for lifecycle. No Zustand in baseline. Domain state composes via atoms inside the Effect runtime. |
| 7 | Backend topology | **Single backend with `EnvironmentConnection` seam.** Ship one local backend per surface; pass `EnvironmentConnection` value into `client-runtime` and components from day 1. Federation later swaps a constant for a `Map<EnvironmentId, EnvironmentConnection>` with zero call-site churn. |
| 8 | Routing model | **File-based via TanStack Router plugin.** `routeTree.gen.ts` codegen. New routes by adding files under `apps/web/src/routes/`. |
| 9 | React Compiler | **On in dev and CI.** Production-like dev. Build cost accepted. |
| 10 | Patch tolerance | **Effect 4.0 beta + patches now.** Pin `effect@4.0.0-beta.x` and `@effect/atom-react@4.0.0-beta.x` in catalog. Carry the local `patchedDependencies` like t3code. Refresh on upstream releases. |
| 11a | Primary hue | **One shared Helioy primary.** All three surfaces use the same `--primary` token. Per-surface distinction via chrome, icon, layout, not hue. |
| 11b | Font stack | **Geist, vendored.** Geist Sans + Geist Mono. Self-hosted. No Google Fonts preconnect. Variable font. |
| 11c | Icon set | **Lucide everywhere.** `lucide-react` as the foundation. Brand SVGs added case-by-case in `assets/` only when shipping integrations. |
| 12 | Status bar primitive | **Both Header and StatusBar.** Baseline ships `<Header>` + `<HeaderItem>` (top axis: tabs, breadcrumbs, actions) and `<StatusBar>` + `<StatusBarItem>` + `<StatusBarSeparator>` + `<StatusBarPriority>` (bottom axis: ambient state). Each surface registers items via slots. Common slots (backend health, environment, version, error) handled at baseline. |

### Implications for §1 blueprint

Three constraints tighten the blueprint in §1.

- The `apps/desktop` build script must accept a surface argument (`--surface=transport-matters|runtime-matters|littleorgans`) and parameterise `productName`, `bundleId`, icon path, userData, and `publishConfig.repo` from a per-surface manifest. Resolution from Q3 + Q4.
- The renderer no longer carries Zustand. `apps/web/src/store.ts` and `uiStateStore.ts` from t3code are not lifted; per-domain atoms in `apps/web/src/state/` replace them. Resolution from Q6.
- The baseline's `apps/web/src/components/ui/` adds `header.tsx` and `status-bar.tsx`, neither of which exists in t3code. Resolution from Q12.

### Implications for §6 pattern checklist

Three patterns are now non-optional, not optional: P2 (`makeIpcMethod`), P10 (`WS_METHODS` + `Rpc.make` + `RpcGroup`), P19 (`AtomRegistry` via `RegistryContext`). They flow directly from Q1, Q5, Q6.

Two patterns are dropped from the baseline (still inspirational, not lifted): the `EnvironmentConnection` registry as a full `Map<>` (Q7 single-with-seam), and any Zustand pattern from §4 (Q6 atom-first).

One pattern is added that has no t3code source: the dual-axis `Header` + `StatusBar` primitive (Q12). Designed fresh in baseline.

## 8. Application to the three Helioy surfaces

**`transport-matters` (immediate, has existing context — Manicure v2)**: lift the trinity (§5.1) first. The cm record `repo:transport-matters` shows existing canvas/react-flow work. Adding the Helioy `ui/` primitives, the pre-React theme bootstrap, and the resizable sidebar layout buys visual coherence without disturbing the React Flow surface. Defer Electron shell until Manicure v2 stabilises. Likely web-first.

**`runtime-matters` (next)**: this is the strongest candidate for the full three-app baseline. The runtime is the *brain*; a desktop shell with fd3-bootstrapped child process maps directly onto how runtime-matters spawns and supervises. Lift §2.2 (P1–P7) end to end. The contract spine in §3 is essential because runtime-matters is the most schema-heavy of the three. Confirm transport (WS vs HTTP+SSE) before adopting `WsRpcClient`.

**`littleorgans` (parallel app)**: per the Helioy thesis, the Little Organs *are* the cognitive components. The "app" is the dashboard that observes/operates them. Lift the design system (§5) and the renderer-server seam (§4.2). The Electron shell is optional — littleorgans might ship web-only for now. The `Atom.family` per-entity pattern (P20) is the natural primitive for "one observable per organ".

Suggested order: lift §5 design tokens into a shared `@helioy/design` package first (cross-cutting, low risk), then use it in `transport-matters` to validate. In parallel, set up the three-app skeleton for `runtime-matters` end to end (§1–4). Use `littleorgans` to validate that `packages/client-runtime` actually generalises across products.

## 9. Next steps

1. Decide the twelve open questions (§7). Some are one-line answers (Effect Schema yes/no, file-based routing yes/no).
2. Stand up `@helioy/baseline` as a real scaffold repo. Three apps + three packages, empty handlers, working dev loop, working `dist:desktop:*` chain, ten tokens, ten primitives. Smallest end-to-end thing that compiles and packages.
3. Use `transport-matters` as the first consumer. Lift §5 tokens + primitives. Keep React Flow. Validate that the design layer is cleanly separable from the host app.
4. Bootstrap `runtime-matters` as a green-field consumer of the full baseline. This is where every pattern earns its place.
5. Bring `littleorgans` online as the third consumer. If the baseline is right, it should require zero patches.
6. Promote any pattern that needed adjustment across products into a refined baseline. Repeat.

Two checkpoints worth honouring: **every new file ≤700 LOC** (t3code's `store.ts`/`service.ts`/`sidebar.tsx` are the cautionary tales), and **`client-runtime` stays framework-free**. The minute renderer-state primitives depend on React, the second consumer of the baseline starts to bleed.

## Appendix: source map

- Branch: `review/pingdotgg-main`, head `d1e85c4e chore(release): prepare v0.0.24`
- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/t3code`
- Upstream: `https://github.com/pingdotgg/t3code`
- Prior eval (still partially valid): `~/.mdx/research/t3code-product-evaluation.md`
- Research method: four parallel `helioy-tools:codebase-analyst` agents covering Electron shell, monorepo+contracts, web architecture, design system. All agents used the fmm-indexed codebase + Read/Glob.
