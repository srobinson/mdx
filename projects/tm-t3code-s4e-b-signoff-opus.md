---
title: Sign-off findings — t3code P1 Slice 4e-b (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-4e-b, sign-off, review, desktop, gateway, shutdown-ordering]
summary: Opus independent plan sign-off on 4e-b (desktop spawns gateway as second managed child). Verdict GO-WITH-FIXES. 4 must-fix; sharpest is a grace-budget mismatch that silently defeats the gateway-before-Python end-fact fidelity the slice exists to protect. All symbols read first-hand on main @ ce294eb (4e-a merged).
status: active
source: opus (5:2.3), reconciled against main @ ce294eb
confidence: high
created: 2026-07-08
---

# 4e-b plan sign-off (opus) — GO-WITH-FIXES

Reviewed `tm-t3code-s4e-b-scout.md` against main @ ce294eb, symbols read first-hand.
Plan is fundamentally sound: DRY generalization is clean, ordering is enforced by
construction, origin trust confirmed, ports additive. 4 must-fix, emission/end-fact
weighted.

## Confirmed sound (no action)

- **§2a generic manager.** `DesktopBackendManager` (desktop/src/backend/DesktopBackendManager.ts)
  touches only `backend.child` generically; `start(options)`/`launchBackend` default to
  `BackendLaunchOptions`/`launchBackendProcess`. `DesktopBackendManager<TOptions = BackendLaunchOptions>`
  keeps both existing construction sites (main.ts::registerAppLifecycle line 276) compiling with zero
  behavior change. No hidden Python coupling.
- **§2b origin trust.** `terminal_bridge.request_origin_from_headers` requires the Host header port ==
  `settings.web_port`; `CaptureRpcClient.request` sends `origin: baseUrl.origin` + Host `127.0.0.1:{webPort}`.
  With `captureRpcUrl = http://127.0.0.1:{webPort}` and webPort == Python's `--web-port`, `origin_allowed_from_headers`
  passes on the `normalized_origin == request_origin` branch. No trust-config change. Already proven by 4e-a's
  live capture RPC. (Note: gateway is unconsumed in 4e-b, so this path is config-correct-for-4e-d, not exercised now.)
- **§2c spawn shape is genuinely Q8-safe.** `node --import tsx <entry>` makes node the direct child that installs
  the SIGTERM handler (`runGatewayProcess::installShutdownHandlers`); tsx loads in-process via `--import`, no
  wrapper subprocess to swallow the signal (unlike `tsx <entry>` or `pnpm start`). graceThenForce's
  `child.kill("SIGTERM")` reaches the handler.
- **§4 ordering enforced by construction.** `DesktopShutdown.#runShutdown` awaits finalizers sequentially in
  array order (log-and-continue on error), so `finalizers: [() => gatewayManager.stop(), () => backendManager.stop()]`
  guarantees gateway.stop() fully resolves before backend.stop() is invoked.
- **§7.1 ordering test does fail on inversion** provided it asserts python SIGTERM strictly after gateway exit
  (as specified), since finalizer order is data and inversion inverts the recorded log.
- **§2d ports additive.** TS `normalizeChannelSpec` (`requirePort`) and Python `_build_channel_spec`
  (`_require_port`) both pick named keys and ignore extras; 8789/8799 are free slots beside proxy/web with no
  cross-channel collision.

## Must-fix (build input for Fable)

### M1 — Grace budget defeats the end-fact fidelity the slice exists for (sharpest; the ordering test will NOT catch it)

The gateway child's stop grace is `DESKTOP_BACKEND_STOP_GRACE_MS = 2_000` (lifecycle/graceThenForce.ts).
graceThenForce SIGKILLs the gateway at 2s. But the gateway's graceful close
(`runGatewayProcess::closeGatewayResources → RunManager.close`) runs `settleRun` per run in **parallel**, each
bounded by `terminateGraceMs` (1s) then `releaseCaptureBestEffort` (`DEFAULT_RELEASE_CAPTURE_TIMEOUT_MS = 5s`,
RunManager.ts). So with **any** live run whose release is slow, the gateway's graceful close exceeds the 2s desktop
grace → gateway is SIGKILL'd mid-release → the runs' real `endReason`/`exitCode` never reach Python's
`CaptureLeaseRegistry.release_capture` → Python's lifespan `registry.close()` emits a generic `shutdown` RUN_EXITED
instead (exactly §4's stated inversion failure-mode, reached here even with correct ordering).

The whole point of gateway-before-Python is to let the gateway emit real end facts before Python dies; a 2s grace
shorter than the gateway's own close budget silently reduces that to Python's generic `shutdown` under load — the
condition where it matters most.

Fix: give `gatewayManager` a `graceMs` ≥ the gateway's `RunManager.close` worst case (terminate grace + release
timeout + margin), or shrink the gateway's internal budgets, and decide it explicitly. The §7.1 ordering test uses
prompt-exiting fakes and cannot surface this; add a test where the fake gateway's stop resolves slower than the grace
and assert either the grace covers it or the degradation is the accepted contract.

### M2 — Dual-child startup failures must be attributable + diagnosable (hard-gate makes this load-bearing)

D-b1 hard-gate is accepted, so a gateway that fails readiness quits the whole desktop via
`showBackendStartupFailure` (main.ts). But `BackendHealthTimeoutError`/`BackendProcessExitError` (backendProcess.ts,
backendHealth.ts) say "backend" generically. A dev with a perfectly working Python canvas (runs still Python-served
in 4e-b) gets a bricked desktop and a dialog that doesn't say the **gateway** failed or why (node missing / tsx
missing / entry not found / port taken / node-pty ABI mismatch). Make the gateway's readiness/spawn/exit errors name
the gateway and likely cause; `showBackendStartupFailure` must distinguish the two children. Without this, hard-gate
turns every gateway-toolchain hiccup into an opaque brick.

### M3 — resolveGatewayEntry must validate existence and terminate at fs root (fail at resolve time, not as a 15s health timeout)

`resolveGatewayEntry` marker-walks up to `pnpm-workspace.yaml`. It must (a) bottom out with a typed error at
filesystem root (no infinite loop / garbage join), and (b) stat the resolved `packages/gateway/src/main.ts` and throw
a typed "gateway entry not found" **before** spawning — otherwise a wrong resolution surfaces as an opaque 15s health
timeout (compounds M2). Avoiding depth-relative `join(moduleDir, "..", "..")` is correct (that class broke main after
PR8).

### M4 — Dual readiness must not leak an unhandled rejection from the surviving child's exit watcher

`waitForLaunchedBackend` races health vs `watchBackendExitBeforeReady(child).promise` (a `Promise<never>`). When one
child fails readiness and the code then stop-both's, the **other** child's exit watcher rejects on its kill with no
awaiter → `unhandledRejection`. Structure the dual race (allSettled, or pre-attach `.catch`, or await both on the
failure path) so the loser's rejection is handled. Add to test §7.2: "gateway exits pre-ready stops Python AND
produces no unhandled rejection."

## Softer notes (not must-fix)

- **node-pty ABI (dev shape).** The dev spawn assumes system-PATH `node` is ABI-compatible with pnpm's node-pty
  prebuild. A mismatch crashes the gateway at boot (node-pty imported by the runtime router) → hard-gate brick. Real
  in dev, not only in the deferred packaged case (§2c mentions ABI only for packaging). Feeds M2's diagnosability.
- **gatewayPort is required-not-optional** in both parsers. Add it to BOTH channel entries in channel-specs.json and
  both parsers in the same change, or startup parse throws.

Scope discipline clean: no cutover, no deletion, gate stays off, both run paths stay live. Only shared surface
touched is `waitForBackendHealth`'s signature (default-compatible).
