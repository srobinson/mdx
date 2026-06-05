# S2 review — PR#301 `feat/s2-harness-enablement` @ `0b813ec7`

**Range:** `main..feat/s2-harness-enablement` (`506e0409..0b813ec7`)
**Method:** committed SHAs only (`git show` / `git diff`); working tree is on another branch and was not read as source of truth
**Tree:** pristine at review (working tree on `feat/s1-provider-condition-signal`, clean)
**Spec:** `~/.mdx/projects/transport-matters-spec-s2-enablement.md`
**Verdict:** **clean**

## Summary

S2 lands the hard enablement gate beside the existing advisory compatibility gate: executor-scoped Postgres intent, `prepare_launch` choke point, resolver/`launch_options` visibility with `harness_disabled`, REST write+read with default-path identity, full 2×4 boundary translation, auth-gating retirement from the resolver path and contract docs, migration `0026_harness_enablement` decoupled from S1. Load-bearing checks hold under code trace. No open production issues found.

## Load-bearing checks

| # | Check | Result |
|---|--------|--------|
| 1 | TWO-GATE: enablement = installed + toggle default-ON; version-compat not an enablement input; resolver compat respects `COMPATIBILITY_ROLLOUT` (advisory does not exclude), matching `prepare_launch` | **PASS** |
| 2 | FAIL-CLOSED: store read failure → typed disable; 2×4 boundary matrix asserts structured non-500 outcomes | **PASS** |
| 3 | TRUST BOUNDARY: natural key `(executor_id, harness_id)` | **PASS** |
| 4 | RETIREMENT SWEEP: auth-gating codes gone from resolver + LAUNCH/HARNESS docs; `access_observation_revision` removed; probe `authentication_probe_failed` retained | **PASS** |
| 5 | Migration 0026 CHECK DDL, ≤32 chars, decoupled from S1 | **PASS** |
| 6 | REST write + persisted read with effective eligibility, path+version, `bin_override` out | **PASS** |
| 7 | General correctness, 700-line limit, reuse, ripple | **PASS** |

### 1. TWO-GATE — PASS

- Enablement inputs only: installed (`observe_resolved_binary` / capability) and user intent (`harness_enabled_sync`, default-on when no row). Version never consulted in `gate_harness_enablement`.
- Compatibility remains `COMPATIBILITY_ROLLOUT = "advisory"`; bounds unchanged, factored into shared `launch_gate_connection.open_launch_gate_connection`.
- Resolver: `compatibility_enforcing()` shared with the launch gate. Under advisory, mismatches become `CompatibilityAdvisory` and do not hard-reject or exclude; under enforcing, they reject/exclude. Tests cover both postures on `resolve_target` and `launch_options`.
- `prepare_launch` runs enablement then compatibility over the same resolved executable; enablement observation is reused via `observe=` so the binary is not re-probed for the advisory gate.

### 2. FAIL-CLOSED + 2×4 matrix — PASS

Typed domain error: `HarnessEnablementRejected` with codes `harness_disabled`, `harness_enablement_unavailable` (and `harness_not_installed` for the installed half of the gate). Store/identity/connect failures wrap with `from exc`.

| Boundary | harness_disabled | harness_enablement_unavailable |
|----------|------------------|--------------------------------|
| Capture RPC | 409 + code (`test_harness_enablement_boundaries`) | 503 + code |
| Claude CLI | exit 1 + `error: code: …` (`test_launch_enablement`) | same |
| Codex CLI | same matrix | same |
| MCP | skin preserves code (`test_mcp_launch_preserves_enablement_outcomes`); `run_proxy` preserves enablement codes into `GatewayResponseError.code` before `action_policy` (`test_run_proxy_preserves_enablement_code_before_action_policy_mapping`); status map on controlplane routes | same |

Never fail-open; non-enablement gateway 500s stay opaque (code left null).

### 3. TRUST BOUNDARY — PASS

- Table PK `(executor_id, harness_id)`; store list/read scoped by executor.
- `test_enablement_store_defaults_on_and_scopes_intent_by_executor`: A disabled does not affect B; no-row remains enabled.

### 4. RETIREMENT SWEEP — PASS

- `_access_evidence` and access-gated connection selection removed; connection selection is topology-only (`connection_unavailable` / `connection_ambiguous`).
- `ResolutionRejectionCode` no longer includes `authentication_*` / `access_*` gating members; `harness_disabled` added.
- `ResolvedTarget.access_observation_revision` removed; no orphan required field.
- `ResolverSnapshots.access_observations` removed as a resolution input (access observations remain in connections store / probe models for S3 diagnostics).
- LAUNCH-CONTRACT / HARNESS-COMPATIBILITY / RUNTIME-SURFACING-S2-PLAN rewritten to two-gate posture; auth surfaces, does not authorize launch.
- Scoped residue: `authentication_probe_failed` remains only as `ProbeFailureReason` / probe tests / connections access-status vocabulary — correct per spec.
- Note (not a defect): older `RUNTIME-SURFACING-PLAN.md` still mentions historical readiness codes including `authentication_required`; that plan was not in the required sweep set for this slice.

### 5. Migration 0026 — PASS

- Revision id `0026_harness_enablement` length 23 (≤32).
- `down_revision = 0024_drop_observation_identity` — independent of S1's 0025; merge-second rebase owns the chain.
- DDL: PK `(executor_id, harness_id)`; nonempty CHECKs only (no closed harness vocabulary) — matches 0022 precedent.
- Head pin + roundtrip step + focused migration test (unique + check violations, up/down).

### 6. REST write + read — PASS

- Write: PUT intent only; test asserts no binary probing on write.
- Read: default_path resolution via `detect_harnesses`; carries `path` + `version`; `resolution="default_path"`, `bin_override_evaluated=false` in contract; eligible = installed ∧ enabled; default-on when unconfigured.
- Origin gate on write; 503 when store pool absent; CORS allows PUT.

### 7. General — PASS

- All new/edited production modules under 700 lines (`resolver.py` 691).
- Shared `open_launch_gate_connection` avoids duplicating four connection bounds.
- Autouse conftest stub keeps unrelated launch tests independent of the hard store gate; enablement tests re-bind the seam explicitly.
- Capture path: `gate_enablement=write` through `captured_run_context`; domain exception surfaces at `capture_rpc_routes` (not swallowed inside `capture_rpc`).

## Issues

None.

## Builder-trust (codex build)

**Trust: high.** Craft is deliberate: pure intent model, store, service, shared launch-gate connection, choke-point wiring, and boundary translation are separated without parallel pipelines. Spec fidelity is strong (two-gate independence, fail-closed typing, executor keying, REST identity semantics, auth retirement without probe-vocabulary collateral). Test rigor matches the brief — full 2×4 matrix, executor scope, posture parity advisory vs enforcing, sticky default-on, migration constraints — with the MCP preservation split correctly across run_proxy and the skin. No material shortcuts or boundary blind spots found; the one large commit is cohesive rather than tangled.

## Counts

- major: 0
- minor: 0
- nits: 0 (doc residue in out-of-sweep `RUNTIME-SURFACING-PLAN.md` noted above only)
