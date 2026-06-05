# Slice A review — new launch contract (model + effort threading)

Branch `feat/launch-contract-model-effort` @ `1dba22d5`, worktree `/Users/alphab/Dev/LLM/DEV/helioy/tm-launch-contract`.
Reviewed against `/Users/alphab/.mdx/projects/tm-launch-contract-scout.md`. Read-only; gate run only.

## Verdict: CLEAN — no blockers, no majors. Two minor observations, both non-defects.

Diff is Python-only (15 files, all `.py`); Slices B/C correctly absent.

---

## 1. Advisory wrapper (`harnesses/launch_target.py`) — THE critical logic: CORRECT

`_passes_to_harness` passes through EXACTLY three verdicts and nothing else:
- `invalid_effort`
- `target_unverified_opt_in_required`
- `target_unavailable` **only when `details.get("reason") == "not_observed"`**

Traced against unmutated `resolver.py`. `target_unavailable` is a shared code carrying SIX distinct reasons:
- `not_observed` (`_select_edge`, explicit off-catalog model) → passes through ✓ (the intended surface case)
- `no_agent_target`, `no_default_target`, `retired` (`_validate_explicit_edge`), `target_probe_failed` (`_validate_explicit_edge`), `compatibility_catalog_unavailable` → all STAY HARD ✓

Critical disambiguation confirmed: the compatibility hard-block path (`_compatibility_disposition` when `compatibility_enforcing()`) CAN emit `code="target_unavailable"` (it is a member of `CompatibilityOutcome`), but its details are built by `_match_details`, which only ever produces `minimum_version`/`recommended_pin_version`/`block_reason_code` and NEVER a `reason` key. So `.get("reason")` is `None` and the enforcing compatibility block stays a hard failure. The reason-level cut is exact, not a code-level over-catch.

`harness_not_installed`, `harness_disabled`, `connection_unavailable`, `connection_ambiguous`, `target_ambiguous` all fall through to `raise LaunchTargetRejected`. No too-broad catch. Advisories for the resolved path (`warnings` → `deprecated_target`, `compatibility_advisories`) are forwarded correctly.

## 2. DRY extraction (`resolver_snapshots.py` + `inventory.py`): CORRECT, no fork

`inventory._harness_item` now CALLS `resolver_snapshots_for_harness` and derives `observation`/`connections`/`target_rows`/`channel_state`/`release` from the returned snapshot; the old inline `ResolverSnapshots(...)` block and its now-dead imports (`merge_executor_blocks`, `embedded_channel_state`, `embedded_release_entry`) are deleted. Behavior-equivalent: helper sets `channel_state=merge_executor_blocks(state, blocks)` and `release=embedded_release_entry(...)` exactly as the old inline code did; `user_enabled` computed identically. `test_inventory` (6) still green.
- The other `ResolverSnapshots(...)` site (`certification_evidence.py::_check_launch_profile`) is intentionally NOT folded in: it assembles from in-hand `StoredExecutorSnapshots` (no async store reads, no block merge), a genuinely different provenance. Correct to leave.

## 3. argv threading (`cli/launch_profile.py`): CORRECT + regression-guarded

- Claude: `_model_argv(model)` → `["--model", model]` when set, no effort flag (`effort` explicitly consumed as `_ = effort`, reserved). ✓
- Codex: `_model_argv(model)` + `_codex_effort_argv(effort)` → `-c model_reasoning_effort=<effort>`, reusing the established `-c` config-arg shape. ✓
- `model=None` ⇒ both helpers return `[]`; no flag leaks. Pinned by `test_client_argv_omitted_model_unchanged` asserting exact claude argv equality and codex `--model`/`model_reasoning_effort=` absence.

Threading is complete across every hop: `PrepareCaptureRequest.to_domain` → `CapturedRunRequest` → `_build_provider_invocation` → `build_claude/codex_captured_invocation` → `client_argv`.

## 4. `cli/codex_cmd.py` (+4): JUSTIFIED, not scope creep

`build_codex_invocation` is the codex-side indirection that `captured_codex.build_codex_captured_invocation` forwards into before reaching `client_argv` (claude calls `client_argv` directly; codex routes through this extra hop). Omitting it would drop model/effort on the codex path. Belongs to the Slice A argv seam.

## 5. `resolver.py` NOT mutated: CONFIRMED (empty diff)

## 6. Tests are real (assert new observable end-state, would fail pre-change): CONFIRMED

- `test_launch_target.py` (new): off-catalog-not-rejected (asserts returned `("claude-future","ultra")` + advisory `target_unavailable`/`not_observed`); invalid-effort-surfaces (`(MODEL,"max")` + `invalid_effort`); omitted-resolves-default (`(MODEL, None, ())`); **hard-unavailability-still-fails** (`harness_not_installed` raises). Builder ADDED a 5th beyond the plan: `test_non_observation_target_failures_stay_hard` (probe_failed `target_unavailable` raises) — directly guards the reason-discrimination subtlety.
- `test_launch_profile.py`: claude/codex argv-threads + omitted-unchanged regression. Adjacency-asserted, not tautological.
- `test_capture_rpc_routes.py`: `test_prepare_request_model_effort_reach_domain` (ingress→domain).
- `test_captured_run.py` + `test_main.py`: end-to-end — `--model` present in `spawn_spec.client.argv`; `test_main` drives the full `/v1/capture/prepare` DB path with `model` set (the ONLY guard the plan flagged as load-bearing). All would error/fail before (new symbols + `--model` not previously emitted).

## 7. GATE

- `api just check` (ruff format, ruff check, mypy — 653 files): **PASS** — "All checks passed!" / "Success: no issues found".
- Affected Python tests: **PASS** — `harnesses/` 616 passed; `test_main` integration + `test_capture_rpc_routes` 19 passed (with test Postgres); launch_profile/launch_target/captured_run 60 passed. (Earlier 2 errors were env-only: no `TRANSPORT_MATTERS_TEST_DATABASE_URL` in the review shell; resolved by exporting the configured `test_url`, then green.)
- JS half of `just check`/`just test-affected` not run — Slice A touches zero TS; unaffected.

## Minor observations (non-blocking, no action required)

- **M1 (design, per-spec):** With a session pool present, `_resolve_launch_target` fills an OMITTED model with the resolver's enumerated default, so the child now launches with an explicit `--model <default>` instead of booting on the harness home default. This is exactly plan decision (a). Note it is DB-conditional: when `optional_session_pool` is `None` the ingress returns the domain unchanged (raw pass-through, no `--model`). Inherent to "Python is the one validator." No end-to-end test pins "omitted + pool → enumerated default reaches argv" (covered transitively by the wrapper test + captured_run argv test); a nice-to-have, not a gap that lets a bug through.
- **M2 (subjective):** `_launch_target_rejection_status` maps `harness_not_installed`/`harness_disabled` to 409 (only connection/compat codes → 503). Defensible either way; not worth a cycle.

## Builder trust verdict

High. The load-bearing correctness point — discriminating the six `target_unavailable` reasons and the compatibility-outcome code collision — is handled exactly right, and the builder demonstrated they understood the subtlety by adding an unprompted `probe_failed` hard-fail test. DRY extraction is clean with no fork and dead imports removed; argv threading is complete across all hops with a real regression guard; no scope creep (codex_cmd.py justified). Tests assert observable end-state and fail pre-change. `resolver.py` left untouched per the "don't corrupt the picker" constraint. mypy + lint clean on 653 files. This is delegatable-grade work; Stuart can hand the codex builder comparably-scoped, boundary-aware slices with orchestrator verification rather than line-by-line babysitting.
