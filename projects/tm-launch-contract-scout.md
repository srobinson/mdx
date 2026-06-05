# Move 1 — thread `model` + `effort` through single-launch (the new launch contract)

Branch: `feat/launch-contract-model-effort` at worktree `/Users/alphab/Dev/LLM/DEV/helioy/tm-launch-contract`.

## Load-bearing decisions (do not relitigate)
- **SURFACE-DON'T-GATEKEEP.** An off-catalog `(model, effort)` request must NOT block. It proceeds to spawn; the harness's own first-turn rejection is the captured verdict (claude→transcript, codex→wire `transport.json`). So the launch path reinterprets specific resolver rejections as ADVISORY pass-through.
- **Do NOT mutate `harnesses/resolver.py`.** It is shared with the inventory/picker API (`GET /api/v1/harnesses` via `launch_options`). Softening its rejections there would corrupt the picker. The advisory reinterpretation lives in a NEW launch-path wrapper only.
- Effort is symmetric internally: every target carries `native_efforts` + `native_default_effort`. Claude's global `/effort` vocab is expanded per-model at `probes/claude.py`; codex has per-model `supported_reasoning_levels`. The launch tuple carries a flat `effort: str | None`.

## Architecture reality: a launch crosses 4 processes / 2 languages
Python control-plane → TS Gateway (`packages/gateway`) `/v1/runs` → TS Runtime (`packages/runtime`) `RunManager` → Python `/capture/prepare` → `prepare_captured_run` → `LaunchProfile.client_argv`.
`model`/`effort` must survive ALL hops. **No shared type crosses the Python↔TS boundary**; miss one hop and the value silently drops, the harness boots on its home default, and the launch *looks* successful with the wrong model. The ONLY guard is an end-to-end test asserting the child argv contains `--model`.

## Terminal seam (where model/effort become CLI args)
`cli/launch_profile.py::LaunchProfile.client_argv` (both `ClaudeLaunchProfile` and `CodexLaunchProfile`). Today: no model flag passed (confirmed; the `-m` in `captured_run.py` is `python -m ...secure_workdir`, unrelated).
- Claude: inject `["--model", model]` when `model` set. No separate claude effort flag today — `effort` is a no-op / reserved for claude.
- Codex: inject `["--model", model]` and `["-c", f"model_reasoning_effort={effort}"]` when set. Reuse the `-c` config-arg shape from `_codex_shell_environment_policy_args`.

## Surface-don't-gatekeep wrapper (THE core correctness point)
`resolve_target` returns EXACTLY ONE of `resolved`/`rejection`. Add a launch-path wrapper `resolve_launch_target_advisory(request, snapshots) -> (model, effort, advisories)`:
- (a) **omitted model** → `resolve_target` picks the enumerated default → use `resolved.model_id`, `resolved.effort`.
- (b) **specified + on-catalog** → use `resolved.*`; forward `warnings` (`deprecated_target`) + `compatibility_advisories` as advisories.
- (c) **specified + off-catalog / invalid effort / unverified** → rejection code in `{target_unavailable(not_observed), invalid_effort, target_unverified_opt_in_required}` → return the RAW REQUESTED model/effort + a launch advisory recording the code+details, and SPAWN ANYWAY.
- (d) **any other rejection** (`harness_not_installed`, `harness_disabled`, `connection_unavailable`, compatibility hard-block when `compatibility_enforcing()`) → STAYS a hard failure. These are infra-availability, not a model/effort verdict.
Rejection sites to reinterpret (read, don't edit resolver): `resolver.py::_select_edge` (`target_unavailable`), `resolver.py::_resolve_effort` (`invalid_effort`), `_validate_explicit_edge` (`target_unverified_opt_in_required`).
Placement: run wrapper Python-capture-side in `capture_rpc_routes` (has pool/DB access — "Python stays the one validator"). Fingerprint uses RAW requested values (control-plane needs no DB read).

## Shared snapshot assembler (DRY refactor-during)
`ResolverSnapshots` is assembled ONLY in `harnesses/inventory.py::_harness_item` (the evidence-store reads: `ExecutorEvidenceStore.latest_harness_observation/list_connections/latest_target_observations`, `ExecutorBlockStore.active_blocks`, `embedded_channel_state`, `embedded_release_entry`, `merge_executor_blocks`). Extract into a shared helper so the launch path builds the same snapshot for one `(harness, connection)`. Do not fork it.

## Full threading path (every symbol to touch)
Python control-plane egress:
- `controlplane/run_models.py`: `LaunchRequest`, `GatewayCreateRunRequest`, `LaunchResult` gain `model: str | None`, `effort: str | None`.
- `controlplane/launch_service.py`: `launch` kwargs; `_normalize_launch_request`; `_NormalizedLaunchRequest`; `_PreparedLaunch`; `_prepare`; `_execute` `GatewayCreateRunRequest(...)`; **`_intent_fingerprint` MUST append `model, effort`** (raw requested) so two launches differing only by model are distinct dispatches.
- `controlplane/service.py::ControlPlaneService.launch` passthrough.
- `controlplane/action_builders.py::launch_action` → add `model`/`effort` (and advisory codes) to `details`.
Python↔Gateway wire:
- `api/v1/run_proxy.py::RunRouteProxy.create_run` body dict — add keys (non-None only, matching `agentId`/`name`).
TS hops:
- `packages/runtime/src/ports.ts::PrepareCaptureInput`; `packages/runtime/src/service/RunManager.ts::prepareCapture` field spread; `packages/runtime/src/adapters/CaptureRpcClient.ts::prepareCaptureBody`; gateway `/v1/runs` CreateRun schema.
Python capture ingress + argv:
- `api/v1/capture_rpc_routes.py::PrepareCaptureRequest` (+aliases) + `to_domain()`; the `_resolved_domain_request` seam runs the advisory wrapper.
- `captured_run_models.py::CapturedRunRequest`; `captured_run_context.py::_build_provider_invocation`; `captured_claude.py::build_claude_captured_invocation`; `captured_codex.py::build_codex_captured_invocation`; `cli/launch_profile.py::client_argv`.
Both clients:
- `api/v1/controlplane_routes.py::launch` (HTTP); `api/v1/controlplane_mcp.py` launch tool + `ControlPlaneMcpAdapter.launch`.

## Slice plan (one feature branch)
- **Slice A (Python capture side, isolated value):** argv seam (`client_argv` both profiles + `captured_claude`/`captured_codex` + `_build_provider_invocation` + `CapturedRunRequest`) + capture ingress (`PrepareCaptureRequest`/`to_domain`) + advisory wrapper (extract snapshot assembler, `resolve_launch_target_advisory`, wire into `_resolved_domain_request`). Tests below. Lands testable value before the control-plane exposes the field.
- **Slice B (TS wire):** the four TS hops. End-to-end argv test spans A+B.
- **Slice C (control-plane egress + clients):** `GatewayCreateRunRequest`, `run_proxy` body, launch_service (+ `_intent_fingerprint`), `launch_action`, `LaunchRequest`, HTTP route, MCP tool+adapter.

## Failing tests (co-located; fail before / pass after)
- `cli/test_launch_profile.py`: `test_claude_client_argv_threads_model` (`--model claude-x` adjacent in argv); `test_codex_client_argv_threads_model_and_effort` (`--model gpt-x` present + `-c model_reasoning_effort=high` present); `test_client_argv_omitted_model_unchanged` (regression).
- `controlplane/test_launch_service.py`: `test_intent_fingerprint_differs_by_model`; `test_execute_threads_model_to_gateway_request`; `test_two_launches_differ_by_model_not_deduped`.
- new advisory test file: `test_off_catalog_model_not_rejected_carries_advisory`; `test_invalid_effort_surfaces_not_blocks`; `test_omitted_model_resolves_enumerated_default`; `test_hard_unavailability_still_fails`.
- `api/v1/test_capture_rpc_routes.py`: `test_prepare_request_model_effort_reach_domain`.
- route/mcp tests: launch tool/route accept + forward `model`/`effort`.

## Gate
`just check` + `just test-affected` (builder, before submit). grok runs full `just check` + `just test` as authoritative pre-merge.
