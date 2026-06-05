# Desktop CLI spec

Author: backend-engineer/codex  
Date: 2026-06-06  
Scope: `transport-matters desktop` flag reuse, launch flow, and canvas launch contract.

## Summary

Current `transport-matters claude` and `transport-matters codex` launch through the right shared runtime core. Current flag definitions live inline in two Typer functions, so a third command cannot reuse them without copying. The minimal fix is to extract shared and agent-specific `Annotated` option aliases, switch the work directory surface to a canonical `--work-dir` option, and have `desktop --agent claude|codex` reuse those aliases plus the existing `run_start` and `run_codex` command paths.

`transport-matters desktop` should default to Claude, keep the selected agent foreground in the user's terminal, and open Electron as a detached canvas viewer for observability and replay. Python owns the existing `run_start` and `run_codex` foreground launch paths. Electron never spawns or owns the agent in F1-F2.

## Grounded facts

- The installed script points at `transport_matters.cli:main` in `api/pyproject.toml:48-49`.
- `claude` and `codex` are registered in `api/src/transport_matters/cli/__init__.py:199-322` and `api/src/transport_matters/cli/__init__.py:358-472`.
- Both commands allow extra args and ignore unknown options for subprocess pass-through in `api/src/transport_matters/cli/__init__.py:203-207` and `api/src/transport_matters/cli/__init__.py:361-365`.
- Pass-through is split by `_split_passthrough` in `api/src/transport_matters/cli/__init__.py:94-105`.
- No `--work-dir` flag exists today. `rg -- '--work-dir|work-dir|work_dir' api/src/transport_matters/cli` returned only internal `directory` names and no flag declaration.
- `transport-matters desktop` does not exist today. `cd api && .venv/bin/python -m transport_matters.cli desktop --help` exits 2 with `No such command 'desktop'`.
- The desktop shell already knows `claude` and `codex` as supported clients in `desktop/src/backendProcess.ts:6-10` and defaults the desktop client to Claude in `desktop/src/main.ts:233-239`.

## Current flag inventory

### Shared surfaces today

| Surface | Accepted today | Definition | Shared | Notes |
| --- | --- | --- | --- | --- |
| Working directory | Positional `[DIRECTORY]` | Claude: `api/src/transport_matters/cli/__init__.py:211-220`; Codex: `api/src/transport_matters/cli/__init__.py:369-378` | Yes | This is not a flag. The charter wants `--work-dir`, so this is the mismatch to fix. |
| `--proxy-port`, `-p` | Optional int | Claude: `api/src/transport_matters/cli/__init__.py:221-231`; Codex: `api/src/transport_matters/cli/__init__.py:379-389` | Yes | Env var `TRANSPORT_MATTERS_PROXY_PORT`, callback `validate_port_option`. |
| `--web-port`, `-w` | Optional int | Claude: `api/src/transport_matters/cli/__init__.py:232-242`; Codex: `api/src/transport_matters/cli/__init__.py:390-400` | Yes | Env var `TRANSPORT_MATTERS_WEB_PORT`, callback `validate_port_option`. |
| `--storage-dir`, `-d` | Optional path | Claude: `api/src/transport_matters/cli/__init__.py:252-269`; Codex: `api/src/transport_matters/cli/__init__.py:401-418` | Yes | No env var on the CLI option by design. The addon still reads `TRANSPORT_MATTERS_STORAGE_DIR`. |
| `--home-dir` | Optional path | Claude: `api/src/transport_matters/cli/__init__.py:270-282`; Codex: `api/src/transport_matters/cli/__init__.py:419-428` | Yes | Parser accepts it, but custom help omits it. Help omission is in `api/src/transport_matters/cli/help.py:67-77` and `api/src/transport_matters/cli/help.py:127-137`. |
| `--debug` | Boolean | Claude: `api/src/transport_matters/cli/__init__.py:308-314`; Codex: `api/src/transport_matters/cli/__init__.py:447-453` | Yes | Flows to `build_mitmdump_argv` through `run_start` and `run_codex`. |
| `--print-command` | Boolean | Claude: `api/src/transport_matters/cli/__init__.py:315-321`; Codex: `api/src/transport_matters/cli/__init__.py:465-471` | Yes | Existing dry run exits through `print_invocation` in `api/src/transport_matters/cli/launch_runtime.py:427-437`. |
| `-h`, `--help` | Boolean | Claude command context: `api/src/transport_matters/cli/__init__.py:203-207`; Codex command context: `api/src/transport_matters/cli/__init__.py:361-365` | Yes | Command help is custom text, not Typer generated text. |
| Pass-through after `--` | List of raw strings | `api/src/transport_matters/cli/__init__.py:94-105` | Yes | Forwarded to the selected child command. |

### Claude-only surfaces today

| Surface | Accepted today | Definition | Notes |
| --- | --- | --- | --- |
| `--upstream`, `-u` | String | `api/src/transport_matters/cli/__init__.py:243-251` | Env var `TRANSPORT_MATTERS_UPSTREAM_URL`, default `https://api.anthropic.com`. |
| `--claude-bin` | Path | `api/src/transport_matters/cli/__init__.py:283-293` | Passed to `run_start` as `claude_bin`. |
| `--no-claude` | Boolean | `api/src/transport_matters/cli/__init__.py:294-300` | Rejects pass-through when set in `run_start`, lines `169-173`. |
| `--no-system-prompt` | Boolean | `api/src/transport_matters/cli/__init__.py:301-307` | Skips injection in `_build_start_invocation`, lines `88-94`. |

### Codex-only surfaces today

| Surface | Accepted today | Definition | Notes |
| --- | --- | --- | --- |
| `--codex-bin` | Path | `api/src/transport_matters/cli/__init__.py:429-439` | Passed to `run_codex` as `codex_bin`. |
| `--no-codex` | Boolean | `api/src/transport_matters/cli/__init__.py:440-446` | Rejects pass-through when set in `run_codex`, lines `300-304`. |
| `--force-http-fallback` | Boolean | `api/src/transport_matters/cli/__init__.py:454-464` | Adds the Codex fallback addon in `api/src/transport_matters/cli/codex_cmd.py:332-337`. |

## Reuse verdict

### Launch flow

The launch flow is reusable.

- Claude calls `prepare_launch` with `CLIENT_NAME_CLAUDE` in `api/src/transport_matters/cli/start_cmd.py:175-198`.
- Codex calls `prepare_launch` with `CLIENT_NAME_CODEX` in `api/src/transport_matters/cli/codex_cmd.py:306-326`.
- `prepare_launch` resolves binary, work dir, ports, run id, storage, and pass-through once in `api/src/transport_matters/cli/launch_runtime.py:335-397`.
- Both commands call `prepare_managed_session`, the shared owned-session seam, in `api/src/transport_matters/cli/start_cmd.py:204-214` and `api/src/transport_matters/cli/codex_cmd.py:352-362`.
- `prepare_managed_session` is explicitly the single managed-launch entry point in `api/src/transport_matters/cli/launch_profile.py:215-246`.
- Claude and Codex own only provider-specific argv and transcript preparation through `ClaudeLaunchProfile` and `CodexLaunchProfile` in `api/src/transport_matters/cli/launch_profile.py:110-151` and `api/src/transport_matters/cli/launch_profile.py:154-201`.
- Both commands persist per-run manifest state through `run_with_workspace_manifest` in `api/src/transport_matters/cli/start_cmd.py:282-288` and `api/src/transport_matters/cli/codex_cmd.py:419-425`.

### Flag definitions

Flag definitions are not reusable as written.

The Typer option declarations are inline inside `claude` and `codex`. Adding `desktop` by copying those parameters would violate the DRY rule and would likely repeat the existing `--home-dir` custom help omission.

## Minimal refactor

### New module

Add `api/src/transport_matters/cli/launch_options.py` as the single source for command option aliases and validation helpers. Keep it below 300 LOC.

```python
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from transport_matters import env_keys
from transport_matters.cli.ports import validate_port_option

AgentName = Literal["claude", "codex"]

AgentOption = Annotated[
    AgentName,
    typer.Option(
        "--agent",
        case_sensitive=False,
        help="Agent to launch in the desktop canvas.",
    ),
]

WorkDirOption = Annotated[
    Path | None,
    typer.Option(
        "--work-dir",
        help="Working directory for the agent and canvas. Defaults to cwd.",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
]

ProxyPortOption = Annotated[
    int | None,
    typer.Option(
        "--proxy-port",
        "-p",
        envvar=env_keys.PROXY_PORT,
        help="Port for the proxy listener. Defaults to a kernel-allocated free port.",
        show_default=False,
        callback=validate_port_option,
    ),
]

WebPortOption = Annotated[
    int | None,
    typer.Option(
        "--web-port",
        "-w",
        envvar=env_keys.WEB_PORT,
        help="Port for the embedded web UI. Defaults to a kernel-allocated free port.",
        show_default=False,
        callback=validate_port_option,
    ),
]
```

The module should also hold `StorageDirOption`, `HomeDirOption`, `DebugOption`, `PrintCommandOption`, `ClaudeUpstreamOption`, `ClaudeBinOption`, `NoClaudeOption`, `NoSystemPromptOption`, `CodexBinOption`, `NoCodexOption`, and `ForceHttpFallbackOption`. The existing `claude`, `codex`, and new `desktop` functions should import and reuse these aliases.

### Work dir migration

Make `--work-dir` canonical across `claude`, `codex`, and `desktop`.

- Replace the public `[DIRECTORY]` parameter in `claude` and `codex` with `work_dir: WorkDirOption = None`.
- Internally keep `run_start(directory=work_dir, ...)` and `run_codex(directory=work_dir, ...)` so `prepare_launch` stays unchanged.
- Simplify pass-through by keeping explicit `--` for child args. With no positional work dir, a first child prompt can no longer be swallowed as `[DIRECTORY]`.
- Update custom help in `api/src/transport_matters/cli/help.py` so `--work-dir` and `--home-dir` are visible for both existing commands and the new desktop command.

Compatibility is not a constraint for this pre-release repo. If the orchestrator wants a softer migration, add a hidden legacy positional parameter for `claude` and `codex` only, reject use of both forms, and delete the positional in the next slice. The default spec is the cleaner break.

### Desktop parser composition

Add `desktop` in `api/src/transport_matters/cli/__init__.py` as a thin command. Keep the actual behavior in `api/src/transport_matters/cli/desktop_cmd.py`.

Shape:

```python
@main.command(
    name="desktop",
    cls=PlainCommand,
    no_args_is_help=False,
    context_settings={
        "help_option_names": ["-h", "--help"],
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
def desktop(
    ctx: typer.Context,
    agent: AgentOption = "claude",
    work_dir: WorkDirOption = None,
    proxy_port: ProxyPortOption = None,
    web_port: WebPortOption = None,
    storage_dir: StorageDirOption = None,
    home_dir: HomeDirOption = None,
    debug: DebugOption = False,
    print_command: PrintCommandOption = False,
    upstream: ClaudeUpstreamOption = "https://api.anthropic.com",
    claude_bin: ClaudeBinOption = None,
    no_claude: NoClaudeOption = False,
    no_system_prompt: NoSystemPromptOption = False,
    codex_bin: CodexBinOption = None,
    no_codex: NoCodexOption = False,
    force_http_fallback: ForceHttpFallbackOption = False,
) -> None:
    ...
```

`desktop` must accept the union of Claude and Codex launch options because `--agent` is parsed at the same level. After parse:

- If `agent == "claude"`, reject Codex-only options with a usage error.
- If `agent == "codex"`, reject Claude-only options with a usage error.
- Forward pass-through from `_split_passthrough(ctx, None)` to the selected child argv.
- Default `agent` is `claude`.
- `--work-dir` maps directly to canvas working dir and to the agent launch working dir.

## Desktop launch design

### Process ownership

Python is the long-lived owner of the launch. `transport-matters desktop` stays primary in the user's terminal, uses the existing foreground launcher path, and keeps stdin/TTY attached to the selected agent exactly as `transport-matters claude` and `transport-matters codex` do today.

Electron is a detached viewer. It opens the canvas route for the web backend that Python already started, then renders observability and replay surfaces from the session store. It does not spawn, supervise, or own the agent child in F1-F2. A real TUI pane inside the canvas is deferred to F3.

New command flow:

1. Python parses `transport-matters desktop` with the shared option aliases.
2. Python resolves the canvas work dir with the same semantics as `resolve_working_dir` in `api/src/transport_matters/cli/launch_runtime.py:232-242`.
3. Python selects the launch profile from `--agent claude|codex`.
4. Python calls the same selected launch path that backs the public command:
   - Claude: `run_start(...)`
   - Codex: `run_codex(...)`
5. The selected launch path still owns `prepare_launch`, `prepare_managed_session`, transcript ownership, storage, manifest, retry semantics, and foreground TTY ownership.
6. After the web backend is ready and the manifest is written, Python emits the startup JSON line and starts the packaged Electron shell detached with `routeUrl`.
7. Electron loads the canvas route at the already-running web port and consumes session data. The agent remains interactive in the original terminal.

Do not rebuild `prepare_launch`, proxy argv, child env, or profile-specific argv in the Electron code. That duplicates logic already covered by `api/src/transport_matters/cli/launch_runtime.py`, `api/src/transport_matters/cli/start_cmd.py`, `api/src/transport_matters/cli/codex_cmd.py`, and `api/src/transport_matters/cli/launch_profile.py`.

### Port handling

If the user supplied `--proxy-port` or `--web-port`, pass those values into the selected Python launch path.

If the user omitted ports, do not pre-allocate in `desktop` and then pass pinned ports to the child. Passing allocator-chosen ports as normal flags makes `prepare_launch` treat them as user supplied, because `resolve_launch_ports` derives `proxy_user_supplied` and `web_user_supplied` from `proxy_port is not None` and `web_port is not None` in `api/src/transport_matters/cli/launch_runtime.py:253-255`. That would disable the existing retry behavior for a bind race.

Preferred contract:

- The Python launcher owns dynamic port allocation.
- Electron learns `web_port`, `proxy_port`, `run_id`, `slug`, and `hash` from a startup JSON line emitted after `write_manifest_for` succeeds and the web backend is ready, with manifest discovery as fallback.
- Existing manifest contains `cwd`, `proxy_port`, `web_port`, `storage_dir`, `run_id`, `slug`, `hash`, and `home_dir` in `api/src/transport_matters/manifest.py:34-52`; it is written in `run_with_workspace_manifest` at `api/src/transport_matters/cli/launch_runtime.py:554-569`.

### Startup JSON contract

Add a desktop-only launch hook, exposed to tests as a hidden option if needed, for example `--emit-startup-json`. The selected Python launch path writes one line to stdout after manifest write and backend readiness, before the interactive child foreground path begins. The same hook starts Electron detached with `routeUrl`.

```typescript
type DesktopAgentKind = "claude" | "codex";

interface DesktopBackendStarted {
  type: "transport_matters.backend_started";
  agent: DesktopAgentKind;
  cwd: string;
  workspace: {
    slug: string;
    hash: string;
  };
  runId: string;
  proxyPort: number;
  webPort: number;
  baseUrl: string;
  routeUrl: string;
  storageDir: string;
  homeDir: string | null;
}
```

`routeUrl` should default to `http://127.0.0.1:{webPort}/canvas`. If the frontend keeps a hash route to avoid server fallback work, use `http://127.0.0.1:{webPort}/#/canvas` and keep this field as the single Electron contract.

### Canvas session contract

The canvas consumes the session store API, not the legacy exchange reducer.

Available API facts:

- API routers mount under `/api` in `api/src/transport_matters/main.py:117`.
- `GET /api/sessions` is defined at `api/src/transport_matters/api/v1/session_routes.py:111-133`.
- `SessionSummary` includes `session_id`, `provider`, `cli`, `run_id`, `cwd`, `workspace_slug`, `workspace_hash`, `native_session_id`, `minted`, `source_descriptor`, `home_dir`, `owner`, and `status` in `api/src/transport_matters/api/v1/session_routes.py:34-59`.
- `GET /api/sessions/{session_id}/events` is defined at `api/src/transport_matters/api/v1/session_routes.py:136-156`.
- `GET /api/sessions/{session_id}/events/stream` is defined at `api/src/transport_matters/api/v1/session_routes.py:159-174`.
- Event rows include `run_id`, `provider`, `cli`, `role`, `ir`, `source_path`, and `source_line` in `api/src/transport_matters/api/v1/session_routes.py:62-87`.

Typed contract for the canvas:

```typescript
interface DesktopLaunchContext {
  agent: "claude" | "codex";
  cwd: string;
  workspace: {
    slug: string;
    hash: string;
  };
  runId: string;
  baseUrl: string;
  routeUrl: string;
}

interface SessionSummary {
  session_id: string;
  provider: string;
  cli: string | null;
  run_id: string;
  cwd: string;
  workspace_slug: string;
  workspace_hash: string;
  native_session_id: string | null;
  minted: boolean;
  source_descriptor: Record<string, unknown> | null;
  home_dir: string | null;
  owner: string;
  status: "active" | "completed" | "archived";
  title: string | null;
  parent_session_id: string | null;
  forked_at_seq: number | null;
  started_at: string;
  created_at: string | null;
  updated_at: string | null;
}
```

Canvas lookup rule:

1. On load, call `GET /api/sessions?owner=local&workspace_hash={hash}&cli={agent}&limit=50`.
2. Prefer sessions whose `run_id` equals `DesktopLaunchContext.runId`.
3. If no matching row exists yet, show the session-picker pane in a pending state and poll or subscribe through the session stream once available.
4. When a matching session appears, spawn a transcript-chat pane using `session_id`.
5. Use `GET /api/sessions/{session_id}/events?owner=local` for backlog, then `GET /api/sessions/{session_id}/events/stream?owner=local&last_seq={lastSeenSeq}` for live append.
6. Deduplicate by `seq`.

This lets desktop open the correct run before the first provider turn has created a session row.

## Open questions for orchestrator

1. **Canonical work dir surface.** Working assumption: replace positional `[DIRECTORY]` with `--work-dir` for `claude`, `codex`, and `desktop` now. Pre-release status makes the cleaner break acceptable.
2. **Canvas route string.** Working assumption: `routeUrl` defaults to `/canvas`. If the frontend chooses hash routing for static hosting, only the `routeUrl` builder changes.
3. **Startup JSON timing.** Working assumption: emit after manifest write and backend readiness, before the foreground child owns the terminal. This gives Electron exact ports and run identity without scraping banners.
4. **Desktop binary discovery.** Working assumption: `transport-matters desktop` launches the packaged Electron app when present and returns a repair hint when absent. Development can keep `pnpm --dir desktop dev` as a separate workflow.

## Verification performed

- `fmm_list_files(group_by="subdir")` returned the indexed project shape: `api/`, `www/`, and `desktop/`.
- `fmm_file_outline` was used for the CLI entrypoint, launch runtime, launch profiles, desktop shell files, workspace identity, manifest, and session API before targeted line reads.
- `find /Users/alphab/.mdx/design -maxdepth 2 -type f` confirmed existing design docs were checked.
- `cd api && .venv/bin/python -m transport_matters.cli claude --help` exited 0.
- `cd api && .venv/bin/python -m transport_matters.cli codex --help` exited 0.
- `cd api && .venv/bin/python -m transport_matters.cli desktop --help` exited 2 with `No such command 'desktop'`.
- `cd api && .venv/bin/python -m transport_matters.cli claude --home-dir /tmp/tm-home-test --no-claude --print-command` exited 0, proving `--home-dir` is accepted despite being omitted from custom help.
- `cd api && .venv/bin/python -m transport_matters.cli codex --home-dir /tmp/tm-home-test --no-codex --print-command` exited 0, proving the same Codex parser behavior.
