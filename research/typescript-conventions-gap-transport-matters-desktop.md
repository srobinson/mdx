---
title: "Desktop shell migration gap audit: transport-matters Electron → littleorgans Tauri 2.x greenfield"
type: research
tags: [tauri, electron, desktop-shell, littleorgans, transport-matters, migration, typescript-conventions, moon, cargo-dist, webview, codesigning]
summary: "Electron capability inventory mapped to Tauri 2.x, renderer TS-conventions audit, a P0-P2 greenfield punch list, two concrete validation-gate plans, and a fallback path. Null hypothesis = Tauri."
status: active
source: codebase-analyst
confidence: high
created: 2026-05-30
updated: 2026-05-30
related:
  - "electron-vs-tauri-2026.md"
  - "electron-vs-tauri-2026-codex-review.md"
  - "typescript-conventions-2026.md"
  - "helioy-electron-baseline.md"
---

# Desktop shell migration gap audit: transport-matters Electron → littleorgans Tauri 2.x greenfield

## Executive summary

`littleorgans/littleorgans/apps/` is an empty stub (one `README.md`). The desktop shell does not exist yet, so this is a **greenfield build**, not a migration. The settled framing (MoE: `electron-vs-tauri-2026-codex-review.md`) is **build Tauri 2.x as a Rust crate** inside the existing Cargo + Moon + cargo-dist toolchain; treat `transport-matters/desktop/` as a legacy reference implementation and risk/pattern source, not the permanent shell.

The Electron shell is genuinely thin: ~600 LOC across 9 source files, a 15-line preload, no tray, no menu, no auto-update wired, no codesigning configured. Its entire job is **spawn a backend → HTTP-poll `/health` → load the web app over loopback**. That supervision job duplicates what `lilo` runtime/session daemon crates already own (verified below), so most of it should be deleted-and-delegated, not ported. The portable renderer (`transport-matters/www/`, 127 ts/tsx files) is clean web tech that carries over to the Tauri webview largely intact: **23 COMPLIES vs 6 GAP** against the TS guide, and zero of the gaps are blockers.

The two hard tails are unchanged from the decision doc: **(1) tri-webview render consistency** (WKWebView/WebView2/WebKitGTK) for the Geist/OKLCH/base-ui design system, and **(2) macOS notarization + Windows codesigning** reconciled with cargo-dist. Both are formalized as run-it validation gates below.

## Project metadata

| Surface | Stack | Evidence |
|---|---|---|
| Electron shell | `electron ^39.2.6`, `@electron/packager ^19`, TS 5.9.3, Vitest 4, pnpm 10.8.1, ESM, NodeNext | `transport-matters/desktop/package.json` |
| Renderer (`www/`) | React 19.2 + Vite 8 + Tailwind 4 + Zustand 5 + TanStack Query/Virtual, Biome 2.4, Playwright (chromium/firefox/webkit/visual) | `www/package.json`, `www/playwright.config.ts` |
| Target monorepo | Rust workspace, `resolver = "3"`, edition 2024, `rust-version 1.95`, v0.8.0, 25 members all `lilo-*`, tokio/sqlx/serde, cargo-dist 0.31 (6 triples), Moon gate `fmt→clippy→check-loc→build→test` | `littleorgans/Cargo.toml`, `moon.yml`, `.moon/toolchains.yml` |
| Tauri target | Tauri 2.9.6 (Dec 2025), updater covers NSIS/MSI/AppImage/.app incl. Linux | v2.tauri.app, web 2026-05-30 |

`.moon/toolchains.yml` declares only `rust: 1.95`; Node and Python toolchains are commented out ("Reserved until TypeScript workspace files are introduced"). A Tauri shell needs **both** toolchains uncommented: Rust for the crate, Node for the renderer build.

---

# Part A — Electron capability inventory → Tauri 2.x mapping

Each row: what Electron does today (file:line) → Tauri 2.x equivalent (verified against v2.tauri.app, 2026-05) → RISK / EFFORT.

### A1. Main-process lifecycle and window host

| Capability | Today (evidence) | Tauri 2.x equivalent | Risk / Effort |
|---|---|---|---|
| App lifecycle (`whenReady`, `activate`, `window-all-closed`, macOS dock behavior) | `desktop/src/main.ts:158-186` `registerAppLifecycle` | `tauri::Builder::default().setup(...)` + `RunEvent` handlers; macOS reopen via `RunEvent::Reopen` | Low / Low |
| Window creation + options (1280×900, min 900×600, deferred show) | `desktop/src/window.ts:17-52` `createWindowOptions`, `createHostedWindow` | `WebviewWindowBuilder` or `tauri.conf.json` `app.windows[]` (inner_size/min_inner_size/visible:false) | Low / Low |
| `ready-to-show` deferred paint | `window.ts:46-48` | `show: false` + `window.show()` after first paint, or `visible` config | Low / Low |
| Quit-time backend cleanup | `main.ts:136-147` `bindBackendQuitCleanup` | **Delete — delegate to core** (see A6) | Low / Low |
| Startup-failure dialog | `main.ts:149-156` `showBackendStartupFailure` via `dialog.showErrorBox` | `tauri-plugin-dialog` `message`/`MessageDialogBuilder` | Low / Low |

### A2. Backend process supervision (the bulk of the shell)

| Capability | Today (evidence) | Tauri 2.x equivalent | Risk / Effort |
|---|---|---|---|
| Spawn backend child (`transport-matters <client> <ws> --web-port --proxy-port`) | `backendProcess.ts:65-102` `buildBackendLaunch`/`launchBackendProcess` | **Do not port.** lilo runtime daemon already owns spawn (see A6). Otherwise: `tauri-plugin-shell` sidecar / `tauri::async_runtime` `Command` | Medium / Medium (delegation) |
| Health poll `GET /health` until ok or 15s timeout | `backendHealth.ts:33-50` `waitForBackendHealth` | Native Rust `reqwest`/`hyper` poll loop, or read a readiness event from `lilod` | Low / Low |
| Exit-before-ready race watcher | `backendProcess.ts:111-134` `watchBackendExitBeforeReady` | `tokio::select!` over health vs child-exit; or subscribe to runtime lifecycle events | Low / Low |
| Graceful stop (`SIGTERM`) | `backendProcess.ts:104-109` `stopBackendProcess` | Delegate to runtime daemon stop verb; never re-implement signal handling in the shell | Low / Low |
| Port/client env resolution + validation | `main.ts:76-87,231-257` `resolveBackendStartupOptions`/`resolvePort` | Rust config parse (serde + clap-style validation) in the shell crate | Low / Low |

### A3. IPC surface and preload bridge

| Capability | Today (evidence) | Tauri 2.x equivalent | Risk / Effort |
|---|---|---|---|
| Preload context-bridge — exposes only `{ appName: "Transport Matters" }` | `preload.ts:1-15` (15 LOC, `contextBridge.exposeInMainWorld`) | Trivial: a single `#[tauri::command] fn app_name()` or a static injected by the webview. The IPC surface is **near-empty today** | Low / Low |
| Renderer↔backend data path: **HTTP `fetch` + SSE**, not Electron IPC | `www/src/api.ts:27-57` `apiUrl`/`createApiTransport`/`setApiTransport`; `www/src/hooks/useExchangeStream.ts:35` `new EventSource` | **Key insight:** the renderer never used Electron IPC for data. It talks to a loopback HTTP server. Under Tauri it can keep HTTP (`lilod` exposes a local port) OR move to `tauri::ipc` commands + `tauri-specta` `bindings.ts`. The `createApiTransport`/`apiUrl`/`setApiTransport` seam is the single swap point | Medium / Medium |
| Typed contract source of truth | hand-written `www/src/types.ts` (586 LOC) | If keeping HTTP: generate DTOs from Rust via **ts-rs** (per TS guide §Rust-Generated). If moving to IPC: **tauri-specta** generates `bindings.ts` from `#[specta::specta]` commands | Medium / Medium |

The preload bridge is a non-event. The real contract is the HTTP/SSE API, and it is cleanly abstracted behind one injectable transport. This is why the decision doc calls renderer migration "near-free."

### A4. Native / OS integrations, window navigation policy

| Capability | Today (evidence) | Tauri 2.x equivalent | Risk / Effort |
|---|---|---|---|
| Navigation hardening (block off-origin `will-navigate`) | `window.ts:54-91` `registerHostedWindowPolicy` | Tauri CSP + capabilities ACL (`dangerous-remote-domain` off by default); `on_navigation` callback in `WebviewWindowBuilder` | Low / Low |
| Open external `https:` in OS browser, deny in-app | `window.ts:61-91` `shell.openExternal` + `setWindowOpenHandler` deny | `tauri-plugin-opener` (`open_url`), default-deny new windows | Low / Low |
| `did-fail-load` error surface | `window.ts:66-74,93-100` `showHostedLoadFailure` | `on_page_load` / navigation error + dialog plugin | Low / Low |
| Tray icon | **none** | `TrayIconBuilder` if needed | N/A / — |
| Native menu | **none** (no `Menu.setApplicationMenu`) | `tauri::menu` (v2 closed the historic context-menu gap) | N/A / Low |
| Sandbox / contextIsolation | `window.ts:27-32` `sandbox:true, contextIsolation:true, nodeIntegration:false` | Tauri is sandboxed-by-default (no Node in webview); capability ACL replaces the manual checklist | Low (improves) / — |

### A5. Auto-update, build, codesigning, notarization, packaging — the hard tail

| Capability | Today (evidence) | Tauri 2.x equivalent | Risk / Effort |
|---|---|---|---|
| Auto-update | **NOT WIRED** (no `electron-updater`, no `autoUpdater` anywhere; baseline Q4 planned it) | `tauri-plugin-updater` — covers NSIS/MSI/AppImage/.app **including Linux** (gain over electron-updater's mac/win-only). Requires a minisign signature on every artifact; cannot be disabled | Medium / Medium |
| Packaging | `@electron/packager` smoke only (`package:smoke` script, `main.ts:188-216` `registerDesktopPackageSmoke`); no production installer | `tauri bundle` → `.app`/`.dmg`, `.msi`/NSIS, `.AppImage`/`.deb`. Windows = `.exe`/`.msi` only (no `.appx`/Store) | Medium / Medium |
| macOS codesign + **notarization** | **none configured** | `tauri.conf.json` `bundle.macOS` (signingIdentity, hardenedRuntime, provider short-name); Apple notarization via `tauri-action`/cargo-dist. Universal-binary double-signing is the known bug class (DoltHub) | **HIGH / High** |
| Windows codesign | **none configured** | EV/OV cert + `signCommand`; reconcile with cargo-dist | **HIGH / High** |
| Distribution pipeline | desktop has its own `justfile`; renderer has cargo-dist-independent `release.sh` | Fold into littleorgans `cargo-dist` (0.31, 6 triples) + `release-plz`. Tauri bundle vs cargo-dist installer reconciliation is unproven | **HIGH / High** (= Gate G2) |
| Tri-webview render consistency | renderer already runs a webkit Playwright project (`playwright.config.ts:29`) but **ships** on Chromium | Validate the design system on real WKWebView/WebView2/WebKitGTK | **HIGH / High** (= Gate G1) |

### A6. lilo-* delegation overlaps (do not port — delegate to core)

Verified by reading `littleorgans/internal/runtime/` and `internal/session/daemon/`:

- **Process spawn + preflight**: `internal/runtime/daemon/src/{backend.rs, spawn_preflight.rs, docker_preflight.rs, shim_socket.rs}` and `internal/runtime/launchers/src/lib.rs` already own process launch, shim wiring, and lifecycle. The Electron app's `backendProcess.ts` (spawn/kill/exit-watch) **duplicates this**. Do not port; the Tauri shell should ask the runtime daemon to spawn.
- **Socket/composition boundary**: `internal/session/daemon/src/{server.rs, service.rs}` is the `lilod` composition root behind the local socket (CLAUDE.md: "after Phase 7, `lilod` is the composed daemon behind the local socket"). The shell connects to that socket; it does not stand up its own supervisor.
- **Health/readiness + lifecycle events**: runtime daemon emits lifecycle events and raw status (CLAUDE.md "Runtime owns ... lifecycle events, and raw runtime status"). The shell's `waitForBackendHealth` HTTP poll should become a subscription to those events, or a thin readiness check against `lilod`.
- **Net**: `backendProcess.ts` + `backendHealth.ts` + the quit-cleanup binding (≈250 LOC of the 600) are **delete-and-delegate**, not port. This makes the Tauri shell thinner than a naive port suggests: window host + navigation policy + a readiness wait, under ~200 LOC Rust.

---

# Part B — Renderer TS-conventions audit (`transport-matters/www/`)

Audited against `typescript-conventions-2026.md`, section by section. This code carries over to the Tauri webview unchanged, so the audit is the carry-over readiness check. 127 ts/tsx files, 48 test files, all source files under the 700-LOC cap (largest non-test source `types.ts` 586, `SamplingRows.tsx` 472).

| TS guide section | Verdict | Evidence |
|---|---|---|
| Project shape (apps under `apps/`, kebab names, scoped) | **N/A** | Standalone Vite app today; folds under `littleorgans/apps/` at migration. `"private": true` correct (`www/package.json:3`) |
| pnpm workspaces / catalogs / Moon | **GAP** | Single-package `pnpm-workspace.yaml`; no catalog, no Moon project, no `catalogMode: strict`. Versions pinned inline. Must adopt catalogs + a Moon project on migration |
| Package manifest & exports | **N/A / COMPLIES** | App not a library: no `exports` map needed; `"type": "module"` set (`package.json:5`). `engines.node ">=20.19.0"` is below the guide's `>=24` (minor GAP) |
| tsconfig strictness baseline | **GAP (partial)** | `strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `isolatedModules`, `verbatimModuleSyntax`, `moduleResolution: bundler` all set (`tsconfig.app.json:12-21`). **Missing `exactOptionalPropertyTypes`** (guide non-negotiable). `target ES2022` vs guide `es2023` (cosmetic) |
| TS version / ESM-only | **COMPLIES** | TS 5.9.3; ESM throughout; `verbatimModuleSyntax` enforced |
| Modules and files | **COMPLIES** | Named exports only — **zero `export default`** found; **zero barrel `index.ts`** found; one cohesive responsibility per module |
| API & type design | **COMPLIES (mostly)** | **Zero explicit `any`** in non-test source. Hand-written discriminated unions in `types.ts` (e.g. `CodexEventSource` literal union, `types.ts:171`). No branded types for ids (minor) |
| Runtime validation & schema | **GAP** | **No schema validation library** (no Zod/Valibot/Effect Schema). External SSE/HTTP payloads are cast, not parsed: `as Record<string, unknown>` in `hooks/exchangeStreamEvents.ts:85,133,297`; `as unknown as InternalRequest` in `components/detail/InspectTab.tsx:250-251`. Boundary input is trusted. This is the **most material renderer gap** |
| Rust-generated TS types | **GAP** | `types.ts` (586 LOC) is hand-written and will drift from the Rust wire source. Guide mandates ts-rs generation for wire-facing DTOs. Today there is no Rust producer; under littleorgans there will be |
| Error handling | **GAP (acceptable)** | Plain `throw new Error(...)` at the API edge (`api.ts:59-68,83,100`), not `neverthrow`/Effect typed `Result`. Consistent within the package, converted at the edge — tolerable, but not the guide's typed-error bar |
| Async & concurrency | **COMPLIES** | `AbortController`/`AbortSignal` wired through health + SSE (`backendHealth.ts:56-63`; renderer hooks). TanStack Query owns fetch concurrency. No unbounded `Promise.all` fan-out seen |
| Dependencies | **COMPLIES** | All ESM-native, ship own types, lean set (react, zustand, tanstack, diff). No CJS-only deps |
| Logging & diagnostics | **COMPLIES (small)** | One `import.meta.env.DEV`-gated path (`components/exchangeListRows.ts:75`); no scattered `console.*` in library code |
| Lints & formatting | **COMPLIES (one weakening)** | Biome 2.4 single tool, CI-gated (`package.json:26` `ci` script). But `noExplicitAny` is `warn` not `error`, and `noNonNullAssertion`/`noUnusedVariables` are `warn` (`biome.json:33-38`). Guide wants `no-explicit-any` enforced |
| Type-safety escape hatches | **COMPLIES (mostly)** | 21 `as` casts, most narrow/justified; `as unknown as T` confined to test setup + two boundary reads (`InspectTab.tsx:250-251`). No `@ts-ignore`/`@ts-nocheck`. The boundary `as unknown as` pairs with the schema GAP — fix both together |
| Testing | **COMPLIES** | Vitest + Testing Library, 48 `*.test.*` colocated, dedicated `tsconfig.test.json` equivalent (`tsconfig.node.json`), Playwright tri-browser + visual-regression matrix (`playwright.config.ts:25-33`). Boundary/error cases covered (e.g. `useExchangeStream.validation.test.tsx`) |
| Documentation | **N/A** | App, not a published library |
| Build & bundling | **COMPLIES** | Vite 8 for the app; `tsc -b --noEmit` as a separate type gate (`package.json:25`); project references via `tsconfig.json` (`tsconfig.app`/`tsconfig.node`) |
| CI | **GAP** | Has a `ci` script but no Moon affected-runs, no changesets, no `--frozen-lockfile` gate, no Rust-type drift check. Adopt on migration |
| Performance | **COMPLIES** | ESM, no deep barrels, `import type` used heavily (90 type-only import lines across 81 files), TanStack Virtual for large lists |
| Metaprogramming | **COMPLIES** | No decorators, no runtime `Proxy` reflection |

**Tally: 23 COMPLIES (incl. mostly/small) · 6 GAP · 4 N/A.** The 6 gaps: (1) no pnpm catalog/Moon wiring, (2) missing `exactOptionalPropertyTypes`, (3) no boundary schema validation, (4) hand-written wire types (no ts-rs), (5) `throw` instead of typed `Result`, (6) no Moon/changesets/drift CI. **None blocks carry-over** — they are quality upgrades to apply during the migration, not defects that stop the renderer running in a Tauri webview. Gaps (3) and (4) are the two worth doing deliberately because they intersect the Rust boundary.

---

# Greenfield punch list — stand up `littleorgans/apps/<shell>` as a Tauri Cargo+Moon member

### P0 — make the shell exist and compile in the workspace

1. **Uncomment `node` (and keep `rust`) in `.moon/toolchains.yml`.** A Tauri app needs Rust for the crate and Node for the renderer build. This is the gate that currently blocks any TS-in-monorepo work.
2. **Add the shell crate to `Cargo.toml` `members`** (e.g. `apps/lilo-desktop`) and a `[workspace.dependencies]` entry; wire a `tauri::Builder` window host. Keep each file < 700 LOC, functions < 150 (CLAUDE.md hard limits; `check-loc-limit.sh` enforces mechanically).
3. **Add a `moon.yml` for the shell** inheriting the Rust task chain (`fmt-check→clippy→check-loc→build→test`) so it lands in `moon ci` and the existing gate.
4. **Port the renderer into `apps/<shell>/` (or `packages/-ui`)** as the Vite build target; point Tauri `frontendDist` at the Vite output. Renderer code is unchanged.
5. **Delete-and-delegate the supervisor**: do NOT port `backendProcess.ts`/`backendHealth.ts`/quit-cleanup. Connect to the `lilod` socket / runtime daemon for spawn + readiness (Part A6).

### P1 — contract and convention hardening

6. **Pick the renderer↔core contract**: keep loopback HTTP (lilod serves a port) OR adopt `tauri::ipc` + `tauri-specta`. Either way, swap is isolated to `createApiTransport`/`apiUrl` (`api.ts:27-57`).
7. **Generate wire DTOs from Rust** (ts-rs default) to retire the 586-LOC hand-written `types.ts` and add a CI drift check (`git diff --exit-code` on the generated dir).
8. **Add boundary schema parsing** for SSE/HTTP payloads (Zod v4 or, if the contract is generated, parse-on-decode) to remove the `as unknown as` reads in `exchangeStreamEvents.ts`/`InspectTab.tsx`.
9. **Close the tsconfig gap**: add `exactOptionalPropertyTypes`; bump `target` to `es2023`, `engines.node` to `>=24`. Promote Biome `noExplicitAny` to `error`.
10. **Adopt pnpm catalogs (`catalogMode: strict`) + Moon project sync + changesets**; CI installs `--frozen-lockfile`.

### P2 — distribution and polish

11. **Wire `tauri-plugin-updater`** (gains Linux) against GitHub Releases; reconcile signatures with cargo-dist (= Gate G2 output).
12. **Native menu/tray only if a need appears** (none today).
13. **Migrate `transport-matters/desktop`'s DI-and-unit-test discipline** into the Rust shell crate's tests (the Electron app's strongest pattern worth keeping).

---

# Validation-gate test plans (concrete)

### Gate G1 — tri-webview render parity for the design system

**Hypothesis to falsify:** the Geist/OKLCH/base-ui design system renders acceptably identically across WKWebView (macOS), WebView2 (Windows), WebKitGTK (Linux).

**Plan:**
1. Build a minimal Tauri shell pointing at a frozen build of `www/` (or a design-token storybook page covering: OKLCH color tokens, Geist font rendering, base-ui primitives, CSS grid/flex layouts, the virtualized list).
2. Capture screenshots of the same routes inside the **real** three webviews (not Playwright browser engines): macOS `.app` on WKWebView, Windows `.msi` on WebView2, Linux `.AppImage` on WebKitGTK.
3. Compare against the Chromium baseline at `maxDiffPixelRatio` ≤ 0.01 (reuse the existing visual-regression tolerance, `playwright.config.ts:20-24`). Extend the existing webkit Playwright project (`playwright.config.ts:29`) as the standing canary.
4. **Pass:** WebKitGTK is the long pole; if OKLCH, Geist subpixel, and base-ui focus-ring render within tolerance on WebKitGTK, G1 passes. **Fail:** any token/layout class diverges beyond tolerance with no CSS-var fallback.

**Pass criterion (one line):** the design system renders within `maxDiffPixelRatio ≤ 0.01` on real WKWebView + WebView2 + WebKitGTK, WebKitGTK being decisive.

### Gate G2 — migration-cost / signing-and-packaging parity with cargo-dist

**Hypothesis to falsify:** `tauri bundle` + signing reconciles cleanly with the existing `cargo-dist` 0.31 / `release-plz` pipeline across the 6 target triples, at a cost no worse than the Electron path.

**Plan:**
1. Produce a signed, notarized macOS `.app`/`.dmg` (universal binary — exercise the DoltHub double-signing bug class), a signed Windows `.msi`/NSIS, and a Linux `.AppImage` from the Tauri shell crate.
2. Drive it through cargo-dist's release flow (or document the exact reconciliation if Tauri bundle must run alongside cargo-dist) for `x86_64`/`aarch64` × {darwin, windows, linux}.
3. Wire `tauri-plugin-updater` end to end: build → sign → publish to GitHub Releases → in-app update applies on all three OSes.
4. Time the full path and compare to the Electron-align baseline (Fallback below).

**Pass criterion (one line):** a signed+notarized mac universal binary, a signed Windows installer, and a Linux AppImage all build, ship via cargo-dist, and self-update through `tauri-plugin-updater`, at cost ≤ the Electron path.

---

# Fallback — if a gate fails, the minimal Electron-align path

The decision doc keeps Electron as a fallback only if a gate fails. The minimal Electron-align effort, given how thin the existing shell is:

- **If G1 fails (webview divergence):** lift `transport-matters/desktop/` into `littleorgans/apps/desktop` as an Electron `apps/desktop` per the locked baseline Q3. The renderer is identical either way (web tech). Add the Node toolchain to Moon but **not** as a Cargo member; the shell stays a JS island beside the Rust chassis. Wire `electron-updater` (Q4) for mac/win; Linux relies on cargo-dist's package output. Still delete-and-delegate the supervisor to lilo runtime crates (Part A6) regardless of shell.
- **If G2 fails (signing/packaging):** Electron's `electron-builder`/notarization path is a decade-proven escape hatch; adopt it for distribution while keeping evaluating Tauri.
- **Cost of fallback:** low. The shell is ~600 LOC and ~250 of it is delete-and-delegate. Per-surface shell tech is explicitly acceptable (decision doc): transport-matters Electron and littleorgans Tauri can coexist; the fallback just keeps littleorgans on Electron too.

---

# Operator decisions needed

1. **When does the `apps/` phase activate?** The whole punch list waits on it; the webview landscape moves, so re-confirm the decision doc at activation.
2. **Renderer↔core contract**: keep loopback HTTP (lilod serves a port, minimal renderer change) OR move to `tauri::ipc` + tauri-specta (more idiomatic, deletes the HTTP hop but changes the renderer's import surface)? This is the one real architectural fork.
3. **Single shared shell vs per-surface shell tech**: the baseline assumed one shell; this audit and the decision doc propose relaxing to per-runtime-family. Stuart owns that call.
4. **Codesigning identities**: Apple Developer ID + notarization credentials and a Windows code-signing cert are prerequisites for G2 and are procurement/operator items, not engineering ones.

---

## Open questions

- Does `lilod` expose (or plan to expose) a local HTTP port the renderer can keep hitting, or is the only local surface the Unix socket? That decides whether the renderer's HTTP transport survives unchanged or must move to IPC.
- Is the `transport-matters` backend binary itself going to be absorbed into `lilo` (the K8s-model says transport-matters stays external observability), or does the littleorgans desktop shell front a different core? If transport-matters stays external, the littleorgans shell's "backend" is `lilod`, not `transport-matters`, and the spawn contract differs.

Sources: [Tauri Updater plugin](https://v2.tauri.app/plugin/updater/), [Tauri AppImage distribution](https://v2.tauri.app/distribute/appimage/), [Tauri 2.0 stable release](https://v2.tauri.app/blog/tauri-20/), [Tauri config reference](https://v2.tauri.app/reference/config/).
