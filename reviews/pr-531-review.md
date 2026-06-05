# PR #531 adversarial review: unify process lifecycle

Range `a973c530..d112b405`. Base PR #530. Scope: issue #529 item 2.

## Verdict: BLOCK

Two findings change user-visible behavior that the PR and issue #529 declare unchanged. Both are small to fix.

## Verification performed

- `cd api && just ci` at `d112b405` in a fresh worktree: Ruff, mypy, migrations, 4401 passed, 16 skipped.
- Retry port selection compared rule by rule against the deleted `bind_failure.handle_bind_failure` and `run._reallocate_proxy_timeout_ports`: equivalent for user-supplied ports.
- `run_client_with_retry`, `BIND_RETRY_ATTEMPTS`, `LaunchRetryExhaustedOutcome`, `format_retry_exhaustion`, `handle_bind_failure` deleted with no dangling references, including `cli/_helpers.py`.
- Supervisor terminate and restore per failed attempt, lease idempotence, combined cleanup errors: covered by `captured/test_shared_lifecycle.py` and `test_capture_rpc.py`.
- RPC contract (`CapturedRunSpawnSpec`, lease `alive`/`close`) unchanged. Launch kind assignment unchanged (local sets `DETACHED`, RPC leaves caller fields).

## Findings

### B1. Channel default ports are no longer pinned across retries

`api/src/transport_matters/cli/launch_runtime.py:138-140` and `:158-175`. `resolve_launch_ports` previously returned `proxy_pinned = proxy_user_supplied or channel_spec is not None`. It now returns bare `proxy_user_supplied`, so a `--channel` launch whose 8797 is stolen between preflight and bind silently reallocates to a random port.

Evidence this was a deliberate contract: introduced by #159 `feat(channels): run stable + preview side by side` under the commit `fix(api): tighten channel isolation`, with `test_codex_channel_default_bind_failure_fails_without_reallocation` asserting exit 2 and `pinned port in use: --proxy-port 8797`. PR #531 renames that test to `test_codex_channel_default_bind_race_reallocates_selected_ports` (`cli/test_codex_channel.py:67-118`) and asserts the opposite, while the PR description and issue #529 state all other observable behavior stays unchanged. `CLAUDE.md` binds each channel to fixed ports.

Fix: keep the pinned flags as they were (`proxy_user_supplied or channel_spec is not None`), or declare the change in the PR and obtain owner sign-off. Restoring the flags also restores the actionable "pinned port in use" message for channel ports through `run._raise_local_bind_conflict`.

### B2. Local proxy readiness exhaustion escapes as a raw exception

`api/src/transport_matters/captured/run.py:208` catches only `CapturedRunBindConflict`. `run.py:436` raises `CapturedRunProxyStartTimeout` (a `RuntimeError`) on timeout exhaustion; nothing between `run_captured_run_on_local_tty` and Typer handles it (`cli/managed_start.py` catches enablement and credential errors only). The user sees a Python traceback with exit code 1 instead of the previous `error: mitmdump did not come up within 5s.` plus `See <log> for details.` from the deleted `_raise_launch_outcome` path. The mitmdump log path is also dropped: the exception carries the message only, while `LaunchExitOutcome.log_path` was previously printed.

The test suite encodes the leak: `captured/test_shared_lifecycle.py:78-82` expects `CapturedRunProxyStartTimeout` from the `local` entry point, not `typer.Exit`.

Fix: map timeout exhaustion in the local entry point the same way bind exhaustion is mapped, via `raise_launch_outcome(last_proxy_timeout)` so the log path survives, and change the local parametrization to expect `typer.Exit`.

## Minor

### M1. `require_web_port` moved outside the resource guard

`run.py:154`. Previously inside the `try/finally` that closed `ctx.resource_stack` (old `run.py:130-131`). If it raises, the prepared runtime home and temporary addons leak. Move it inside the guarded region.

### M2. Proxy-only local launches now classify bind conflicts as timeouts

`cli/runner.py:126-140`. Foreground spawn passes no `mitmdump_log`, so `_proxy_not_ready_outcome` cannot read EADDRINUSE and returns the timeout outcome. A proxy-only launch on a stolen port therefore retries three times on fresh ports and then hits B2. Previously mitmdump's own exit code propagated at once with its stderr live on the terminal. Acceptable if intended, but it is undeclared. Fixing B2 makes the end state a clean error; note the change in the PR.

## Not findings

- Port selection for user-supplied ports matches the deleted policy exactly.
- Banner is now printed after `build_invocation` rather than before; no observable effect.
- `run.py` imports `cli.launch_outcomes` at module level; the seam import test passes.
- `CapturedRunLease` construction sites in production code do not touch `_supervisor`.

## Re-review at `d49ddf27` (delta `d112b405..d49ddf27`)

Verdict: BLESS. Full range `a973c530..d49ddf27` holds.

- B1 fixed: `cli/launch_runtime.py:138-168` returns `proxy_pinned`/`web_pinned` (user supplied or channel spec) again. `cli/test_codex_channel.py` restored to fail-fast exit 2 with `pinned port in use: --proxy-port 8797` and a single attempt.
- B2 fixed: `captured/run.py:437-438` returns the retained `LaunchExitOutcome` to the local entry point, which routes it through `raise_launch_outcome` (message plus log path, exit 1). `captured/test_shared_lifecycle.py` now expects `typer.Exit` locally and adds `test_local_timeout_exhaustion_keeps_the_cli_error_and_log`.
- M1 fixed: `captured/run.py:154-156` and `:194` place `require_web_port` inside the print guard and the acquired resource owner. New `test_local_web_port_validation_closes_prepared_runtime_resources`.
- M2 fixed: `cli/runner.py:101-114` probes attempted ports only after the child has exited and no signal arrived, so a foreground proxy losing a race is classified as a bind failure while a live child holding its ports stays a timeout. Two new `test_runner.py` cases cover both branches. `BindFailure.log_path` widened to `Path | None`.

No new retry path introduced. `cd api && just ci` at `d49ddf27` in a fresh worktree: 4404 passed, 16 skipped.
