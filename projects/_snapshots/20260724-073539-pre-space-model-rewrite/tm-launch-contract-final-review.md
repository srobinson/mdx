# TM launch-contract (model+effort) — final pre-merge review

Branch `feat/launch-contract-model-effort` @ `dd7d5143` (worktree `/Users/alphab/Dev/LLM/DEV/helioy/tm-launch-contract`).
3 commits: `1dba22d5` capture, `eb9d0f9c` gateway/TS, `dd7d5143` control-plane. Read-only review; gate run.

## Verdict: MERGE-READY (yes)

No correctness bugs, dropped hops, or broken callers. Threading integrity, idempotency, audit,
and both clients are correct and tested. Full gate green in both languages. The findings below are
back-compat/coverage observations for owner awareness, not blockers.

---

## Focus results

### 1. End-to-end integrity — CONFIRMED, no hop drops model/effort
Traced `model`/`effort` across all 4 processes / 2 languages. Every hop threads both, and every hop
has a test:
- control-plane `launch()` kwargs -> `_NormalizedLaunchRequest` -> `_PreparedLaunch` -> `_execute`
  builds `GatewayCreateRunRequest(model=, effort=)` (test_launch_manage `test_execute_threads_model_to_gateway_request` asserts `request.model`).
- `run_proxy.RunRouteProxy.create_run` body — non-None spread matching `agentId`/`name`
  (test_run_proxy_controlplane asserts wire bytes `"model":"gpt-5.4","effort":"high"`).
- gateway `/v1/runs` -> runtimeRouter reads `body.model`/`body.effort`, validates via
  `optionalStringFromBody` (400 on `""`/non-string), forwards to `createWithDisposition`
  (gateway app.test.ts asserts `runtime.prepared` carries them; runtimeRouter.test.ts asserts 400 on malformed).
- `RunManager.prepareCapture` spreads `model`/`effort` (undefined-guarded); `createRunFingerprint`
  includes them (RunManager.test.ts + RunManager.idempotency.test.ts assert forward + drift-conflict).
- `CaptureRpcClient.prepareCaptureBody` sends `model`/`effort` (CaptureRpcClient.test.ts asserts the HTTP body).
- Python `PrepareCaptureRequest` (+`to_domain`) -> `CapturedRunRequest` -> `_build_provider_invocation`
  -> `build_{claude,codex}_captured_invocation` -> `client_argv` (`_model_argv`/`_codex_effort_argv`).
  test_capture_rpc_routes `test_prepare_request_model_effort_reach_domain`; test_launch_profile asserts
  `--model` + `-c model_reasoning_effort=`; test_captured_run asserts `--model` in `spawn_spec.client.argv`.

Sufficiency judgement: there is **no single assertion spanning all 4 processes to child argv**. Coverage
is a chain of per-hop unit tests plus two argv tests. The Python<->TS boundary is covered on **both halves**
by literal field-name assertions (`CaptureRpcClient.test.ts` body + `test_capture_rpc_routes.to_domain`),
which is where a silent drop would occur. Given no shared type crosses the boundary and the 4-process reality,
the matched-field-name per-hop chain is **sufficient**; a true single end-to-end test would need a live
4-process spawn. Accepted.

### 2. Idempotency (Slice C) — CORRECT, tests are not tautologies
`_intent_fingerprint` appends `model, effort` right after `harness` (raw requested values; control-plane
does no DB read — normalize passes them straight through). Guards:
- `test_intent_fingerprint_differs_by_model` / `_differs_by_effort` — direct digest inequality.
- `test_two_launches_differ_by_model_not_deduped` — two **distinct** dispatch ids + distinct models ->
  `spawn_count == 2`, both gateway requests carry the distinct models (real dispatch, not tautology).
- integration `changed_model` — **same** dispatch_id + different model -> 400 "dispatch_id was already
  used for a different launch request" (fingerprint truly distinguishes; retry-identical still dedups).
RAW requested values confirmed used pre-resolution.

### 3. Audit + both clients — CORRECT
`launch_action` records `model`/`effort` in `details` (integration + test_launch_manage assert audit
details). HTTP route forwards `body.model`/`body.effort`; MCP tool + `_McpControlPlaneAdapter.launch`
accept + forward; `run_proxy` sends non-None only (spread matches `agentId`/`name`).

### 4. Regression / back-compat — CLEAN, with one flagged behavior change
- All new params default to `None`; no existing caller signature breaks (mypy green).
- Direct CLI path (`prepare_captured_run`) builds the invocation **in-process**, bypassing HTTP
  `/capture/prepare`, so an omitted model stays `None` -> no `--model` -> argv identical to before.
- Fingerprint now differs for `None` vs a value (per task: acceptable — flagged).

### 5. Gate — PASS (judged by content)
- `just check`: ruff format (653 files unchanged), ruff check "All checks passed!", mypy
  "Success: no issues found in 653 source files", all TS typechecks pass. biome: **1 info** (non-blocking).
- `just test`: **Python 3268 passed, 2 skipped** (152.97s). **JS all passed, 0 failed**: desktop 102,
  shell 1247, common 24, contract 8, activity 286 (+33 skip), runtime 186 (+2 skip), gateway 21.
  Feature packages (runtime, gateway) green.

---

## Findings (most severe first)

### F1 — MEDIUM (verify intent + coverage gap): capture-time gating expansion
`_resolve_launch_target` runs on **every** `/capture/prepare` (canvas panes *and* control-plane service
launches), gated only on session-pool presence. It runs the full `resolve_target`, whose infra rejections
— `connection_unavailable`, `target_unavailable{compatibility_catalog_unavailable,no_default_target,
target_probe_failed}`, `connection_ambiguous`, `target_ambiguous` — are **not** in `_passes_to_harness`
and become hard 409/503 **before** `prepare_capture` ever runs.

Before this change, `/capture/prepare` only gated on harness enablement (`harness_not_installed`/
`harness_disabled`, raised inside `capture_rpc.prepare_capture`). So a previously-working **omitted-model**
canvas launch can now 409/503 if the executor's evidence store lacks a registered connection or embedded
release. The embedded compatibility release ships in-package (usually non-None), and a logged-in harness
usually has a connection row — but this couples canvas/service launch success to evidence-store population
that capture never required before.

Coverage: the wrapper (`resolve_launch_target_advisory`) and snapshot assembler are well unit-tested
(`test_launch_target.py` covers all 4 plan cases; `resolver_snapshots_for_harness` is reused/exercised by
the inventory path). But the **capture-route seam** (executor_id/channel/intent lookup, calling the wrapper,
rejection->HTTP-status mapping in `_launch_target_rejection_status`) has **no integration test**: the one
capture-route test that would hit it (`test_prepare_continuation_builds_the_recovered_lineage_fields`)
monkeypatches `resolve_launch_target_advisory` out. No test drives `/capture/prepare` with a real pool
asserting (a) a resolved model reaches argv, or (b) a hard rejection maps to 409/503.

Recommend: confirm the gating expansion is intended, and add one integration test through `/capture/prepare`
with a populated pool covering both a resolved-default-model launch and a hard-rejection -> 409/503.

### F2 — LOW (double-gate / preemption): overlapping compatibility enforcement
The resolver enforces compatibility only under `compatibility_enforcing()` — the **same** posture flag the
pre-existing S2f gate (`compatibility_service.gate_launch_preparation`) uses. In **enforcing** mode both gate
the capture path, and `_resolve_launch_target` runs first, so a capture-RPC launch gets the resolver's
compatibility rejection (503) and the S2f compatibility-fact artifact/audit is **not** written for that
blocked launch. In **advisory** mode (current live posture) both merely record advisories (resolver ->
`launch_fields.launch_advisories`, S2f -> its fact artifact): redundant but harmless. Confirm the double-gate
is acceptable, or dedupe so one authority owns compatibility at the capture seam.

### F3 — LOW (by-design note): Claude effort accepted but not applied
Claude `effort` is accepted, resolved, threaded, fingerprinted, and audited, but silently dropped at the
argv seam (`ClaudeLaunchProfile.client_argv`: `_ = effort`; no Claude effort flag). Matches the plan's stated
decision, but a user who selects a Claude effort sees it recorded yet not applied to the launched process.
Worth a UI/doc note.

### F4 — LOW (by-design note): audit records raw request, not resolved target
`launch_action`/`LaunchResult` record the **raw requested** `model`/`effort` (`None` when omitted), while the
resolved target lands in argv. An omitted-model launch that pins the enumerated default audits as `model=null`
yet spawns with `--model <default>`. By design (control-plane does no DB read; fingerprint keys on raw). Minor
observability asymmetry.

### F5 — INFO (flagged per task): omitted model now pins enumerated default in argv
For capture-RPC launches (canvas/service), an omitted model now resolves to the enumerated default and injects
`--model <default>`, where before nothing was passed (harness home default). By design (plan case a). If the
enumerated default matches the harness home default there is no observable change.

## Quality / craft notes
- DRY snapshot extraction (`resolver_snapshots_for_harness`) is faithful — inventory's five-read gather is
  replaced by the shared helper with no fork or behavior drift; `match_release` still receives the
  blocks-merged channel state.
- `_model_argv`/`_codex_effort_argv` are clean shared helpers; non-None spreads match the existing
  `agentId`/`name` idiom on both the Python egress and the TS `RunManager` spread.
- `resolve_launch_target_advisory` correctly surfaces exactly the three plan-sanctioned verdicts
  (`target_unavailable`+not_observed, `invalid_effort`, `target_unverified_opt_in_required`) and hard-fails
  everything else, including explicitly `retired` and `probe_failed` targets.
