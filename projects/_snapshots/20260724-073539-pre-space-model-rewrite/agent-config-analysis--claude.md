---
title: sm run --agent-config end-to-end analysis (Claude pane)
type: research
tags: [session-matters, sm-cli, agent-config, moe-claude]
summary: --agent-config is a string passed CLI→smd→agent_config.rs; resolves to env vars (CLAUDE_CONFIG_DIR + [env] table) and is folded into launch env before crossing the rtmd wire. rtmd has no agent_config concept.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

# `sm run --agent-config` — end-to-end analysis (Claude pane)

Independent MoE read. Co-investigator: Codex pane at `session-matters:helioy-tools:codebase-analyst:2:3.2`. No coordination during investigation.

Scope: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters` (HEAD = `b919b3d`, release 0.2.5). Sibling repo `runtime-matters` consulted via grep + targeted file reads where the wire crosses the boundary.

## 1. Surface

`--agent-config` is declared once and reaches two retained CLI shapes (`sm run` and `sm create session`) plus the MCP `session_run`/`agent_run` tools.

| Layer | File | Line | Decl |
|-------|------|------|------|
| Clap field | `crates/sm-cli/src/cli/cli_def.rs` | 105–106 | `#[arg(long = "agent-config", help = generated_help::SESSION_RUN_AGENT_CONFIG_HELP)] pub agent_config: Option<String>` on `SessionCreateArgs` |
| Help text | `crates/sm-cli/src/cli/generated_help.rs` | 16 | `pub const SESSION_RUN_AGENT_CONFIG_HELP: &str = "Agent config name or explicit agent.toml path.";` |
| Inheritance into `sm run` | `crates/sm-cli/src/cli/cli_def.rs` | 78–90 | `RunArgs` flattens `SessionCreateArgs` (line 79–80) |
| MCP exposure | `crates/sm-daemon/src/mcp_tools.rs` | 131 | `let agent_config = optional_string(arguments, "agent_config").map(ToString::to_string);` |
| MCP schema snapshot | `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@session_run.snap` | 10–13 | `"Agent config name resolved as ~/.agm/<name>/agent.toml, or an explicit agent.toml path."` |
| CLI help test | `crates/sm-cli/tests/cli_get_test.rs` | 71 | asserts `--agent-config` appears in `sm create session --help` output |

Allowed shape: any UTF-8 string. Clap performs no validation; an empty string is accepted at the surface but would fail resolution. The field is `Option<String>`, so `--agent-config ""` is distinct from omission (the empty string would be passed to the daemon and attempted as a resolution input).

The doc-string distinction between two modes is real, but disambiguation lives in the daemon, not at clap.

## 2. Resolution

All resolution happens server-side, in `crates/sm-daemon/src/agent_config.rs`. Total file LOC: 161, single commit history (`be655b5 feat: ship session-matters v1`, 2026-05-18).

### Entry point
`crates/sm-daemon/src/agent_config.rs:16-24` — `resolve_agent_config(requested: Option<&str>) -> Result<Option<ResolvedAgentConfig>>`:

- `None` requested → returns `Ok(None)`.
- Otherwise, reads `HOME` from env; bails with `"HOME is required for agent config resolution"` if unset (line 22).
- Delegates to `resolve_agent_config_with_home` (lines 26–47).

### Name-vs-path discriminator
`crates/sm-daemon/src/agent_config.rs:49-54` — `agent_config_path`:

```rust
fn agent_config_path(requested: &str, home: &Path) -> PathBuf {
    if is_path_like(requested) {
        return expand_home(requested, home);
    }
    home.join(".agm").join(requested).join("agent.toml")
}
```

`is_path_like` (lines 56–61) returns true if the input:
- contains `std::path::MAIN_SEPARATOR` (i.e. `/` on Unix); OR
- starts with `~`; OR
- starts with `.`; OR
- ends with `.toml`.

`expand_home` (lines 63–71) maps `~` → home, `~/foo` → home/foo, anything else verbatim.

Otherwise the daemon constructs `$HOME/.agm/<requested>/agent.toml` and reads that file.

### Filesystem locations searched
Exactly one path is checked per resolution. There is no search list and no fallback. If the file is not a regular file (`!path.is_file()`), the daemon bails immediately at line 28–33 with `"agent config not found: {requested} (looked for {path})"`.

### TOML schema (what an `agent.toml` may contain)
`crates/sm-daemon/src/agent_config.rs:73-96` — `agent_env`:

Recognized keys:
1. `claude_config_dir` (top-level, string) → emitted as `LaunchEnv { key: "CLAUDE_CONFIG_DIR", value }`.
2. `[env]` table → every `key = "value"` becomes a `LaunchEnv`; values must be strings.

Both keys are optional. Unknown keys at the top level are silently ignored. Output is sorted by `BTreeMap` insertion order (claude_config_dir first if present, then [env] in TOML order; the BTreeMap re-sorts alphabetically per the `BTreeMap` semantics in lines 74–91).

Error surface:
- `claude_config_dir` not a string → `"agent config `claude_config_dir` must be a string"` (line 78)
- `[env]` not a table → `"agent config `env` must be a table"` (line 84)
- Non-string env value → `"agent config env `{key}` must be a string"` (line 88)
- Bad TOML → `"failed to parse agent config {path}"` (line 39)
- File unreadable → `"failed to read agent config {path}"` (line 36)

### `ResolvedAgentConfig`
`crates/sm-daemon/src/agent_config.rs:10-14`:
```rust
pub struct ResolvedAgentConfig {
    pub requested: String,    // the verbatim CLI arg
    pub path: PathBuf,        // the resolved filesystem path
    pub env: Vec<LaunchEnv>,  // computed env entries
}
```

The resolved `path` is computed and threaded into `spawn_launch` but is **not persisted** anywhere visible to the caller (see §4 and §6).

## 3. Wire

Two boundaries to cross: CLI → smd (over the smd unix socket), and smd → rtmd (over `~/.rtm/sock`). Only the first carries `agent_config`.

### CLI → smd

`SpawnRequest` in `crates/sm-core/src/proto.rs:17-38`:

```rust
pub struct SpawnRequest {
    pub runtime: RuntimeKind,
    pub role: String,
    #[serde(default)] pub workspace: String,
    #[serde(default)] pub dir: Option<String>,
    #[serde(default)] pub namespace: Option<Namespace>,
    #[serde(default = "default_spawn_target")] pub target: String,
    #[serde(default)] pub agent_config: Option<String>,   // <-- line 29
    #[serde(default)] pub env: Vec<LaunchEnv>,
    #[serde(default)] pub shell_resume: Option<ShellResume>,
    #[serde(default)] pub labels: Vec<crate::Label>,
    #[serde(default)] pub force: bool,
}
```

CLI constructs it at `crates/sm-cli/src/cli/run.rs:38-55`:
```rust
RpcRequest::Spawn {
    request: SpawnRequest {
        ...
        agent_config: args.agent_config,
        env, // captured caller env (line 23)
        ...
    },
},
```
The CLI itself never touches the value. `args.agent_config` is the raw `Option<String>` straight from clap.

MCP path: `crates/sm-daemon/src/mcp_tools.rs:116-164` (`agent_run`/`session_run`) reads `agent_config` from arguments at line 131 and forwards via `handle_direct`. Same `SpawnRequest` shape.

### smd → rtmd

`crates/sm-driver/src/rtmd.rs:48-80` — `RtmdDriver::spawn` constructs a *different* `SpawnRequest` (the one from `lilo_rm_core`/runtime-matters):

```rust
let payload = self.client
    .spawn(SpawnRequest {
        session_id,
        runtime: runtime_kind(launch.runtime),
        env: launch.env.clone(),
        cwd: launch.cwd.clone(),
        target: runtime_target(&launch.target)?,
        force: launch.force,
        shell_resume: launch.shell_resume.clone(),
    })
    .await
```

Cross-checked against the rtm-core type at `runtime-matters/crates/rtm-core/src/types/spawn.rs:77-92` (read via direct file inspection; runtime-matters is not indexed under session-matters' fmm scope):

```rust
pub struct SpawnRequest {
    pub session_id: Uuid,
    pub runtime: RuntimeKind,
    #[serde(default)] pub isolation: IsolationPolicy,
    #[serde(default, skip_serializing_if = "Option::is_none")] pub image: Option<String>,
    #[serde(default)] pub env: Vec<LaunchEnv>,
    pub cwd: std::path::PathBuf,
    pub target: SpawnTarget,
    #[serde(default, skip_serializing_if = "is_false")] pub force: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")] pub shell_resume: Option<ShellResume>,
}
```

**There is no `agent_config` field on the rtmd wire.** The runtime-matters codebase contains zero references to `agent_config`, `agent-config`, `agent.toml`, or `.agm` (verified by full grep across `runtime-matters/`). rtmd treats the result solely as opaque env vars.

### Persistence

`Session.agent_config: Option<String>` at `crates/sm-core/src/session.rs:83` stores the **raw requested string**, not the resolved path. Backed by a TEXT column added by migration `add_tmux_and_agent_config_columns` at `crates/sm-store/src/sqlite/migrations.rs:90-94`.

## 4. Runtime effect

`crates/sm-daemon/src/handler.rs:132-212` (`DaemonState::spawn`):

1. Line 142: `let agent_config = resolve_agent_config(request.agent_config.as_deref())?;`
   Any resolution error aborts the spawn before any rtmd traffic, identity authorization, or session record commit.
2. Line 143: `let launch = spawn_launch(id, &request, agent_config.as_ref());`
3. Line 176: `agent_config: request.agent_config` — the unresolved string is mirrored into `Session`.

`spawn_launch` (`crates/sm-daemon/src/handler.rs:606-641`):

```rust
fn spawn_launch(
    id: Uuid,
    request: &SpawnRequest,
    agent_config: Option<&ResolvedAgentConfig>,
) -> SpawnLaunch {
    let mut env = request.env.clone();
    if env.is_empty() {
        env = capture_caller_env();             // daemon-side fallback
    }
    if let Some(config) = agent_config {
        merge_env(&mut env, config.env.clone()); // agent_config wins on key collision
    }
    env.retain(|item| !item.key.starts_with("HELIOY_SESSION_"));
    upsert_env(&mut env, LaunchEnv::new("HELIOY_SESSION_ID", id.to_string()));
    upsert_env(&mut env, LaunchEnv::new("HELIOY_SESSION_ROLE", request.role.clone()));
    upsert_env(&mut env, LaunchEnv::new("HELIOY_SESSION_WORKSPACE", request.workspace.clone()));
    ...
    SpawnLaunch { runtime, cwd, target, env, shell_resume, force }
}
```

Layering, lowest to highest priority:
1. `request.env` from the CLI (`lilo_rm_core::capture_caller_env()` snapshot taken at `crates/sm-cli/src/cli/run.rs:23`), or daemon-side caller env if request env is empty.
2. `agent_config.env` (merged via `merge_env` → `upsert_env`, `crates/sm-daemon/src/handler.rs:658-670`): agent config **overrides** caller env on key collision.
3. `HELIOY_SESSION_ID`, `HELIOY_SESSION_ROLE`, `HELIOY_SESSION_WORKSPACE`: injected last via `upsert_env`; any prior `HELIOY_SESSION_*` keys are stripped at line 618. These always win.

Net: an `agent.toml` can set `CLAUDE_CONFIG_DIR`, and any other env var the operator wants, on top of the inherited caller env, but cannot override the three `HELIOY_SESSION_*` keys. It cannot influence `runtime`, `role`, `dir`, `target`, `force`, `isolation`, or `image` — those are fixed at the CLI surface or hard-coded in `RtmdDriver::spawn`.

## 5. Works today

Verified by `crates/sm-daemon/tests/handler.rs:95-149` (`agent_config_env_reaches_spawn_driver`): an explicit `.toml` path round-trips end-to-end through the handler, the env vars reach the fake spawn driver, and the raw requested path is persisted on `Session.agent_config`.

### Minimum end-to-end invocation (explicit path)

```sh
cat > /tmp/demo.toml <<'EOF'
claude_config_dir = "/tmp/claude-home"

[env]
HELIOY_AGENT_NAME = "demo"
EOF

sm run claude \
    --role engineer \
    --dir "$PWD" \
    --agent-config /tmp/demo.toml
```

Observable outcome:
- A session record is created with `agent_config = "/tmp/demo.toml"` (verifiable via `sm get session id:<uuid>`; CLI test at `crates/sm-cli/tests/cli_get_test.rs:182` confirms field round-trip).
- The Claude runtime is spawned with `CLAUDE_CONFIG_DIR=/tmp/claude-home` and `HELIOY_AGENT_NAME=demo` plus the standard `HELIOY_SESSION_*` trio.

### Minimum named lookup

```sh
mkdir -p ~/.agm/demo-agent
cat > ~/.agm/demo-agent/agent.toml <<'EOF'
claude_config_dir = "/tmp/claude-home"
EOF

sm run claude --role engineer --dir "$PWD" --agent-config demo-agent
```

Observable outcome: same as above, with `Session.agent_config = "demo-agent"` (the name, not the resolved path). Verified by unit test `resolves_named_agent_config_from_home_agm` at `crates/sm-daemon/src/agent_config.rs:103-130`.

> Note: `~/.agm/` does **not** exist on this machine. Any unprepared `--agent-config <name>` invocation will fail with `"agent config not found: <name> (looked for /Users/alphab/.agm/<name>/agent.toml)"`.

### `sm create session` parity

`sm create session claude --role engineer --dir "$PWD" --agent-config /tmp/demo.toml` works identically (`create_session` at `crates/sm-cli/src/cli/run.rs:16-18` is just `spawn_session(args, "headless", false)`). Round-trip equality is asserted at `crates/sm-cli/tests/cli_get_test.rs:182` (`agent_config` field matches between `sm run` and `sm create session`).

### MCP

```json
{"name": "session_run", "arguments": {"runtime": "claude", "role": "engineer", "dir": "/abs/path", "agent_config": "/tmp/demo.toml"}}
```

Schema documented at `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@session_run.snap:10-13`.

## 6. Gaps / stubs / TODOs

Nothing is `unimplemented!()` or `todo!()`. The shape is small and intentional. The gaps are scope, polish, and documentation.

| # | Gap | Location |
|---|-----|----------|
| 1 | `~/.agm/` is not bootstrapped or seeded anywhere. No `examples/` or `docs/` directory exists in `session-matters/` (verified by `ls`). First-time users have no scaffold. | repo root (absent) |
| 2 | Resolved `ResolvedAgentConfig.path` is computed (line 44 `crates/sm-daemon/src/agent_config.rs`) but discarded. `Session.agent_config` only holds the verbatim CLI string. There is no field, log line, or response payload exposing which file was actually read. | `crates/sm-daemon/src/handler.rs:176`; `crates/sm-core/src/session.rs:83` |
| 3 | The TOML schema reads only `claude_config_dir` and `[env]`. Nothing in `agent.toml` can set `role`, `runtime`, `target`, `dir`, `isolation`, `image`, or the rtmd `isolation`/`image` fields that exist on the rtm-core side. The "named profile" value-add is therefore narrow: `claude_config_dir` plus arbitrary env. | `crates/sm-daemon/src/agent_config.rs:73-96` |
| 4 | `is_path_like` (line 56–61) ends-with `.toml` rule treats a name like `tools.toml` as a relative path resolved against CWD (via `PathBuf::from(value)` at line 70). Footgun: a user picks a name with a `.toml` suffix and gets unexpected behavior. Also: bare relative paths without `/` or leading `.` will *not* trigger `is_path_like` even if the file exists in CWD. | `crates/sm-daemon/src/agent_config.rs:56-61, 63-71` |
| 5 | The CLI help string is shorter than the MCP description. CLI says `"Agent config name or explicit agent.toml path."`; MCP says `"Agent config name resolved as ~/.agm/<name>/agent.toml, or an explicit agent.toml path."` Operators have to read the MCP schema (or source) to discover the `~/.agm/` convention. | `crates/sm-cli/src/cli/generated_help.rs:16` vs. snap file line 11 |
| 6 | `claude_config_dir` special-casing hard-codes one runtime's pattern. Codex (the other supported runtime per `RuntimeKind`) has no analogous convenience. The mechanism degrades to "set env yourself in `[env]`" for any non-Claude runtime, which makes the `claude_config_dir` key feel arbitrary. | `crates/sm-daemon/src/agent_config.rs:75-80` |
| 7 | No CLI integration test exercises the resolution error path. `missing_agent_config_is_structured_error` (lines 153–160) covers the daemon function in isolation; nothing asserts the error survives `RpcResponse::Error` and renders cleanly through `sm run` / `sm create session`. | `crates/sm-daemon/src/agent_config.rs:153-160` |
| 8 | CHANGELOG (`session-matters/CHANGELOG.md`) and README do not document `--agent-config` outside the MCP tool table (lines 111–112). The feature shipped silently in `be655b5 feat: ship session-matters v1`. | `CHANGELOG.md`, `README.md` |
| 9 | No `Default` or empty fallback: if a user invokes `sm run claude --role x --dir $PWD` without `--agent-config`, the runtime gets only the captured caller env and `HELIOY_SESSION_*`. There is no project-level or namespace-level default agent profile. Each call must opt in by name or path. | `crates/sm-daemon/src/handler.rs:142` |
| 10 | `[env]` keys collide silently with `HELIOY_SESSION_*` namespace if an operator tries to override them. The strip-then-upsert at line 618 guarantees `HELIOY_SESSION_*` wins, but no warning or error tells the operator they were ignored. | `crates/sm-daemon/src/handler.rs:618` |

Adjacent observation (out of scope for this brief, flagged for context): `RunArgs.detach` (cli_def.rs:88) is parsed by clap but `crates/sm-cli/src/cli/run.rs:12-14` passes only `args.session`, `args.target`, `args.force` to `spawn_session`. `--detach` is silently ignored. Not an agent_config issue, but in the same neighborhood.

## 7. Smallest deltas to unblock real use

Ranked by leverage. Each is local, low-risk, and falls below the 700-LOC refactor threshold.

### D1. Persist + surface the resolved path (highest leverage)

**Problem**: operators cannot tell which file was used. Debugging "wrong agent" is filesystem archaeology.

**Change**:
- `crates/sm-daemon/src/handler.rs:176` — when `agent_config.is_some()`, set `Session.agent_config = Some(resolved.path.display().to_string())` instead of `request.agent_config`. The verbatim request is recoverable from the path; the path is *not* recoverable from a bare name.

Before:
```rust
agent_config: request.agent_config,
```
After:
```rust
agent_config: agent_config
    .as_ref()
    .map(|r| r.path.display().to_string())
    .or(request.agent_config),
```

Update the snapshot test `crates/sm-daemon/tests/handler.rs:130-133` to assert the resolved path. Update `crates/sm-cli/tests/cli_get_test.rs:182` similarly (`agent_config` field on `sm get session` now reflects the resolved path; the `sm run` and `sm create session` outputs already match each other).

### D2. Bring CLI help into parity with MCP

**Problem**: discoverability cliff. `sm run --help` mentions only "name or path"; MCP knows about `~/.agm/<name>/agent.toml`.

**Change**: `crates/sm-cli/src/cli/generated_help.rs:16`

Before:
```rust
pub const SESSION_RUN_AGENT_CONFIG_HELP: &str = "Agent config name or explicit agent.toml path.";
```
After:
```rust
pub const SESSION_RUN_AGENT_CONFIG_HELP: &str =
    "Agent config name resolved as ~/.agm/<name>/agent.toml, or an explicit agent.toml path. \
     TOML keys: claude_config_dir (string), [env] (table of strings).";
```

Then re-run `cargo insta accept` for the MCP snapshot (or align both via a single source — the snap already pulls from this constant if the generator does, which I have not verified).

### D3. Tighten `is_path_like` for the `.toml` footgun

**Problem**: `sm run claude --role x --dir $PWD --agent-config tools.toml` will look for `tools.toml` in CWD, not in `~/.agm/tools.toml/agent.toml`. Surprising.

**Change**: `crates/sm-daemon/src/agent_config.rs:56-61`

Drop the `ends_with(".toml")` clause; treat the `.toml` extension as a path indicator only when paired with a path separator. The path mode then becomes "contains `/`, starts with `~`, or starts with `.`" — explicit, no ambiguous middle ground.

Before:
```rust
fn is_path_like(value: &str) -> bool {
    value.contains(std::path::MAIN_SEPARATOR)
        || value.starts_with('~')
        || value.starts_with('.')
        || value.ends_with(".toml")
}
```
After:
```rust
fn is_path_like(value: &str) -> bool {
    value.contains(std::path::MAIN_SEPARATOR)
        || value.starts_with('~')
        || value.starts_with('.')
}
```

Add a unit test in the `tests` module (lines 99–161) asserting `tools.toml` resolves to `~/.agm/tools.toml/agent.toml`, not to a relative file.

> Note: this is a behavior change. The current implementation accepts bare `agent.toml` and uses CWD. The MoE conversation should decide if that's load-bearing for any caller; from grep, it is not.

### D4. CLI end-to-end test for the not-found error

**Problem**: error surface is tested at the function level only.

**Change**: add a test in `crates/sm-cli/tests/cli_get_test.rs` (or a new test file) that invokes `sm run claude --role x --dir $TMPDIR --agent-config does-not-exist` against the `DaemonFixture` and asserts the error message contains `agent config not found: does-not-exist`.

This guards the `RpcResponse::Error` → CLI render path that is currently untested.

### D5. Seed `~/.agm/` from `sm doctor` or as a one-shot helper

**Problem**: cold start UX. The named-lookup path is empty by default.

Two cheap options:
1. Have `sm doctor` (`crates/sm-cli/src/cli/doctor.rs`) report `~/.agm/` status: exists, contents (names), and a hint message if empty.
2. Ship `examples/agent.toml` in-repo with comments documenting both recognized keys, and a CLAUDE.md or README pointer to it.

Either is < 50 LOC.

### D6. Broaden the TOML schema (lowest urgency, highest design weight)

**Problem**: a named profile that can only set env is barely a profile.

A non-breaking expansion would let `agent.toml` set *defaults* for `role`, `runtime`, `target`, `dir`, `force`, `labels`, and `isolation`. CLI args still override on collision (so `sm run claude --agent-config base --role override` works). Implementation:

- Extend `ResolvedAgentConfig` with optional default fields.
- In `DaemonState::spawn` (around line 137–143), apply defaults from `agent_config` to `request` for any field that is currently empty/`None`/default-valued.
- This is the only delta that touches more than one file and should land behind a brainstorm; D1–D5 do not need one.

---

## Method notes

- Tools used: `fmm_search`, `fmm_list_files`, `fmm_file_outline`, `fmm_read_symbol`, supplemented by `grep` and `Read` for the runtime-matters crate (not indexed by session-matters' `.fmm.db`).
- Snapshots inspected directly: `mcp_schema_snapshot_test__mcp_tool@session_run.snap` and `runtime_contract_snapshot_test__rtmd_payload_json_shapes_are_snapshotted.snap`.
- Git blame on `agent_config.rs:49-54` returned a single commit (`be655b5`, 2026-05-18), so the implementation is the original v1 ship; no follow-up edits.
- Cross-repo claims (no agent_config concept in runtime-matters) verified by `grep -rni 'agent.toml|agent_config|agent-config' runtime-matters/` returning zero hits.
