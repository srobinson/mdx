# Brief: wire startup provider verification into the desktop backend

Issue #399 phase 2. Worktree `.claude/worktrees/startup-verify`, branch
`feat/startup-access-wiring`, based on `main` at b648598c.

`harnesses/access_verification:verify_provider_access` shipped in PR #400 with zero
production callers. This slice gives it one. Nothing about the pass itself changes.

Reuse map (read it first): `~/.mdx/projects/tm-startup-verify-reuse-map.md`.
Roadmap: `docs/plans/AUTOPILOT-WIRE-PLAN.md`.

## The constraint that shapes everything

Verification launches N real harness processes through the proxy. Three backends run
this lifespan: the CLI desktop backend, every captured run's embedded web runtime, and
the test suite. Only the first may verify. An embedded runtime that verifies spawns
harnesses recursively; a test suite that verifies leaves detached processes behind,
because `asyncio.to_thread` cannot be cancelled.

So verification is opt-in, exactly like the gateway supervisor. Copy that precedent
verbatim in shape:

- `config.py:Settings.gateway_supervise` is `bool = False`, commented "Default False so
  tests and bare create_app() never spawn a child process".
- `env_keys.py:GATEWAY_SUPERVISE` carries the matching comment.
- `cli/desktop_cmd.py` (in the `backend_env` builder, near the `GATEWAY_SUPERVISE` line)
  sets it to "1".
- `launch/environment.py:build_launch_env` sets `GATEWAY_SUPERVISE` for the embedded web
  runtime and pops it otherwise. **Do not** set the verification flag there, and do not
  stop at not setting it. See the inheritance correction below; omission alone leaves the
  guard open.

Name it `startup_access_verification`, env key `STARTUP_ACCESS_VERIFICATION`. Do not
name the setting `verify_provider_access`; that collides with the function.

### Inheritance correction (supersedes any earlier reading of the guard)

Setting the flag only in `cli/desktop_cmd.py` is necessary and NOT sufficient. Verified
first-hand on this tree:

- `cli/desktop_cmd.py:_apply_desktop_backend_env` does `os.environ.update(env)`, so the
  flag lands in the desktop backend's own process environment.
- `launch/environment.py:build_launch_env` starts from `os.environ.copy()` (line 189) and
  is the single chokepoint for captured-run env: `captured/claude.py:164` and
  `cli/explicit_proxy.py:80` are its only production callers.
- So every captured run inherits `STARTUP_ACCESS_VERIFICATION=1` from the desktop backend
  unless `build_launch_env` removes it. `GATEWAY_SUPERVISE` is set and popped there for
  exactly this reason.

The failure this opens is bounded at one extra level, not unbounded recursion. Verification's
own children cannot re-verify: `_verification_request` sets `web_runtime=WEB_RUNTIME_EXTERNAL`,
and `addon_runtime.py:598` starts a web runtime (and therefore a lifespan) only when
`settings.web_runtime == "embedded"`. What the inherited flag does cause is that every
user-launched canvas run, which IS embedded, hosts a backend that inherits the flag and runs
its own verification pass, N harnesses wide, every time the user opens a pane.

Do not describe this as recursion in the code comment. State the actual reason: an embedded
captured-run backend must never verify, because verification is the desktop backend's startup
job and a pane launch would repeat it N harnesses wide.

Required: an **unconditional** `env.pop(env_keys.STARTUP_ACCESS_VERIFICATION, None)` in
`build_launch_env`. Unconditional, not the conditional set/pop `GATEWAY_SUPERVISE` uses:
the embedded runtime wants a gateway supervisor and must never want verification. Comment
the pop with the recursion reason, not with what the line does.

Add a test that a captured run's launch env never carries the flag when the parent
process has it set. Credit: the reviewer found this before any code was written.

## Work

### 1. `capture_rpc.py`: expose the registry's dependencies

`CaptureLeaseRegistry.__init__` assigns `self._dependencies` and nothing reads it
publicly. Add a read-only `dependencies` property. The lifespan must use the instance
`create_capture_registry` built, not a second `default_claude_run_dependencies()` call,
whose `control_plane_grants` would drift from the live one.

### 2. `harnesses/resolver_snapshots.py`: one shared per-harness reader

`resolver_snapshots_for_harness` takes eight arguments. `api/v1/capture_rpc_routes.py:_resolve_launch_target`
assembles them inline; this slice needs the identical assembly. Do not write a second copy.

Add a factory that binds the assembly once and returns
`Callable[[HarnessId], Awaitable[ResolverSnapshots]]`. It owns `local_executor_id()`,
`resolve_channel_id(None, os.environ)`, a fresh `datetime.now(UTC).isoformat()` per call,
`ExecutorEvidenceStore`, `ExecutorBlockStore`, and the `HarnessEnablementStore` intent
lookup filtered to the harness.

Move the `SnapshotReader` type alias out of `access_verification.py` into this module,
next to its producer, and have `access_verification` import it.

Then migrate `_resolve_launch_target` onto the factory and delete its inline assembly.
Verify first that `executor_id` and `intent` have no other use in that function; the
survey says they do not, confirm it.

`instant` must be computed per call, not bound once. `verify_provider_access` calls its
reader twice per harness and the second call reads back what the proxy just wrote.

`ExecutorBlockStore("", pool)` at the launch site passes an empty `database_url` while
`harnesses/inventory` passes the real one. `database_url` feeds only the sync-write
seam; these paths read. Pass the real URL from the factory and say why in one line.

Leave `harnesses/inventory:_harness_item` alone. Its caller binds the context once for
all harnesses and fetches intents in a single query; routing it through a per-harness
factory would turn one query into N.

### 3. `harnesses/access_verification.py`: the guarded task body

Add `run_startup_verification`, the analogue of `state_refresh:run_startup_refresh`
(which is a four-line try/except around one call, read it).

It must await the refresh task before verifying. `access_policy:_access_context` needs
`snapshots.observation`, which only `refresh_harness_state` writes, so a pass that races
the refresh reports `not_launchable` for every harness. `run_startup_refresh` swallows
its own exceptions, so awaiting it cannot raise; `CancelledError` must still propagate.

### 4. `main.py`: create the task

Currently 601 lines. Keep the lifespan body lean: put the wiring in a module-level
helper next to `_start_session_backed_services`, do not inline 25 lines into `lifespan`.

- The capture registry is built inside `lifespan`, after `_start_session_backed_services`
  returns, so the verification callable cannot be a `partial` in
  `_start_session_backed_services` the way `harness_refresh` is. Build it in the lifespan
  after the registry exists.
- Guard on the settings flag AND a live session pool, mirroring the refresh guard.
- Test seam: a pre-set `app.state.harness_access_verification` wins over the default,
  exactly as `app.state.harness_state_refresh` does.
- Store the task at `app.state.harness_access_verification_task`, initialised to None
  beside `app.state.harness_refresh_task`.
- Cancel it in the `finally` before the session pool closes, via
  `_close_lifespan_resource` + `_cancel_quietly`, same as the refresh task.

**Workspace.** `verify_provider_access(workspace=...)` fills both the harness cwd and
`workspace_root`, and at startup no user workdir is selected. Use a TM-owned neutral
directory, `settings.storage_dir / "runtime" / "access-verification"`, created with
`mkdir(parents=True, exist_ok=True)`. This mirrors the `runtime / "shared-proxy"`
precedent in `lifespan`. It is not cosmetic: for Claude the cwd drives `CLAUDE.md`
discovery, so a project directory would change what the harness sends. Neutral is the
decision; do not substitute `Path.cwd()`.

### 5. Shutdown

`asyncio.to_thread` cannot be interrupted, so cancelling the task leaves the worker
thread waiting on a harness turn for up to `DEFAULT_VERIFICATION_TIMEOUT_S` (120s).
Establish by test or direct observation whether that blocks interpreter shutdown or
`lifespan` teardown. Report the finding. If it does block, fix it; if it does not,
document why in one line where the task is cancelled.

## Gates

`cd api && just check` and `cd api && just test`, both verbatim. Never bare `pytest`;
without `TRANSPORT_MATTERS_TEST_DATABASE_URL` it errors ~298 times. No frontend change
in this slice, so no `www` suite.

## Tests to add

- No task when `startup_access_verification` is False. This is the guard that keeps the
  test suite and embedded runtimes from spawning harnesses; it is the most important
  test in the slice.
- No task when there is no session pool.
- A pre-set `app.state.harness_access_verification` wins over the default.
- Ordering: verification does not begin until the refresh task has completed. Use the
  barrier style already in `test_main.py` (see the `barrier_refresh` test around line
  319), not a sleep.
- The registry `dependencies` property returns the instance `create_capture_registry`
  built.
- The extracted reader produces the snapshots the inline assembly produced. The existing
  `capture_rpc_routes` tests must stay green unchanged; if any needs editing, say so and
  why rather than editing quietly.

## Repo rules

No file over 700 lines, no function over ~150. Zero duplication. No narrating comments;
a comment earns its place only by explaining a non-obvious why. Conventional commit
subjects, imperative mood. Match surrounding style: this codebase writes short
declarative comments that explain intent, and never uses em dashes.

## Out of scope, do not touch

- The startup screen. `FirstRunScreen` already ships harness cards, a `pending` tone,
  accelerated polling and a per-harness "Test access" button. Phase 3.
- The manual "Test access" button's duplicate evidence path. Known, deliberate, phase 3.
- Workflow step 5's comparator seam. Phase 4.
- `harnesses/inventory`.
