# PR#299 S2f part 1 adversarial review (grok)

| Field | Value |
|-------|-------|
| PR | [#299](https://github.com/littleorgans/transport-matters/pull/299) |
| Range | `main...feat/s2f-resolver-gating-setup` (`10e922fb`…`5e1c4eea`) |
| Method | `git diff main...HEAD` / `gh pr diff 299` + full file read of gate, resolver, launch seams, stores, tests |
| Tree at verdict | `feat/s2f-resolver-gating-setup` @ `5e1c4eea`, **clean** |
| Scope | Read-only review; no gates; no source writes; authorized write only to this `~/.mdx` file |
| Specs | scout `~/.mdx/projects/transport-matters-scout-s2f.md`, `RUNTIME-SURFACING-S2-PLAN.md` S2f (two-PR split), `HARNESS-COMPATIBILITY.md`, `LAUNCH-CONTRACT.md` |
| Decision under test | ADVISORY (never blocks); ENFORCING branch built-dead under `COMPATIBILITY_ROLLOUT='advisory'`; gate scope version+block; setup actions part 2 |

## Summary

S2f part 1 lands the pure resolver (`resolve_target` / `launch_options`), the first production `match_release` caller as a single advisory gate at `prepare_launch`, sync audit + fact recording, and dead enforcing branch with per-seam acceptance tests. Live-launch safety is structural: best-effort `except Exception` (re-raises only `HarnessCompatibilityRejected`), 2s version probe over the already-resolved binary, 5s connect timeouts on store paths, and `--print-command` skips the gate entirely. Boundaries hold (no setup actions, no inventory, no enforcing flip). One Major remains on test rigor for the named best-effort failure matrix; no production advisory-block path found.

**Counts: 0 Blocker / 1 Major / 4 Minor**

## Focus checklist

| Focus | Verdict | Evidence |
|-------|---------|----------|
| Gate at `prepare_launch` only; three seams converge | PASS | `launch_runtime.py:334-343`; captured path via `gate_compatibility=write` (`captured_run_context.py:257`); codex via `gate_compatibility=not print_command` (`codex_cmd.py:404`); per-seam tests in `test_launch_compatibility_gate.py` |
| Advisory never blocks/stalls; best-effort wrap | PASS (code) / PARTIAL (tests) | `gate_launch_preparation` try/except (`compatibility_service.py:328-352`); probe explode → None + claude seam launch proceeds; **named store/write/config modes lack dedicated launch-proceeds tests** (Major 1) |
| `--print-command` skips gate (no probe/store/write) | PASS | codex seam `test_print_command_skips_the_gate_entirely`; claude/capture via `write=not print_command` / `gate_compatibility=not print_command` |
| Hard connect timeouts; no unbounded DB connect / probe | PASS (stated scope) | `GATE_CONNECT_TIMEOUT_S=5` on `active_blocks_sync` + `ControlPlaneAuditSyncWriter`; probe `DEFAULT_VERSION_TIMEOUT_S=2.0` + `TimeoutExpired` → None. Residual: no `statement_timeout` / overall wall clock after accept (Minor 1) |
| Only one version probe; no auth probe / second which-walk | PASS | `observe_resolved_binary` over `client_path` only (`capabilities.py:145-157`); no `run_authentication_probe` / `probe_environment` in gate module |
| ENFORCING dead under advisory; fails closed when flipped | PASS | `COMPATIBILITY_ROLLOUT = "advisory"`; enforcing fixture raises on incompatible / missing / internal failure after record; three seams reject same fixture under flip |
| Resolver: LAUNCH-CONTRACT order; composes `match_release` + `resolve_connection` | PASS | `resolve_target` mismatch order (`resolver.py:438-518`); `_tuple_match` → `match_release`; `_select_connection` → `resolve_connection`; no I/O |
| Gate scope version+block only (route/target S2g) | PASS | Gate calls `match_release` without route/model; resolver ships pure for later inventory |
| Facts + `harness_compatibility_gate` audit; sync psycopg; idempotent dispatch | PASS | `write_compatibility_facts` + `compatibility_facts_action` + `gate_audit_action` / `gate_dispatch_identity`; `ControlPlaneAuditSyncWriter.write_all`; dispatch identity excludes `facts_recorded` |
| Reuse/DRY: no 4th fact bundle; no 8th store copy; no second which-walk | PASS | Consumes `LaunchPreparation` + run storage; `fetch_models` / `fetch_models_sync` extracted; `as_harness_id` centralized; codex CA cluster extracted to `codex_trust.py` (codex_cmd 479 LOC) |
| Boundaries: no setup / inventory / enforcing flip | PASS | Two-PR plan note; no setup adapters/routes; rollout constant stays advisory |
| Test rigor: enforcing reject, advisory record, best-effort, resolver | PARTIAL | Per-seam enforcing+advisory present; internal failure only on observe + one claude seam; resolver unit coverage strong (no hypothesis library; property-style cases covered) |

## Hygiene (28 changed files only)

| File | LOC | Notes |
|------|-----|-------|
| `harnesses/resolver.py` | 591 | New pure core; under 700; largest functions ~80L |
| `harnesses/compatibility_service.py` | 352 | New gate; clear advisory/enforcing split |
| `cli/codex_cmd.py` | 479 | CA trust extracted first (was 693); under 700 |
| `cli/codex_trust.py` | 238 | Mechanical extract |
| `cli/launch_runtime.py` | 398 | Single choke wiring; storage pin + gate flag |
| `session/pool.py` | 174 | `fetch_models` / `fetch_models_sync` + connect timeout |
| `controlplane/audit.py` | 188 | Sync writer with connect timeout |
| `harnesses/blocks_store.py` | 307 | `active_blocks_sync` |
| `harnesses/connections_store.py` | 421 | `fetch_models` migration; `list_connections_sync` unused (Minor 2) |
| Tests | 311+321+565 | Service, seam, resolver; shared `install_gate_fakes` |

No new file over 700. No production function past ~150 in the slice. Duplication reduced (store reads, facts audit action, session URL resolver, harness id narrow).

## Issues

### Issue 1 — Severity: Major
- **File:** `api/src/transport_matters/harnesses/test_compatibility_service.py:228-234` and `cli/test_launch_compatibility_gate.py:188-206`
- **Description:** Best-effort launch-proceeds coverage is only the probe `RuntimeError` path (unit + one claude seam). The review brief and scout name manifest error, DB unreachable, probe timeout, artifact write failure, and any raise as required modes. Structurally `except Exception` covers them, but there is no dedicated test that `active_blocks_sync` / audit `write_all` / `write_compatibility_facts` / `_gate_database_url` failures leave advisory launch ungated with no raise. Probe timeout is handled in-band as `version=None` (not ungated), so it is a different outcome path and also lacks an explicit gate-level assertion.
- **Suggestion:** Add unit cases that stub each collaborator to raise (and one that returns timed-out/unknown version) and assert `gate_launch_preparation` returns `None` or records `harness_version_unknown` as appropriate with no exception. Optionally one codex/capture seam case mirroring the claude internal-failure test.
- **Status:** open

### Issue 2 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/compatibility_service.py:84-86` and `session/pool.py:38-46`
- **Description:** Store safety is connect-timeout only (`GATE_CONNECT_TIMEOUT_S=5`). After the server accepts, `SELECT`/`INSERT` have no `statement_timeout` and the gate has no overall wall clock. A wedged post-accept store can still stall launch beyond the "hard connect timeout" story (CLI preflight already hard-blocks dead stores, so this is residual).
- **Suggestion:** Set a session `statement_timeout` on gate connections, or wrap the whole `_gate` body in a hard deadline slightly above connect+probe budget.
- **Status:** open

### Issue 3 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/connections_store.py:412-421`
- **Description:** `list_connections_sync` is introduced with no callers and no `connect_timeout_s` parameter (unlike `active_blocks_sync` / `fetch_models_sync` gate use). Dead surface that looks launch-safe but is not timeout-shaped.
- **Suggestion:** Drop until a caller needs it, or plumb `connect_timeout_s` and document non-launch use.
- **Status:** open

### Issue 4 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/compatibility_service.py:19-24`
- **Description:** Module docstring claims the only added live-path cost is the bounded `--version` probe. Success path also does `active_blocks_sync`, fact artifact write, and audit `write_all` (two sync handshakes when recording). Latency story oversells.
- **Suggestion:** Document probe + bounded store read/write as the advisory cost; keep the "no auth probe / no second which-walk" claim (that part is accurate).
- **Status:** open

### Issue 5 — Severity: Minor
- **File:** `api/src/transport_matters/cli/conftest.py:162-179`
- **Description:** Autouse stubs `preflight_session_store_or_exit` for CLI mechanics tests so they never need live Postgres, but does not stub `gate_launch_preparation`. With ambient test-prefixed DB config the gate can perform real probe/store/audit work on every non-print launch test; without it, URL/guard failures fail closed into ungated (fast). Asymmetry with the preflight stub.
- **Suggestion:** Autouse-stub `gate_launch_preparation` to return `None` in CLI conftest (S2f seam tests already install their own fakes), or pass `gate_compatibility=False` from test helpers that only care about launch mechanics.
- **Status:** open

## Non-issues (checked, plan-sanctioned)

- ENFORCING branch is code-dead under the constant; tests flip it explicitly.
- Resolver pure module is unused by the live gate; version+block scope is intentional; route/target join is S2g.
- Setup actions, inventory, first-run, package pointer flips are correctly absent (part 2 / S2g).
- `match_release` and `resolve_connection` are composed, not forked.
- Attribution (`resolve_compatibility_release_id`) is not mixed into the authorization gate.
- Workspace storage is finalized before the gate records (`resolve_run_storage` + validation reorder).
- codex_cmd refactor-first CA extract clears the 700 headroom cleanly.
- DriftEmitter `release_id`/`route_id`/`model_id` still absent on live evidence fields is allowed as planner follow-up; facts + gate audit carry context.
- Revoked channel status is covered at `match_release` unit level (`test_compatibility.py` parametrize); gate tests sample paused/missing.

## Craftsmanship verdict

Tight choke-point design with real reuse (one gate, shared store fetch, sync audit split, codex extract): production advisory safety looks sound; close the best-effort failure-mode test matrix before merge confidence matches the brief.

---

## Delta re-verify `5e1c4eea..23d34d79` (HEAD `23d34d79`)

| Prior finding | Status | Evidence |
|---------------|--------|----------|
| Major 1 best-effort failure matrix | **resolved** | `test_each_collaborator_failure_leaves_the_launch_ungated` (manifest/blocks_read/audit_write/facts_write/database_url); existing probe RuntimeError; codex seam `test_advisory_launch_survives_internal_gate_failure` |
| Minor 1 statement_timeout / wall clock (escalated blocker elsewhere) | **resolved** | `GATE_STATEMENT_TIMEOUT_S=5` on blocks+audit; `GATE_DEADLINE_S=30` via `_gate_within_deadline` daemon join; `TestLaunchNeverStalls` (blocks_select/audit_insert_commit/facts_artifact) asserts return <2s with 0.2s deadline; enforcing fails closed on deadline |
| Minor 2 dead `list_connections_sync` | **resolved** | dropped from `connections_store.py` |
| Minor 3 docstring latency oversell | **resolved** | module doc: probe+identity hash+store read+fact/audit under connect/statement/deadline bounds |
| Minor 4 conftest gate-stub asymmetry | **resolved** | cli conftest autouse stubs gate; seam module restores real `gate_launch_preparation` |

Escalated peer findings also present in delta and look correct on read:
- executable_identity via `resolved_binary_identity` + fact assertion test
- resolver evidence bound to executor/release/version; sole-ready connection; explicit target + complete-effort checks + tests

Abandonable worker: join does not wait past deadline; facts write remains atomic (`atomic_write_model_json`); abandoned daemon may leave eventual fact/audit after ungated return (best-effort side effect, not launch stall or half-written artifact). No new merge-blocking issue in the 12-file delta.

**Verdict: verify clean**

---

## Delta re-verify design change `ff637e98..9b198ac7` (HEAD `9b198ac7`)

Stuart ripped abandonable-worker/staging; gate is synchronous best-effort.

| Check | Verdict | Evidence |
|-------|---------|----------|
| Stall class (store) | CLOSED | `_open_gate_connection`: connect 5s, statement_timeout 2s (SELECT/INSERT/COMMIT), tcp keepalive idle/interval 5 count 3; probe 2s via `observe_resolved_binary` |
| Residual hang | local FS only | `resolved_binary_identity` full-file hash + `atomic_write_model_json` artifact: no wall clock; accepted outside store wedge class; no half-written artifact |
| Best-effort skip | PASS | outer `except Exception` → None; `_record` inserts then artifact then commit; fail before commit discards; commit-after-artifact mismatch accepted; connection always closed in finally |
| Dead machinery | GONE | no GATE_DEADLINE / _gate_within_deadline / _AbandonableGate / stage_* / StagedModelJson / cancel_safe; `atomic_write_model_json` restored as sole write |
| Enforcing / seams / resolver | still present | TestBestEffortRecording enforcing fail-closed; seam advisory/enforcing/print-command; resolver ready/stale/effort tests |
| Stale prose | nit | `blocks_store.active_blocks_sync` + `write_actions_sync` still mention "abandoning" cancel/close; not a runtime ref |

**Verdict: verify clean**
