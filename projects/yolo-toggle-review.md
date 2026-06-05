# PR #155 review — launcher "Bypass all permission checks" toggle

- **Target:** commit `0a28ba0` vs `main` (`git diff main...HEAD`), branch `feat/launcher-bypass-permissions`, 25 files, +453/-74.
- **Reviewer:** engineering-code-reviewer, disciplines `/code-review` (xhigh recall) + `/code-hygiene` (inspection only).
- **Tree state:** verified pristine before and after review — HEAD `0a28ba0`, `git status` clean, diff sha `070581…` unchanged across the whole pass. No writes by reviewer or any subagent.
- **Gate (reported by orchestrator, not re-run):** desktop 29 · www check+test · api 1589 — green.

## Verdict

**Correctness and security: CLEAN.** No Blocker, no Major.
Counts: **0 Blocker · 0 Major · 7 Minor** (4 test/hygiene, 1 cleanup, 2 design).

The boolean threads correctly through all nine layers and defaults OFF everywhere (Pydantic `Field(default=False)`, the two frozen-slotted dataclasses, all five Python builder/argv signatures, the zustand initial state, the persist `migrate`, `createCapturedRun`'s param, and `resetCapturedRunStoreForTests`). The wire field is a strict boolean — no path lets it inject arbitrary argv or passthrough. The bypass arg is a fixed module constant (`--dangerously-skip-permissions` / `--yolo`), inserted exactly once per harness, only when truthy, at the specified argv position (Claude `[path,*passthrough,*bypass,*session]`; Codex `[path,*envpolicy,*bypass,*resume,*passthrough]`). DRY holds: it mirrors the `oscColorReplies` / `runtime_template` / `defer_session_ownership` carriers with no parallel launch path, and the flag→argv mapping lives only in the two `LaunchProfile` concrete classes.

## Minor findings

| # | Severity | Location | Fact | Suggested fix |
|---|----------|----------|------|---------------|
| M1 | Minor (hygiene) | `api/src/transport_matters/test_run_manager.py:431` | File is 735 LOC (was 717); PR adds +14. Already over the 700-LOC hard limit before the commit. | CLAUDE.md (user global) "Refactoring threshold: absolutely no exceptions": *"Files already over 700 lines must be refactored before new code is added to them … These thresholds are hard limits, not aspirations."* Split the test module before adding. Test file; no exemption exists in any governing CLAUDE.md. |
| M2 | Minor (hygiene) | `api/src/transport_matters/api/v1/test_run_routes.py:436` | File is 729 LOC (was 705); PR adds +20. Already over 700 before the commit. | Same rule as M1. |
| M3 | Minor (test) | `api/src/transport_matters/test_captured_run_web_separation.py:90` | Claude integration test leases real resources (`WorkspaceLock` flock fd + an `ExitStack` rmtree callback) in two `_prepare_bypass_permissions_run` calls placed *before* the `try`. If the second `prepare_captured_run` raises, `enabled_lease` is never closed (teardown asymmetry). Latent — the error path does not trigger today. | Acquire both leases inside the `try`, or use a single `contextlib.ExitStack`. |
| M4 | Minor (coverage) | `api/src/transport_matters/test_captured_run_web_separation.py:119` | Codex captured-path test sets `defer_session_ownership=True` ⇒ `managed_session=None` ⇒ no `resume` token, so it only asserts `count('--yolo')==1` and never proves `--yolo` precedes a real `codex resume <id>` in the captured path. Only the `launch_profile` unit test proves that ordering, and it bypasses `prepare_captured_run`. Same lease-leak pattern as M3 also applies here. | Add a captured-path case with an owned codex session asserting `--yolo` index < `resume` index. |
| M5 | Minor (cleanup) | `api/src/transport_matters/cli/test_launch_profile.py:287` | `del bypass_permissions` is a no-op: `ARG` (flake8-unused-arguments) is not in the repo's ruff `select`, and the sibling `prepare` method in the same `_FakeMintProfile` leaves six unused kwargs without `del`. Inconsistent and unnecessary. | Drop the `del`; leave the param unreferenced like the neighbor. |
| M6 | Minor (design) | `www/src/session-canvas/model/capturedRunStore.ts` (`partialize`/`migrate`) | Bypass is a **persisted, sticky, global** flag: `partialize` writes it, `migrate` re-arms a stored `true` on reload, and it then applies to every future Claude/Codex pane until toggled off. This is by-design (mirrors `oscColorReplies`), but for a "skip ALL permission prompts" control it means one forgotten toggle silently arms unprompted tool execution across all future runs. | Confirm the persistence trade-off is intended for a security control; consider a per-run/per-spawn opt-in or a persistent visible banner. Non-blocking. |
| M7 | Minor (design) | `api/src/transport_matters/api/v1/run_routes.py` (`RunViewModel`) / `CapturedRunPane` | No per-run surfacing: argv is fixed at spawn, so a pane launched in bypass mode keeps running in bypass after the user toggles the flag off, and nothing on the pane indicates it. The only indicator is Settings → trailing `On`, decoupled from the live terminals it governs. | Carry a bypass marker on the run view / pane and show a badge. Non-blocking. |

## Code-hygiene inspection

- **Measurements:** 25 files, +453/-74. Implementation surface is tiny (`launch_profile.py` +10, `api.ts` +5, `commandModel.ts` +21, `capturedRunStore.ts` +31, plus ~1-2 line threading in 9 other source files); the rest is tests.
- **Duplication:** none. Constants defined once (`launch_profile.py:52-53`); the `[ARG] if flag else []` splat appears exactly twice and intentionally mirrors the adjacent `session`/`resume` idiom in the same functions. No parallel launch path.
- **Dead code:** only the M5 `del` no-op.
- **Placement / boundaries:** cohesive — the new field sits beside its sibling carriers in every model; the flag→argv mapping is correctly isolated to the two profiles; frontend threading mirrors `oscColorReplies`.
- **Only hygiene flag:** the two over-700 test files (M1/M2). Natural seam: split each by behavior cluster (e.g. spawn/threading vs lifecycle/rollback for `test_run_manager.py`; per-endpoint groups for `test_run_routes.py`) into sibling modules before further growth. Verify with the existing repo gate (`just`-style api test recipe), not bare pytest.
