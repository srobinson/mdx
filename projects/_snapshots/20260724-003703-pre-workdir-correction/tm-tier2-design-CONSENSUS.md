---
title: "Tier 2 shared-proxy: consensus design (v2, subprocess + dual-context)"
type: design
tags: [transport-matters, performance, proxy, mitmproxy, addon, overlays, session-store, scaling, tier-2, consensus]
summary: "Two bounded contexts over one shared kernel. Desktop/API-managed runs use ONE shared mitmdump SUBPROCESS (demux by listen port, overlays via a local control channel, no request pausing) for 50-run scale. Standalone CLI (transport-matters claude/codex) keeps the current one-process-per-run embedded model WITH breakpoints. The addon, demux/binding, capture recorders, session writer, and OverrideStore are single-sourced; only proxy lifecycle + breakpoint wiring diverge."
status: consensus-final (dual sign-off, Codex + Claude backend-engineers, 2026-06-16)
confidence: high
created: 2026-06-16
updated: 2026-06-16
sources:
  - ~/.mdx/projects/tm-tier2-design-proposal-claude.md
  - ~/.mdx/projects/tm-tier2-design-proposal-codex.md
  - ~/.mdx/projects/tm-tier2-spike-mitmproxy-modes.md
  - ~/.mdx/projects/tm-tier2-seams-and-questions.md
---

# Tier 2 shared-proxy: consensus design (v2)

Synthesis of two independent proposals (Codex + Claude, cross-runtime MoE) plus the Peer Consensus
round, which converged on **subprocess** after request-pausing was dropped as a requirement, and the
user's "best of both worlds" scoping. Cite `file::symbol`, never line numbers, in derived specs.

## Scope: two bounded contexts, one shared kernel

Request **pausing/breakpoints are NOT required** for the scaling target. Overlays (modify request
in-transit) ARE required. This splits captured runs along a seam that already exists in the code
(`web_runtime`):

- **Context A — standalone CLI (`transport-matters claude` / `codex` on a TTY).** `web_runtime="embedded"`:
  the addon and the breakpoint/override routes are co-resident in that run's mitmdump process, which is
  why breakpoints work there today. **Keep entirely as-is:** one process per run, embedded web,
  breakpoints + overlays. One operator, one run, pause-and-edit is the right model here.
- **Context B — desktop canvas / API-managed runs.** `web_runtime="external"` (breakpoints already do
  not work here). **This is Tier 2:** ONE shared mitmdump subprocess for all runs, demux by listen
  port, overlays via a control channel, NO pausing. The 50-run scaling target.

**Shared kernel (single-sourced, consumed by both contexts):** the addon hooks/handlers, demux +
`ProxyRunBinding`, capture recorders (`exchange_recorder.py`, `codex/exchange.py`), the session
writer/tailer, and `OverrideStore` + `request_pipeline.py::run_pipeline` overlay application.

**DRY guardrail (CLAUDE.md, user-approved dual-mode):** the only divergence is a thin
**proxy-lifecycle + breakpoint-wiring** wrapper selected by entry point. No duplication of capture/addon/
override logic. The no-parallel-implementation rule applies to the kernel; the two lifecycle wrappers
are intentional. Consequence: `breakpoint.py` and `pause_session.py` are **NOT deleted** — they remain
for Context A and are simply not wired in Context B, and no per-run breakpoint refactor is needed
(breakpoints stay confined to the one-run-per-process CLI, where process-global state already equals
per-run).

## Decisions (the five forks)

- **HQ1 — register/deregister on ONE long-lived shared mitmproxy** (Context B). Spike-proven:
  `master.options.update(mode=[...])` adds/removes listeners at runtime on a live `DumpMaster`; async,
  gated by an **accept-probe** (poll-connect). `proxyserver.servers.is_updating` is best-effort only
  (not reliably public in mitmproxy 12.2.2 introspection); the accept-probe is authoritative.
- **HQ2 — listen-port demux.** Key = `flow.client_conn.sockname[1]` (**primary**; present on every
  accepted TCP connection regardless of mode), with `flow.client_conn.proxy_mode.custom_listen_port` as
  the **cross-check**. A mismatch is a hard demux violation: 502 / kill flow, mark proxy unhealthy, fail
  the test gate. (`proxy_mode.listen_port` is a bound method, not a value — do not use it.)
- **HQ3 — single shared mitmdump SUBPROCESS (Context B).** Both reviewers flipped here after pausing was
  dropped. Embedding a `DumpMaster` in the API process was **proven feasible** (probe: master runs on
  the API loop concurrently with an HTTP endpoint) but rejected: the 50->1 process / 50->1 pool win
  comes from **sharing**, which a subprocess achieves equally, while embedding alone carries unproven
  API event-loop saturation under 50 TLS-terminated streams, blast-radius concentration (a TLS/parse
  crash would take down API + UI + control plane + all runs), fd concentration, and the Mode A/B knob.
  Embedding's only remaining edge was "no IPC", but a control channel is needed anyway for runtime
  register/deregister. Subprocess also has lower migration churn: `supervisor_core.py::ProcessSupervisor.spawn`
  and `captured_run_models.py::CapturedRunLease.close` already exist — the change is "spawn 1 shared
  mitmdump, not N; deregister, don't terminate."
- **HQ4 — one shared Postgres pool + one tailer registry (in the shared subprocess) with sharded async
  commit dispatch, AND commit-ack -> cursor-advance coupling.** Keep one pool/registry. Replace the
  blocking `SessionWriter.submit_blocking` poll-thread dispatch with a bounded per-shard `asyncio.Queue`
  drained by N workers, sharded by `session_id`, `N <= session_pool_max_size`. **Correctness gate
  (blocker):** the per-session cursor/durable offset must advance ONLY on `CommitResult` success (a
  per-session completion future), never on enqueue — otherwise an async commit failure silently drops
  transcript data (the loss `submit_blocking` prevents today via `run_coroutine_threadsafe(...).result(timeout)`).
  Add a **public async submit** around `SessionWriter._commit_batch` for on-loop workers (today's
  `submit_blocking` raises if called on its own loop). Reuse the EXISTING `index/tailer.py::TranscriptTailer.unregister`
  on deregister (it already pops `_cursors`; only tests call it today).
- **HQ5 — one shared subprocess + supervised restart/re-register; runs stay process-resident.** A pool
  of K subprocesses is the fallback ONLY if the load test shows one mitmdump cannot carry 50 concurrent
  TLS-terminated streams (see Risks). The binding registry mirror lives in the API process, so on
  subprocess death the supervisor respawns, re-sends all bindings, re-registers all modes, and re-pushes
  overrides. In-flight flows error; clients retry. Runs do not survive an API restart (client PTYs die
  with the API), unchanged from today.

## Component model (Context B)

New package `api/src/transport_matters/shared_proxy/` (server layer). Keep new code here, not in
`run_manager.py` (644 lines, in the >600 watch band; refactor if an integration edit nears 700).

- **`SharedProxyManager`** on `app.state.shared_proxy_manager` (API process), sibling to
  `app.state.run_manager`. Spawns and **supervises the single shared mitmdump subprocess** (reusing
  `ProcessSupervisor`), owns the local **control channel** client (UDS), the lifecycle binding-registry
  mirror (`by_run_id`/`by_listen_port`), `proxy_generation`/`mode_generation`, and `register`/
  `deregister`/`set_overrides`/supervisor. Run-scoped exchange/meta reads are served from the API
  process by resolving the run's `StorageBackend` via run metadata (disk artifacts, as today —
  `api/v1/exchanges.py::list_exchanges`/`get_exchange`/`get_pipeline_tokens` are StorageBackend reads,
  NOT Postgres); only the Postgres session-correlation surfaces use Postgres. Neither hops the subprocess.
- **Shared mitmdump subprocess** holds: the `DumpMaster` + listener set, the `SharedProxyAddon`, the
  **shared core** (one `httpx.AsyncClient`, one `TokenCounter`, one `create_async_pool` Postgres pool,
  one `TranscriptTailer` registry + sharded dispatcher, one `OverrideStore`), and the per-run binding
  table keyed by listen port (pushed from the API on register). Mode mutation happens HERE (it owns the
  Master), triggered by control-channel messages.
- **Control channel** (local, loopback-only): typed JSON over a **Unix domain socket**, messages
  `register_listener(binding)`, `deregister_listener(run_id)`, `set_overrides(scope, payload)`, each
  **ACKed** before the API route returns. Re-hydrated on register and on subprocess restart. (Claude's
  alternative: forward the run-scoped override routes to the subprocess's embedded web runtime
  `addon_runtime.py::start_web_runtime` which already hosts `api/v1/overrides.py::patch_overrides`;
  pick one in Slice 5. UDS is the default for one uniform channel alongside register/deregister.)
- **`ProxyRunBinding`** — the SHARED-process per-run identity source (Context B). Slice 1 ADDS it; it does NOT strip per-run identity from `Settings`, which Context A's one-process-per-run launch still needs (see Run-identity replacement). Holds run_id, cli,
  listen_port, mode_kind/spec, upstream, working_dir, storage_dir + `StorageBackend`, agent_home_dir,
  owned-session fields, launch_fields, default_client_passthrough, per-run `recent_auth`, `active_flows`,
  `state`. Lives in the subprocess; the API keeps a lifecycle mirror.
- **Relation to `RunManager`:** keeps run lifecycle/PTY/lease; the lease stops owning a per-run mitmdump
  `ProcessSupervisor` and instead `lease.close()` calls `shared_proxy.deregister(run_id)` over the
  control channel + terminates the client PTY. Tier-1 admission semaphore reused as front-door
  backpressure (and widenable: register-a-route << spawn-a-process).

## Spawn flow (Context B; ordered, per-step rollback)

1. Admit (Tier-1 semaphore, `RunManager._spawn_new_admitted`).
2. Build client launch context WITHOUT starting mitmdump (reuse `captured_run_context.py::build_captured_run_context`, runtime-home, managed session, workspace lock, manifest, client env).
3. Allocate one loopback listen port.
4. `register_listener` over the control channel: API sends the binding (run_id, listen_port, upstream, mode_kind, storage_dir, owned-session, current overrides). Subprocess: insert binding (by listen_port) BEFORE exposing the mode (no unmapped-flow race), add the mode, `options.update`, **accept-probe** readiness, register the owned-session tailer cursor, then ACK. Rollback: subprocess removes mode+binding on failure; API frees the port.
5. On ACK, spawn the client PTY (unchanged contract: Claude `ANTHROPIC_BASE_URL=http://127.0.0.1:{port}`; Codex explicit-proxy env). Rollback: deregister + terminate PTY.
6. Register `ManagedRun`, start `_drain_run`.

Readiness timeout reuses the Tier-1 typed `proxy_start_timeout` (503). Cursor-registration failure
aborts spawn (silent transcript loss unacceptable). Every step idempotent and reverse-unwound.

## Teardown flow (Context B; deregister, never kill)

`RunManager._teardown_run` -> `lease.close` -> `shared_proxy.deregister(run_id)` over the channel.
Subprocess: mark binding draining; remove the mode + `options.update`; wait for the listener to refuse
new connections (accept-probe inverse); drain `active_flows` (bounded); `TranscriptTailer.unregister(session_id)`
+ flush snapshot; drop this run's `recent_auth`; remove the binding; ACK. **Never** terminate the shared
subprocess, **never** close the shared core. API frees the port + terminates the client PTY. Last run
may leave `mode=[]` (proven accepted on 12.2.2); a reserved internal loopback mode is optional defense.

## Flow -> run resolution (Context B addon)

`request`/`websocket_start`: resolve binding by `sockname[1]` (cross-check `custom_listen_port`),
add `flow.id` to `active_flows`, stamp `run_id`+`listen_port` into `flow.metadata`. `response`/
`websocket_message`/`websocket_end`/`error`: read `run_id` from metadata first, re-resolve via
`by_run_id`, port as fallback; remove from `active_flows` on completion. **Unmapped flow** (port has no
active binding, or `sockname[1] != custom_listen_port`): fail closed — 502 (HTTP)/close (websocket),
increment `shared_proxy_unmapped_flow_total`, log only flow id + port + generations (never payload/auth).
Never fall through to a default/last-seen binding.

## Run-identity replacement (process env -> binding) — Slice 1, HQ3-agnostic

`get_settings()` is `@lru_cache`'d, so per-run identity is a process-global singleton today; the binding
refactor is REQUIRED regardless of HQ3, which keeps Slices 1-4 HQ3-agnostic (Slices 5-9 are
subprocess-specific) and makes the topology decision cheap to apply. **Slice 1 ADDS `ProxyRunBinding`
as the identity source for the SHARED subprocess; it does NOT delete the per-run fields from `Settings`**
(`run_id`, `storage_dir`, `breakpoint_timeout_s`, `breakpoint_skip_models`), which Context A's
one-process-per-run launch (and its breakpoint path) still reads. `get_settings()` stays for
process-global config AND for Context A per-run identity. Move list (all refs verified against live code;
Context B / shared-path reads only):
- `addon_runtime.py::load_capture_runtime` -> split `load_shared_proxy_core(settings)` + `create_binding_runtime(binding_request)`.
- `addon_runtime.py::_launch_run_context`, `::_register_owned_cursor` -> take binding.
- `addon_handlers.py::handle_http_request`, `::handle_codex_websocket_message`, `::_should_skip_breakpoint` -> binding.
- `pause_session.py` is **NOT in this move list**: it is breakpoint-only, never on the Context-B shared path, and Context A is one-process-per-run where `get_settings()` already equals per-run identity. Refactoring it to a binding would be needless churn and self-contradictory with keeping breakpoints intact.
- `exchange_recorder.py::persist_unparsed_exchange`/`persist_http_exchange`/`persist_http_provisional_exchange` -> binding storage + run_id.
- `codex/exchange.py::persist_codex_provisional_exchange`/`_persist_codex_exchange`/`persist_codex_handshake_failure` -> binding storage + run_id.
- `storage/__init__.py::get_storage` -> not used from shared addon paths; run-scoped API routes resolve storage from run metadata.
- `api/v1/exchanges.py::list_exchanges` (+peers), `api/v1/meta.py::get_meta` -> run-scoped `/v1/runs/{runId}/...`, resolving the run's `StorageBackend` via run metadata (disk-artifact reads, as today — NOT Postgres).
- `counting.py::_recent_auth` is a module-global VAR with `set_recent_auth`/`get_recent_auth` accessors -> move per-run recent-auth onto the binding via those accessors.
- `flow_state.py::capture_request_flow_state` -> add `run_id`+`listen_port` (or a lightweight `binding_ref`; never store a mutable manager object in flow metadata).

## Overlays (required; both contexts)

Overlay **application** is identical and single-sourced: the addon reads
`override_state.py::get_store().get_all(scope=(run_id, track_id))` synchronously in
`request_pipeline.py::run_pipeline` (run_id from demux), in-process, zero added latency. Only
edit-**propagation** differs by context:
- Context A (CLI embedded): UI edits hit the co-resident embedded-web override routes directly (current
  behavior, unchanged).
- Context B (shared subprocess): UI edit -> API run-scoped override route -> `set_overrides(scope, payload)`
  over the control channel -> subprocess `OverrideStore` updated, ACK before the API route returns.
  Re-hydrated on register + restart. `OverrideStore` stays the single source the addon reads. Within the
  subprocess it is read by the addon and written by the control-channel handler on the same proxy loop,
  so an `asyncio.Lock` suffices there; rule: never hold a lock across an `await`.

## Control plane (Context B): overrides yes, pausing no, SSE/counting per-run

- **Breakpoints: not wired in Context B; kept intact for Context A.** No per-run pause serializer, no
  cross-process pause/release, no `/breakpoint/*` on the shared path. `breakpoint.py` / `pause_session.py`
  remain for the CLI embedded path.
- **Counting:** `TokenCounter` shared in the subprocess; move `counting.py` recent-auth onto the binding
  (process-global is cross-run contamination).
- **SSE:** run-aware broker; `/v1/runs/{runId}/stream`; every event carries `run_id`. Served by the API
  from Postgres + control-channel state; delete/replace the global `/api/stream`.
- **Run-scoped routes + frontend:** exchanges/meta/overrides/stream become `/v1/runs/{runId}/...`;
  `www/src/api.ts` + `www/src/hooks/useExchangeStream.ts` take `run_id` (canvas already knows it from
  `capturedRunStore.ts`). Origin check as `run_routes.py::create_run`; `run_id` is an authz boundary.

## Session store (HQ4 realized, in the shared subprocess)

Shared core built once at subprocess startup (httpx + `TokenCounter` + `create_async_pool` +
`SessionWriter` + `TranscriptTailer`); per-run only the snapshot writer + cursor registration.
`session_store_preflight.py::check_session_store` runs once at startup. Sharded async dispatch
(per-`session_id` queue, N<=`session_pool_max_size` workers) with **commit-ack -> cursor-advance**
coupling and a public async submit around `_commit_batch`. Per-session ordering + dead-lettering
(`quarantine_window_blocking`) preserved; cross-run head-of-line removed; pool never over-subscribed.
Reuse `TranscriptTailer.unregister` on teardown.

## Crash / failure model (HQ5)

Subprocess death -> API supervisor respawns, re-sends all bindings, re-registers modes, re-pushes
overrides; in-flight errors, clients retry. Unmapped flow -> 502 fail-closed. DB outage -> existing
spawn preflight; active runs keep proxying, tailer applies per-run backpressure, degraded-capture
surfaced per run. API restart -> runs do not survive (process-resident). Subprocess isolation: a
proxy crash no longer touches the API/UI.

## Migration (ordered, independently shippable; delete at cutover; DRY)

1. **Binding context refactor (HQ3-agnostic).** `ProxyRunBinding`; thread run_id+storage through handlers/recorders/codex/flow_state; still one mitmdump per run. Existing tests assert unchanged. Removes most `get_settings().run_id` from addon paths.
2. **Run-scoped storage/meta reads.** Move exchange/meta API to `/v1/runs/{runId}/...`, resolving the run's `StorageBackend` via run metadata (disk-artifact reads, as today; not Postgres); delete global routes before slice end.
3. **Run-scoped SSE broker** + frontend URL migration.
4. **Sharded tailer dispatcher** with commit-ack->cursor-advance + public async submit (prove 50-cursor: 1 poison + 49 healthy, no head-of-line, no data loss on commit failure).
5. **Control channel + `SharedProxyManager` + shared mitmdump subprocess.** Spawn ONE, register/deregister listeners, set_overrides; supervised restart + re-hydrate. Prove runtime add/remove (reverse + `regular`), empty mode, accept-probe readiness.
6. **`SharedProxyAddon` demux.** Two bindings prove request/response/websocket/storage/overlays cannot cross runs.
7. **RunManager integration (Context B only).** `prepare_captured_run` for API-managed runs registers a binding via the control channel instead of `cli/runner.py::start_prepared_proxy`; keep Tier-1 admission; rollback tests at every failure point.
8. **Cutover delete (Context B path only).** API-managed captured runs use the shared subprocess; remove per-run mitmdump spawn FROM THE API-MANAGED PATH. **Context A (standalone CLI embedded) is unchanged** and keeps per-run process + breakpoints. No parallel implementation of the kernel remains; the two lifecycle wrappers are the intentional, user-approved divergence.
9. **Load + road test.** 50 mixed Claude+Codex on the shared subprocess; overlays applied; teardown churn; poison-cursor isolation; subprocess restart + re-register; **single-proxy TLS throughput under 50 concurrent streams** (decides whether one subprocess suffices or HQ5's bounded pool is needed).

## Open spikes / risks (gates before Context B cutover)

1. **RESOLVED — `regular`-mode (Codex) runtime mutation + demux.** Probe proved `regular@127.0.0.1:PORT` runtime add/remove with matching `sockname`/`custom_listen_port` on 12.2.2. Codex seam: `cli/codex_cmd.py::build_codex_invocation`, `codex/transport.py::is_codex_websocket_flow`.
2. **RESOLVED — empty mode list.** `options.update(mode=[])` accepted on 12.2.2.
3. **RESOLVED — embedding feasibility.** Proven feasible; rejected for subprocess (isolation).
4. **OPEN — single-proxy TLS throughput at 50 streams.** Subprocess removes API-loop contention, but ONE mitmdump still does all TLS terminate/re-encrypt on its process. Load test (Slice 9) decides one-vs-bounded-pool (HQ5). Mitigate: no blocking work in hooks (disk via `to_thread`, DB thread-bridged, counting async).
5. **OPEN — `options.update` under high churn.** 50 rapid register/deregister each rewrite the whole mode list (serialized in the subprocess). Churn test in Slice 5; coalesce/debounce fallback.
6. **OPEN — shared CA / confdir across upstreams.** One subprocess Master needs one confdir/CA covering Anthropic + ChatGPT; confirm cert generation per upstream host.
7. **OPEN — fd ceiling on the shared subprocess.** All listeners + upstream sockets concentrate there; raise `ulimit`.

## Expected payoff

Context B at 50 runs: ~51 processes (50 clients + 1 shared proxy) vs ~100 today; mitmproxy RAM 50x->1x;
one shared pool removes the connection ceiling; spawn becomes register-a-route (sub-100ms). Context A
keeps breakpoints. No cross-process pause machinery is ever built. Subprocess isolation keeps a proxy
crash off the API/UI.
