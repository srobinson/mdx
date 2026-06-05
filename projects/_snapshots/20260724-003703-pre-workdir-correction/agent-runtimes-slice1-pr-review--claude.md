---
title: Slice 1 PR#118 adversarial review (runtime-home unification)
type: review
tags: [transport-matters, agent-runtimes, runtime-home, slice1, pr-118, moe]
summary: PR#118 delivers Slice 1 correct and in-scope; 0 Blocker, 0 Major, 1 latent non-Slice-1 note.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Slice 1 PR#118 review — `feat: unify runtime home planning` @ 9fdd7c9

Reviewed `git diff main...HEAD` (== `gh pr diff 118`, cross-checked: 13 files, 691+/45-).
Tree pristine before verdict. READ-ONLY; no worktree writes. Spec:
`~/.mdx/projects/agent-runtimes-ephemeral-home-spec.md` (§3, §4, §8, §10 Slice 1 + Auth-source note).

## Verdict: CLEAN — 0 Blocker, 0 Major. 1 latent note (not a Slice 1 defect).

## Load-bearing checks

**1. Durability invariant (§4) — PASS.** `runtime_home.py` `plan_runtime_home`:
`descriptor_home = child_home if mode==TEMPLATE else manual_home`. TEMPLATE → descriptor_home
== child_home (runtime overlay `<storage>/runtime-home/<client>`), so `prepare_managed_session`,
`ClaudeLaunchProfile.prepare`/`claude_projects_root`, `CodexLaunchProfile.prepare`/
`codex_sessions_root`/`seed_codex_session`, the owned `source_descriptor`, and
`tailer.register_session_cursor` (via `_binding_extra_fields`) all resolve under the runtime home —
the same root the child gets as `CLAUDE_CONFIG_DIR`/`CODEX_HOME` (`runtime_home_dir or home_dir`).
Tests `test_claude_template_descriptor_resolves_under_runtime_projects` /
`test_codex_template_descriptor_seeds_runtime_sessions_without_mutating_template` assert
`source.path` under `child_home/projects|sessions`, `source.home_dir == child_home`, template
`projects`/`sessions` absent. NATIVE → descriptor_home None; MANUAL → descriptor_home manual_home —
both == pre-diff `request.home_dir`/`home_dir`, unchanged.

**2. projects/sessions local in template mode (§4) — PASS.** `_template_local_names` adds
`projects` (claude) / `sessions` (codex) to `extra_local_names` → `prepare_runtime_home_overlay`
unions into `local_names` → `_symlink_source_home_entries` skips them → real local dirs, template
not written through. Non-template returns `frozenset()` so the symlink-to-source behavior (which
keeps manual/native descriptor and child resolving to the same physical file) is preserved.

**3. Native-auth fallback (§10) — PASS.** Codex: `prepare_runtime_home_overlay` runs
`_copy_overlay_local_files` (content `auth.json`, create-exclusive) THEN `_copy_overlay_auth_files`
(native `auth.json`, create-exclusive `_copy_secret_file_if_missing`/O_EXCL) → native wins only when
content is pristine. `auth_source = native_home if should_overlay or manual_home is not None else
content_source`. Claude metadata: `seed_env[CLAUDE_CONFIG_DIR] = auth_source` (when present) →
`ClaudeSeeder.seed` reads `_default_claude_config_path` → native userID/oauthAccount injected if
absent. Test `test_codex_template_overlay_copies_native_auth_fallback` asserts runtime auth.json ==
native bytes, template has none. Native/manual not regressed (CLI `run_codex` already sourced auth
from native via `_default_codex_home`; this unifies captured to match). Content-config pinning and
credential-token symlinks are correctly deferred to Slice 2.

**4. run_codex unification (§8) — PASS.** `run_codex` calls `plan_runtime_home` +
`prepare_runtime_home` after addon resolution, BEFORE `prepare_managed_session`
(home_dir=`descriptor_home`); passes `runtime_home_dir` to `build_codex_invocation`; old
`from .home_seed import seed_home_dir` import and the in-place `seed_home_dir(CODEX, home_dir=...)`
branch deleted, replaced by `seed_direct_home_if_needed` (MANUAL-only). `--force-http-fallback`
preserved — `run_codex` stays on `build_codex_invocation`; test
`test_run_codex_force_http_fallback_still_resolves_addons` asserts
`resolve_codex_addons_and_ca(force_http_fallback=True)`. (In Slice 1 `run_codex` never builds an
overlay — `use_runtime_overlay=False`, no template input — so CLI behavior is byte-identical.)

**5. Generic launch-field carrier (§10/§12) — PASS, field-agnostic.** `env_keys.LAUNCH_FIELDS`
(`TRANSPORT_MATTERS_LAUNCH_FIELDS`) ← `build_launch_env` json.dumps → `Settings.launch_fields:
dict[str,Any]` (pydantic-settings auto JSON-decode, round-trip verified empirically) →
`addon_runtime._register_owned_cursor` `**settings.launch_fields` spread BEFORE explicit
`minted`/`source_descriptor` (explicit wins, no clobber) → `tailer.register_session_cursor` carries
extras onto the re-bound transcript binding via `_binding_extra_fields` (`__dict__` minus
`model_fields`). `runtime_template` rides it; no B6 lineage fields added prematurely.

**6. RuntimeHomePlan defaults preserve native/manual — PASS.** `client_path=None` → PROXY_ONLY
(all None). NATIVE: content=native, descriptor_home=None. MANUAL: child_home==content_source →
`runtime_home_dir` property None → no overlay, `seed_direct_home_if_needed` seeds in place exactly
like pre-diff.

## Scope fences — no bleed

- CapturedRunRequest.runtime_template: field added (default None) is the §3 contract shape;
  NO producer (RunManager unchanged, `run_codex` passes None) → Slice 4 input plumbing absent. OK.
- Slice 2: native auth is COPIED (Slice 1) not symlinked; no Linux `.credentials.json`; content
  config still env-sourced (not pinned). All correctly deferred.
- B6: no api/v1 changes. Slice 3: no rmtree-teardown change (`run_codex` overlay never active, so its
  new `stack.callback(rmtree)` never registers; captured path's rmtree condition unchanged).

## Test reality — real, not vacuous

All 4 durability/carrier tests fail against pre-diff code: descriptor tests rely on the planner's
`descriptor_home==child_home` (pre-diff used `request.home_dir`, resolving off the runtime root);
`test_register_session_cursor_preserves_dynamic_launch_fields` and
`test_launch_fields_carrier_reaches_owned_cursor` assert propagation that the pre-diff
spread/extraction did not perform.

## Gate

- `just check`: ruff format clean, ruff check clean, mypy clean (357 files). GREEN.
- `pytest src/transport_matters/cli/ index/test_tailer.py`: 315 passed; 7/7 new `test_runtime_home.py`.
  The only 2 errors are `test_db_cmd.py` setup `MissingDatabaseConfigError` (no local Postgres test
  DB configured in the reviewer shell) — environment-only, unrelated to this diff (no DB code changed).

## Lone latent note (NOT a Slice 1 defect)

`index/adapters/base.py` `SessionBinding` has no `extra="allow"`. Carrier extras (`runtime_template`,
future B6 lineage) land in `__dict__` via `model_copy(update=...)` and are re-attached to the cursor
binding by `_binding_extra_fields` (in-memory ride works — verified), but `model_dump()` /
`model_dump_json()` DROP them (verified: `survives model_dump: False`). No Slice 1 consumer serializes
`runtime_template` (provenance recording is Slice 4 §10/§12), so zero live effect now. Flag for the
future serializing consumer: persisting carried fields will require a real model field or
`extra="allow"`, else the launch-facts read-back is empty. Recommend a tracking note on Slice 4/B6.
