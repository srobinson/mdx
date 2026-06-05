---
title: 'Plan — t3code DMG packaging scout (standalone .app: bundle Python+wheel, close reach-backs, .app smoke)'
type: projects
tags: [transport-matters, t3code, dmg, packaging, electron, python-bundling, standalone, scout, plan, postgres, reach-back]
summary: >
  Scout for the DMG packaging track on main @ 4c20d35 (read-only). The shipped product is a signed macOS
  .app (Electron) with the wheel bundled inside; goal = a bought .app launches from itself alone and runs a
  canvas claude run (RUN_STARTED→EXITED), zero reach into packages/ or the workspace. FINDINGS that reshape
  the brief: (1) there is NO electron-builder anywhere — the repo declares @electron/packager in the catalog
  but uses it NOWHERE; the current "packaged" .app is HAND-ROLLED by desktop/scripts/package-smoke-build.mjs
  (copies node_modules Electron.app + desktop/dist, NO Python, NO wheel, NO gateway) and its smoke asserts
  only main-window-created — a shell-only smoke. (2) Packaging is fully greenfield: no python-build-standalone,
  no dmg, no notarization, no electron-updater, no latest.json anywhere. (3) The DMG launch topology is the
  desktop's THIRD mode, registerAppLifecycle (Electron is the entry, spawns the backend itself) — and it
  hard-codes the backend as `command: "transport-matters"` off PATH (backendProcess.buildBackendLaunch) and
  leaves GATEWAY_ENTRY unset so gatewayProcess.resolveGatewayEntry walks for the workspace pnpm-workspace.yaml
  → both BUGS in a bundle. (4) LOAD-BEARING and co-equal with Python bundling: the desktop backend
  (`_desktop-backend`) calls preflight_session_store_or_exit() — it HARD-BLOCKS on the Postgres session store,
  so "runs a canvas run" cannot pass without a reachable store. Recommend: python-build-standalone + the wheel
  as the bundled interpreter; electron-builder (not @electron/packager) for .app+dmg+future auto-update; a
  Finder-launch resources resolver (process.resourcesPath) that sets the backend interpreter path AND
  GATEWAY_ENTRY from the bundled wheel; and DECOMPOSE — the Postgres-store bundling and the latest.json update
  feed are each their own follow-on slice, not folded into the first standalone-launch slice.
status: active
source: scout (fable 5:2.2), first-hand on main @ 4c20d35
confidence: high
created: 2026-07-08
---

# Plan — DMG packaging: make the .app launch standalone

Goal (from cm 019f4258 + WHEEL.md "The packaging track (next)"): a bought user's `.app`, installed from a
DMG with NO workspace checkout and NO system pip/python, launches from itself alone and runs a canvas claude
run to `RUN_STARTED → EXITED`. Every runtime reach into `packages/` or the workspace is a bug to close.

---

## 0. Recovered current packaging state (main @ 4c20d35)

### There is no electron-builder, and the current ".app" is a hand-rolled shell smoke

- **No electron-builder anywhere.** The repo declares `@electron/packager` in the root `package.json`
  catalog and `pnpm-workspace.yaml`, but a repo-wide grep finds it imported/invoked NOWHERE. WHEEL.md and
  cm 019f4258 both say "electron-builder"; the repo has neither wired. This is a discrepancy to resolve
  (§2b): electron-builder is the right tool for `.app` + `.dmg` + signing + `electron-updater`, and the
  catalog's `@electron/packager` is a declared-but-unused vestige.
- **The current packaged `.app` is hand-rolled**, by `desktop/scripts/package-smoke-build.mjs`: on darwin it
  `cp -R node_modules/electron/dist/Electron.app`, deletes `default_app.asar`, and copies `desktop/{dist,
  assets, package.json}` into `Contents/Resources/app/`. It bundles ONLY the Electron shell JS. It bundles
  NO Python, NO wheel, NO `gateway/` bundle. It is a build harness for the smoke, not a distributable.
- **The smoke is shell-only.** `desktop/src/packageSmoke.ts::runPackagedAppSmoke` launches that app with
  `DESKTOP_PACKAGE_SMOKE=1` and asserts a single marker `status: "main-window-created"`. Under that env,
  `main.ts::registerDesktopLifecycleFromEnv` takes the `registerDesktopPackageSmoke` branch and just opens a
  window — it never spawns the backend or gateway. So the existing `desktop` CI xvfb job proves the preload
  loads, nothing about a real run.
- **No packaging scaffolding exists at all**: grep finds no python-build-standalone, PyInstaller/py2app,
  `.dmg`, `codesign`/`notarize`, `electron-updater`, or `latest.json`. This track is greenfield.

### The three desktop launch modes, and which one the DMG uses

`main.ts::registerDesktopLifecycleFromEnv` branches on env:

1. `DESKTOP_PACKAGE_SMOKE=1` → `registerDesktopPackageSmoke` (window only). The current CI smoke.
2. `DESKTOP_ROUTE_URL` set → `registerHostedDesktopLifecycle` (Electron is a detached VIEWER onto a backend
   Python already spawned). This is the dev/CLI path: `transport-matters desktop` (Python) resolves +
   spawns Electron via `cli/desktop_viewer.py::spawn_detached_electron`, which already injects
   `GATEWAY_ENTRY = packaged_gateway_entry()` into Electron's env (D1-b).
3. Neither → `registerAppLifecycle` → `startBackendAndCreateWindow`: **Electron is the entry and spawns the
   backend AND gateway itself.** THIS is the DMG/standalone topology — and it is the one with the open
   reach-backs, because nothing upstream (no Python parent) sets the packaged env for it.

### What proves runs today, and the gap the .app fills

- `just verify-wheel` / `linux-wheel-spawn` (D1-c) boot the GATEWAY ALONE in stub mode and spawn a PTY —
  NO Python backend, NO Postgres. So the "inner" gate never exercises the full backend boot.
- The `.app` smoke is the FIRST time the full Python backend boots in a bundled context, which is where the
  reach-backs and the session-store dependency (§1) actually bite.

---

## 1. LOAD-BEARING: the backend hard-blocks on the Postgres session store

`cli/desktop_cmd.py` (the `_desktop-backend` subcommand the desktop spawns) calls
`launch_runtime.preflight_session_store_or_exit()` before serving. `config.resolve_database_url` returns a
`postgresql://` URL (the active store is Postgres, per CLAUDE.md and `session/`). So a bundled `.app` whose
backend cannot reach Postgres exits non-zero at preflight, and NO canvas run can reach `RUN_STARTED`.

This makes "the store" a decision co-equal with Python bundling, and it directly gates the brief's acceptance
test. Options (Stuart's decision, §6):

- **Bundle an embedded Postgres** in the `.app` (a `postgres`/`initdb` binary set, a per-user data dir under
  `~/Library/Application Support`, a postmaster started at launch). Faithful to the current store, but heavy:
  large binaries, every `.dylib` must be signed/notarized, lifecycle (initdb-once, start/stop, port) is real
  work. Likely its own slice.
- **A desktop SQLite store mode** — a `session/` store backend swap for the desktop. Smaller and simpler to
  bundle, but a real backend change (the store contract, migrations, `SessionWriter`), and it forks the
  store from the server story.
- **Provided/ambient store for the first slice** — scope the first standalone-launch slice to prove launch +
  gateway spawn + a run against a store the harness provides (e.g. the CI `postgres` service), and make
  embedded-store its own follow-on. This keeps the first slice about bundling+reach-backs and is my
  recommendation for sequencing (§5), with the store decision made explicitly next.

Flag: without resolving this, the outer `.app` smoke cannot assert `RUN_STARTED → EXITED` end to end on a
truly clean machine. It CAN assert standalone launch + gateway readiness + backend boot against a provided
store.

---

## 2. Python bundling: the load-bearing unknown (Stuart's decision)

### 2a. Options surveyed, with a recommendation

The `.app` must run the Python backend with no system Python. The wheel is `py3-none-any` but its deps are
heavy: `mitmproxy` (pulls cryptography, brotli, ...), `fastapi[standard]` (uvicorn, websockets),
`psycopg[binary,pool]` (bundles libpq), `alembic`, `typer`. Expect a bundled interpreter + site-packages of
roughly ~150–250 MB before Electron.

- **python-build-standalone (astral's standalone CPython) + `pip install` the wheel into it — RECOMMENDED.**
  A relocatable CPython tarball (the same builds `uv` uses) unpacked into `.app/Contents/Resources/python`,
  then the wheel (with `[node]`? no — desktop uses Electron's execPath node, so base wheel) installed into
  its site-packages. Yields `.../python/bin/transport-matters` (the console script) as an absolute,
  PATH-independent entrypoint the desktop invokes directly. Pros: matches the existing `uv`/wheel toolchain,
  no build-time freezing step, updates by reinstalling the wheel, transparent contents for signing. Cons:
  size, and every `.so`/`.dylib` under it must be signed for notarization.
- **PyInstaller / py2app (freeze to one bundle).** Produces a self-contained backend binary. Cons:
  mitmproxy + psycopg + uvicorn are notoriously fiddly to freeze (hidden imports, data files, native libs);
  higher ongoing maintenance; opaque bundle. Not recommended given the standalone-CPython path is simpler
  and reuses the wheel we already gate.
- **uv-managed embedded env.** Ship `uv` + let it materialize a venv on first launch. Cons: first-launch
  network dependency and a pip/uv resolve on the user's machine — antithetical to "installs one DMG, never
  runs pip". Rejected for the shipped product (fine as a dev convenience only).

**Recommendation: python-build-standalone + the wheel, unpacked into `.app/Contents/Resources/`.** Size,
signing surface (every bundled binary/dylib), and the update mechanism all follow from this: updates replace
the wheel (or the whole Resources payload) and re-sign; the DMG carries the full interpreter, so there is no
runtime pip. Say this explicitly to Stuart.

### 2b. electron-builder vs @electron/packager

Recommend **electron-builder**: it produces the `.app` AND the `.dmg`, handles macOS codesign +
notarization config, and pairs with `electron-updater` for the deferred auto-update leg — all of which the
roadmap needs. `@electron/packager` only emits the `.app` directory; DMG, signing, and updates would each be
bolt-ons. Add electron-builder as a desktop devDependency and remove the unused `@electron/packager` catalog
entry (or repurpose). electron-builder's `extraResources` is the seam that copies the bundled Python +
wheel + the gateway bundle into `Contents/Resources/`.

---

## 3. Reach-back inventory + fix seams (the standalone `registerAppLifecycle` path)

Cite file+symbol. Every item below is a runtime reach into the workspace/PATH that a Finder-launched bundle
must not make.

| # | Reach-back | Where (file + symbol) | Fix seam |
|---|---|---|---|
| R1 | Backend spawned as bare PATH command `transport-matters` | `desktop/src/backendProcess.ts::buildBackendLaunch` (`command: "transport-matters"`) | Add a backend-interpreter override: a `DESKTOP_BACKEND_BIN` env (mirroring `DESKTOP_APP_BIN`/`DESKTOP_ELECTRON_BIN` in `env.ts`/`env_keys.py`) that the bundled app sets to `Contents/Resources/python/bin/transport-matters`; `buildBackendLaunch` prefers it over the PATH default. |
| R2 | Gateway entry defaults to workspace `packages/gateway/src/main.ts` | `desktop/src/gateway/gatewayProcess.ts::resolveGatewayEntry` (walks to `pnpm-workspace.yaml`) | In `registerAppLifecycle`, set `GATEWAY_ENTRY` from the bundled resources (the wheel's `gateway/main.js` under Resources) BEFORE `launchGateway`, exactly as `spawn_detached_electron` already does for the viewer path. Node interpreter is already `process.execPath` (D1-b) — no reach-back there. |
| R3 | No bundled-resources locator | (absent) `desktop/src/**` never references `app.isPackaged` / `process.resourcesPath` | New `resolveBundledResources()` seam: when `app.isPackaged`, root at `process.resourcesPath`; expose the Python entrypoint (R1) and the gateway entry (R2) from it. This is the single "where am I bundled" source. |
| R4 | Backend `workspaceDir = process.cwd()` | `desktop/src/main.ts::registerAppLifecycle` (`workspaceDir = process.cwd()`) | Not a hard bug (it is the run's working dir), but a Finder launch has `cwd = /`. Default to a sane workspace (home / a chosen dir) when packaged, so runs open somewhere meaningful. Minor. |
| R5 (dev-only) | Python `resolve_electron_launch` walks `__file__` parents for a `desktop/` dir | `api/src/transport_matters/cli/desktop_viewer.py::_resolve_desktop_app_dir` | Dev/CLI path only (not the Finder-launch topology). `DESKTOP_APP_BIN`/`DESKTOP_APP_DIR` overrides already exist. No change needed for the bundle; note it so it is not mistaken for a bundle reach-back. |

The clean composition: a `resolveBundledResources()` in the desktop shell (R3) feeds both the backend
interpreter path (R1) and `GATEWAY_ENTRY` (R2). electron-builder's `extraResources` places `python/` (the
standalone interpreter + wheel) and the gateway bundle under `Contents/Resources/`; the resolver reads them
via `process.resourcesPath`.

---

## 4. The `.app` smoke (outer acceptance test)

The brief's outer test: launch the FULLY BUNDLED app from itself alone (no workspace on PATH/cwd) and assert
a canvas run reaches `RUN_STARTED → EXITED`. Design, honoring "CI is ubuntu/xvfb; macOS `.app` signing is
Stuart-local":

- **Extend the existing `desktop` xvfb job**, don't fork it. Today it builds the desktop and runs the
  shell-only `package:smoke`. The new smoke builds a REAL bundle (Electron + python-build-standalone + the
  wheel + the gateway bundle via electron-builder's linux target = a portable app dir / AppImage) and
  launches it from a temp dir with a scrubbed env (no repo on PATH, cwd outside the checkout), asserting a
  canvas run `RUN_STARTED → EXITED`. This proves the BUNDLING MECHANISM (bundled Python boots the backend,
  bundled gateway spawns a PTY, zero packages/ reach) on the CI runner.
- **macOS `.app` + DMG + signing/notarization is a Stuart-local gate**, mirroring WHEEL.md's macOS row:
  `just` recipe(s) that build the `.app`/`.dmg` locally and run the same standalone smoke against the darwin
  prebuild. CI cannot sign (no Apple identity) and darwin runners bill ~10x; the proportionate control is one
  local command plus the linux-portable CI proof of the mechanism.
- **Store dependency (§1) applies here**: the smoke's backend boot hits `preflight_session_store_or_exit`.
  For the first slice, run the smoke against a provided store (the CI `postgres` service the `desktop` job
  can add, as `product-plane` already does) so the run reaches `RUN_STARTED → EXITED`; embedded-store makes
  the smoke truly machine-clean in its own slice.
- Reuse, don't reinvent: the assertion is the same shape as `test_gateway_wheel_spawn.py` (POST a run to the
  gateway/backend, poll to EXITED). The new part is that it runs against the packaged app's OWN backend +
  gateway, launched from the bundle.

---

## 5. Decomposition — this slice vs deferred

This is large. Recommended split (confirm with Stuart):

- **Slice DMG-1 (this one): standalone launch + reach-backs + linux-portable smoke.**
  electron-builder wired; python-build-standalone + wheel bundled via `extraResources`; the
  `resolveBundledResources` seam (R3) feeding the backend interpreter (R1) and `GATEWAY_ENTRY` (R2); the
  extended xvfb smoke that launches the bundled app standalone and asserts a run `RUN_STARTED → EXITED`
  against a provided store; local `just` recipe for the macOS `.app`/`.dmg` + local smoke. Deliberately NOT
  signed/notarized (unsigned `.app` still installs, hits Gatekeeper's "unidentified developer" prompt).
- **Slice DMG-2 (deferred, distinct): the session store on the desktop.** Decide embedded-Postgres vs a
  SQLite desktop store mode (§1) and implement it so the `.app` runs on a truly clean machine with no
  provided store. This is the piece that makes the standalone smoke machine-clean.
- **Slice DMG-3 (deferred, distinct — confirmed as a SEPARATE concern per the brief): the update feed.**
  `latest.json` version feed + in-app notify-only ("vX.Y.Z available → Download"), which needs NO Apple
  signing and ships first among updates. Silent auto-update (`electron-updater`/Squirrel) is a later leg that
  needs code signing + notarization. NOT folded into DMG-1.
- **Signing/notarization** is its own gate that unblocks silent updates and removes the Gatekeeper prompt;
  it rides whichever slice Stuart schedules an Apple Developer identity into. Flag, do not assume.

The brief's "the app launches standalone" == DMG-1 (bundle Python+wheel + close reach-backs + standalone
smoke), with the store as the one dependency that must be decided before the smoke can assert a full run.

---

## 6. Test plan — how standalone launch is proven green

| Concern | Proof | Where |
|---|---|---|
| Reach-backs closed | Unit tests: `buildBackendLaunch` prefers `DESKTOP_BACKEND_BIN`; `registerAppLifecycle` sets `GATEWAY_ENTRY` from bundled resources; `resolveBundledResources` roots at `resourcesPath` when packaged | desktop vitest (`just check`/`just test`) |
| Bundled backend boots standalone | The extended xvfb smoke: launch the linux-portable bundle from a temp dir, scrubbed env, no repo on PATH; backend answers health | `desktop` CI job (ubuntu/xvfb) |
| Canvas run end to end | Same smoke drives POST run → poll `RUN_STARTED → EXITED` through the bundled gateway | `desktop` CI job, against a provided `postgres` service |
| macOS `.app`/`.dmg` | `just` recipe builds + runs the standalone smoke against the darwin prebuild | Stuart-local (WHEEL.md macOS row) |
| No packages/ reach | Assert (grep/test) the bundle contains no `packages/` and the launched app never resolves the workspace `pnpm-workspace.yaml` | smoke + a structural check |

Gate verbatim: `just check` + `just test`. CI note: macOS signing/notarization and the DMG are Stuart-local;
CI proves the mechanism on linux-portable under xvfb.

---

## 7. Decisions flagged for Stuart

1. **[DECISION — load-bearing] Python bundling.** Recommending python-build-standalone + the wheel unpacked
   into `Contents/Resources/`. Confirm, or pick PyInstaller/py2app. Size (~150–250 MB pre-Electron), signing
   surface (every bundled dylib), and updates (replace the wheel/Resources) all follow.
2. **[DECISION — load-bearing, co-equal] The session store.** The desktop backend hard-blocks on Postgres
   (`preflight_session_store_or_exit`). Embedded Postgres vs a SQLite desktop store vs provided-store-for-now
   (DMG-2). This gates "runs a canvas run" on a clean machine. My recommendation: provided store for DMG-1,
   embedded/SQLite decided as DMG-2 before shipping to buyers.
3. **[DECISION] electron-builder vs @electron/packager.** Recommending electron-builder (`.app` + `.dmg` +
   signing + `electron-updater`). The catalog's unused `@electron/packager` gets removed. Confirm.
4. **[DECISION] Scope of DMG-1.** Confirm the split: DMG-1 = standalone launch + reach-backs + linux smoke
   (unsigned); DMG-2 = store; DMG-3 = update feed. The brief already asked to keep the update feed separate —
   confirmed here.
5. **[DECISION] Signing/notarization timing.** Unsigned ships and installs (Gatekeeper prompt); signing
   removes the prompt and unblocks silent auto-update. Needs an Apple Developer identity — schedule it.
6. **[RISK] Bundle size + darwin-only first.** mitmproxy + Electron + CPython is a large DMG; worth stating
   the target size and that Windows is parked (WHEEL.md) so packaging is darwin-first.

---

## 8. Build order (once signed off)

1. electron-builder wired (config + a build recipe), producing an unsigned `.app`/`.dmg` locally and a
   linux-portable in CI.
2. python-build-standalone + wheel via `extraResources`; `resolveBundledResources` (R3).
3. Close R1 (`DESKTOP_BACKEND_BIN`) and R2 (`GATEWAY_ENTRY` in `registerAppLifecycle`), with unit tests.
4. Extend the xvfb smoke to launch the bundle standalone and assert `RUN_STARTED → EXITED` against a provided
   store; local `just` macOS recipe.
5. (DMG-2/3 deferred: store bundling; latest.json + notify.)

codex + opus (5:2.3) sign off on this PLAN before any build.
