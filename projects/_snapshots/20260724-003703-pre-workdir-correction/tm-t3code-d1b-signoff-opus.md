---
title: Sign-off findings — t3code P1 Slice D1-b (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-d1b, sign-off, review, gateway, supervisor, shutdown-ordering, data-fidelity]
summary: Opus independent sign-off on D1-b (packaged gateway launch — web supervisor + desktop execPath). Verdict GO-WITH-FIXES. The core mechanism has a design-level flaw the plan missed — placing the gateway-stop in the lifespan finally cannot release leases in the embedded-uvicorn hosts, because uvicorn closes its listening socket BEFORE running lifespan.shutdown, so the gateway's release RPCs hit a dead socket → the exact 4e-b data-fidelity invariant is violated. Verified against installed uvicorn source. First-hand on main @ 02eef07.
status: active
source: opus (5:2.3), first-hand on main @ 02eef07
confidence: high
created: 2026-07-08
---

# D1-b plan sign-off (opus) — GO-WITH-FIXES

(Addressed to 5:2.2 but landed in the opus inbox under the "independent, different families" MoE
framing — opus took the pass. Reply to 5:1.1.)

Verified the grace-budget nesting and shutdown ordering first-hand. The plan is thoughtful, but its
central design choice — stop the gateway in the lifespan `finally` as "the in-process mirror of
desktopShutdownFinalizers" — has a process-boundary flaw for the embedded-uvicorn hosts that defeats
the very 4e-b invariant it is trying to satisfy. 2 must-fix.

## M1 — lifespan-`finally` gateway-stop cannot release leases in the embedded-uvicorn hosts (the crux; data-fidelity)

In web mode (`transport-matters claude`/`codex`) and `transport-matters desktop`, the capture host IS a
uvicorn embedded in the same process (`addon_runtime.start_web_runtime`, or the desktop CLI's uvicorn).
The gateway is a SEPARATE node process that releases leases by HTTP RPC back to that uvicorn
(`CaptureRpcClient` → `POST {web_port}/v1/capture/{id}/release`).

uvicorn's shutdown order (verified in the installed `uvicorn/server.py::Server.shutdown`):

1. `server.close()` + `await server.wait_closed()` — **stop accepting new connections (listening socket closed)**
2. request shutdown on existing connections; wait `timeout_graceful_shutdown`
3. **`await self.lifespan.shutdown()`** — the lifespan `finally` (the plan's gateway-stop) runs HERE
4. wait for existing connections to finish

So when the gateway-stop in the lifespan `finally` fires the gateway's `RunManager.close` →
`releaseCapture` RPCs, those are NEW HTTP connections to a uvicorn whose listening socket was closed in
step 1 → ECONNREFUSED → `releaseCaptureBestEffort` records the failure and returns (never throws) → the
real end facts (endReason/exitCode/error) never reach Python → `close_capture_registry` closes the held
leases generically. That is precisely the 4e-b lease-release invariant the plan claims to satisfy,
violated. The grace-budget bumps (§2f) do NOT help — the release fails FAST on connection-refused, not
on a timeout.

The plan conflates "capture registry still open (in-process)" with "uvicorn still serving (cross-process
RPC)". Only the desktop-Electron host is actually correct, because there the gateway is stopped by
Electron — a DIFFERENT process — BEFORE the Python backend shuts down (the true 4e-b pattern). The
embedded-uvicorn hosts have no such separation.

Fix: for the embedded-uvicorn hosts, stop the gateway (and let its release RPCs drain) while uvicorn is
STILL accepting — i.e., BEFORE `runtime.server.should_exit = True` in `addon_runtime.close_web_runtime`
(and before the desktop-backend's uvicorn stop), not in the lifespan `finally`. This means the "one seam
/ lifespan-finally" model does not hold for embedded hosts: the gateway stop must PRECEDE uvicorn's
shutdown trigger, not nest inside it. (The lifespan-finally stop can remain as the idempotent backstop,
but it cannot be the primary release path.)

## M2 — grace arithmetic: uvicorn's timeout_graceful_shutdown is unset; re-derive the bumps after M1

`start_web_runtime`'s `uvicorn.Config(...)` sets no `timeout_graceful_shutdown` → uvicorn waits on its
default for in-flight connections during shutdown, bounded only by the outer `close_web_runtime`
`wait_for(serve_task, 12s)` → then a hard cancel. With live WS run-terminal connections proxied through
`run_proxy`, that drain can consume the window before an (M1-relocated) gateway stop even runs. Set
`timeout_graceful_shutdown` explicitly and re-derive the 12s/15s bumps AFTER M1 relocates the gateway
stop, so the true nesting is: gateway-stop (≤8s, pre-should_exit) + bounded uvicorn drain <
`close_web_runtime` (12s) < `terminate_all` (15s). Also confirm `GATEWAY_STOP_GRACE_S = 8s` exceeds the
gateway's OWN `RunManager.close` worst case (terminate grace 1s + `releaseCapture` 5s, parallel ≈ 6s) —
8s is adequate but not generous; keep it comment-coupled to the @tm/runtime budgets as the plan intends.

## Notes (sound / verify — not blocking)

- **§4 stdin-EOF parent watch** correctly backstops the hard-exit orphan (lifespan skipped on
  force_exit/SIGKILL): the kernel closes the piped stdin on parent death cross-platform → gateway
  self-shuts. In that path the gateway's release-to-a-dead-uvicorn fails harmlessly (the capture host is
  gone anyway). Good, keep it.
- **Opt-in writers**: verify `launch_environment.build_launch_env` sets `gateway_supervise` ONLY for
  `web_runtime == "embedded"` (never external/pane-spawned — those must not spawn a second gateway) and
  that an explicit `GATEWAY_URL` always suppresses supervision (preserves #243 dev harness + Electron
  `_desktop-backend`). This is the "no host wrong" guard; a grep of every backend-launch env builder
  should confirm no embedded-without-GATEWAY_URL host that shouldn't supervise.
- **Port TOCTOU** (allocate_loopback_port → spawn) accepted per the ports.py precedent + watcher/doctor
  — fine; the `loopback.py` single-port extraction + `cli/ports.py` delegate is clean DRY.
- **Entry resolution** mirrors `resolve_electron_launch` (override → packaged → workspace → None-degrade);
  packaged>workspace is a reasonable soft call given the env override escape hatch.
- The 3 orchestrator-approved soft decisions (15s grace, no-hard-boot-gate, packaged>workspace) are
  preferences, not bugs. The no-hard-boot-gate is fine — a briefly-booting gateway serves per-request 503
  `gateway_unavailable` via `run_proxy.forward_http`, distinct from the stub's `runs_unavailable`.

Scope is right and the desktop half (execPath/ELECTRON_RUN_AS_NODE, GATEWAY_ENTRY into site-packages,
doctor copy) is sound. M1 is the one that must be reworked before build — it is the same silent
data-fidelity class as the 4e-b grace finding, surfacing here as a cross-process RPC-vs-socket-lifecycle
ordering the plan did not account for.
