---
title: Sign-off findings — t3code P1 Slice 4e-d (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-4e-d, sign-off, review, cutover, deletion]
summary: Opus independent plan sign-off on 4e-d (destructive cutover + delete Python run path). Verdict GO-WITH-FIXES. The deletion architecture is sound and the importer evidence is mostly accurate, but the sweep MISSED 3 surviving test files (each = red CI) and omits an emission-critical must-preserve. All importers re-grepped first-hand on main @ 84da72c.
status: active
source: opus (5:2.3), first-hand on main @ 84da72c (4e-a + 4e-b merged)
confidence: high
created: 2026-07-08
---

# 4e-d plan sign-off (opus) — GO-WITH-FIXES

Independently re-grepped every deletion target and relocated symbol on main @ 84da72c.
Deletion architecture is sound; 503 stub + relocations are the right shape. But the
importer sweep missed **3 surviving test files** (each red CI on its own) and the plan
omits the emission-critical must-preserve.

## Confirmed dead / sound (independently verified)

- The 7 source deletions are genuinely unreachable: no barrel/`__all__`/star re-export of any
  dying module; the only string/dynamic references to the dying modules live inside dying or
  rewritten test files. Non-test importers match the plan exactly (run_routes → main.py +
  capture_rpc_routes[DEFAULT_OWNER,require_http_origin] + space_routes[require_http_origin];
  run_manager → run_routes + run_storage._live_run_storage; run_terminal/run_models/osc/run_preparation/
  run_continuation → only dying modules).
- **No surviving runtime reader of `app.state.run_manager`** beyond what the plan drops (main.py sets it;
  run_storage._live_run_storage drops it; capture_rpc_routes:141 is a comment; runs_health docstrings). No
  hidden runtime break.
- `require_http_origin` surviving consumers (space_routes ×4, capture_rpc_routes ×3) and the
  `send_run_error_and_close` relocation are complete; run_proxy has its own same-named method (no collision).
- 4e-a's emitter is real (`session/writer.py::run_lifecycle_emitter`, wired in lifespan) — the lifecycle-fidelity
  premise holds.
- 503 stub golden rule is correct: exchanges/meta are separate routers; `GET /runs/{id}` cannot shadow the
  `/runs/{id}/exchanges` sibling under FastAPI exact-path matching.
- Doctor 503 handling correctly identified: `runs_health.fetch_runs` does `raise_for_status()` (a 503 raises
  HTTPStatusError, not ConnectError → would crash) — the plan's fix is right.

## Must-fix

### M1 — Deletion-safety: 3 surviving test files the plan's §2 omits (each = red CI)

The plan lists 12 test deletions + 4 rewrites. Three more surviving tests break and are unlisted:

- **(a) `api/v1/test_main_lifespan_shared_proxy.py`** (NOT in any list). Monkeypatches
  `transport_matters.main.run_routes.create_run_manager` / `close_run_manager` and asserts
  `app.state.run_manager._shared_proxy_unavailable_reason`. Post-cutover main.py imports no `run_routes` and
  sets no `app.state.run_manager` → patch raises AttributeError + the assertion is dead. The premise
  (shared-proxy failure degrades runs) is obsolete: runs are gateway-owned and `shared_proxy_unavailable_reason`
  becomes unconsumed. Rewrite to assert `app.state.shared_proxy_manager` degradation (that path survives,
  main.py lines ~249-261) or delete. The plan even notes the shared proxy is now vestigial but never flags this
  test.
- **(b) `shared_proxy/test_run_preparation.py`** (NOT in the delete list). Imports + patches
  `transport_matters.shared_proxy.run_preparation.*` — the deleted module → collection failure. DELETE it. This
  is the 13th test file; the plan's count of 12 is short by one.
- **(c) `test_pty_session.py::test_package_root_terminal_modules_import_in_subprocess`**. Asserts
  `import transport_matters.run_terminal` and `...run_manager` each return returncode 0 in a subprocess. Both
  deleted → assertion fails. Drop `run_terminal` + `run_manager` from its module tuple (keep
  captured_run_models + pty_session).

### M2 — Emission must-preserve: the capture-registry emitter injection must survive the create_run_manager deletion (silent-data-loss class)

main.py lifespan constructs the capture registry with `emit_run_lifecycle=run_lifecycle_emitter(session_pool)`
in a block (the "registry constructed only after the session pool" comment block) that sits **immediately
before and separate from** `create_run_manager(...)`. Post-cutover this registry emitter is the SOLE remaining
RUN_STARTED/EXITED path. "Drop create_run_manager + run_manager state" (plan §5) must touch ONLY the
run_manager construction + its `close_run_manager` finalizer — the capture-registry construction block must stay
verbatim, and `close_capture_registry` in the finally must stay. Severing the emitter silently drops every
canvas run's lifecycle history (the exact L3 regression 4e-a existed to fix). The plan does not call this out;
make it an explicit preserve-line in the build brief with a test that a proxied run still lands RUN_STARTED/EXITED.

### M3 — Placement/DRY: DEFAULT_OWNER (softer)

`DEFAULT_OWNER = "local"` is already triplicated (run_routes, space_routes, session_routes;
capture_rpc_routes imports the run_routes copy). Moving it into `launch_resolution.py` is import-clean
(capture_rpc_routes already imports launch_resolution) but launch_resolution is a capture-plane module —
forcing space/session routes to depend on it for a bare constant is wrong coupling. Prefer a neutral shared
leaf (alongside the new `origin.py`, or a small constants module) and collapse all three definitions. At
minimum don't leave three copies behind a fourth relocation.

## Softer notes

- **resolved_worktree relocation consumer list is slightly wrong.** Actual surviving consumers are
  `test_capture_rpc_routes.py` + `test_meta.py` (plus the rewrite survivors `test_cli_web_control_plane.py`
  and `test_run_lifecycle_emission.py`), NOT `space/test_models.py` (not a consumer). Re-point every real
  consumer to `space/testing.py`.
- **test_cli_web_control_plane.py rewrite must remove the module-level imports** (`SpawnRun`,
  `PreparedRunHarness`, `PtyHarness`, `make_manager`), not just re-fixture the one breakpoint test — otherwise a
  dangling import fails collection. (Usage is concentrated at one test setup, so scope is small.)
- **Top RUNTIME (non-CI) risk to actually prove:** the rewritten `test_exchanges_live_run_storage.py` must
  exercise a run prepared THROUGH `CaptureLeaseRegistry.prepare_capture` (→ `prepare_captured_run` writes the
  manifest), then assert exchanges + meta resolve with `app.state.run_manager` ABSENT. If it fabricates the
  manifest directly, it does not prove gateway-owned-run resolution — that is the silent-404-on-every-canvas-run
  risk of dropping `_live_run_storage`.
- **capture_rpc_routes.py:141 comment** references the deleted `run_routes.get_run_manager_from_app` — reword.
- **forward_http hardening (§1):** the `httpx.ConnectError` + `httpx.TimeoutException` set is right; confirm it
  wraps all four HTTP legs uniformly (create/list/get/terminate), not just create.

Scope discipline clean (Stuart's D-d1 503-on-reattach + D-d2 delete continuation/idempotency + external-web are
honored). The architecture is right; the gaps are completeness in the deletion sweep and one emission
preserve-line.
