---
title: Plan — t3code P1 Slice D1, wheel-packaging the gateway (mapping + decomposition)
type: projects
tags: [transport-matters, t3code, p1, slice-d1, scout, plan, packaging, wheel, node, node-pty, windows]
summary: 'Maps the packaged-gateway problem first-hand on main @ 81cca42 and decomposes it. KEY FINDINGS that reshape the brief — (1) node-pty 1.2.0-beta.14 SHIPS N-API prebuilds for all six platforms inside the npm package and its loader explicitly supports the bundled layout (prebuilds/ beside the bundle), so there is no prebuild pipeline to build and no Electron-rebuild trap; (2) pg is pure JS, so node-pty is the ONLY native dep in the gateway graph; (3) the wheel can therefore stay py3-none-any (bundle + all-platform prebuilds ride the existing hatch artifacts precedent) — no per-platform wheel matrix, which matters with CI billing down. The real build work is D1-b: Python has NO gateway launcher today (desktop-only spawn); web mode serves the D2 503 stub. Decomposition D1-a → D1-b → D1-c, with 5b/Windows kept as its own deferred slice. Stuart decisions: D1-node (recommend execPath-as-node for desktop + system-node-with-doctor for web, optional [node] extra via nodejs-wheel-binaries) and D1-win (defer 5b).'
status: active
source: scout (fable 5:2.1), first-hand on main @ 81cca42; nodejs-wheel-binaries verified on PyPI
confidence: high
created: 2026-07-08
---

# Plan — Slice D1: package the gateway into the wheel (mapping + decomposition)

Everything below read first-hand on main @ 81cca42 unless marked external.

---

## 1. The bundle-embed precedent (brief §1) — reuse this, invent nothing

The two SPA bundles already ride a complete build→embed→serve pipeline:

- **Build**: `www/vite.shared.ts::productViteConfig` anchors vite `outDir` to the
  workspace root → `api/src/transport_matters/{www,canvas}`. Version stamped from
  git describe / `TRANSPORT_MATTERS_VERSION` (same source hatch-vcs uses).
- **Embed**: `api/pyproject.toml` `[tool.hatch.build.targets.wheel]` `artifacts`
  globs (`src/transport_matters/www/**`, `.../canvas/**`, plus
  `channel-specs.json`, `settings.example.toml`, `migrations/**`).
- **Gate**: `api/justfile::build` runs `uv build` then greps the wheel listing and
  prints `✓ www/ bundle embedded` / `! NOT in wheel` guidance. Root
  `justfile::build` and `install-local` order the frontend builds before
  `uv build` / `uv tool install`.
- **Serve/degrade**: `main.py::mount_frontend_bundles` mounts each dir only
  `if dir.exists()` — a wheel or checkout without bundles degrades instead of
  crashing.

**D1 extension**: a third embedded directory,
`api/src/transport_matters/gateway/` (sibling of `www/` and `canvas/`; no Python
module of that name exists, and the CLAUDE.md "WWW workspace naming" section
gains one line). New `artifacts` glob, same wheel-check echo, same build-order
wiring in root `justfile::build` / `install-local`.

## 2. What must ship (brief §2) — and the two findings that shrink it

### (a) The gateway as a built distributable

Dependency graph of `packages/gateway/src/main.ts` (first-hand from package
manifests): `fastify` (pure JS), `@tm/activity` (`fastify`, **`pg` — pure JS**,
`xstate` — pure JS), `@tm/runtime` (`@fastify/websocket`, **`node-pty` — the
single native dep**), `@tm/common` (nothing). `tsx` is devDependency-only, used
by the `start` script.

Bundle with **esbuild** (already pinned in the lockfile at 0.28.1 as vite's
engine; add as a devDep): `main.ts` → one `main.js` (`--platform=node
--bundle`), with `node-pty` handled per (b). Workspace `@tm/*` TS sources inline
into the bundle — no workspace `node_modules` at runtime, no tsx.

Known bundling risks to test in-slice, with a fallback: fastify's optional/lazy
requires and pino's worker-thread transports (unused — the gateway logs via
console) generally esbuild-bundle fine, but if the bundle fights back, the
fallback is `pnpm deploy --filter @tm/gateway --prod` (a pruned, self-contained
node_modules tree copied into the package dir). Heavier (~tens of MB) but zero
bundler risk. Try esbuild first; the acceptance test (run the built artifact
against a dev Python with a real spawn) decides.

### (b) node-pty native — FINDING: already solved upstream

node-pty `1.2.0-beta.14` (the pinned catalog version) **ships prebuilds inside
the npm package** for all six targets: `prebuilds/{darwin-arm64,darwin-x64,
linux-arm64,linux-x64,win32-arm64,win32-x64}`. Sizes: POSIX ~360KB total;
win32 ~23MB (ConPTY dlls/pdbs). Two properties verified in the installed
package:

- **N-API** (`node-addon-api ^7.1`): ABI-stable across Node versions **and
  Electron** — Node-API addons need no Electron rebuild. The "4e-b trap"
  (NODE_MODULE_VERSION mismatch) applies to node-gyp-versioned builds, which
  this is not.
- **Bundler-aware loader**: `lib/utils.js::loadNativeModule` resolves
  `build/Release` → `build/Debug` → `prebuilds/{platform}-{arch}` relative to
  `..` (unbundled) **then `.` (bundled)** — the comment says "the current dir
  for bundled". So the shipped layout is: `gateway/main.js` +
  `gateway/prebuilds/**` copied verbatim from the installed node-pty package
  (mark `.node` requires external or rely on the runtime require). The
  darwin/linux dirs also carry the `spawn-helper` executable — the copy step
  must preserve the exec bit (wheel packaging preserves modes; verify in the
  wheel-check).

Consequence: **no prebuild-install, no node-gyp at install time, no per-platform
compile step owned by us.** Shipping all six platform dirs keeps the wheel
`py3-none-any` at ~23MB extra (win32 dominates). Option: ship POSIX-only now
(~360KB) and add win32 with the Windows leg — a one-line glob choice, noted as a
default (POSIX-only until D1-d) rather than a Stuart decision.

### (c) A node runtime — the real decision (§3)

## 3. D1-node (Stuart): where does the packaged gateway get node?

Today `gatewayProcess.ts::buildGatewayLaunch` hardcodes `command: "node"` (PATH
lookup), and `GatewayStartupError` already names "Node.js not on PATH" as a
likely cause. Options:

- **(A) Ship a standalone node binary in the wheel.** Works everywhere, but:
  ~45–55MB per platform, forces per-platform wheels (a build matrix we cannot
  run with CI billing down), and makes every Node CVE a wheel release.
  **Variant A′ (verified external)**: depend on
  [`nodejs-wheel-binaries`](https://pypi.org/project/nodejs-wheel-binaries/)
  (njzjz/nodejs-wheel; 24.x, ~8.6M downloads/month) as an **optional extra**
  `transport-matters[node]` — pip resolves the right platform wheel, our wheel
  stays pure, zero matrix on our side. Cost: an unofficial third-party
  dependency in the trust chain.
- **(B) `ELECTRON_RUN_AS_NODE=1` + `process.execPath`.** The desktop always has
  a node — Electron's. With node-pty on N-API prebuilds the ABI objection is
  gone. **Desktop-only** by construction: packaged web mode (the
  `transport-matters` CLI without a desktop) has no Electron.
- **(C) Require a system node.** Zero bloat, wheel stays `py3-none-any`. The
  failure mode already exists as product behaviour: no gateway → the D2 503
  stub + canvas "terminal_unavailable" degrade (s4f D-f1). Needs `doctor` to
  say so plainly.

**Recommendation — hybrid, no single loser:** **B for the desktop** (execPath
as node; free, PATH-independent, N-API-safe) + **C for web mode** (system node,
found via PATH; graceful D2 degrade + a `doctor` check naming the fix) + **A′ as
the opt-in** for batteries-included web (`pip install transport-matters[node]`;
the Python gateway launcher probes the extra before PATH). This keeps ONE
universal wheel, no CI matrix, and every leg verifiable on Stuart's mac today.

## 4. Entry wiring (brief §4) — the seam is ready; the launcher is not

- `desktop/src/gateway/gatewayProcess.ts::resolveGatewayEntry`: env override
  `TRANSPORT_MATTERS_GATEWAY_ENTRY` wins (stat-checked), else walk up to
  `pnpm-workspace.yaml` and join `packages/gateway/src/main.ts`.
  `buildGatewayLaunch` already forks: `.ts` → `node --import tsx <entry>`,
  otherwise `node <entry>` — **the packaged `.js` path exists and is tested**;
  what changes for D1-node(B) is `command` (from `"node"` to
  `process.execPath` + `ELECTRON_RUN_AS_NODE=1` in env), a small option on
  `buildGatewayLaunch`.
- Gateway child env contract (verified `packages/gateway/src/main.ts` +
  `desktop/src/env.ts`): `TRANSPORT_MATTERS_GATEWAY_PORT`,
  `TRANSPORT_MATTERS_CAPTURE_RPC_URL`, `TRANSPORT_MATTERS_DATABASE_URL`;
  `channel-specs.json` already carries per-channel `gatewayPort`.
- **The gap the brief undersells**: today the gateway is spawned by the
  **desktop only** (`desktop/src/main.ts::launchGatewayProcess`;
  `backendProcess.ts` hands Python `TRANSPORT_MATTERS_GATEWAY_URL`). Web mode
  has **no launcher at all** — `main.py` mounts the `runs_unavailable` D2 stub
  when `settings.gateway_url` is unset, and nothing in `cli/` spawns a gateway.
  "Canvas spawns the gateway EVERYWHERE" therefore needs a **new Python-side
  gateway supervisor** for web mode: resolve the packaged entry
  (`Path(__file__).parent / "gateway" / "main.js"` with env override), resolve
  node per D1-node, spawn, gate on `/health` (poll pattern exists in
  `cli/runs_health.py` and the desktop's `backendHealth`), self-set
  `gateway_url`, terminate on shutdown with the same SIGTERM-grace lesson as
  Q8/`DESKTOP_GATEWAY_STOP_GRACE_MS`. Precedent for packaged-vs-dev resolution:
  `cli/desktop_viewer.py::resolve_electron_launch` (env override → packaged →
  workspace → typed error) — mirror its shape.
- **Desktop packaged handoff**: the CLI already builds the desktop launch env
  (`cli/desktop_launch_config.py`); it gains `TRANSPORT_MATTERS_GATEWAY_ENTRY`
  pointing into site-packages so the Electron child's `resolveGatewayEntry`
  override branch fires. Note the desktop itself is still workspace-run
  (`electron .`, no electron-builder distributable), so "packaged desktop" in
  P1 means wheel-install + workspace desktop — the wheel entry override must
  win over the workspace walk in that layout (it does: override is checked
  first).

## 5. Windows / 5b (brief §5): fold or defer? — DEFER, decoupled by the N-API finding

Recommend **keep 5b its own slice, after D1-a/b** (Stuart decision D1-win):

- The coupling the brief feared — "Windows packaging must match the node ABI
  the prebuilds were built for" — is dissolved: node-pty's win32 prebuilds are
  N-API and ship in the package. The Windows *packaging* leg is a glob choice
  (§2b), not engineering.
- 5b (Job Objects) is orthogonal correctness work: per the P1 spec §5b, the
  Windows Job over the PTY agent lives at
  `packages/runtime/src/adapters/platform/JobObject.ts` (spawn-edge ownership),
  and Python's Job over mitmproxy is ctypes-only. None of it gates the wheel
  shipping POSIX-first.
- It is **unverifiable here**: no Windows machine, CI billing down. Folding it
  into D1 would hold the finish line hostage to an untestable leg.
- **Q7** (only if/when the Windows leg opens): survey npm for a maintained
  Win32 Job Object binding first; expectation from this scout is that none is
  current, and the answer is a minimal N-API addon shipped the same way
  node-pty ships (a `prebuilds/win32-*` dir beside the bundle — the pipeline
  D1-a builds is reusable), with a helper-exe as the fallback if the addon
  fights. The Python edge needs no dependency (ctypes).

## 6. Build matrix / verifiability (brief §6) — the payoff of §2b

With the §3 recommendation the wheel is **one `py3-none-any` artifact**: pure
Python + the gateway JS bundle + node-pty prebuild dirs. No per-platform wheel
matrix at all — the only per-platform binaries are upstream-shipped (node-pty)
or resolved by pip (A′ extra).

| Leg | Verifiable where |
| --- | --- |
| D1-a bundle + wheel embed | **mac, now** (build wheel, unzip-check, run bundle) |
| D1-b web-mode launcher + desktop execPath | **mac, now** (uv tool install the wheel; `transport-matters claude` + canvas spawn; desktop run) |
| D1-c linux-x64 | **mac via docker** (uv + node image; POSIX prebuilds already in wheel) |
| D1-d win32 + 5b | needs a Windows machine or CI — deferred |

## 7. Proposed decomposition

- **D1-a — build + embed the gateway distributable** (mac-verifiable, no
  runtime behaviour change): esbuild bundle script (gateway `build` →
  `api/src/transport_matters/gateway/{main.js,prebuilds/**}`), hatch artifacts
  glob + wheel-check echo, root `build`/`install-local` ordering, CLAUDE.md WWW
  note. Acceptance: `node api/src/transport_matters/gateway/main.js` boots
  against a dev Python and spawns a real captured run; wheel listing shows the
  artifacts; spawn-helper exec bit survives the wheel round-trip.
- **D1-b — packaged launch wiring** (mac-verifiable; the real new code): Python
  web-mode gateway supervisor (packaged-entry + node resolution per D1-node,
  health gate, gateway_url self-config, graceful stop; degrade to the D2 stub
  when no node) + desktop `GATEWAY_ENTRY` handoff + `buildGatewayLaunch`
  execPath option + `doctor` checks. This slice consumes Stuart's D1-node call.
- **D1-c — linux verification + optional `[node]` extra** (small): docker
  verification recipe; `transport-matters[node]` extra via
  `nodejs-wheel-binaries` if Stuart takes A′.
- **D1-d — Windows leg + 5b** (deferred, own slice): win32 prebuilds glob,
  Windows packaging verification, Job Objects per Q7. Blocked on a Windows
  verification path, not on D1-a/b/c.

## 8. Stuart decisions

- **D1-node**: hybrid recommended — desktop uses `ELECTRON_RUN_AS_NODE` +
  `execPath` (B); web mode requires system node with doctor guidance + the
  existing D2 degrade (C); optional `[node]` extra via `nodejs-wheel-binaries`
  (A′) for batteries-included web. Alternatives: A (own node in wheel) buys
  zero-dep web at the cost of per-platform wheels + a build matrix we cannot
  run right now.
- **D1-win**: defer the Windows leg + 5b to D1-d (recommended), or fold win32
  prebuilds into D1-a's glob now (+23MB wheel, still unverifiable).

## 9. Risks

- esbuild vs fastify/pino dynamic requires — tested in D1-a, `pnpm deploy`
  fallback named.
- node-pty is a **beta** pin (1.2.0-beta.14); the prebuild layout is the
  feature we lean on — pin exact (already exact in the catalog) and add a
  build-time assert that `prebuilds/{platform}-{arch}` exists before copy.
- Wheel mode-bit preservation for `spawn-helper` (checked in D1-a acceptance).
- Web-mode supervisor lifecycle: a leaked gateway child on CLI crash — reuse
  the s5 self-reap thinking (gateway already exits on SIGTERM; parent-death
  watch can ride the existing patterns) rather than inventing new reaping.
