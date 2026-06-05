---
title: "Tier 2 design: shared multi-mode mitmdump for 50+ captured runs"
type: design
tags: [transport-matters, performance, proxy, captured-run, addon, session-store, scaling, tier-2]
summary: "Collapse one-mitmdump-process-per-run into a single long-lived multi-mode mitmdump that demuxes by listen port to a per-run runtime binding, sharing one Postgres pool / httpx client / token counter. Removes the 50-process, 50-pool, ~15GB ceiling that Tier 1 cannot."
status: proposed
confidence: medium-high
created: 2026-06-16
depends_on: branch perf/spawn-concurrency-reliability (Tier 1)
---

# Tier 2: shared multi-mode mitmdump

## Why Tier 1 is not enough for 50

Tier 1 (admission semaphore, off-loop cached preflight, typed retryable timeout, pool `min_size=0`,
frontend stagger) makes a burst of spawns **reliable and bounded**: no more 500s, no event-loop
stall, graceful queueing. But it does not change the steady-state cost. At 50 concurrent runs you
still pay, per run:

- 1 `mitmdump` process (Python + mitmproxy + httpx + psycopg pool + addon imports, ~80-150 MB) plus
  1 client process. ~250-500 MB/run -> **~15 GB at 50**.
- Its own Postgres pool (now `min_size=0`, `max_size=10`). Idle runs hold ~0 now, but every actively
  writing run can grow toward 10 -> the **~100-connection ceiling is the first hard wall** at roughly
  15-30 active runs.
- A fresh interpreter start importing the whole `transport_matters` stack.

The only way to "support 50 easily" is to stop paying these per-run. That means **one proxy process**
for all runs.

## Target architecture

One long-lived `mitmdump` started once (at API startup or first captured run), running mitmproxy's
**multi-mode** feature: many reverse-proxy listeners in a single process, each
`reverse:{upstream}@127.0.0.1:{proxy_port}`. Each captured run still gets its own loopback
`proxy_port` and the client contract is unchanged (`ANTHROPIC_BASE_URL=http://127.0.0.1:{proxy_port}`
from `captured_claude.py::build_claude_captured_invocation`). The addon resolves the **per-run
runtime from the listen port** the flow arrived on (mitmproxy exposes the server/listen address on
the flow), so one addon instance serves all runs.

Shared core (one instance, process-wide):
- one Postgres pool, one httpx upstream client, one `TokenCounter`, one transcript-tailer registry.

Per-run binding (cheap, created/destroyed per run):
- `run_id`, `storage_dir`, `upstream`, owned-session binding, registered against its `proxy_port`.

Spawning a run becomes: allocate a loopback port -> **register a reverse mode + a per-run binding on
the shared proxy** -> spawn the client. Teardown becomes: **deregister the mode + binding**, never
kill the shared process.

## The one open question (de-risk first, before any refactor)

Does mitmproxy support **adding/removing reverse `mode` entries at runtime** on a running instance
(via the `mode` option list, the addon API, or a control channel), or only at process start?

- If **runtime mode mutation works**: incremental register/deregister per run. Best case. Prototype:
  start `mitmdump` with the addon, then mutate `ctx.options.mode` (add/remove a `reverse:...@:port`)
  while running and confirm the new listener accepts traffic and a removed one stops, with no flow
  leakage across ports.
- If **modes are start-time only**: fall back to a **small pool of shared proxies** (e.g. 4-8
  processes, each multi-mode, started with a batch of modes), or a **restart-with-debounce** strategy
  (rare). Even a fixed pool of 8 multi-mode proxies serving ~6-7 runs each collapses 50 processes ->
  8 and 50 pools -> 8.

This prototype is a half-day spike and gates the whole effort. Do it first.

## Seams to change (verified file::symbol)

| Seam | Today | Tier 2 |
|---|---|---|
| `cli/launch_runtime.py::build_mitmdump_argv` | emits one `--mode reverse:{upstream}` + one `--listen-port` | emit/maintain a multi-mode listener set, or a control op that adds a mode |
| `captured_run.py::prepare_captured_run` + `cli/runner.py::start_prepared_proxy` | `sup.spawn("mitmdump", ...)` per call, then `wait_for_port_ready` | register a route on the shared long-lived proxy (add listen mode + per-run binding); readiness = new listener accepts |
| `addon.py::TransportMattersAddon` (+ `addon_handlers`) | one process-global runtime; `addons = [TransportMattersAddon()]` | resolve per-run runtime from the flow's listen port on each event |
| `addon_runtime.py::load_runtime` / `load_capture_runtime` | one runtime from one `Settings`, one `SessionWriter`/pool/tailer | split: shared core (pool, httpx, TokenCounter, tailer registry) + per-run binding |
| `config.py::Settings` | run identity (`run_id`, `storage_dir`, `upstream`) carried as per-process env | per-run context attached to the route registration, not process env |
| `run_manager.py::CapturedRunLease` / `ManagedRun.lease` teardown (`RunManager.terminate`, `_rollback_post_prepare`) | lease owns a `ProcessSupervisor`; teardown `supervisor.terminate_all()` | teardown deregisters the run's route; never kills the shared process |
| `session_store_preflight.py::check_session_store` | per-run preflight (Tier 1: off-loop + cached) | once at shared-proxy startup |

## Proposed slicing (spec each, build small, adversarial review on every slice)

1. **Spike**: prototype runtime mode add/remove on a live mitmdump. Output: go/no-go + which fallback.
2. **Runtime split**: factor `load_runtime`/`load_capture_runtime` into shared-core + per-run binding,
   no behavior change yet (still one proxy per run, but routing through the binding). Pure refactor,
   fully covered by existing tests.
3. **Addon demux**: `TransportMattersAddon` resolves the per-run binding from the flow listen port.
   Add tests for two bindings on two ports in one addon instance.
4. **Shared proxy lifecycle**: a process-resident shared proxy manager on `app.state` (sibling to
   `RunManager`); start once, register/deregister routes. `prepare_captured_run` calls register
   instead of spawning. Teardown deregisters.
5. **Shared session store**: one pool/httpx/TokenCounter/tailer-registry for all runs; preflight once.
6. **Cutover + delete**: remove the per-run `ProcessSupervisor` spawn path and per-run pool. No
   parallel implementations left (DRY: delete the old path).

## Expected payoff

- Processes at 50 runs: **~51 (50 clients + 1 proxy)** vs ~100 today; **mitmproxy RAM 50x -> 1x**.
- Postgres connections: **one shared pool** instead of up to 50 pools -> the first hard wall is gone.
- Spawn latency: no per-run interpreter start or stack import; register-a-route is sub-100ms ->
  50 terminals start fast even without large admission concurrency.
- Tier 1's admission semaphore stays as backpressure but can be widened sharply.

## Risks / watch items

- Flow-to-run attribution must be airtight (listen port is the key); a mismatch would cross-contaminate
  transcripts/wire capture, the product's core contract. Heavy test coverage on demux.
- One proxy is now a single point of failure for all runs; needs supervised restart + run re-register,
  or the bounded-pool fallback for blast-radius isolation.
- Breakpoint/pause-next-turn semantics (per-run) must map onto the shared addon.
- macOS fd ceiling still applies to the API parent (PTYs + sockets); orthogonal, raise `ulimit`.

## Recommendation

Land Tier 1 now (branch `perf/spawn-concurrency-reliability`) to kill the 500 and make bursts
reliable today. Schedule Tier 2 as a spec'd, sliced build starting with the half-day mitmproxy
runtime-mode spike, which decides incremental-vs-pooled. Treat slices 4-6 as high-blast-radius
(capture contract): adversarial review + real 50-run load test before merge.
