# `sm run --agent-config` current implementation analysis

Scope: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`, with the runtime hop checked in `../runtime-matters` where `sm-driver` hands work to `rtmd`.

## 1. Surface

- `sm run` is the `Command::Run(RunArgs)` CLI leaf, and clap is configured to require arguments before running the command body. `crates/sm-cli/src/cli/cli_def.rs:27-31`
- `RunArgs` flattens `SessionCreateArgs`, adds `--target` with default `headless`, adds `--force`, and parses `--detach`; the `detach` field is parsed but not consumed by `cli::run::run`. `crates/sm-cli/src/cli/cli_def.rs:78-90`, `crates/sm-cli/src/cli/run.rs:12-14`
- `SessionCreateArgs` defines the visible session identity inputs: positional `<RUNTIME>`, `--role`, `--dir`, `--namespace`, repeated `--label`, and `--agent-config <AGENT_CONFIG>`. `crates/sm-cli/src/cli/cli_def.rs:94-107`
- The runtime parser accepts only `claude` and `codex`. `crates/sm-core/src/runtime.rs:10-13`, `crates/sm-core/src/runtime.rs:33-39`
- The `--agent-config` clap field is `Option<String>` with no value parser, no existence check, and no path canonicalization at the CLI layer. `crates/sm-cli/src/cli/cli_def.rs:105-106`, `crates/sm-cli/src/cli/run.rs:39-47`
- The generated CLI help string is exactly `Agent config name or explicit agent.toml path.` `crates/sm-cli/src/cli/generated_help.rs:16`
- The single source of truth for the public run tool describes `agent_config` as an optional string and describes the MCP form as `~/.agm/<name>/agent.toml` or an explicit `agent.toml` path. `tools/run.toml:1-3`, `tools/run.toml:115-121`
- Generated MCP schema exposes `agent_config` as a string input and exposes `session.agent_config` as nullable output. `crates/sm-cli/src/mcp/generated_schema/session_run.json:6-9`, `crates/sm-cli/src/mcp/generated_schema/session_run.json:61-66`
- The MCP handler reads `agent_config` as an optional string and puts it into the same `SpawnRequest` field used by the CLI path. `crates/sm-daemon/src/mcp_tools.rs:121-132`, `crates/sm-daemon/src/mcp_tools.rs:136-152`
- `sm create session` reuses `SessionCreateArgs`, so it also accepts `--agent-config`, but it does not expose `--target`, `--detach`, or `--force`. `crates/sm-cli/src/cli/cli_def.rs:164-175`, `crates/sm-cli/src/cli/namespace.rs:9-14`, `crates/sm-cli/tests/cli_get_test.rs:58-75`
- Help coverage asserts the `sm run --help` surface includes the agent config text. `crates/sm-cli/tests/cli_help_surface_test.rs:41-59`

## 2. Resolution

- The CLI sends the raw `args.agent_config` string to `smd`; resolution happens in the daemon. `crates/sm-cli/src/cli/run.rs:36-47`, `crates/sm-daemon/src/handler.rs:137-143`
- `smd` requires its own process `HOME` environment variable when an agent config is requested. `crates/sm-daemon/src/agent_config.rs:16-24`
- Disambiguation is heuristic: a value is treated as path like when it contains the platform separator, starts with `~`, starts with `.`, or ends with `.toml`. `crates/sm-daemon/src/agent_config.rs:56-61`
- Path like values are expanded only for `~` and `~/...`; every other value is passed directly to `PathBuf::from`. `crates/sm-daemon/src/agent_config.rs:63-71`
- Non path like values resolve to `$HOME/.agm/<requested>/agent.toml`, where `HOME` is the daemon process environment. `crates/sm-daemon/src/agent_config.rs:20-23`, `crates/sm-daemon/src/agent_config.rs:49-54`
- The resolved file must exist as a regular file before any runtime spawn happens. `crates/sm-daemon/src/agent_config.rs:26-33`, `crates/sm-daemon/src/handler.rs:137-143`
- The daemon reads the file as TOML and extracts environment entries from the parsed TOML value. `crates/sm-daemon/src/agent_config.rs:35-40`
- The accepted `agent.toml` schema is currently small: optional top level `claude_config_dir` must be a string and becomes `CLAUDE_CONFIG_DIR`; optional `[env]` must be a table whose values are strings. `crates/sm-daemon/src/agent_config.rs:73-96`
- `[env]` can override `claude_config_dir` by using the same `CLAUDE_CONFIG_DIR` key because both paths insert into the same `BTreeMap`. `crates/sm-daemon/src/agent_config.rs:74-90`
- The resolver stores the original request string, the resolved path, and the derived env, but downstream code currently uses the env and later persists the original request string. `crates/sm-daemon/src/agent_config.rs:10-14`, `crates/sm-daemon/src/handler.rs:142-143`, `crates/sm-daemon/src/handler.rs:163-177`
- Named resolution and explicit path resolution both have unit coverage. `crates/sm-daemon/src/agent_config.rs:103-130`, `crates/sm-daemon/src/agent_config.rs:133-150`
- Missing named configs fail with an error that includes `agent config not found` and the requested name. `crates/sm-daemon/src/agent_config.rs:153-160`

## 3. Wire

- The CLI canonicalizes the run directory before building the spawn request, and daemon side validation rejects empty, relative, or non directory paths. `crates/sm-cli/src/cli/run.rs:79-95`, `crates/sm-daemon/src/spawn_request.rs:36-48`
- The CLI captures the caller environment and includes it in `SpawnRequest.env`. `crates/sm-cli/src/cli/run.rs:20-24`, `crates/sm-cli/src/cli/run.rs:39-55`
- The sm CLI to smd wire type is `sm_core::SpawnRequest`; it carries `agent_config: Option<String>`, `env: Vec<LaunchEnv>`, `shell_resume`, labels, target, and force. `crates/sm-core/src/proto.rs:17-38`
- The daemon spawn handler normalizes the request, resolves the agent config, converts the request into a `SpawnLaunch`, validates the target, calls the spawn driver, then persists a `Session`. `crates/sm-daemon/src/handler.rs:137-161`, `crates/sm-daemon/src/handler.rs:163-177`
- `SpawnLaunch` has no `agent_config` field; it carries runtime, cwd, target, env, shell resume, and force. `crates/sm-driver/src/driver.rs:21-28`
- `spawn_launch` starts from `request.env`, captures daemon env only when `request.env` is empty, merges agent config env, strips any existing `HELIOY_SESSION_*` entries, and then upserts `HELIOY_SESSION_ID`, `HELIOY_SESSION_ROLE`, and `HELIOY_SESSION_WORKSPACE`. `crates/sm-daemon/src/handler.rs:606-641`
- Env merge semantics are last writer wins for matching keys. `crates/sm-daemon/src/handler.rs:658-670`
- The persisted session stores only the original `request.agent_config`, not the resolved path or parsed env. `crates/sm-daemon/src/handler.rs:163-177`, `crates/sm-core/src/session.rs:67-89`
- SQLite schema and insert logic include `agent_config TEXT`, and row reads restore it into `Session.agent_config`. `crates/sm-store/src/schema.rs:1-20`, `crates/sm-store/src/sqlite/sessions.rs:31-55`, `crates/sm-store/src/sqlite/sessions.rs:271-298`
- `RtmdDriver` maps session-matters runtime values to runtime-matters runtime values and sends `launch.env` inside `lilo_rm_core::SpawnRequest`; no `agent_config` field crosses into runtime-matters. `crates/sm-driver/src/rtmd.rs:48-80`, `crates/sm-driver/src/rtmd.rs:233-244`
- The runtime-matters public spawn request contains `env`, `cwd`, `target`, `force`, and `shell_resume`, but no agent config field. `../runtime-matters/crates/rtm-core/src/types/spawn.rs:77-92`
- Runtime-matters builds a `LaunchSpec` through the runtime launcher and backend before the shim asks back for the actual launch spec. `../runtime-matters/crates/rtm-daemon/src/handler.rs:101-110`, `../runtime-matters/crates/rtm-daemon/src/handler.rs:177-180`
- Runtime-matters `LaunchSpec` contains argv, env, cwd, and shell resume. `../runtime-matters/crates/rtm-core/src/launcher.rs:31-37`

## 4. Runtime effect

- The only implemented effect of `--agent-config` is environment mutation before runtime launch. `crates/sm-daemon/src/agent_config.rs:73-96`, `crates/sm-daemon/src/handler.rs:606-641`
- `claude_config_dir` becomes `CLAUDE_CONFIG_DIR` in the runtime environment, and arbitrary `[env]` string entries become runtime environment entries. `crates/sm-daemon/src/agent_config.rs:75-90`
- The Claude launcher uses argv `claude` and returns `runtime_env(request)` for env. `../runtime-matters/crates/rtm-launchers/src/claude.rs:14-20`
- The Codex launcher uses argv `codex` and returns `runtime_env(request)` for env. `../runtime-matters/crates/rtm-launchers/src/codex.rs:14-20`
- `runtime_env` starts with `request.env`, then upserts `HELIOY_SESSION_ID`, `HELIOY_RUNTIME`, `RTM_SESSION_ID`, and `RTM_RUNTIME_KIND`. `../runtime-matters/crates/rtm-launchers/src/lib.rs:55-74`
- The shim clears the inherited process environment, applies `LaunchSpec.env`, and sets `LaunchSpec.cwd` before running the runtime command. `../runtime-matters/crates/rtm-cli/src/cli/shim.rs:92-98`, `../runtime-matters/crates/rtm-cli/src/cli/shim.rs:125-131`
- For tmux targets, the bootstrap env passed to `tmux respawn-pane` is deliberately only the shim socket env; the actual runtime env arrives later through `ShimLaunch` and is applied by the shim. `../runtime-matters/crates/rtm-daemon/src/shim_socket.rs:38-49`, `../runtime-matters/crates/rtm-daemon/src/shim_socket.rs:130-147`, `../runtime-matters/crates/rtm-daemon/src/shim_socket.rs:149-160`, `../runtime-matters/crates/rtm-platform/src/tmux.rs:201-221`
- No code in the traced path turns agent config into runtime argv, model selection, instructions file selection, or a typed runtime policy. `crates/sm-daemon/src/agent_config.rs:73-96`, `../runtime-matters/crates/rtm-launchers/src/claude.rs:14-20`, `../runtime-matters/crates/rtm-launchers/src/codex.rs:14-20`

## 5. Works today

### Minimum file shape

A named config works when the daemon process can read `$HOME/.agm/demo/agent.toml` with this shape. `crates/sm-daemon/src/agent_config.rs:20-24`, `crates/sm-daemon/src/agent_config.rs:49-54`, `crates/sm-daemon/src/agent_config.rs:73-96`

```toml
claude_config_dir = "/absolute/path/to/claude-config"

[env]
HELIOY_AGENT_NAME = "demo"
```

An explicit config works when `--agent-config` is an existing `agent.toml` path, preferably absolute because the daemon resolves relative explicit paths in daemon process context. `crates/sm-daemon/src/agent_config.rs:56-71`, `crates/sm-daemon/src/agent_config.rs:133-150`

### Minimum commands

For a named config, the normal user command is:

```bash
sm run claude --role general --dir "$PWD" --agent-config demo --detach
```

The prerequisites are a running `rtmd`, a running `smd`, and a readable `$HOME/.agm/demo/agent.toml`. `README.md:9-16`, `README.md:26-29`, `crates/sm-daemon/src/agent_config.rs:49-54`

For an explicit config path, the normal user command is:

```bash
sm run claude --role general --dir "$PWD" --agent-config /absolute/path/to/agent.toml --detach
```

That path is treated as explicit because it contains a separator or ends with `.toml`. `crates/sm-daemon/src/agent_config.rs:56-61`

### Observed smoke result

- The isolated named smoke command ran `sm run claude --role agent-config-named --dir $PROJECT --agent-config demo --detach` and returned a running session line. `~/.mdx/projects/agent-config-analysis--smoke.log:1-4`
- The named smoke runtime received `CLAUDE_CONFIG_DIR`, `HELIOY_AGENT_NAME`, `HELIOY_SESSION_ID`, `HELIOY_RUNTIME`, `RTM_SESSION_ID`, and `RTM_RUNTIME_KIND`. `~/.mdx/projects/agent-config-analysis--smoke.log:5-12`
- The named smoke session persisted `agent_config: "demo"` and a transcript path. `~/.mdx/projects/agent-config-analysis--smoke.log:13-20`
- The isolated explicit smoke command ran `sm run claude --role agent-config-explicit --dir $PROJECT --agent-config /var/.../explicit-agent.toml --detach` and returned a running session line. `~/.mdx/projects/agent-config-analysis--smoke.log:21-24`
- The explicit smoke runtime received the explicit `CLAUDE_CONFIG_DIR` and `HELIOY_AGENT_NAME` values. `~/.mdx/projects/agent-config-analysis--smoke.log:25-32`
- The explicit smoke session persisted the explicit path string in `agent_config`. `~/.mdx/projects/agent-config-analysis--smoke.log:33-40`
- Focused tests passed for named resolution, explicit path resolution, missing config errors, daemon env merge into the spawn driver, and rtmd env forwarding. `~/.mdx/projects/agent-config-analysis--tests.log:1-8`, `~/.mdx/projects/agent-config-analysis--tests.log:21-24`, `~/.mdx/projects/agent-config-analysis--tests.log:41-56`

## 6. Gaps, stubs, and current limits

- `--agent-config` is parsed as a raw string, so the CLI cannot catch missing files, relative path ambiguity, invalid TOML, or invalid env value types before contacting `smd`. `crates/sm-cli/src/cli/cli_def.rs:105-106`, `crates/sm-cli/src/cli/run.rs:39-47`, `crates/sm-daemon/src/agent_config.rs:26-40`, `crates/sm-daemon/src/agent_config.rs:73-96`
- Relative explicit paths are ambiguous because path like values such as `./agent.toml` are converted with `PathBuf::from` inside the daemon, while the CLI sends the raw string unchanged. `crates/sm-daemon/src/agent_config.rs:56-71`, `crates/sm-cli/src/cli/run.rs:39-47`
- Named lookup is tied to daemon `HOME`, not `SM_HOME`, not the caller environment after daemon startup, and not the session directory. `crates/sm-daemon/src/agent_config.rs:16-24`, `crates/sm-daemon/src/agent_config.rs:49-54`
- `ResolvedAgentConfig.path` is computed but not persisted or returned; session records keep the original request string. `crates/sm-daemon/src/agent_config.rs:10-14`, `crates/sm-daemon/src/handler.rs:163-177`, `crates/sm-store/src/sqlite/sessions.rs:31-55`
- The file schema is implicit TOML value parsing, not a typed `AgentConfig` struct with a version, required fields, or generated documentation. `crates/sm-daemon/src/agent_config.rs:35-40`, `crates/sm-daemon/src/agent_config.rs:73-96`, `tools/run.toml:115-121`
- `claude_config_dir` is runtime specific in name but daemon side resolution has no runtime argument, so that field can be applied to a Codex spawn as just another env variable. `crates/sm-daemon/src/agent_config.rs:73-96`, `crates/sm-daemon/src/handler.rs:606-641`, `../runtime-matters/crates/rtm-launchers/src/codex.rs:18-20`
- MCP `session_run` schema marks only `runtime` and `role` as required, but the MCP handler requires `dir` or deprecated `workspace`. `crates/sm-cli/src/mcp/generated_schema/session_run.json:50-54`, `crates/sm-daemon/src/mcp_tools.rs:121-126`
- CLI `sm run` sends caller env, but MCP `session_run` sends an empty env, which makes `spawn_launch` fall back to daemon process env before adding agent config env. `crates/sm-cli/src/cli/run.rs:20-24`, `crates/sm-daemon/src/mcp_tools.rs:140-149`, `crates/sm-daemon/src/handler.rs:611-617`
- `RunArgs.detach` is parsed and documented, but `cli::run::run` does not read it. This is adjacent to the smoke command because current `sm run` already returns after spawning. `crates/sm-cli/src/cli/cli_def.rs:85-89`, `crates/sm-cli/src/cli/run.rs:12-14`
- The current implementation has no config effect for runtime model, prompt, instruction file, command args, isolation, image, or runtime target; only env crosses the rtmd hop. `crates/sm-daemon/src/agent_config.rs:73-96`, `crates/sm-driver/src/rtmd.rs:58-68`, `../runtime-matters/crates/rtm-core/src/types/spawn.rs:77-92`

## 7. Smallest deltas to unblock real use

### 1. Make explicit path handling deterministic

Current behavior treats `./agent.toml` as explicit but resolves it in daemon context. `crates/sm-daemon/src/agent_config.rs:56-71`, `crates/sm-cli/src/cli/run.rs:39-47`

High leverage change:

```rust
// before, sm-cli sends raw args.agent_config
agent_config: args.agent_config,

// after, sm-cli absolutizes explicit local paths before RpcRequest::Spawn
agent_config: normalize_agent_config_arg(args.agent_config.as_deref())?,
```

Implementation target: add a CLI side helper near `spawn_session` that recognizes the same path like rules, expands `~`, and canonicalizes relative paths against the caller cwd before line 46. `crates/sm-cli/src/cli/run.rs:20-47`, `crates/sm-daemon/src/agent_config.rs:56-71`

### 2. Persist the resolved config path beside the request string

Current records keep `request.agent_config`; they drop `ResolvedAgentConfig.path`. `crates/sm-daemon/src/agent_config.rs:10-14`, `crates/sm-daemon/src/handler.rs:163-177`, `crates/sm-store/src/sqlite/sessions.rs:31-55`

High leverage change:

```rust
// before
agent_config: request.agent_config,

// after sketch
agent_config: agent_config.as_ref().map(|config| config.requested.clone()),
agent_config_path: agent_config.as_ref().map(|config| config.path.clone()),
```

Implementation target: add `Session.agent_config_path`, a store migration, generated schemas, and list/get rendering. The existing migration pattern is already in `add_tmux_and_agent_config_columns`. `crates/sm-core/src/session.rs:67-89`, `crates/sm-store/src/sqlite/migrations.rs:90-94`, `crates/sm-store/src/schema.rs:1-20`

### 3. Replace dynamic TOML walking with a typed schema

Current parsing uses `toml::Value` and hand validates only `claude_config_dir` plus `[env]`. `crates/sm-daemon/src/agent_config.rs:35-40`, `crates/sm-daemon/src/agent_config.rs:73-96`

High leverage change:

```rust
#[derive(serde::Deserialize)]
struct AgentConfigToml {
    claude_config_dir: Option<String>,
    #[serde(default)]
    env: BTreeMap<String, String>,
}
```

Implementation target: parse `AgentConfigToml` in `resolve_agent_config_with_home`, keep the existing error messages, and add schema examples to the generated public docs. `crates/sm-daemon/src/agent_config.rs:26-47`, `tools/run.toml:115-121`

### 4. Make MCP `session_run` required fields truthful

The generated schema does not require `dir`, while the handler requires `dir` or `workspace`. `crates/sm-cli/src/mcp/generated_schema/session_run.json:50-54`, `crates/sm-daemon/src/mcp_tools.rs:121-126`

High leverage change:

```toml
# before
tools.session_run.params.dir.required = false

# after, if MCP should keep requiring explicit dirs
tools.session_run.params.dir.required = true
```

Implementation target: update `tools/run.toml`, regenerate schemas, and keep the deprecated `workspace` alias as optional compatibility input. `tools/run.toml:84-105`, `crates/sm-daemon/src/mcp_tools.rs:123-126`

### 5. Add one CLI integration test that proves both modes through rtmd

The daemon unit test proves env reaches a spawn driver, and the driver unit test proves env reaches rtmd. `crates/sm-daemon/tests/handler.rs:95-149`, `crates/sm-driver/tests/rtmd_spawn.rs:23-70`

High leverage change:

```rust
#[test]
fn run_agent_config_named_and_explicit_reach_runtime_env() { /* fake runtime records env */ }
```

Implementation target: add a CLI test using `DaemonFixture::start_with_runtime_path` and a fake runtime that writes selected env vars to a temp file. `crates/sm-cli/tests/common/mod.rs:27-65`, `crates/sm-cli/tests/common/mod.rs:207-228`

## Project metadata

- Language and build system: Rust workspace, edition 2024, Cargo resolver 3. `Cargo.toml:1-15`
- Workspace crates: `sm-paths`, `sm-core`, `sm-store`, `sm-driver`, `sm-daemon`, and `sm-cli`. `Cargo.toml:1-10`
- Relevant dependencies: clap, tokio, serde, rusqlite, toml, uuid, `lilo-rm-client`, and `lilo-rm-core`. `Cargo.toml:26-40`
- Runtime dependency: `smd` connects to `rtmd` through `RTM_SOCKET_PATH`, `$XDG_RUNTIME_DIR/rtm/sock`, or `~/.rtm/sock`; daemon startup probes rtmd protocol before serving. `crates/sm-paths/src/lib.rs:98-103`, `crates/sm-daemon/src/server.rs:18-30`, `crates/sm-daemon/src/server.rs:126-149`

## Open questions

- The intended long term location for named configs is not defined beyond daemon `$HOME/.agm/<name>/agent.toml`. `crates/sm-daemon/src/agent_config.rs:20-24`, `crates/sm-daemon/src/agent_config.rs:49-54`
- The intended schema for Codex specific config is not defined in the current `agent.toml` parser. `crates/sm-daemon/src/agent_config.rs:73-96`, `../runtime-matters/crates/rtm-launchers/src/codex.rs:14-20`
- The intended semantics of `--detach` are not implemented in `sm run`, so future foreground attach behavior would need to account for agent config env propagation as part of the same run path. `crates/sm-cli/src/cli/cli_def.rs:85-89`, `crates/sm-cli/src/cli/run.rs:12-14`
