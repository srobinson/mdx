# Transport Matters detached desktop instances spec

Status: implementation ready. Verified against live tree at `87d6d3e` on 2026-06-20. `fmm validate` reports all 851 indexed files current.

## Goal

Make `transport-matters desktop [--channel X]` start a channel scoped desktop backend, open the Electron viewer, write a small runtime record, and return to the shell. Keep the current blocking behavior behind an explicit foreground flag. The design stays small: no daemon, no supervisor, no `stop`, no separate `ps`. Operators kill the recorded PID.

## Current seams

`api/src/transport_matters/cli/__init__.py:desktop` accepts `--channel`, `--work-dir`, `--web-port`, and `--storage-dir`, then calls `desktop_cmd.run_desktop_launch`. `api/src/transport_matters/cli/__init__.py:desktop_backend` registers the hidden `_desktop-backend` command from `desktop_cmd.DESKTOP_BACKEND_COMMAND` and calls `desktop_cmd.run_desktop_backend_server`.

`api/src/transport_matters/cli/desktop_cmd.py:run_desktop_launch` starts with `channel.activate_channel`, builds a `DesktopLaunchPlan`, prints the backend started JSON, spawns Electron through `spawn_detached_electron`, then calls `serve_desktop_backend`. `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_backend_server` also starts with `activate_channel`, then runs the same backend without Electron. `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend` applies launch env, runs session store preflight, creates uvicorn with `main.LOG_CONFIG`, starts uvicorn in a daemon thread when an `on_backend_ready` callback exists, waits for the web port, runs the callback, then joins the uvicorn thread. That join is why the command blocks today.

`api/src/transport_matters/cli/desktop_cmd.py:spawn_detached_electron` uses `subprocess.Popen` with `stdin=DEVNULL`, `stdout=DEVNULL`, `stderr=DEVNULL`, `close_fds=True`, and `start_new_session=True`. It builds the viewer env from `os.environ` and only sets `DESKTOP_ROUTE_URL`, `CWD`, `STORAGE_DIR`, and `WEB_PORT`. It does not set `CHANNEL`. `desktop/src/main.ts:registerDesktopLifecycleFromEnv` resolves channel identity from env before taking the hosted route branch, so `run_desktop_detached` must call `activate_channel(channel)` as its first step. Otherwise `transport-matters desktop --channel preview` with no `TRANSPORT_MATTERS_CHANNEL` env would spawn a viewer with stable identity and no preview badge. `justfile:channel-restart` exports `TRANSPORT_MATTERS_CHANNEL={{channel}}`, so the live smoke would mask this direct CLI bug.

`api/src/transport_matters/main.py:LOG_CONFIG` defines only a console `logging.StreamHandler`; `main.create_app` copies that config and writes logs to process streams. Detached logging should redirect child stdout and stderr to a file rather than adding a FastAPI file logger.

`api/src/transport_matters/storage_roots.py:default_storage_root`, `api/src/transport_matters/config.py:Settings.storage_dir`, and `api/src/transport_matters/main.py:lifespan` establish the runtime convention: shared proxy state lives under `storage_dir / "runtime" / "shared-proxy"`. Channels come from `api/src/transport_matters/channel.py:ChannelSpec`, whose `home`, `proxy_port`, and `web_port` isolate `stable` and `preview`. `api/src/transport_matters/cli/channel_cmd.py:list_channels` prints the configured channel table today.

## CLI contract

Add `--foreground` to `transport-matters desktop`. This name is clearer than `--tail` or `--attach`: `tail` becomes its own log command, while `attach` could imply attaching to an existing instance. Default behavior is detached. `--foreground` keeps the current uvicorn streaming behavior by calling the existing `run_desktop_launch` path.

Update root `justfile:channel-restart` to accept variadic desktop args and pass them through. The default remains detached. A foreground preview remains available as:

```bash
just channel-restart preview --foreground
```

Recommended recipe shape:

```just
channel-restart channel="preview" *desktop_args:
    cd "{{www_dir}}" && pnpm install && pnpm build
    cd "{{desktop_dir}}" && pnpm install && pnpm build && pnpm electron:install
    uv run --project "{{api_dir}}" transport-matters channel ensure-db {{channel}}
    TRANSPORT_MATTERS_CHANNEL={{channel}} uv run --project "{{api_dir}}" transport-matters desktop --channel {{channel}} {{desktop_args}}
```

Add `transport-matters tail [channel]` with `-f, --follow` and `-n, --lines INT` defaulting to 100. The channel argument is optional and resolves through `TRANSPORT_MATTERS_CHANNEL`, then `stable`, using `channel.resolve_channel_spec`. Without `--follow`, print the last N log lines and exit. With `--follow`, print the last N lines, flush, then poll for appends until Ctrl C. Missing log exits non zero with the exact path.

## Runtime record

Create `api/src/transport_matters/cli/desktop_runtime.py` as the shared seam for `desktop_cmd`, `channel_cmd`, and the new `tail` command. This placement keeps all consumers inside `cli/` and avoids a package root module importing `cli/home_io`. Keep it under 700 LOC. Suggested exports:

- `DesktopRuntimeRecord`, a frozen dataclass.
- `desktop_runtime_dir(storage_dir: Path) -> Path`.
- `desktop_record_path(storage_dir: Path) -> Path`.
- `desktop_log_path(storage_dir: Path) -> Path`.
- `write_desktop_record(path: Path, record: DesktopRuntimeRecord) -> None`.
- `read_live_desktop_record(path: Path, pid_alive: Callable[[int], bool] = is_pid_alive) -> DesktopRuntimeRecord | None`.
- `is_pid_alive(pid: int) -> bool`, implemented with `os.kill(pid, 0)` and errno handling.

Promote `api/src/transport_matters/cli/home_io.py:_write_atomic_json` to public `write_atomic_json` and update its current `cli/claude_home.py` callers. `desktop_runtime` must reuse that public helper. This satisfies `api/src/transport_matters/test_private_import_boundary.py:violations`, which flags `ImportFrom` aliases beginning with a single underscore. `api/src/transport_matters/manifest.py:write` is a second inline copy of the same atomic pattern; consolidation there is optional.

Record path: `desktop_runtime.desktop_record_path(resolved_storage)`. Log path: `desktop_runtime.desktop_log_path(resolved_storage)`. `resolved_storage` is the value from `desktop_cmd._resolve_storage_dir`, which applies `.expanduser().resolve()`, honors `--storage-dir`, and otherwise uses `storage_roots.default_storage_root(channel)`, which honors `$TRANSPORT_MATTERS_HOME`.

Schema:

```json
{
  "schema_version": 1,
  "channel": "preview",
  "pid": 12345,
  "proxy_port": 8797,
  "web_port": 8798,
  "log_path": "/Users/alphab/.transport-matters-preview/runtime/desktop.log",
  "started_at": "2026-06-20T07:24:57Z"
}
```

Field traceability: `channel` comes from `channel.ChannelSpec.id`; ports come from `desktop_cmd._resolve_backend_ports`; `pid` comes from the backend `subprocess.Popen` handle; `log_path` and record path come from `cli.desktop_runtime`; `started_at` is UTC at successful child spawn. Pin `started_at` to UTC, trailing `Z`, no microseconds, for example `datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")`, and assert that shape in the schema test.

`channel_cmd.list_channels` adds one `pid` column after `web`. For each `ChannelSpec`, compute the record path through `desktop_runtime.desktop_record_path(default_storage_root(spec.id))`, then read the record, verify pid liveness, and print the PID if alive. `tail` computes its log path through `desktop_runtime.desktop_log_path(default_storage_root(channel_id))`. Invalid JSON, missing fields, dead pids, and `PermissionError` from `os.kill` render blank. Stale records may be unlinked as cleanup, but must never fail list. PID reuse can show a false live PID after OS reuse; accept that caveat. Instances launched with explicit `--storage-dir` are another accepted KISS edge: they write a valid record and log in that storage dir, but they sit outside the channel scoped `channel list` and default `tail` view.

## Detached launch mechanism

Add `desktop_cmd.run_desktop_detached` and keep `run_desktop_launch` as the foreground implementation. `run_desktop_detached` calls `activate_channel(channel)` first, then `prepare_desktop_launch` with `launch_viewer=True`. It derives cwd from `plan.env[env_keys.CWD]`, storage from `plan.event["storageDir"]`, opens `desktop.log` in append mode, and starts `plan.command` with:

```python
subprocess.Popen(
    list(plan.command),
    cwd=str(Path(plan.env[env_keys.CWD])),
    env=plan.env,
    stdin=subprocess.DEVNULL,
    stdout=log_handle,
    stderr=subprocess.STDOUT,
    close_fds=True,
    start_new_session=True,
)
```

The parent writes the runtime record from `Popen.pid`, then calls `spawn_detached_electron(plan.electron_launch, plan.event)`, then returns. This is sound without a double fork because `start_new_session=True` places the backend in a new session, stdio is detached from the terminal, file descriptors are closed except the log, and parent exit leaves the backend alive under the OS parent. If Electron spawn fails after the backend record is written, the backend remains recorded with a killable PID; surface the error clearly, but keep the record.

Killing the PID stops the backend. The already detached Electron viewer will show its existing load failure behavior until the operator closes it. Optional follow up: teach `desktop/src/main.ts:registerHostedDesktopLifecycle` to poll `/health` and close the window when the hosted backend dies. Defer that unless dogfooding proves the load failure is confusing.

## Implementation slices

1. Detached runtime, listing, and tail. Add `cli/desktop_runtime.py`, public `home_io.write_atomic_json`, `--foreground`, `run_desktop_detached`, record writing, log redirection, `channel list` PID rendering, `transport-matters tail [channel]`, and root `justfile:channel-restart` passthrough. Tests: atomic record write, pid liveness, stale cleanup, default detached dispatch, `run_desktop_detached` calls `activate_channel` before preparing launch, flag only preview viewer env carries `CHANNEL`, foreground dispatch, Popen args, log path, record schema including `started_at`, Electron spawn failure leaves a killable record, no provider launch, PID column rendering, `--storage-dir` documented edge, and pure Python tail with and without `--follow`. Gate: `just check`; `just test`; `cd api && just ci`; `cd desktop && just package-smoke`; live launch smoke below.

2. Help docs and optional hosted close. Update `_DESKTOP_HELP`, README, and `docs/CHANNELS.md`. If dogfooding asks for it, add the optional Electron health poll in `desktop/src/main.ts:registerHostedDesktopLifecycle`; otherwise leave it deferred. Gate: `just check`; `just test`; `cd api && just ci`; `cd desktop && just package-smoke`; live launch smoke below.

Live launch smoke for every slice:

```bash
just channel-restart preview
uv run --project api transport-matters channel list
uv run --project api transport-matters tail preview
uv run --project api transport-matters tail -f preview
kill <PID from channel list>
uv run --project api transport-matters channel list
```

Expected proof: the launch command returns, `channel list` shows a preview PID while live, `tail preview` shows uvicorn or app startup logs from `desktop.log`, killing the PID makes the preview PID column blank on the next list, and the worktree remains clean except intended changes.
