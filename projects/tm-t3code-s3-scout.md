---
title: Scout — t3code P1 slice 3, Capture RPC seam (B-S3)
type: projects
tags: [transport-matters, t3code, p1, slice-3, capture-rpc, scout, reuse-map]
summary: Recon of the existing capture code and runtime package for the prepare_capture / release_capture / capture_health seam. Resolves Q2 to loopback HTTP/JSON with code evidence. Baseline main @a55335b.
status: active
source: scout (fable), brief from orchestrator transport-matters:general:5:1.1
confidence: high (all claims verified against the tree)
created: 2026-07-07
---

# Scout — Capture RPC seam (t3code P1 slice 3)

Baseline `main` @ `a55335b`, clean tree. Spec ref `tm-t3code-p1-spec.md` §2c.
Citations are file + symbol. Recon only; no source edits.

## 1. Reuse Map

Every slice capability → existing owner or "none found".

| Capability | Existing owner | Status |
| --- | --- | --- |
| Start + own the mitmproxy child | `api/src/transport_matters/cli/runner.py::start_prepared_proxy` spawns under `ProcessSupervisor` with child name `"mitmdump"`; invoked inside `captured_run.py::prepare_captured_run` | Reuse as-is (already inside the wrapped call) |
| Allocate ports | `cli/ports.py::allocate_port_pair` via `captured_run_dependencies.py::default_claude_run_dependencies`; bind-retry ×3 + readiness-timeout retry with jitter live inside `prepare_captured_run` | Reuse as-is |
| Write manifest / session facts / workspace lock | `captured_run_context.py::write_captured_run_manifest`, `persist_owned_session_facts`; `lock.py::WorkspaceLock` — all inside `prepare_captured_run` | Reuse as-is |
| Prepare seam (abstract) | `run_models.py::PrepareCapturedRun` (Protocol) and `run_models.py::CapturedRunLeaseHandle` (Protocol, `close()` only) — the exact injection seam `RunManager` already uses (`run_manager.py::RunManager.__init__` `prepare_run=prepare_captured_run`) | Reuse for typing the registry and tests |
| Dependency bundle | `captured_run_dependencies.py::CapturedRunDependencies` + `default_claude_run_dependencies()` | Reuse as-is |
| run_id → lease registry | **None found standalone.** Today `run_manager.py::ManagedRun.lease` holds the lease per run inside `RunManager` (deleted in slice 4e). Searches: `grep -rn "lease" api/src` → only `run_manager.py`, `run_models.py`, `captured_run*.py`, `shared_proxy/run_preparation.py` | New (small dict + lock in the new module) |
| Idempotent close | `captured_run_models.py::CapturedRunLease.close` — **confirmed idempotent** (§5) | Reuse as-is |
| Child health | `supervisor_core.py::ProcessSupervisor.poll_any` (returns `(name, returncode)` of an exited child or `None`). **No public health surface on the lease** — `CapturedRunLease._supervisor` is private, and the repo's module-privacy rule (`test_private_import_boundary.py`) forbids reaching in from another module | Small addition: public `alive()`/`health()` on `CapturedRunLease` (same module, private access legal) |
| Loopback HTTP, Python side | The FastAPI app itself: `main.py::create_app` + the `api/v1/` router convention; lifespan-owned state precedent `api/v1/run_routes.py::create_run_manager`/`close_run_manager` on `app.state`; error surface `api/v1/errors.py::raise_api_error` | Reuse: new router on the existing app, no new server process |
| Loopback HTTP precedent between these two processes | Slice 1's `api/v1/run_proxy.py::RunRouteProxy` (`httpx.AsyncClient`, `trust_env=False`, 10s timeout) + `config.py::Settings.gateway_url` — Python→Runtime direction; `api/v1/test_run_proxy.py` proves the cross-process test pattern (`TestClient` + fake gateway) | Precedent confirmed; the RPC is the mirror direction |
| HTTP client, Runtime (TS) side | **No client dependency exists** (`packages/runtime/package.json`: fastify, @fastify/websocket, @tm/common only). Root `package.json` `engines.node >= 20.19` → built-in `fetch` (undici); `packages/gateway/src/app.test.ts` already uses global `fetch` | Reuse built-in `fetch`; zero new dependency |
| Wire coercions, TS side | `@tm/common` safe variants (`nonEmptyString`, `safeInteger`, `safeIntegerString`) — per `packages/AGENTS.md`, safe variants are for untrusted wire payloads | Reuse |
| Fake-caller test patterns | Python: `api/v1/test_run_proxy.py` (TestClient against `create_app`); `prepare_captured_run` already takes `supervisor_factory` + `proxy_starter` injectables for hermetic tests. TS: `packages/runtime/src/server/runtimeRouter.test.ts` (colocated vitest, fastify + `inject`); for a real `fetch` client use `app.listen({ port: 0 })` as `packages/gateway/src/app.test.ts` does | Reuse both |

**Callers of the wrapped code today (blast radius).** `prepare_captured_run` has exactly one production caller: `run_manager.py::RunManager` (as the default of the injectable `prepare_run`). `CapturedRunLease.close` is called only through `RunManager._close_lease` (duck-types `aclose`/`close`). The CLI detached path (`cli/start_cmd.py`) uses the sibling `captured_run.py::run_captured_run_on_local_tty` and never touches `prepare_captured_run`. Wrapping adds a new caller; **no signature change, no existing caller breaks.**

**Second lease type exists.** `shared_proxy/run_preparation.py::SharedCapturedRunLease` (shared-proxy path, `web_runtime == "external"`, chosen in `run_manager.py::RunManager._prepare_request`). It has no per-run supervisor, so per-child health does not apply to it. This slice wraps the per-run path (`prepare_captured_run`) per the brief; the `CapturePort` contract should not bake in "health = one child process" (see §7).

## 2. Quality Map (code-hygiene, inspection only)

Measurements (`wc -l`):

| File | LOC | Verdict |
| --- | --- | --- |
| `captured_run.py` | 370 | healthy |
| `captured_run_models.py` | 116 | healthy |
| `run_manager.py` | 682 | **near the 700 hard limit — add nothing to it in this slice** (the design keeps rpc code out of it anyway) |
| `run_models.py` | 207 | healthy |
| `shared_proxy/run_preparation.py` | 217 | healthy |
| `packages/runtime/src/server/runtimeRouter.ts` | 302 | healthy |

Duplication: the **resource-release triplet** (manifest unlink + `WorkspaceLock.__exit__` + `resource_stack.close()`) appears in five places — `captured_run.py::run_captured_run_on_local_tty` (finally), `captured_run.py::prepare_captured_run` (except), `captured_run_models.py::CapturedRunLease.close`, `shared_proxy/run_preparation.py::SharedCapturedRunLease._release_local_resources`, `shared_proxy/run_preparation.py::_finish_shared_preparation` (except). Grooming rec: extract one release helper in `captured_run_models.py` and call it from all five. **Optional, separate commit if taken** — it touches teardown paths, and lifecycle invariants deserve their own reviewable diff (persistence/teardown-change risk).

Dead code: none found in the area (`run_captured_run_on_local_tty` is live via `cli/start_cmd.py`).

Boundary: `CapturedRunLease._supervisor` is module-private; the RPC layer must not reach into it (`test_private_import_boundary.py` enforces this). Health belongs as a public method on the lease itself.

Error-shape note: `run_manager.py::RunManager._prepare_request` maps `CapturedRunBindConflict`/`CapturedRunProxyStartTimeout` → `RunManagerError` codes. The RPC router should translate the same two domain exceptions straight to HTTP error codes at the route layer (repo convention: domain exceptions translated at the FastAPI layer) — do not route through `RunManagerError`.

## 3. Verified entry points (claimed → actual)

| Spec/brief claim | Actual | Drift |
| --- | --- | --- |
| `prepare_captured_run` allocates ports, writes manifest, starts proxy under `ProcessSupervisor`, returns `tuple[CapturedRunSpawnSpec, CapturedRunLease]` | Confirmed: `captured_run.py::prepare_captured_run` (plus bind-retry ×3 and proxy-readiness-timeout retry the spec does not mention) | none |
| `CapturedRunLease.close` idempotent | Confirmed (§5) | none |
| `CapturedRunSpawnSpec` serializable | Confirmed (§below) | none |
| RPC lands at `capture/rpc.py` + `capture/self_reap.py` (spec §7) | **No `capture/` package exists**; the api package is flat modules + `api/v1/` routers | **Drift — land flat** (§4 placement) |
| `packages/runtime/src/ports.ts` exists | **Does not exist.** `packages/runtime/src/` = `index.ts` + `server/runtimeRouter.ts` only | Drift — `ports.ts` is created by this slice |
| Canonical home for `CapturePort` / `CaptureRpcClient` | `src/ports.ts` + `src/adapters/CaptureRpcClient.ts`, per `packages/AGENTS.md` canonical context shape; `@tm/activity` is the live reference (has `ports.ts`, `adapters/`, `service/`) | none |
| Gates | Root `justfile`: `just check`, `just test` (test runs suites serially, includes `pnpm --filter @tm/runtime test` and `cd api && just test`); `api/justfile`: `check: format lint typecheck`, `test = uv run python -m pytest` | none |
| Test layout | Python colocated (`src/transport_matters/test_*.py`, per `api/CLAUDE.md`); TS colocated `*.test.ts` (`runtimeRouter.test.ts`) | none |

**Serializability facts.** `CapturedRunSpawnSpec` (`captured_run_models.py`): run_id str, three `Path`s, two ports, `client: ManagedClient | None` (`cli/runner.py::ManagedClient` — frozen dataclass of str/list[str]/dict[str,str]/Path), `launch_env: dict[str, str]`, `managed_session: ManagedSession | None` (`cli/launch_profile.py::ManagedSession` — two strs), harness str. Fully JSON-mappable with Path→str; no live handles. The wire DTO is a straightforward mapping.

## 4. Q2 resolution — loopback HTTP/JSON (decisive)

**Loopback HTTP/JSON. stdio JSON-RPC is structurally wrong for this tree:**

1. **There is no parent-child pipe between Runtime and Python.** In the P1 interim topology, the desktop spawns the Runtime server and Python remains the separately-launched front door. stdio JSON-RPC would force Runtime to spawn a second Python process and hand-roll framing — new lifecycle, new protocol, contradicts §1 of the spec.
2. **The Python side already has the server.** The FastAPI app is running whenever capture is possible; the RPC is one new `api/v1` router on it. Zero new server infrastructure.
3. **Slice 1 already proved loopback HTTP between exactly these two processes** — `api/v1/run_proxy.py::RunRouteProxy` (httpx, `Settings.gateway_url`) in the Python→Runtime direction, with `test_run_proxy.py` as the cross-process test pattern. The capture RPC is the mirror arrow.
4. **The Runtime side needs no new dependency**: Node ≥ 20.19 built-in `fetch` (precedent: `packages/gateway/src/app.test.ts`).
5. Independently testable both sides with a fake peer (the brief's CARRY constraint): Python via `TestClient` + injected `supervisor_factory`/`proxy_starter` fakes; TS via `CaptureRpcClient` pointed at a throwaway fastify app on `listen({ port: 0 })`.

**Exactly what to reuse:** existing FastAPI app + `api/v1` router convention + `raise_api_error`; `app.state` lifespan pattern from `run_routes.py::create_run_manager`/`close_run_manager`; `default_claude_run_dependencies`; `asyncio.to_thread(prepare_captured_run, ...)` calling shape from `RunManager._prepare_request`; `PrepareCapturedRun` + `CapturedRunLeaseHandle` protocols from `run_models.py`; TS built-in `fetch` + `@tm/common` safe coercions. New config: one Runtime-side setting for the Python base URL (env var, mirror of `gateway_url`).

## 5. Idempotency of `CapturedRunLease.close` — CONFIRMED

`captured_run_models.py::CapturedRunLease.close` guards with `_closed`:

```python
if self._closed:
    return
self._closed = True
```

then `_supervisor.terminate_all()`, `restore_signal_handlers()`, manifest unlink (`FileNotFoundError` suppressed), `_workspace_lock.__exit__`, `_resource_stack.close()`. Second call is a no-op. `SharedCapturedRunLease` (`shared_proxy/run_preparation.py`) carries the same `_closed` guard on both `aclose` and `close`.

## 6. Plan (ordered, bound to the reuse map)

1. **Python module `capture_rpc.py`** (flat, sibling of `captured_run.py` — no `capture/` package; name it `capture_rpc.py`, not bare `rpc.py`, matching the descriptive flat-module convention): `CaptureLeaseRegistry` (dict[str, `CapturedRunLeaseHandle`] + `asyncio.Lock`), `prepare_capture(request)` → `to_thread(prepare_captured_run, ...)` with `default_claude_run_dependencies()`, register lease by run_id, return spawn-spec DTO; `release_capture(run_id)` → pop + `to_thread(lease.close)`, missing id = success (idempotent contract); `capture_health(run_id)`.
2. **Public health on the lease**: `CapturedRunLease.alive() -> bool` in `captured_run_models.py`, implemented against its own `_supervisor` (via `poll_any()`-style check; private access is legal inside the defining module). This is the only edit to existing capture code.
3. **Router `api/v1/capture_rpc_routes.py`**: three routes wrapping the module; translate `CapturedRunBindConflict`/`CapturedRunProxyStartTimeout` via `raise_api_error`; wire in `main.py::create_app` + lifespan close that **closes all registered leases on shutdown** (mirror `close_run_manager`; otherwise an app restart orphans mitmdump children).
4. **Python tests** (colocated `test_capture_rpc.py`, `api/v1/test_capture_rpc_routes.py`): fake caller = `TestClient`; hermetic prepare via the existing `supervisor_factory`/`proxy_starter` injection points. Assert: prepare registers a lease; release closes exactly once and twice-is-safe; health flips when the fake supervisor reports a dead child; shutdown closes leftovers.
5. **Runtime `src/ports.ts`**: `CapturePort` (`prepareCapture`/`releaseCapture`/`captureHealth`) — port vocabulary only, no IO.
6. **Runtime `src/adapters/CaptureRpcClient.ts`**: `CapturePort` impl over built-in `fetch`, base URL injected; parse with `@tm/common` safe coercions; export both through `src/index.ts` (single import surface rule).
7. **Runtime tests** (colocated `CaptureRpcClient.test.ts`): fake Python = fastify app on `listen({ port: 0 })` (gateway test pattern); cover envelope round-trip, release idempotency (two calls, one effect), health of a dead capture, and error paths (non-2xx, unreachable).
8. **Gates, verbatim**: root `just check` + `just test`; inner loop `cd api && just test` and `pnpm --filter @tm/runtime test`.

Optional step 0 (separate commit, orchestrator's call): the five-site release-triplet consolidation from §2. Not required for the slice.

## 7. Open risks

- **Route exposure**: the RPC mounts on the browser-facing Python app. `run_proxy.py` gates mutating routes with `terminal_bridge` origin checks; the capture RPC is internal-only and needs an explicit gating decision (origin check, loopback-only bind assumption, or shared token). Builder decision, flag in the PR.
- **Request DTO forward-compat**: the fake-caller slice needs only workspace/harness/etc., but the real caller (4d) needs `space_id`/`worktree_id`/`runtime_template`/`launch_fields` (`CapturedRunRequest` fields). Shape the wire request to carry them now (optional fields) to avoid a 4d wire break.
- **Health semantics are path-specific**: `SharedCapturedRunLease` has no per-run child. Keep `CapturePort.captureHealth` semantically "is capture alive for run_id", not "is the child process alive".
- **App-shutdown lease sweep** (plan step 3) is correctness, not polish — without it a Python restart leaks mitmdump children.
- CARRY (unresolved by design): no PTY, no run-serving wiring in this slice; both sides tested against fakes only. Confirmed feasible with existing injection points on both sides.

## 8. Recommended build order

Python first (steps 1–4: the contract's semantics live there), then TS client (5–7), then full gates (8). Single branch, one PR; steps 2 and 0 as distinct commits if taken.
