# CLI PR-2 adversarial review

Reviewer: backend-engineer/claude (CLI reviewer)
PR: #40 `feat/cli-desktop-cmd` @ `3090732`
Scope: `transport-matters desktop` command + detached Electron canvas viewer
Spec: `cli-spec.md` (Desktop parser composition + Desktop launch design) + CHARTER ratified topology
Base: `8b236be` (FE F1 canvas #39, merged)
Date: 2026-06-06

## Verdict

**0 blockers, 1 major, 3 minors.**

The launch topology, DRY reuse, cross-agent rejection, port-retry preservation, and
startup ordering are all correct and well engineered; the full two-sided gate is green
(api 1153 + desktop typecheck/25 tests). The one major is a cross-system contract gap:
the `routeUrl` matches the letter of hard-check 4 but does not carry the launch context
that the already-merged FE F1 parses from query params, so a desktop-launched canvas
cannot scope to the run it just started. I treat that as merge-gating; the orchestrator
owns the blocker-vs-major call given HC4 specified bare `/canvas`.

## Hard-check results

### 1. Terminal interactive / Python-primary, Electron detached — PASS

- The agent is spawned on a real PTY by `run_client_children_until_outcome`
  (`runner.py`), reusing the unchanged `run_start`/`run_codex` foreground path. The
  desktop command only swaps in a wrapped `run_client_with_retry`; it does not change
  who owns the terminal.
- Electron is started by `spawn_detached_electron`
  (`desktop_cmd.py:151-181`) with `stdin/stdout/stderr=DEVNULL`, `close_fds=True`,
  `start_new_session=True`. It cannot read the TTY and runs in its own session, so the
  agent keeps stdin/TTY and Electron does not own or supervise the agent child.
- Ordering inside `run_client_children_until_outcome`: mitmdump up ->
  `_wait_web_ui_ready_for_hook` -> `_notify_backend_ready` (emit + spawn Electron) ->
  THEN spawn the agent on the PTY. Electron is launched before the agent grabs the
  terminal, exactly as the charter requires.

### 2. DRY reuse — PASS (one wiring-duplication minor, see Minor 3)

- `desktop` reuses the `launch_options.py` aliases (the same `Annotated` options as
  `claude`/`codex`), `prepare_managed_session` (via the unchanged `run_start`/`run_codex`
  paths), and `LaunchProfile` resolution. `--agent claude|codex` selects the branch.
- No launch/proxy/argv logic is duplicated in `desktop_cmd.py`, `runner.py`, or
  `desktop/src`. `runner.py`'s +136 lines are a new opt-in `on_backend_ready` hook plus a
  de-duplicating refactor (`_proxy_not_ready_outcome` collapses a previously inlined
  bind-failure block). The hook is gated on `on_backend_ready is not None`, so
  `claude`/`codex` behavior is unchanged.

### 3. `--work-dir` maps to canvas + agent dir — PASS

- `desktop` passes `directory=work_dir` to `run_start`/`run_codex`
  (`__init__.py`), so the agent launches in `--work-dir`.
- The canvas receives the same dir through the startup event: `build_backend_started_event`
  reads `launch_env[CWD]` (derived from `work_dir`) and computes `workspace.slug/hash`
  from it (`desktop_cmd.py:130-148`). One flag, both surfaces.

### 4. startup-JSON timing + routeUrl — PARTIAL (see Major 1)

- Timing is correct: the event is emitted in `on_backend_ready`, which fires after
  mitmdump and the web UI are ready and before the agent takes the PTY.
- `routeUrl` equals `http://127.0.0.1:{webPort}/canvas` (`LOOPBACK_HOST = "127.0.0.1"`,
  `loopback_http_url`), matching HC4 literally. But bare `/canvas` does not deliver the
  launch context the merged FE parses. See Major 1.

### 5. Detached Electron, no double-spawn / double-load — PASS

- `registerDesktopLifecycleFromEnv` (`desktop/src/main.ts:254+`) dispatches to
  `registerHostedDesktopLifecycle` when `DESKTOP_ROUTE_URL` is set and returns; it does
  NOT call `registerAppLifecycle` (the backend-spawning + window path). So a viewer
  launched by the Python desktop command never spawns its own backend and creates exactly
  one window at `routeUrl`. The only new process spawn is the Python-side `Popen`.
- `backendProcess.ts` adds `--work-dir` to the standalone self-spawn argv, keeping the
  non-hosted Electron-spawns-backend path compatible with PR-1's positional removal.

### 6. Child owns dynamic port allocation — PASS

- `desktop` forwards `proxy_port`/`web_port` straight through (None when unset); it never
  pre-allocates. `test_desktop_command_forwards_to_codex_without_preallocating_ports`
  (`test_desktop.py:65-93`) monkeypatches `allocate_port_pair` to raise if called and
  asserts both ports arrive as `None`. The child's `resolve_launch_ports` keeps deriving
  `*_user_supplied` from `is not None`, so the bind-race retry is preserved. The web-UI
  readiness wait returns a `BindFailureOutcome` into the same retry loop.

### 7. desktop/src minimal, LOC/fn, Pydantic, imports — PASS

- `desktop_cmd.py` is 325 LOC (<700); longest fn `prepare_desktop_launch` ~46 lines
  (<150). `desktop()` in `__init__.py` is ~100 lines (<150). All other touched files are
  well under limits.
- No Pydantic models are introduced; the new value objects are frozen dataclasses
  (`ElectronLaunch`, `DesktopLaunchPlan`), consistent with the rest of `cli/`
  (`LaunchPreparation`, `ManagedSession`). Pydantic v2 is not required here.
- Imports are all public; no cross-module private import; no cycle
  (`__init__` -> `desktop_cmd` -> {`net`, `runner` type-only, `workspace`, `env_keys`};
  `runner` does not import `desktop_cmd`). `test_private_import_boundary` passes in the
  green suite.

## Findings

### Major 1 — `routeUrl` does not deliver the launch context the merged FE F1 parses

`api/src/transport_matters/cli/desktop_cmd.py:145` (`"routeUrl": f"{base_url}/canvas"`)

The implementation matches HC4's literal `http://127.0.0.1:{webPort}/canvas`, but the
already-merged FE F1 (#39) reads `CanvasLaunchContext` from the URL query string:

- `www/src/session-canvas/SessionCanvasRoute.tsx:9-17`: `const search = window.location.search`
  -> `parseCanvasLaunchContext(search)`; `hasLaunchLookup = workspaceHash !== null && cli !== null`.
- `www/src/session-canvas/route.ts:14-20`: `parseCanvasLaunchContext` reads `owner`,
  `workspace_hash`, `cli`, `run_id` from the query params.
- `www/src/session-canvas/route.test.ts:13`: the expected shape is
  `?owner=local&workspace_hash=hash-1&cli=codex&run_id=run-1`.

Because the desktop viewer loads bare `/canvas` (no query string), `window.location.search`
is empty, `parseCanvasLaunchContext` returns all-nulls, and `hasLaunchLookup` is false. The
canvas cannot run the cli-spec "Canvas lookup rule" (prefer sessions whose `run_id` equals
the launched run); it degrades to an unscoped picker. The headline behavior the
startup-JSON contract exists to enable, open the correct run before the first provider
turn, does not work end to end.

The CHARTER ratified open question 2 says the context is delivered "via query params first",
and FE F1 already implemented that parser. The two halves were specced separately and the
`routeUrl` shape did not get reconciled with the merged FE.

Fix (small, localized to the CLI side): build `routeUrl` with the params FE parses, e.g.
`f"{base_url}/canvas?owner=local&workspace_hash={wid.hash}&cli={agent}&run_id={run_id}"`
(URL-encoded). The event already carries `agent`, `workspace.hash`, and `runId`; `owner`
is the constant `local`. Update `test_desktop.py:133` to the new shape and add a test that
a launched canvas URL yields a non-null `hasLaunchLookup` against the FE parser contract.

This is feature-defeating, so I would gate merge on it. I am leaving it as Major rather
than Blocker only because it conforms to the letter of HC4; the blocker-vs-major call is
the orchestrator's given that HC4 specified bare `/canvas`.

### Minor 1 — `DESKTOP_LAUNCH_CONTEXT` env var is currently inert

`api/src/transport_matters/cli/desktop_cmd.py:157` (set in `spawn_detached_electron`),
`desktop/src/env.ts:14` (key defined)

`spawn_detached_electron` sets `TRANSPORT_MATTERS_DESKTOP_LAUNCH_CONTEXT` to the full event
JSON, but nothing consumes it: a grep across `desktop/src` and `www/src` finds only its
definition. The hosted main path (`registerHostedDesktopLifecycle`) uses only
`DESKTOP_ROUTE_URL`; no preload reads the context. It is the forward-looking adapter seam
for the later preload-IPC path (charter Q2), which is fine, but today it is dead. Once
Major 1 is fixed by putting the context on the URL, either wire this env var through a
preload bridge or drop it until the IPC path lands, so the channel is not mistaken for a
working handoff.

### Minor 2 — ambient `TRANSPORT_MATTERS_UPSTREAM_URL` hard-fails `desktop --agent codex`

`api/src/transport_matters/cli/desktop_cmd.py:40,232-234` (`_CLAUDE_ONLY_OPTIONS`,
`_option_supplied`)

`_option_supplied` correctly uses `ctx.get_parameter_source` (not value comparison), and
treats both `COMMANDLINE` and `ENVIRONMENT` as supplied. Among the claude-only options,
`upstream` is the only one carrying an `envvar` (`UPSTREAM_URL`). So a user who exports
`TRANSPORT_MATTERS_UPSTREAM_URL` (a documented env var, used for non-default claude upstreams)
and runs `transport-matters desktop --agent codex` is rejected with
`error: --upstream only valid with --agent codex` even though they never typed `--upstream`.
The rejection tests (`test_desktop.py:48-62`) only cover the `COMMANDLINE` source, so this
edge is unguarded.

Recommend: for env-backed cross-agent options, reject only on `ParameterSource.COMMANDLINE`
(an ambient env var is not an explicit per-invocation choice), or exclude `upstream` from
`ENVIRONMENT`-triggered rejection. Add a test exporting `TRANSPORT_MATTERS_UPSTREAM_URL`
with `--agent codex`.

### Minor 3 — DI wiring for `run_start`/`run_codex` is duplicated in `desktop()`

`api/src/transport_matters/cli/__init__.py` (the `desktop` claude/codex branches)

`desktop()` repeats the full dependency-injection kwargs block (`require_addon`,
`partial(resolve_mitmdump_executable, ...)`, `which`, `port_in_use`, `allocate_port_pair`,
`inject_system_prompt`, `print_banner`, etc.) that `claude()` and `codex()` already pass.
The launch logic itself is shared (run_start/run_codex own it), so this is wiring
duplication, not logic duplication, and it sits in the thin command layer (outside HC2's
named files). Still, the charter DRY bar is strict; extracting
`_invoke_claude_launch(...)`/`_invoke_codex_launch(...)` helpers (or default-binding
`partial`s) that fill the standard collaborators would remove ~25 repeated lines and give
one edit site when the launch signature changes. Non-blocking.

## Notes (scrutinized, correct)

- Cross-agent rejection uses `ctx.get_parameter_source` and the `ParameterSource` enum,
  not default-value comparison. This is the correct approach: it does not false-reject the
  `upstream` default URL or env-set ports (the shared port options are not agent-scoped).
  The only residue is Minor 2.
- Port non-pre-allocation is proven by a test that raises if `allocate_port_pair` is
  called, not merely asserted.
- The `on_backend_ready` hook tears down all children on exception
  (`_notify_backend_ready`), so a failed emit or Electron spawn does not orphan the proxy
  or agent.
- `runner.py`'s web-UI readiness wait is opt-in (hook-gated), so it does not add a wait to
  the existing `claude`/`codex` launches.

## Verification performed

- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`
  -> green: `ruff format --check` (288 files), `ruff check` (All checks passed!),
  `mypy` (Success: no issues found in 288 source files), pytest **1153 passed** (matches
  the builder's count).
- `cd desktop && pnpm typecheck && pnpm test` -> green: tsc (app + test configs) exit 0,
  vitest **7 files / 25 tests passed**.
- `git diff main...3090732` read in full for `desktop_cmd.py`, `__init__.py`, `runner.py`,
  `help.py`, `env_keys.py`, `desktop/src/{main,backendProcess,env}.ts`, and `test_desktop.py`.
- Grep for `DESKTOP_LAUNCH_CONTEXT` / launch-context consumers across `desktop/src` and
  `www/src`; read the FE F1 `route.ts` / `SessionCanvasRoute.tsx` query-param contract.

## Fix round verified — @ `73fa12c` (fixes verified: clean)

Delta vs `3090732` reviewed; all four findings resolved, no regression.

- Major 1 RESOLVED: `build_backend_started_event` now sets
  `routeUrl = f"{base_url}/canvas?{urlencode({owner: local, workspace_hash: wid.hash, cli: agent, run_id: ...})}"`.
  Param names match FE F1's `route.ts` parser exactly; new test asserts the parsed query
  via `parse_qs`. End-to-end desktop->canvas correlation restored.
- Minor 1 RESOLVED: `DESKTOP_LAUNCH_CONTEXT` removed from `desktop_cmd.py`, `env_keys.py`,
  and `desktop/src/env.ts`, plus the dead `context_json` line.
- Minor 2 RESOLVED: `_option_supplied` now returns `source == ParameterSource.COMMANDLINE`
  only; new `test_desktop_ignores_ambient_cross_agent_env` proves ambient
  `TRANSPORT_MATTERS_UPSTREAM_URL` + `--agent codex` exits 0.
- Minor 3 RESOLVED: DI kwargs extracted into a typed `_SharedDesktopLaunchKwargs` /
  `shared_launch_kwargs` spread. Kwarg sets exact-match the pre-fix code (claude 21,
  codex 20, shared/agent-specific disjoint); `proxy_port`/`web_port`/wrapped
  `run_client_with_retry` unchanged, so topology and port-non-prealloc do not regress.
- Gates re-run green: api `just ci` = ruff + mypy clean, **1154 passed** (+1 new test);
  desktop `pnpm typecheck` exit 0, **25 tests passed**.
