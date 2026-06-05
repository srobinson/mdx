---
title: transport-matters ↔ t3code Whole-App Alignment — Report & Proposal
type: projects
tags: [transport-matters, t3code, electron, desktop, backend-lifecycle, alignment, proposal]
summary: A report/proposal classifying what transport-matters can leverage from current t3code; with Windows/Linux desktop first-class and Effect-TS viable (only the mitmproxy capture pipeline is truly Python-bound), t3code's Effect-based desktop lifecycle becomes direct leverage — the launcher target is a TS/Effect backend running the Python mitmproxy process as a managed child — and a strategic option reduces Python to a capture sidecar while the portable control-plane surfaces move to TS/Effect.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-04
updated: 2026-07-04
---

# transport-matters ↔ t3code Whole-App Alignment — Report & Proposal

**This is a report and proposal only. Nothing here is committed work.** Every
recommendation is framed as "what we can leverage from the latest t3code," for
Stuart to approve, defer, or reject later. Citations are **file + symbol**, never
line numbers. Claims I could not verify first-hand are flagged inline.

**Sources.** Two scout findings (ground truth): upstream `align-scout-t3code.md`
(t3code `main`, HEAD `cabc93bad`) and our-fork `align-scout-transport-matters.md`
(branch `feat/activity-slice-1b-read`, HEAD `bd64539`). Plus the parked launcher
spec `launcher-spec-desktop-relaunch.md`. I spot-checked code in both repos to
resolve the load-bearing claims (backend teardown mechanism, hosted-close
teardown gap, env duplication); those checks are noted where they matter.

---

## 1. Executive Summary — top leverage items

transport-matters copied t3code's `apps/desktop` Electron skeleton and diverged
into a different product (a wire-observability proxy/inspector/canvas over a
Python control plane). The leverage is therefore concentrated in the **desktop
shell and engineering conventions**, not the product.

**Scope note — Windows/Linux desktop is first-class** (confirmed with Stuart; it
is a primary reason we are on Electron). Cross-platform correctness is a
first-class evaluation axis throughout this report, not an afterthought.

**Premise update (Pass 2) — Effect-TS is viable for the desktop; Python is only
truly required for the mitmproxy capture code.** An earlier draft assumed the
Python control plane made Effect-TS non-applicable (bucket C). That is wrong: the
Activity package is already TypeScript, and — verified in §8 — only the
**wire-capture pipeline** is genuinely mitmproxy-bound. The **desktop lifecycle,
session store, read/stream API, and run management are Python-by-choice and
portable to TS/Effect**. This promotes t3code's Effect-based desktop lifecycle
from *adapt-in-Python* to **direct leverage**, and reframes the launcher target as
*a TS/Effect backend that runs the Python mitmproxy process as a managed child*
(§5c, §8). Ranked by value:

| # | Item | Bucket | Effort | Risk | One-line why |
|---|------|--------|--------|------|--------------|
| 1 | **Adopt t3code's Effect-TS desktop lifecycle directly** — `DesktopLifecycle`/`DesktopBackendManager`/`DesktopShutdown` in TS; the backend it owns becomes the Python **mitmproxy sidecar** run as a managed child | **A** (direct lift) / **B** (Effect adoption cost) | M–L | M | Premise-corrected (§8): single-language lifecycle fixes the orphan bug, brings grace-then-force + one coordinator for free, and largely dissolves the DRY item. |
| 2 | **OS-conditional lifecycle + WSL-style launch handling** — reuse t3code's platform-branched teardown and OS-specific launch structure | **B** | M | M | Windows/Linux are first-class, so `DesktopLifecycle.ts`'s platform branches (`!win32`/`!darwin`) and the WSL env/backend split are direct templates, not "no equivalent." |
| 3 | **DRY the cross-language desktop contract** — env keys, backend command string, and runtime-status JSON are hand-mirrored across Python and TS | **B** | S | L | Zero-tolerance DRY today; **largely dissolves** if the lifecycle moves to TS (§8) — only the TS→mitmproxy-sidecar launch args stay cross-language. |
| 4 | **Decompose `main.ts` / `desktop_cmd.py` using t3code's seam names** — `DesktopLifecycle` / `DesktopWindow` / `DesktopBackendManager` / `DesktopEnvironment` boundaries, without Effect | **A** (naming) / **B** (split) | M | L | Both files sit at/over the 700-LOC hard limit; the launcher spec already needs the split, and upstream supplies clean, proven seam names. |
| 5 | **`.electron-runtime` pinned-binary dev launch + smoke** — decouple the Electron binary from the npm dep for dev/CI | **A** | S–M | L | Upstream actively de-flakes exactly the launch path a fork inherits (`#3662`, `#3557`); cheap resilience for our smoke pipeline across OSes. |
| 6 | **Schema-validated, self-registering IPC pattern** (`makeIpcMethod`) — adopt *if/when* the desktop bridge grows past its current 3 methods | **B** | M | L | Our bridge is tiny today (`appName`/`platform`/`getPathForFile`); this is a "hold in reserve" pattern, not a now-item. |

**The critical section-5 verdict up front:** t3code **validates** the parked
launcher spec's direction (Electron owns the backend; a single coordinator drives
all quit paths; SIGTERM + grace before force-kill) and offers a cleaner grace
idiom to adapt. It does **not supersede** the spec. Corrected framing (Windows/
Linux first-class): OS-level parent-death reaping — **Windows Job Objects** and
**Linux `PR_SET_PDEATHSIG`** — makes process parentage the **core cross-platform
teardown mechanism**, which is exactly t3code's model. The spec's backend-side
parent-death watchdog (stdin-EOF + `getppid()` poll) is therefore a **macOS-only
backstop** (macOS has neither mechanism), not the universal core. Keep the
watchdog for macOS; borrow the grace-then-force and single-coordinator shape; and
close the fork's POSIX-only launcher debt so the model actually runs on Windows
(§5d).

---

## 2. Relationship & alignment mechanic

**Genesis.** transport-matters copied t3code's `apps/desktop` Electron skeleton
and evolved it. The two repos have **different remotes and no shared git
history**, so there is **no merge-base**. Alignment is therefore a **manual
port / re-baseline**, item by item — never a `git merge`, `git cherry-pick`, or
rebase. Every adopted item is a fresh, hand-written change reviewed on its own
merits against our tree.

**Scale gap (context for effort).** By fmm: t3code is ~1,938 files / ~511k LOC
(Effect-TS, five `apps/*`, ten `packages/*`); transport-matters is ~967 files /
~154k LOC. The desktop shells are the only truly comparable surface: t3code's
`apps/desktop` is ~114 files / ~30.5k LOC; ours (`desktop/`) is a thin shell (~10
source files, ~10 tests). We inherited a *concept*, not the mass.

**Tracking upstream going forward (proposal).** Since there is no merge-base:

- Keep a short **provenance note** per ported file (a one-line header pointing at
  the upstream `file::symbol` it was adapted from), so future ports can diff
  intent, not bytes. `desktop/src/env.ts` already does this ("Mirrors
  `api/src/transport_matters/env_keys.py`; rename both together").
- Re-scout upstream `apps/desktop` on a cadence (or when we touch the desktop),
  diffing *our seams* against theirs rather than chasing every commit. Upstream's
  desktop churn is concentrated in areas we do not have (preview automation, WSL,
  SSH, Clerk, updater), so the relevant surface is small.
- Treat the two scout docs as the current baseline; this report is the decision
  layer on top of them.

---

## 3. Architecture comparison (side-by-side)

| Dimension | transport-matters (ours) | t3code (upstream) | Alignment stance |
|-----------|--------------------------|-------------------|------------------|
| **Monorepo layout** | Top-level `api/` (Python core), `desktop/`, `www/packages/*`, `packages/activity` | `apps/{desktop,server,web,mobile,marketing}` + `packages/{contracts,shared,client-runtime,ssh,tailscale,effect-*}` | **Divergent by product.** Our Python plane has no upstream analogue; do not chase `apps/*` topology. |
| **Build orchestration** | `just` + `uv` + `pnpm` + Vite + Hatch (wheel embeds built `www`/`canvas`) | `vite-plus` (`vp`) task runner + `electron-builder` + `scripts/*` Effect CLIs | **Divergent.** `vp`/electron-builder are Effect/Node-shaped; our Hatch/PyPI release flow is product-correct. |
| **TS config** | Shared strict `tsconfig.base.json` | Shared strict `tsconfig.base.json` (`NodeNext`, `verbatimModuleSyntax`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `erasableSyntaxOnly`; `tsgo`) | **Already aligned in spirit.** Consider adopting the remaining strict flags we lack (see §4). |
| **Lint** | Biome | Oxlint + custom `oxlint-plugin-t3code` (Effect house rules) | **Mostly divergent.** The plugin encodes Effect discipline we do not run; a few rules generalize (§4). |
| **Test** | Vitest (desktop/web), pytest/ruff/mypy (api), Playwright (shell); co-located `*.test.ts` | `@effect/vitest` `it.effect(...)` + test layers; co-located `*.test.ts`; `smoke-test.mjs` | **Convention already kept** (co-located tests, package smoke). `it.effect` is Effect-specific → skip. |
| **IPC** | Minimal `contextBridge` (`preload.cts`, key `transportMattersDesktop`: `appName`/`platform`/`getPathForFile`) + HTTP API for everything else | `DesktopIpc` typed service; `makeIpcMethod` wraps each handler with `Schema.decode/encode` validation, span-tracing, auto-unregister; 73 channel constants | **Adopt-if-grows (B).** Our HTTP-API-first choice is sound for a web-served product; the schema-validation wrapper is worth lifting only if the bridge expands. |
| **Electron shell** | Electron 39; secure `BrowserWindow` (`contextIsolation`, `sandbox`, `nodeIntegration:false`); hosted loopback routes; manual package smoke | Electron 41; same secure posture; custom `desktop://` protocol; electron-builder + updater | **Aligned at the security posture.** Protocol/updater are upstream-product scale; our loopback routes are simpler and correct for us. |
| **Backend-process lifecycle** | Python backend spawned by Electron *or* detached; teardown split across TS (`bindBackendQuitCleanup`) and Python (`stop_desktop_record`); **known orphan on hosted close** | Node backend spawned in a per-run Effect `Scope`; SIGTERM + 2s `forceKillAfter`; pool anchored to layer scope; `DesktopShutdown` Deferred coordinator | **The core leverage area — §5.** Adopt the *pattern*, not Effect. |
| **Target platforms & OS-conditional handling** | Windows/Linux/macOS all first-class; **but launcher is POSIX-only today** (`os.kill`, `start_new_session`; no Windows branch — §5d) | Windows + WSL/Linux primary; teardown explicitly OS-branched (`DesktopLifecycle.ts`: SIGINT/SIGTERM only `!== "win32"`, window-all-closed quit only `!== "darwin"`); WSL subsystem (`DesktopWslEnvironment.ts`, `DesktopWslBackend.ts`) | **Leverage (§4.1a).** t3code is the cross-platform reference; we carry POSIX-only debt to close. |

---

## 4. Leverage opportunities (grouped by theme)

Ordered by value within each theme. Bucket key: **A** = directly portable, **B** =
pattern to adapt in our stack, **C** = not applicable (says why).

### Theme 1 — Desktop skeleton (the direct inheritance)

**4.1 Backend-teardown hardening (bucket B).** *Highest value; full treatment in
§5.*
- Upstream: `apps/desktop/src/backend/DesktopBackendManager.ts` spawns with
  `killSignal: "SIGTERM"` + `forceKillAfter: DEFAULT_BACKEND_TERMINATE_GRACE`
  (verified: 2s); `DesktopBackendPool.layer` anchors instance scopes to the layer
  scope; `DesktopShutdown` (a `Deferred` coordinator) funnels every quit path; a
  top-level app finalizer stops every pool instance *before* `electronApp.quit()`.
- Ours: `desktop/src/main.ts::bindBackendQuitCleanup` (SIGTERM on `before-quit`,
  owned path only) + `desktop/src/backendProcess.ts::stopBackendProcess` +
  Python `api/src/transport_matters/desktop_runtime.py::stop_desktop_record`.
- **Value:** fixes the active orphan bug. **Effort:** M. **Risk:** M.
  **Recommendation: adapt** — the parked launcher spec is the vehicle (§5).
  *Cross-platform:* the teardown must be OS-branched — parentage + Job Objects on
  Windows, `PR_SET_PDEATHSIG` + killpg on Linux, the watchdog on macOS (§4.1a, §5d).
  *Premise update (§8):* with Effect-TS viable, the higher-leverage form is a
  **direct lift** of t3code's `DesktopBackendManager` (Effect `Scope` +
  `forceKillAfter`) in TS, owning the Python **mitmproxy sidecar** as its managed
  child — bucket **A**, not just B.

**4.1a OS-conditional lifecycle + WSL-style launch handling (bucket B) — reclassified from non-alignment.**
- Upstream: `apps/desktop/src/app/DesktopLifecycle.ts` registers `SIGINT`/`SIGTERM`
  handlers only when `environment.platform !== "win32"` and gates the
  window-all-closed quit on `!== "darwin"`; the WSL subsystem
  (`apps/desktop/src/wsl/DesktopWslEnvironment.ts`,
  `apps/desktop/src/wsl/DesktopWslBackend.ts::reconcile`, `wslPathParsing.ts`) is
  a self-contained OS-conditional launch/env layer (PR #3588 warms WSL before
  preflight).
- Ours: `desktop/src/main.ts` has no explicit OS branching in its signal/quit
  wiring, and the Python launcher assumes POSIX throughout (§5d).
- **Why reclassified:** the fork scout filed t3code's WSL/OS handling under "no
  equivalent." With Windows/Linux first-class, the *product features* (WSL distro
  detection) are not ours, but the **OS-conditional lifecycle *pattern*** —
  platform-branched signal registration, `!== "darwin"` window-quit semantics, and
  an isolated per-OS launch/env module — is exactly the structure we need.
- **Value:** high; it is the blueprint for making the launcher spec run correctly
  on all three OSes. **Effort:** M. **Risk:** M. **Recommendation: adapt** the
  branching structure and semantics; skip the WSL product specifics.
  *Cross-platform:* this item *is* the cross-platform axis for the desktop shell.

**4.2 `.electron-runtime` pinned-binary dev launch + smoke (bucket A).**
- Upstream: `apps/desktop/scripts/ensure-electron-runtime.mjs` downloads a pinned
  Electron zip into a local runtime dir and chmods it; `start-electron.mjs` /
  `smoke-test.mjs` resolve the launch command via
  `scripts/lib/electron-launcher.mjs`. Dev launch was explicitly de-flaked in
  `#3662` ("Fix electron dev launch and add test") and `#3557`.
- Ours: `desktop/src/packageSmoke.ts::runPackagedAppSmoke` +
  `desktop/scripts/package-smoke-build.mjs` + `desktop/scripts/assert-preload-cjs.mjs`
  (portable-package smoke, no pinned-binary decoupling).
- **Value:** cheap CI/dev resilience; upstream is de-flaking the very path a fork
  inherits. **Effort:** S–M. **Risk:** L. **Recommendation: adopt** the
  pinned-binary resolver if/when dev-launch flakiness appears; low urgency while
  smoke is green. *Cross-platform:* pins the correct
  `electron-v…-${platform}-${arch}` binary per OS, so it de-risks Windows/Linux
  dev + CI, not just macOS.

**4.3 Schema-validated, self-registering IPC (bucket B).**
- Upstream: `apps/desktop/src/ipc/DesktopIpc.ts` + `makeIpcMethod` — each handler
  wrapped with `Schema.decodeUnknownEffect` (payload) → handler →
  `Schema.encodeUnknownEffect` (result), span-traced, acquire/release-registered
  (auto-unregister on scope close); channel names centralized in
  `src/ipc/channels.ts`.
- Ours: `desktop/src/preload.cts` exposes 3 methods; contracts live in the HTTP
  API (`www/packages/core/src/transport.ts`,
  `api/.../api/v1/router.py`), not in IPC.
- **Value:** low today (tiny bridge), high *if* the bridge grows (e.g. richer
  canvas control). **Effort:** M. **Risk:** L. **Recommendation: hold in
  reserve** — do not build speculatively; lift the wrapper the day a fourth
  non-trivial bridge method appears. *Cross-platform:* neutral (IPC is
  OS-agnostic).

**4.4 Borrow upstream seam names when decomposing (bucket A).**
- Upstream boundaries: `src/electron/*` (platform adapters) vs `src/app/*` vs
  `src/backend/*` vs `src/ipc/*`; names like `DesktopLifecycle`,
  `DesktopWindow`, `DesktopBackendManager`, `DesktopServerExposure`.
- Ours: `desktop/src/main.ts` (655 LOC) mixes channel identity, hosted attach,
  owned-backend spawn, preload smoke, and lifecycle policy in one file.
- **Value:** navigability + a shared vocabulary with upstream, at zero runtime
  cost. **Effort:** M (it is a file split). **Risk:** L. **Recommendation:
  adopt the names, not the Effect** — see §7 roadmap; the launcher spec already
  requires this split. *Cross-platform:* the `DesktopLifecycle` seam is the
  natural home for the OS branches from §4.1a.

### Theme 2 — Engineering conventions

**4.5 Cross-language contract DRY (bucket B) — second-highest value.**
- Verified duplication: `desktop/src/env.ts::ENV` is a hand-mirror of
  `api/src/transport_matters/env_keys.py` (header comment: "Mirrors … rename both
  together"); `desktop/src/backendProcess.ts::DESKTOP_BACKEND_COMMAND` duplicates
  the Python command string; `desktop/src/desktopRuntime.ts::parseDesktopRuntimeStatus`
  re-declares the shape of `api/.../desktop_runtime.py::DesktopRuntimeStatusJson`.
- Upstream analogue: t3code centralizes cross-boundary shape in
  `packages/contracts` (effect/Schema, schema-only, no runtime logic) — one
  source of truth for the WS protocol and the `DesktopBridge`. We cannot lift
  `contracts` (it is Effect/Schema and Node↔Node), but the *principle* (one
  declared contract, both sides derive from it) is the adoptable pattern.
- **Value:** DRY is a zero-tolerance rule here; a comment is not a guardrail.
  **Effort:** S. **Risk:** L. **Recommendation: adapt** — either generate the TS
  side from the Python env/runtime schema, or (cheaper first step) add a
  cross-language parity test asserting the key set and command string match.
  *Cross-platform:* neutral, but the contract must carry any OS-specific launch
  env keys (e.g. a Windows detach flag) once the spec adds them.

**4.6 Strict TS baseline parity (bucket A).**
- Upstream `tsconfig.base.json` sets `verbatimModuleSyntax`,
  `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `erasableSyntaxOnly`,
  `allowImportingTsExtensions`. Our `tsconfig.base.json` is strict but (per the
  fork scout) carries "fewer … Effect language-service conventions."
- **Value:** catches a class of bugs cheaply. **Effort:** S per flag (but each
  flip surfaces real fixes). **Risk:** L–M (fix churn). **Recommendation: adopt
  selectively** — audit which strict flags we already set; add
  `noUncheckedIndexedAccess` / `exactOptionalPropertyTypes` if not present,
  flag-by-flag so the fix churn is bounded. *Cross-platform:* neutral.

**4.7 Custom lint rules that generalize (bucket C-mostly).**
- `oxlint-plugin-t3code` rules: `namespace-node-imports`, `no-global-process-runtime`,
  `no-inline-schema-compile`, `no-manual-effect-runtime-in-tests`. Three of four
  are Effect-specific (**C** — they police a runtime we do not use).
  `no-inline-schema-compile` (hoist compiled encoders/decoders out of hot paths)
  has a general analogue but no Effect-free home in our stack today.
- **Recommendation: skip.** We run Biome, not Oxlint; porting the plugin would
  fight our toolchain for near-zero gain.

**4.8 "Many small guarded fixes" cadence (bucket A, cultural).**
- Upstream's recent history is dominated by small `[codex]`-prefixed defensive
  guards (guard clipboard copy, reject unsupported pairing, ignore stale reducer
  events). This is a *practice*, not code.
- **Recommendation: note, don't port.** It matches our own "fix every Minor now"
  posture; no action beyond keeping the discipline.

### Theme 3 — Cross-cutting

**4.9 Single teardown coordinator (bucket B).** Upstream's `DesktopShutdown`
`Deferred` is the one place all quit paths (before-quit, window-all-closed,
non-Windows SIGINT/SIGTERM, fatal startup) converge. Ours scatters teardown
across `bindBackendQuitCleanup`, the (proposed) SIGTERM→`app.quit` handler, and
the Python stop seam. **Recommendation: adapt** the convergence discipline into
the launcher spec (§5) — one owned teardown, explicit ordering vs `app.quit()`.

**4.10 Do not inherit upstream's file-size profile (bucket C, cautionary).** The
fork scout is right: `apps/desktop/src/preview/Manager.ts` (~2,973 LOC),
`DesktopBackendManager.ts` (~819 LOC, `makeBackendInstance` a ~432-line
function). Borrow upstream's *seam names and patterns*, never its file sizes; our
700-LOC / 150-LOC limits stand.

---

## 5. Backend-lifecycle deep dive — does upstream validate or supersede the parked launcher spec?

This is the decision the brief centers on. Short answer: **validates, does not
supersede.**

### 5a. The two teardown models, side by side

**t3code (verified).** The backend is a `ChildProcess` spawned inside a per-run
Effect `Scope` (`DesktopBackendManager.ts::makeBackendInstance` →
`runBackendProcess`) with `killSignal: "SIGTERM"` and `forceKillAfter` = 2s.
Closing the scope sends SIGTERM, waits the grace, then SIGKILLs — platform-native,
no manual `.kill()`. `DesktopBackendPool.layer` anchors every instance scope to
the pool's layer scope so instances are not orphaned when the app shuts down
(the header comment names the exact failure: otherwise "the WSL backend child
process gets hard-killed by the OS instead of receiving the graceful SIGTERM +
grace period"). `DesktopApp.program` blocks on `shutdown.awaitRequest` and
registers a **top-level finalizer that iterates `pool.list` and `stop()`s every
instance before `electronApp.quit()`** — precisely because "the
`electronApp.quit()` path can race ahead of the layer-scope cascade." All quit
signals funnel through the `DesktopShutdown` `Deferred` coordinator.

**transport-matters (verified).** Two launch modes:
1. **Electron-owned backend.** `desktop/src/main.ts::registerAppLifecycle`
   spawns the Python backend via
   `desktop/src/backendProcess.ts::launchBackendProcess` and registers
   `bindBackendQuitCleanup` → SIGTERM on `before-quit`. **Verified gap:** it calls
   `bindHostedWindowLifecycle` *without* `quitOnWindowAllClosed: true`, so on
   macOS closing the only window neither quits Electron nor tears down the backend.
2. **Detached backend + hosted viewer.** The Python CLI
   (`api/.../cli/desktop_cmd.py::run_desktop_detached`) starts the backend with
   `subprocess.Popen`, writes a `DesktopRuntimeRecord`, and spawns Electron with
   `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`. Electron enters
   `registerHostedDesktopLifecycle`, which *does* set `quitOnWindowAllClosed:
   true` and polls backend liveness — but **verified gap:** nothing on the
   viewer-close path reaches `desktop_runtime.py::stop_desktop_record`. The
   detached backend survives viewer close (orphan by current design).

### 5b. The real cross-platform picture (corrected framing)

t3code's teardown is excellent on **graceful** quit paths, but every one of those
(`before-quit`, `window-all-closed`, finalizers, `DesktopShutdown`) requires
Electron to run its shutdown. The hard case is Electron being **SIGKILLed**, when
none of that fires. What reaps the backend then is **OS-level parent-death
behaviour**, which is platform-specific:

| OS | Parent-death reaping | Consequence |
| --- | --- | --- |
| **Windows** | **Job Objects** (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) reap the child tree when the owner closes | Parentage is the core mechanism; no watchdog needed |
| **Linux** | **`PR_SET_PDEATHSIG`** signals the child on parent death | Parentage is the core mechanism; no watchdog needed |
| **macOS** | **Neither** — orphans reparent to `launchd`, not killed | A backend-side watchdog is required |

With Windows/Linux **first-class**, the corrected framing is: **process parentage
is the core cross-platform teardown mechanism — exactly t3code's model — and the
launcher spec's parent-death watchdog (stdin-EOF + `getppid()` poll) is a
macOS-only backstop, not the universal core.** (My first draft wrongly pinned the
whole verdict on macOS, under-counting the two OSes where the model reaps by
construction.)

There is a sharper consequence for us: **the spec's chosen POSIX mechanisms
(`killpg`/`setsid`/`getpgid`, `start_new_session`) do not exist on Windows.** So
the spec as written does not merely lack a macOS backstop — it does not run on
Windows at all without a Job-Object path. That is the debt §5d names.

Therefore:

- **Validated by upstream (adopt the shape, all OSes):**
  - *Electron owns the backend.* The spec's VS Code sidecar model **is** t3code's
    model; on Windows/Linux the OS makes parentage reap the child for free.
  - *SIGTERM + grace before force-kill.* t3code's `forceKillAfter` (2s) is the
    clean idiom; the spec's `stop_desktop_record` (SIGTERM → poll → SIGKILL) is
    the Python equivalent. "Always escalate, never leave it to the OS."
  - *Never let `quit()` win the race.* t3code's top-level finalizer stops every
    backend *before* `electronApp.quit()` — the analogue of the spec's
    `bindBackendQuitCleanup` + post-ready exit watcher.
  - *One coordinator.* `DesktopShutdown` validates converging all quit paths onto
    one owned teardown.

- **Kept, but scoped correctly:**
  - *Parent-death watchdog* → **macOS-only backstop** (macOS lacks Job
    Objects/`PDEATHSIG`). Necessary on macOS; redundant-but-cheap on Windows/Linux
    where the OS already reaps. Keep it, label it macOS.
  - *killpg group reaping* addresses our Python **multi-process** backend (uvicorn
    workers + a `mitmdump` child) — t3code's single Node child needs none. Keep
    the intent, but it needs a **Windows Job-Object equivalent** (§5d).

### 5c. Verdict

**t3code validates the parked launcher spec and refines its graceful mechanism;
it does not supersede it.** The Electron-owns-backend re-architecture is
directionally identical to upstream, and on Windows/Linux upstream's parentage
model is the core mechanism to lean on. Refinements to fold in:

1. **Single-coordinator teardown** (upstream's `DesktopShutdown` shape) rather
   than several independently-wired handlers.
2. **Grace-then-force contract** (SIGTERM + bounded grace + guaranteed SIGKILL) on
   *every* teardown path, matching the 2s `forceKillAfter` idiom.
3. **OS-branch the mechanism** (new, from the cross-platform correction):
   parentage + Job Objects on Windows, `PR_SET_PDEATHSIG` + killpg on Linux,
   watchdog on macOS. Adopt t3code's `DesktopLifecycle.ts` platform-branching
   structure (§4.1a) as the template.

The spec's decisions stand; the watchdog stays (scoped to macOS) and the killpg
intent stays (needs a Windows equivalent). See §5d for the concrete debt.

**Premise impact on the launcher (Pass 2).** With Effect-TS viable, "the backend
Electron owns" is best read as **a TS/Effect backend process that spawns the Python
mitmproxy capture process as its managed child** — a *direct* adoption of
`DesktopBackendManager` (per-run `Scope` + `forceKillAfter`), not a Python
re-implementation. This **simplifies the parked spec**: (a) the backend
self-lifecycle, record write/unlink, and even the parent-death watchdog collapse
into the Effect `Scope`/finalizer model on the TS side; (b) the cross-language
env/command/runtime-status DRY item (§4.5) largely dissolves — only the
TS→mitmproxy launch args stay cross-language; (c) the cross-platform teardown (Job
Objects / `PR_SET_PDEATHSIG` / macOS watchdog backstop) now applies to **the Python
mitmproxy child**, managed by Effect's `ChildProcess` + `forceKillAfter`. The one
new seam it introduces: the **breakpoint control plane** (arm/release the held
flow) must cross the TS→Python boundary as explicit RPC, because the pause holds a
live mitmproxy flow in-process (§8d).

### 5d. POSIX-only launcher debt (cross-platform blocker)

With Windows/Linux first-class, the current fork launcher and the parked spec are
both POSIX-shaped and will not run correctly on Windows as written. Verified
symbols:

| Symbol / mechanism | POSIX assumption | Windows reality | Fix direction |
| --- | --- | --- | --- |
| `desktop_runtime.py::is_pid_alive` (`os.kill(pid, 0)` + `errno.ESRCH`/`EPERM`) | signal-0 liveness probe | `os.kill` maps to `TerminateProcess`; signal-0 semantics do not carry and the `errno` codes differ | portable liveness check (`OpenProcess`/`psutil`) or OS branch |
| `desktop_runtime.py::stop_desktop_record` (`os.kill(pid, SIGTERM)` → `SIGKILL`) | graceful SIGTERM then SIGKILL | no SIGTERM delivery to a GUI-less child; `os.kill` hard-terminates | Windows: `CTRL_BREAK_EVENT` to the process group, or Job-Object close |
| `cli/desktop_cmd.py` `start_new_session=True` (two call sites) | POSIX `setsid` detach | ignored/unsupported | Windows: `creationflags=CREATE_NEW_PROCESS_GROUP` (+ `DETACHED_PROCESS`) |
| launcher spec's `os.setsid` / `os.killpg` / `os.getpgid` group model | group leader + `killpg` subtree reap | no POSIX process groups | Windows: a **Job Object** owning the backend subtree (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) |

**Recommendation.** Treat cross-platform teardown as a first-class requirement of
the launcher work, not a follow-up: put the OS branch behind one seam
(`DesktopLifecycle` + a Python `desktop_process` module) — POSIX on macOS/Linux,
Job Objects + `CREATE_NEW_PROCESS_GROUP` on Windows. The spec should state this
explicitly; today it silently assumes POSIX.

---

## 6. Explicit non-alignment (legitimate product divergence — do NOT chase upstream)

These surfaces have no t3code equivalent and should not be aligned. **Non-alignment
here means *product shape*, not implementation *language*:** several of these Python
surfaces are portable to TS/Effect (§8), and porting them is a language/cohesion
choice, not product convergence toward upstream's chat app.

- **Wire proxy + breakpoint editing** — `api/.../addon.py::TransportMattersAddon`,
  `api/.../pause_session.py::handle_breakpoint`. t3code orchestrates agents
  through its own server; it has no transparent wire proxy.
- **Codex explicit HTTPS proxy** — `api/.../codex/transport.py`,
  `api/.../shared_proxy/manager.py::SharedProxyManager`.
- **Tier-1 capture store** — `api/.../storage/disk.py::DiskStorageBackend`. Our
  per-run raw/derived wire artifacts are the product's source of truth; upstream
  has orchestration state, not a wire corpus.
- **Postgres session store + transcript correlation** —
  `api/.../session/writer.py::SessionWriter`,
  `api/.../session/async_dao.py::AsyncSessionDao`,
  `api/.../session/listen.py::SessionEventListener`.
- **Wire inspector UI** — `www/packages/inspector/src/app.tsx::BrowserAppShell`.
- **Canvas-managed runs** — `www/packages/canvas/.../SessionCanvasRoute.tsx`,
  `api/.../run_manager.py::RunManager`, `api/.../api/v1/run_routes.py::run_terminal_socket`.
- **`@tm/activity`** (current branch) — reads session/run lifecycle from our
  Postgres event surface; a product feature, not a fork of anything upstream.
- **Toolchain by product need** — `just`/`uv`/Hatch/PyPI, Biome, loopback routes
  (vs `vp`/electron-builder/Oxlint/`desktop://` protocol). These solve our
  Python-plane + web-served constraints correctly.
- ~~**The Effect-TS runtime model itself**~~ — **CORRECTED (Pass 2, §8): no longer
  non-alignment.** The earlier claim that Effect-TS was inapplicable assumed a
  Python control plane; in fact only the mitmproxy *capture pipeline* is
  Python-bound. Adopting Effect-TS for the **desktop lifecycle** is now direct
  leverage (§8). What stays genuinely non-aligned is Effect for the **capture
  pipeline** — that remains Python because mitmproxy is Python.
- **WSL/SSH/Tailscale/Clerk/updater/preview *product* subsystems** — no analogue
  in our shell; do not import them. **Caveat (corrected — see §4.1a):** the
  *OS-conditional lifecycle pattern* those subsystems sit on **is** leverage now
  that Windows/Linux are first-class, and is reclassified *out* of non-alignment.
  Only the product features (WSL distro detection, Clerk auth, preview
  automation) stay non-aligned; the platform-branching *structure* does not.

---

## 7. Prioritized roadmap (PROPOSAL — nothing committed)

Sequenced tiers. Each item is a proposal for Stuart to approve, defer, or drop.

### Tier 1 — Quick wins (S, low risk)
- **R1. Cross-language contract parity test** (§4.5) — add a test asserting
  `env.ts::ENV` ⇄ `env_keys.py`, `DESKTOP_BACKEND_COMMAND` (TS ⇄ Python), and the
  runtime-status JSON shape match. Cheapest guardrail; closes a live DRY gap.
- **R2. Strict-TS flag audit** (§4.6) — confirm which upstream strict flags we
  already set; add the missing ones one at a time.
- **R3. Provenance headers** (§2) — one-line "adapted from upstream `file::symbol`"
  headers on inherited desktop files, so future re-scouts diff intent.

### Tier 2 — Structural (M, low–moderate risk)
- **R4. Decompose `main.ts` + `desktop_cmd.py` using upstream seam names** (§4.4)
  — split `desktop/src/main.ts` into `DesktopLifecycle`/`DesktopWindow`/env
  modules and `cli/desktop_cmd.py` (697 LOC, at the limit) per the launcher
  spec's own module plan (`desktop_orchestration.py`, `desktop_backend_process.py`).
  Names from t3code, no Effect. **Do this before the next desktop feature.**
- **R4b. Adopt t3code's OS-conditional lifecycle structure** (§4.1a) — port the
  platform-branching shape from `DesktopLifecycle.ts` (signal registration by OS,
  `!== "darwin"` window-quit) into the `DesktopLifecycle` seam from R4. Prereq for
  R6's OS-branched teardown.
- **R5. `.electron-runtime` pinned-binary dev/smoke** (§4.2) — adopt if dev-launch
  flakiness appears; hold otherwise. Pins the right per-OS Electron binary, so it
  also de-risks Windows/Linux CI.

### Tier 3 — Deep (M–L, moderate risk) — the correctness core
- **R6. Execute the parked launcher spec** (`launcher-spec-desktop-relaunch.md`),
  folding in the §5c refinements (single-coordinator framing; grace-then-force
  contract on every path; **and OS-branched teardown** — parentage + Job Objects
  on Windows, `PR_SET_PDEATHSIG` + killpg on Linux, watchdog on macOS). This is
  the highest-value item overall; it fixes the active orphan bug on both the owned
  path (missing `quitOnWindowAllClosed` on macOS) and the detached path (viewer
  close never reaching `stop_desktop_record`). **Cross-platform blocker:** close
  the POSIX-only launcher debt (§5d) *as part of* this work, not after — the spec
  does not run on Windows as written. Sequence per the spec's own slice plan,
  inserting the OS-branch seam.
- **R7. Schema-validated IPC** (§4.3) — deferred until the bridge grows.

**Suggested order:** R1–R3 (a day of hardening) → R4 + R4b (unblocks safe desktop
growth and gives the OS-branch seam) → R6 (the real fix, cross-platform) → R5/R7
as triggered.

---

## 8. Strategic option — converge control plane on TS/Effect (Python as a mitmproxy sidecar)

Response to the Pass-2 premise correction. This is a **strategic proposal, not a
commitment**, and it is deliberately honest about porting cost.

### 8a. What is truly mitmproxy-bound (verified catalog)

The Python plane classified by whether it *requires* Python (mitmproxy) or is
Python-by-choice. Method: `rg` for mitmproxy imports/usage across `api/` + symbol
inspection. "Bound" = imports mitmproxy at runtime **or** manipulates live
`HTTPFlow`/`WebSocketMessage` objects (most such modules import mitmproxy only
under `TYPE_CHECKING` but are still flow-coupled at runtime).

| Surface (file+symbol) | LOC scale | Verdict | Note |
| --- | --- | --- | --- |
| `shared_proxy/subprocess.py` (`DumpMaster`), `shared_proxy/addon.py`, `shared_proxy/process.py` | ~4.1k | **HARD-BOUND** | The mitmproxy process + addon + supervision. This *is* the proxy. |
| `addon.py::TransportMattersAddon`, `addon_handlers.py` | top-level | **HARD-BOUND** | The addon mitmproxy loads; flow hooks. |
| `codex/transport.py`, `codex/exchange*.py` (`is_codex_websocket_flow`, `ensure_codex_transport_state`, …) | ~12.2k | **HARD-BOUND (flow-coupled)** | Operate on live `flow.metadata`/`flow.websocket`; run in-process with the proxy. |
| `pause_session.py`, `breakpoint.py`, `response_stream.py`, `exchange_recorder*.py`, `flow_state.py`, `request_pipeline.py` | spread | **HARD-BOUND (flow-coupled)** | Breakpoint hold/release, streaming capture, exchange recording — all touch the live flow. |
| `adapters/*::matches(flow)` | entry only | **PARTIAL** | The `matches()` flow entry is coupled; the IR/normalization it drives is portable (next row). |
| `index/*`, `adapters/*` parsing → `ir.ContentBlock`/`NormalizedTurn` | ~5.9k | **PORTABLE** (large) | Pure byte→IR transformation; big surface to re-express in TS. |
| `session/*` (`SessionWriter`, `AsyncSessionDao`, `SessionEventListener`) | ~8.2k | **PORTABLE** | Postgres writes + LISTEN/NOTIFY (asyncpg). TS analogue: `pg`. Non-trivial. |
| `api/*` (FastAPI routes: run/session/breakpoint/terminal) | ~11.5k | **PORTABLE** | HTTP/WS read+stream API. Already how `@tm/activity` (TS) reads Postgres. |
| `run_manager.py`, `supervisor*.py`, `pty_session.py`, `api/v1/terminal.py` | spread | **PORTABLE** (non-trivial) | PTY + process supervision. TS analogue: `node-pty`. Real effort. |
| `cli/desktop_cmd.py`, `desktop_runtime.py`, `cli/ports.py` | ~1.4k | **PORTABLE (easy)** | The desktop launcher — exactly what `DesktopBackendManager` replaces. **Zero** mitmproxy. |
| `storage/*` (`DiskStorageBackend`) | ~3.8k | **PORTABLE** | Tier-1 disk artifacts. fs + serialization. |

**Honest answer to "how much is truly mitmproxy-bound":** the **capture pipeline**
— proxy subprocess + addon + all live-flow logic (Codex transport, breakpoint hold,
response streaming, exchange recording, adapter flow-matching). That is roughly **a
third of the plane** (`shared_proxy` + `codex` + the flow-capture modules ≈ 20k+
LOC), and it is genuinely Python because mitmproxy is Python. The **desktop
lifecycle, session store, read/stream API, run/PTY management, storage, and the
IR/normalization output are Python-by-choice**. Stuart's premise holds: the desktop
lifecycle in particular has **zero** mitmproxy coupling.

### 8b. The reshaped architecture

- **Python sidecar owns:** the mitmproxy process, flow capture, Codex WS/HTTP
  derivation, the breakpoint flow-hold, and writing captured artifacts (Tier-1 disk
  + Postgres session store — or it writes raw and TS owns the store; see 8c).
- **TS/Effect owns:** the desktop lifecycle (direct `DesktopBackendManager` lift),
  the read/stream API, run/PTY management (canvas), and the UI. It spawns the Python
  sidecar as a managed `ChildProcess` under an Effect `Scope`.
- **The clean process boundary is Postgres + Tier-1 disk** (already serialized),
  plus one **control channel** for the breakpoint arm/release (the only live
  in-process coupling today).

### 8c. Two horizons

**(a) NEAR-TERM — desktop lifecycle in Effect-TS now (S–M, low–moderate risk).**
Adopt t3code's `DesktopLifecycle`/`DesktopBackendManager`/`DesktopShutdown` in the
`desktop/` package (already TS). The managed child is the existing Python mitmproxy
backend, unchanged. This is **direct upstream reuse**, fixes the orphan bug with the
proven Effect `Scope` + `forceKillAfter` model, and dissolves most of the
cross-language desktop DRY. **Unlocks:** a single-language, upstream-aligned
lifecycle; the parked launcher spec collapses to "adopt `DesktopBackendManager` +
OS-branch the child reap." **Cost:** introduces Effect as a `desktop/` dependency
(t3code's lifecycle is Effect-native); the alternative is re-expressing the pattern
in plain TS (what the imperative shell + launcher spec already do) at lower
fidelity. **Risk:** the breakpoint control channel (TS→Python) is the one new seam.

**(b) BROADER — progressively port the portable surfaces to TS/Effect (L, staged,
optional).** Move session store, read/stream API, run/PTY management, storage, and
eventually IR/normalization to TS, leaving Python a pure **mitmproxy sidecar**.
**Honest cost:** tens of thousands of LOC (`api/` ~11.5k + `session/` ~8.2k +
`index`/`adapters` ~5.9k + storage ~3.8k + run/PTY), much of it load-bearing product
logic with real test suites. A **multi-quarter effort**, not a refactor. Sequence,
lowest-risk first: (1) desktop lifecycle (horizon a); (2) run/PTY management
(self-contained, `node-pty`); (3) read/stream API + session *reads* (TS already
reads Postgres via `@tm/activity`); (4) session *writes* + LISTEN/NOTIFY; (5)
storage; (6) IR/normalization (largest, last). Each stage keeps Postgres/disk as the
Python↔TS boundary so it lands incrementally.

### 8d. Honest risks

- **Do not oversell the rewrite.** Horizon (b) is a large, optional strategic bet;
  its value is single-language cohesion + upstream reuse, not a bug fix. Horizon (a)
  is the high-ROI, low-regret move.
- **Breakpoint control plane is the sharpest coupling.** The pause holds a live
  mitmproxy flow in-process (`pause_session.py`, `breakpoint.py`). Splitting
  API(TS)↔proxy(Python) requires an explicit RPC/IPC channel for arm/release/edit
  (an `asyncio.Event`/live flow does not cross a process boundary).
- **Codex capture stays Python** regardless (~12.2k LOC flow-coupled). "Python =
  mitmproxy sidecar" means "mitmproxy + all flow-capture logic," not "just the addon
  file."
- **IR/normalization is the long pole** (~5.9k LOC of adapter/index parsing with
  correctness-critical tests); leave it last, or leave it in the sidecar.
- **Verification scope.** I catalogued coupling by imports + symbol inspection, not
  by running a port; per-surface effort estimates are directional, not measured.

### 8e. Canvas → TS/Effect port (near-term candidate)

Stuart is leaning toward porting Canvas to TS/Effect for the battle-tested code it
unlocks. Scoped rigorously below: the terminal/PTY reuse claim is **verified**; the
capture seam is **clean but real**.

**Current Canvas shape (file+symbol).**
- *Frontend (already TS):* `www/packages/canvas/src/session-canvas/SessionCanvasRoute.tsx::SessionCanvasRoute` (React + xterm).
- *Backend (Python):* `run_manager.py::RunManager` (on `app.state`; `spawn`/`attach`/`detach`/`terminate`/`list`/`close`); the terminal transport in `run_terminal.py` (`ScrollbackRing`, `TerminalFanout`, `TerminalAttachment`, `PtyChunk`); the PTY spawn `pty_session.py::spawn_pty_process`; the WS endpoint `api/v1/run_routes.py::run_terminal_socket` + `create_run`; and capture setup `captured_run.py::prepare_captured_run`.

**1. What moves + what to reuse (verified against t3code).** t3code has a
battle-tested Effect terminal stack (`apps/server` depends on `node-pty`; `apps/web`
uses `@xterm/xterm`):

| Canvas (ours, Python) | t3code reuse target | Notes |
| --- | --- | --- |
| `RunManager` (terminal/attach half) | `apps/server/src/terminal/Manager.ts::TerminalManager` (Context.Service: `attachStream`/`write`/`resize`) | Effect service; open/attach/write/resize/history-reset lifecycle. |
| `pty_session.py::spawn_pty_process`, `supervisor_pty*.py` | `apps/server/src/terminal/PtyAdapter.ts` + `NodePtyAdapter.ts` (+ `BunPtyAdapter.ts`) | Pluggable PTY adapter over `node-pty`; `resizePtyProcess`. |
| WS `run_terminal_socket` + `www/packages/core/src/transport.ts` run types | `packages/contracts/src/terminal.ts` (`TerminalOpenInput`/`AttachInput`/`WriteInput`/`ResizeInput`/`AttachStreamEvent`/`SessionSnapshot`) | Schema-validated terminal wire protocol; replaces our ad-hoc WS shape. |
| xterm in `SessionCanvasRoute.tsx` | `apps/web` xterm wiring | Same `@xterm/xterm`; renderer largely stays. |
| `run_terminal.py::ScrollbackRing` + `TerminalFanout` (seq'd byte-capped ring, multi-attach fan-out, per-attachment queues, resume-from-seq) | `TerminalSessionState.history: string` + `attachStream` | **Partial reuse.** t3code has single-history + attach-stream; our **multi-viewer fan-out with resume-from-seq** is richer and must be preserved/re-ported, not lifted. |

Verdict on the "battle-tested code" claim: **true for the PTY adapter, terminal
session lifecycle, resize, wire contract, and xterm** (direct reuse). **Our
multi-attach seq-resume fan-out is a feature to preserve**, not something t3code
hands us. Net: the terminal transport de-risks substantially; the fan-out/scrollback
semantics are ours to carry over.

**2. The capture seam (the crux — verified).** Canvas spawns *captured* runs:
`RunManager.spawn` calls `prepare_captured_run` (injected in `RunManager.__init__`),
which — verified in `captured_run.py::prepare_captured_run` — allocates proxy/web
ports, writes the run manifest, and **starts the mitmproxy proxy process**
(`start_prepared_proxy` under a Python `ProcessSupervisor`), returning
`tuple[CapturedRunSpawnSpec, CapturedRunLease]`:
- `CapturedRunSpawnSpec` = a **serializable launch envelope**: `client` (agent
  command), `launch_env` (proxy env vars), `proxy_port`/`web_port`, `storage_dir`,
  `mitmdump_log`, `managed_session`, `harness`. The PTY-spawned agent needs only
  `client` + `launch_env` — plain strings that cross a process boundary trivially.
- `CapturedRunLease` = a **live Python handle**: `_supervisor` (the running
  mitmproxy), `_workspace_lock`, `_resource_stack` — torn down at run end.

The seam therefore decomposes cleanly:
- **TS/Effect run manager owns:** PTY spawn (from the envelope's `client`+`launch_env`),
  terminal fan-out, scrollback ring, attach/detach, run state/lifecycle, the WS
  terminal endpoint.
- **Python must own (RPC seam):** `prepare_capture(request) -> CapturedRunSpawnSpec`
  (start the mitmproxy proxy, return the envelope) and `release_capture(run_id)`
  (terminate the proxy, drop the workspace lock + resource stack). The lease lives in
  Python; TS references it by `run_id`.

**Seam verdict: clean and well-bounded, NOT invasive** — a 2-call bind/release RPC
over a serializable envelope, directly analogous to the breakpoint arm/release seam
(§8d). Honest caveat: it splits a run into **two coupled lifecycles** (TS terminal +
Python capture) joined by `run_id`/lease, so teardown ordering must be designed
(PTY-exit → release capture; who authoritatively ends the run). A design task, not a
rewrite. It holds only because the proxy + capture stay Python (Pass-2 premise); the
terminal half is genuinely independent of mitmproxy.

**3. Effort / risk / sequencing.**
- **Hosting dependency → sequence *with or after* the desktop-lifecycle port.** The
  Canvas backend today is served by the Python FastAPI app (`/runs`, WS terminal on
  `app.state`) and is consumed by both the desktop canvas **and** the web-served
  `/canvas`. A TS run manager needs a **TS/Effect host** to serve those routes —
  exactly what horizon (a) stands up. So Canvas is the natural **first big surface in
  horizon (b)**. (Porting it with no TS host would strand the run manager in Electron
  main and break the web-served `/canvas` path.)
- **De-risked by reuse:** the PTY adapter, terminal session lifecycle, resize, wire
  contract, and xterm come from t3code rather than reimplemented — the historically
  fiddly parts (PTY portability, resize races, wire framing) arrive battle-tested.
  **Not de-risked:** our multi-attach seq-resume fan-out, the capture RPC seam design,
  and the serving-host question.
- **Honest cost: Medium.** Larger than the desktop-lifecycle lift (horizon a) but
  well-bounded: terminal transport ≈ direct reuse; fan-out/scrollback ≈ port our
  ~213-LOC `run_terminal.py` semantics to TS; capture seam ≈ 2 RPCs + teardown
  ordering; plus the TS host to serve `/runs`. It is the **highest-value horizon-(b)
  surface** precisely because the reusable t3code code is densest here.
- **Risk flags:** (i) two-lifecycle teardown ordering (terminal vs capture); (ii)
  preserving multi-viewer resume-from-seq (a real product behaviour absent from
  t3code's simpler history model); (iii) the serving host must cover both desktop and
  web-served `/canvas`.

*Unverified:* I did not confirm t3code's `TerminalManager` supports multi-viewer
resume-from-sequence (its `history: string` + `attachStream` reads as single-history
replay, not our seq-cursor fan-out); treat that parity as a port task, not reuse.

## 9. Open questions & risks

1. **Detached-backend ownership policy (product decision, blocks R6 framing).**
   Should a detached backend intentionally survive Electron-viewer close, or
   should viewer close stop it? The stop seam exists
   (`desktop_runtime.py::stop_desktop_record`, used by `channel_cmd.py::stop`) but
   is not wired to hosted window close. The launcher spec assumes "stop on close";
   confirm before executing.
2. **Cross-platform scope — RESOLVED (Windows/Linux first-class, confirmed with
   Stuart).** An earlier draft wrongly treated macOS as the sole target; the §5
   verdict is now framed for all three OSes (parentage is the core mechanism on
   Windows via Job Objects and Linux via `PDEATHSIG`; the watchdog is a macOS-only
   backstop). The concrete open work this creates: close the POSIX-only launcher
   debt (§5d). Remaining sub-question: which Windows detach/reap primitive do we
   standardize on — a Job Object, or `CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT`?
3. **`forceKillAfter` grace budget.** Upstream uses 2s. Confirm our Python backend
   (uvicorn workers + `mitmdump` child) actually flushes and exits within the
   chosen grace on SIGTERM, or force-kill drops in-flight capture writes. Not yet
   measured.
4. **Should the TS desktop contract be generated from Python schemas** (R1's
   stronger form) rather than parity-tested? Generation is more DRY but adds a
   codegen step; parity test is the pragmatic first move.
5. **`@tm/activity` topology.** Branch-local experiment or future core workspace
   member? Out of scope for alignment, but it affects where any shared desktop
   contract code would live.
6. **Unverified upstream internals.** I did not read t3code's `DesktopShutdown`
   Deferred or the pool layer-scope wiring first-hand (the scout did, at high
   confidence). I verified directly this round: the `forceKillAfter`/`killSignal`
   mechanism (`DesktopBackendManager.ts`), the OS-conditional signal/quit branches
   (`DesktopLifecycle.ts`: `!== "win32"` / `!== "darwin"`), the WSL subsystem
   files, and our fork's POSIX-only launcher symbols (§5d). The §5 argument depends
   on the scout's account of the coordinator being accurate; it is consistent with
   the code I did read.

---

*Prepared as a decision layer over the two alignment scouts and the launcher
spec. All recommendations are proposals; no work is committed.*
