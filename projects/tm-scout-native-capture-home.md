# Scout: native-home capture, per-launch config as process env

Read-only scout of `api/src/transport_matters/cli` and `launch` plus the
`captured/` seam, per orchestrator brief `tm-harvest-native-home-scout`.
Citations are path + symbol. Worktree untouched.

## Reuse Map

### 1. Current writers into a harness home for a captured run

Claude:

- `api/src/transport_matters/cli/home_overlay.py` `materialize_runtime_home_overlay` / `materialize_runtime_home_template_overlay`: constructs the overlay itself. Symlinks source entries; copies `settings.json`, `.claude.json`, credentials as overlay-local real files (`home_constants._CLAUDE_OVERLAY_LOCAL_NAMES`).
- `api/src/transport_matters/cli/claude_home.py` `ClaudeSeeder.seed`: writes `.claude.json` (copies `userID`/`oauthAccount`, sets `hasCompletedOnboarding`, cwd `hasTrustDialogAccepted`) and `settings.json` (`skipDangerousModePermissionPrompt` via `_ensure_claude_skip_dangerous_prompt`).
- `api/src/transport_matters/cli/claude_home.py` `apply_claude_proxy_env_settings`: writes `settings.json` `env` block: `ANTHROPIC_BASE_URL`, `TRANSPORT_MATTERS_RUN_ID`, `TRANSPORT_MATTERS_AGENT_HOME_DIR`, `NO_PROXY`. Sole caller: `api/src/transport_matters/captured/claude.py` `_build_claude_captured_invocation`, gated on `materialize_runtime_home`.
- `api/src/transport_matters/cli/claude_home.py` `apply_claude_control_plane_client`: writes `.mcp.json` `mcpServers` (authenticated HTTP server). Reached via `home_seeders.seed_control_plane_client` ← `controlplane/provisioning.py` `prepare_control_plane_grant`.

Codex:

- `api/src/transport_matters/cli/codex_home.py` `CodexSeeder.seed`: copies `auth.json` (`home_io._copy_secret_file_if_missing`), repoints hook trust keys (`_relocate_codex_hook_trust_state`) and merges cwd trust (`_merge_codex_project_trust`), both into `config.toml`.
- `api/src/transport_matters/cli/codex_home.py` `apply_codex_control_plane_client`: writes `config.toml` `[mcp_servers.<name>]`.
- `api/src/transport_matters/cli/run_context.py` `install_codex_run_context`: writes an identity block into `AGENTS.md` in the runtime home. Called from `cli/codex_cmd.py` `build_codex_invocation`, gated on `runtime_home_dir is not None`.
- `api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare` → `codex_session.seed_codex_session`: pre-seeds the owned rollout under `codex_home.codex_sessions_root(home_dir, env)` — a write under the home's `sessions/` tree.

Both, orchestration layer:

- `api/src/transport_matters/cli/home_seeders.py` `seed_home_dir` / `seed_control_plane_client`: dispatch to the `HarnessSeeder` protocol (`ClaudeSeeder`, `CodexSeeder`), one symmetric path per harness.
- `api/src/transport_matters/cli/runtime_home.py` `prepare_runtime_home` (overlay path) and `seed_direct_home_if_needed` (MANUAL non-overlay homes; sole caller `cli/codex_cmd.py`).

### 2. Existing mechanisms passing per-launch values as process env

- `api/src/transport_matters/env_keys.py`: the canonical `TRANSPORT_MATTERS_*` key registry; its module docstring names `launch/environment.py` as the single writer.
- `api/src/transport_matters/launch/environment.py` `build_launch_env`: the launch env (addon side): `RUN_ID`, `STORAGE_DIR`, `PROXY_PORT`, `CWD`, `HARNESS`, `AGENT_HOME_DIR`, `RUN_IDENTITY`, `RUNTIME_HOME`, `OWNED_NATIVE_SESSION_ID`, `OWNED_SOURCE_DESCRIPTOR`, `LAUNCH_FIELDS`, `RESUME_CONTEXT`.
- `api/src/transport_matters/launch/environment.py` `build_managed_child_env`: the child env owner. Strips proxy/trust/internal keys, sets `HTTP_PROXY`/`HTTPS_PROXY`/... (codex explicit proxy), `NO_PROXY`, `CODEX_CA_CERTIFICATE`, the home via `HOME_DIR_ENV_BY_HARNESS` (`CLAUDE_CONFIG_DIR` / `CODEX_HOME`), and arbitrary `extra_env`.
- Spawn spec `client.env`: `cli/runner.py` `ManagedClient.env`, populated exactly once from `build_managed_child_env` — by `captured/claude.py` `_build_claude_captured_invocation` and `cli/codex_cmd.py` `build_codex_invocation`. `baseline_harvest.py` states the ownership rule in a comment: "spec.client.env is owned by the launch seam ... never layer a second writer over it."
- Owner verdict: `build_managed_child_env` owns the child process env. A second writer of the same values DOES exist, on disk: `apply_claude_proxy_env_settings` duplicates `ANTHROPIC_BASE_URL`, `NO_PROXY`, `RUN_ID` into claude's `settings.json` `env`, and writes `AGENT_HOME_DIR` with a potentially different value (see Quality Map).

### 3. Does the harness honor the route as process env?

- Claude: yes, established by repo evidence. `captured/claude.py` `_build_claude_captured_invocation` already passes `extra_env={"ANTHROPIC_BASE_URL": proxy_url}` into the child env; `api/README.md` documents `ANTHROPIC_BASE_URL=http://localhost:8787 claude` as the manual flow; `cli/banner.py` `proxy_hint` prints the same for proxy-only mode; `captured/test_run_web_separation.py` and `cli/test_start_children.py` assert it on `spawn_spec.client.env`.
  - Caveat the fix must carry: `cli/home_constants.py` (`_CLAUDE_DAEMON_LOCAL_NAMES` comment) records the route-loss bug — claude's daemon rebuilds a background worker's env from dispatch state, so process env alone did not survive that path; the `settings.json` `env` write exists for that reason. Whether native-home capture re-exposes that bug is a product question the plan must answer, not silently drop.
- Codex: yes, and it is already env-only. The route is `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`/`WS_PROXY` set by `build_managed_child_env(proxy_url=...)` (explicit proxy, mitm `regular` mode); no on-disk route write exists for codex. Trust rides `CODEX_CA_CERTIFICATE`, also env.

### 4. Control-plane MCP client delivery paths other than home files

- Claude: `--mcp-config <path>` is already wired. `captured/claude.py` `ClaudeCapturedInvocation.mcp_config_path` → `--mcp-config` in passthrough; `captured/context.py` `_build_provider_invocation` derives the path as `home.directory / ".mcp.json"`; `cli/test_control_plane_grant_capture.py` asserts the flag. The flag mechanism is home-agnostic — only the current file location is home-coupled.
- Codex: no MCP flag or env path found, but the repo already passes per-launch root config overrides as CLI `-c key=value`: `cli/launch_profile.py` `_codex_shell_environment_policy_args` and `_codex_effort_argv`. No existing `-c mcp_servers...` usage; whether codex accepts nested table overrides via `-c` is unknown from repo.
- Env-based MCP delivery: none found. Searches: `rg "mcp-config|mcp_config|--mcp"`, `rg "MCP_" api/src`, `rg "mcp_servers"`, export scan of `claude_home.py`/`codex_home.py`.

### 5. Blast radius of `RuntimeHomePlan.runtime_home_dir` being None

Definition: `cli/runtime_home.py` `RuntimeHomePlan.runtime_home_dir` — None when `child_home` is None or equals `content_source` (i.e. native, no overlay).

Hard dependents on non-None (fail or degrade):

- `captured/context.py` `_prepare_home_and_grant`: cleanup callback (`shutil.rmtree` of `runtime-home`), and `directory` feeding everything below.
- `captured/context.py` `_build_provider_invocation`: raises `RuntimeError("captured Claude launch has no prepared runtime home")` when write-mode claude has `home.directory is None`; `mcp_config_path` derivation returns None without it.
- `captured/claude.py` `build_claude_captured_invocation` / `_build_claude_captured_invocation`: `materialize_runtime_home=True` asserts non-None and calls `apply_claude_proxy_env_settings`; `child_home_dir = runtime_home_dir or invocation.home_dir`.
- `controlplane/provisioning.py` `prepare_control_plane_grant`: raises `ControlPlaneGrantPreparationError("control plane grant requires a seeded per-run home")` when None — a granted native-home launch is currently impossible.
- `cli/codex_cmd.py` `build_codex_invocation`: gates `install_codex_run_context`; child home falls back to `home_dir`.
- `run/identity.py` `RunIdentitySeed.runtime_home` / `RunSelfIdentity.runtime_home`: flows into `RUN_IDENTITY` JSON, `TRANSPORT_MATTERS_RUNTIME_HOME` env (`build_launch_env` sets or pops), and the rendered identity markdown ("Runtime home" row).
- `cli/runtime_home.py` `prepare_runtime_home` (returns None when `runtime_home_dir` is None — the credential-error preflight branch for NATIVE mode already exists) and `seed_direct_home_if_needed`.

Descriptor/storage note: `launch/manifest.py` `write_workspace_manifest` and `persist_owned_session_facts` consume `descriptor_home` (`RuntimeHomePlan.descriptor_home`), not `runtime_home_dir`; native mode already yields `descriptor_home=None`, which those paths accept.

Tests pinning the current shape: `cli/test_captured_run.py` (`_runtime_home_is_required_by_type`, cleanup-on-failure), `captured/test_run_web_separation.py` (`CLAUDE_CONFIG_DIR == runtime home`, `RUNTIME_HOME` env on both spec envs, codex `CODEX_HOME` under `runtime-home/`), `cli/test_control_plane_grant_capture.py` (runtime-home lifecycle plus `--mcp-config` argv), `cli/test_runtime_home.py`, `cli/test_runtime_home_launch_fields.py`, `cli/test_home_seed.py`, `launch/test_identity_env.py`.

Also on the seam: `baseline_harvest.py` passes `home_dir=<workspace>/.baseline-homes/<harness>` (MANUAL mode, fresh dir) — the direct cause of the first-run gate hang the brief names.

### 6. Quality map

1. Second-writer hazard (the central one): the claude route is written twice — process env (`build_managed_child_env` `extra_env`) and `settings.json` `env` (`apply_claude_proxy_env_settings`) — with no precedence rule established in-repo for claude's `settings.json` `env` versus inherited process env. Worse, `TRANSPORT_MATTERS_AGENT_HOME_DIR` gets two writers with potentially DIFFERENT values: `build_launch_env(home_dir=invocation.home_dir)` uses the descriptor home while the settings write uses `runtime_home_dir`. Any fix should collapse to one writer per value.
2. `".mcp.json"` is an inline literal in two places (`claude_home.py` `apply_claude_control_plane_client`, `captured/context.py` `_build_provider_invocation`); every other home filename lives in `home_constants`.
3. No source file this change touches exceeds the 700-line limit (`home_overlay.py` 546, `cli/__init__.py` 549, `runner.py` 519, `codex_cmd.py` 500, `context.py` 548). Two test files are over: `cli/test_runtime_home.py` 731 and `cli/test_desktop.py` 704 — `test_runtime_home.py` is in scope for this change and must be split before meaningful additions.
4. No dead code found on this seam; control-plane seeding is symmetric through the `HarnessSeeder` protocol and `seed_direct_home_if_needed` has one live caller.

## Plan

Ordered steps bound to owners named above. No code written; this is sequencing for the builder.

1. Route by env only. In `captured/claude.py` `_build_claude_captured_invocation`, the child env already carries `ANTHROPIC_BASE_URL`, and `build_launch_env` already carries `RUN_ID`/`AGENT_HOME_DIR`; retire the `apply_claude_proxy_env_settings` call for the native-home path rather than inventing a new carrier. Resolve the daemon route-loss caveat (Reuse Map §3) explicitly with Stuart before deleting the settings write outright.
2. Native-home plan. `plan_runtime_home` already models `RuntimeHomeMode.NATIVE` with `runtime_home_dir=None` and `prepare_runtime_home` already runs the credential preflight for that shape; captured launches switch by passing `use_runtime_overlay=False` at the `captured/context.py` `_prepare_home_and_grant` call site. Do not add a new mode.
3. Relax the claude invocation contract. `build_claude_captured_invocation`'s hard requirement on a runtime home (and the matching `RuntimeError` in `_build_provider_invocation`) is the type-level gate `test_captured_run.py` pins; it must learn the native shape instead of being bypassed.
4. Control-plane grant off the home. `prepare_control_plane_grant` currently requires the per-run home only as a place to write `.mcp.json`; the `--mcp-config` flag (`ClaudeCapturedInvocation.mcp_config_path`) already decouples file location from home — point it at run storage. Codex has no equivalent yet; scope that separately, evidence is missing in-repo.
5. Gates and identity. `RUNTIME_HOME` env and `RunSelfIdentity.runtime_home` go None-shaped for native runs (both already model None); update `test_run_web_separation.py` expectations that pin `CLAUDE_CONFIG_DIR` to the overlay.
6. Baseline harvest. `baseline_harvest.py` drops its `.baseline-homes` `home_dir` so runs hit the native home, which is the brief's stated outcome for the theme/trust hang.

Gate commands, verbatim: `just test-affected` as the inner loop, `just check` and `just test` as the merge authority, CI as the verdict.
