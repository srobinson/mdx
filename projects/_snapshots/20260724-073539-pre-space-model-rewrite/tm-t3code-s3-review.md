# PR#234 review — t3code P1 slice 3: Capture RPC seam

- **Branch / head:** `feat/capture-s3` @ `dc20681` (tree pristine).
- **Baseline:** `main` @ `a55335b` (merge-base).
- **Method:** xhigh adversarial pass. 10 finder angles (5 correctness + reuse/simplify/efficiency + altitude + conventions) + sweep, each verified against `main:<path>` source. Happy-path suites run green by finders (7 Python + 5 TS).
- **Verdict:** no Blocker. **4 Major, 9 Minor.** Two of the Majors (M1, M2) are behavioral divergences from `RunManager` that *may* be intentional slice-3 deferrals; they are flagged as "verify intent" because the seam silently accepts input it does not honor.

Scope honored: did not flag PTY spawn, run serving, two-lifecycle teardown (slice 4d), the Q2 loopback-HTTP decision, or `CapturedRunLease.close` idempotency (already correct).

---

## Major

### M1 — `web_runtime="external"` is accepted but silently mis-routed (wrong proxy topology)
`api/src/transport_matters/capture_rpc.py:81`

`CaptureLeaseRegistry.prepare_capture` unconditionally calls `self._prepare_run`
(= `prepare_captured_run`, the **dedicated per-run mitmdump** path). The existing
orchestrator branches on runtime: `RunManager._prepare_request`
(`run_manager.py:347-362`) routes `web_runtime == WEB_RUNTIME_EXTERNAL` to
`prepare_shared_captured_run(..., shared_proxy=self._shared_proxy_manager)`. The
registry holds no shared-proxy manager and never branches.

The contract advertises the field on all three surfaces — pydantic
`PrepareCaptureRequest.web_runtime` (default `embedded`, accepts `external`), TS
`CaptureWebRuntime = "embedded" | "external"`, and the route round-trip test
**explicitly posts `"webRuntime": "external"` for a `{"kind":"canvas"}` run** and
asserts it round-trips. Canvas is the seam's primary use case, so an `external`
capture request gets the wrong proxy topology (dedicated instead of shared), or
the runtime distinction is dropped. Either wire the shared proxy or reject
`external` until it is supported; do not accept an input the seam cannot honor.
*Verify intent: shared-proxy wiring may be a later slice, but the field should
then be rejected, not silently accepted.*

### M2 — Session-store preflight dropped; `check_session_store` dependency is dead-wired
`api/src/transport_matters/capture_rpc.py:79`

`RunManager._prepare_request` runs `await self._ensure_session_store_available()`
before every prepare (`run_manager.py:345`), which calls
`self._dependencies.check_session_store` (`run_manager.py:444`) and fails fast
when Postgres is unreachable. The capture registry never calls
`check_session_store`, though it is a field on `CapturedRunDependencies` and is
populated by `default_claude_run_dependencies()`. Result: `/v1/capture/prepare`
starts a proxy against a dead session store instead of failing fast, and the
wired dependency is never exercised (both test `_dependencies` fixtures supply a
`check_session_store` that nothing calls). *Verify intent: `defer_session_ownership`
may justify skipping the preflight; if so, drop the dead dependency wiring.*

### M3 — Cancellation between prepare and registration orphans a fully-prepared lease
`api/src/transport_matters/capture_rpc.py:81-94`

`prepare_capture` awaits `asyncio.to_thread(self._prepare_run, ...)` (the proxy
child is started, `WorkspaceLock` acquired, `ExitStack` populated), then awaits
`async with self._lock` to register the lease. Both awaits are cancellation
points. If the loopback request is cancelled (client abort / fetch timeout /
disconnect) after the thread returns the lease but before the dict insert, the
lease is neither registered nor closed: the mitmdump proxy keeps its port, the
lock/manifest stay held, `ExitStack` never closes. The caller never received a
`run_id`, so `/release` can never reclaim it — permanent leak until API restart.
Directly hits the brief's focus #1/#2 (no leaked lease/proxy on failure paths).
Fix: register-or-close under a `finally`/`CancelledError` guard (or `shield` the
insert).

### M4 — `responseError` throws on a non-object `detail`, losing HTTP status and killing its own fallback
`packages/runtime/src/adapters/CaptureRpcClient.ts:138`

`optionalRecord(record(payload, "error response").detail)` calls `record()` on
`detail`, which throws `capture_rpc_malformed_response` whenever `detail` is not
an object. FastAPI's default validation error (422) has `detail` as a **list**;
Starlette 404/405 have `detail` as a **string**. No custom exception handler is
registered anywhere in `api/`, so those default shapes reach this line
unchanged. The deliberately written fallback chain
(`?? nonEmptyString(...error) ?? \`...HTTP ${status}\``) is therefore dead code
for every framework-level error: a malformed prepare body surfaces as a
statusless "malformed field optional record: expected object" instead of the
real validation failure. Guard `detail` with `optionalRecord` semantics that
tolerate non-object shapes (fall through to the top-level / status fallback).

---

## Minor

### m5 — `_default_upstream` duplicates the harness→upstream default rule
`api/src/transport_matters/api/v1/capture_rpc_routes.py:190`

Verbatim second copy of `run_manager.py:404`
(`CLAUDE_UPSTREAM_DEFAULT if request.harness == CLAUDE_HARNESS_NAME else ""`).
Violates user CLAUDE.md "DRY: no compromise". Promote one helper (e.g.
`default_upstream_for_harness` in `captured_run_models.py`, which already owns
`CLAUDE_UPSTREAM_DEFAULT`) and call it from both sites.

### m6 — `install_signal_handlers=True` would crash off the main thread
`api/src/transport_matters/capture_rpc.py:91`

The registry forwards `install_signal_handlers` into `prepare_captured_run`,
which runs inside `asyncio.to_thread`. When true it calls
`supervisor.install_signal_handlers()` → `signal.signal()`, raising
`ValueError: signal only works in main thread`. Latent (default `False`, no
caller flips it), but the seam exposes the knob and any true value is a hard
500. Drop the parameter for the RPC path or document that it must stay false.

### m7 — `launch_fields: dict[str, Any]` uses `Any` without the required comment
`api/src/transport_matters/api/v1/capture_rpc_routes.py:77`

`api/CLAUDE.md` Types: "`Any` requires a comment explaining why". The domain
field is `Mapping[str, object]` and the sibling producer returns
`dict[str, object]`; use `dict[str, object]` (comment-free, and it stops
silently disabling type checking on pass-through values).

### m8 — Generic wire-coercion helpers re-derived instead of living in `@tm/common`
`packages/runtime/src/adapters/CaptureRpcClient.ts:235`

`record` / `stringRecord` / `stringArray` / `optionalRecord` / `booleanField` /
`integerField` are generic `unknown`→typed coercions with no domain knowledge;
`record` is byte-identical to guards already in `@tm/activity`
(`adapters/transcriptRecords.ts`) and `www/packages/core/isRecord.ts`.
`packages/AGENTS.md`: "@tm/common is the single home ... The moment a primitive
is needed by a second package it belongs in @tm/common, not copied. Duplication
across packages is a defect." Promote the reusable slice to `@tm/common`.

### m9 — `get_capture_registry_from_app` reimplements the established app.state accessor
`api/src/transport_matters/api/v1/capture_rpc_routes.py:123`

`run_routes.py:161-173` already establishes `get_run_manager_from_app(app: Any)` /
`close_run_manager(app)`. The new function diverges: `app: object`,
`cast("Any", getattr(app, "state", app))` (uncommented `Any` cast — `api/CLAUDE.md`
"`Any` requires a comment") and a dead `app` fallback (a FastAPI app always has
`.state`). Mirror the sibling's shape.

### m10 — `close()` vs a late-finishing `prepare_capture` leaks a lease on shutdown
`api/src/transport_matters/capture_rpc.py:122`

`close()` snapshots+clears `self._leases` under the lock, then closes outside it.
A `prepare_capture` whose worker thread inserts after that snapshot leaves its
lease's proxy/lock orphaned at process exit. Low probability (uvicorn drains
in-flight requests first), but the same class as M3.

### m11 — Coverage gaps on the exact behaviors the brief cares about
`api/src/transport_matters/captured_run_models.py:98` / `test_capture_rpc.py`

`CapturedRunLease.alive()` (the real `supervisor.poll_any()` read) has zero
coverage — "health reflects a dead proxy child" is proven only with a `FakeLease`
returning a fixed bool, so an inverted `poll_any` check or a missing
`not self._closed` guard would pass CI. Also untested: the
`CaptureRunAlreadyRegistered` / duplicate-run_id close-then-raise branch, and the
cancellation-leak path (M3). Add a real-`poll_any` alive() unit and a
duplicate-run_id registry test.

### m12 — Non-JSON non-2xx bodies mislabeled as `capture_rpc_malformed_json`
`packages/runtime/src/adapters/CaptureRpcClient.ts:125`

`responsePayload` runs before the `response.ok` check, so a 502 with an
HTML/plain-text body throws `capture_rpc_malformed_json` (a client-side parse
fault) instead of surfacing the HTTP failure. Status is preserved, unlike M4, but
the classification is still wrong. Parse only after branching on `response.ok`,
or tolerate non-JSON error bodies.

### m13 — `new URL(path, baseUrl)` with absolute paths discards any baseUrl path prefix
`packages/runtime/src/adapters/CaptureRpcClient.ts:72`

Every request path is absolute (`/v1/capture/...`), so a `baseUrl` carrying a
path prefix (reverse-proxy subpath) is silently dropped, producing hard-to-
diagnose 404s. Correct under the current origin-root mount; document the
origin-only contract or resolve relative to `baseUrl.pathname`.

---

## Checked and cleared (no finding)
- Request/response field round-trip is complete and symmetric (20 request fields, 10 response fields); all pydantic aliases match the TS camelCase keys; `proxyPort` never null; `webPort` key always present; empty-string false-rejection not reachable (variable-value maps use `stringRecord`).
- `_parse_uuid_id` → `parse_uuid_id` move: no stale callers, no now-unused imports in `run_routes.py`, PEP 695 `[IdT: (SpaceId, WorktreeId)]` with `TYPE_CHECKING` import resolves at runtime.
- Idempotency of `release_capture`/`close`/lease `close()` is correct (pop-under-lock, close-outside-lock; double release → `False`; `close_count` stays 1).
- `ExceptionGroup` from `close()` is caught by `_close_lifespan_resource` (it is an `Exception` subclass).
- TestClient lifespan: pre-set fake `CaptureLeaseRegistry` survives the lifespan `isinstance` check; not replaced.
- Origin policy: loopback origin the client sends (`baseUrl.origin`, matching the connect Host) satisfies `origin_allowed_from_headers`.
- `run_id` is `uuid4`, so `CaptureRunAlreadyRegistered` is effectively unreachable in production (still worth the test in m11).
- Protocol (not ABC) for `CaptureLeaseHandle`/`PrepareCapture` is correct (shape-only). No em dashes in new files. No private-name imports across modules.
