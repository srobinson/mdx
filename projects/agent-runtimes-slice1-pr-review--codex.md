# PR #118 slice 1 review, Codex pass

Head: `9fdd7c94a2c1a5b026a81e0d1fc4117e7ddf6bb5`
Base: `origin/main`
Worktree: read only review, no code edits.

## Additional findings

1. Major, stale launch fields can leak into unrelated runs.

   `api/src/transport_matters/launch_environment.py:129-155` starts from `os.environ.copy()` and only writes `TRANSPORT_MATTERS_LAUNCH_FIELDS` when `launch_fields` is truthy. A parent run with this env var set leaves stale template metadata in a native or manual child run. `api/src/transport_matters/config.py:98` then parses it into `Settings.launch_fields`, and `api/src/transport_matters/addon_runtime.py:96-103` applies it to the owned cursor binding.

2. Major, proxy only explicit homes are dropped.

   `api/src/transport_matters/cli/runtime_home.py:87-96` returns a proxy only plan with `descriptor_home=None` whenever `client_path is None`, even if the caller supplied `home_dir`. The changed launch paths then pass `descriptor_home` into the env and manifest at `api/src/transport_matters/cli/codex_cmd.py:420,432,489` and `api/src/transport_matters/captured_run_context.py:119,136,164,205,225`, so `--no-codex` or `--no-claude` plus `--agent-home-dir` no longer carries the manual home that previous code passed through.

3. Major, new production `Any` types lack the required explanation.

   `api/CLAUDE.md:10-12` says `Any` requires a comment explaining why. This PR adds `dict[str, Any]` at `api/src/transport_matters/config.py:98` and `api/src/transport_matters/cli/runtime_home.py:70` without explaining why the launch field value cannot use a narrower JSON value type.
