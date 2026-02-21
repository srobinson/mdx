# auth-token-debug, Codex

## 1. Env-passthrough audit, host

Host isolation has one important distinction: implicit inherited env is filtered, explicit `--env` is not.

The CLI builds the spawn env in `spawn_env`. Host isolation starts with `capture_caller_env()`, while Docker starts empty (crates/rtm-cli/src/cli/spawn.rs:74-78). The same function then applies every explicit `--env` override with `upsert_launch_env` (crates/rtm-cli/src/cli/spawn.rs:79-83). `--env KEY=value` is accepted as a literal pair, and `--env KEY` reads the key from the caller env (crates/rtm-cli/src/cli/spawn.rs:85-99). Empty keys are rejected, but there is no auth key filter in this explicit path (crates/rtm-cli/src/cli/spawn.rs:101-106).

The implicit host capture does filter Claude runtime state. `capture_caller_env()` calls `capture_env_from_os()` (crates/rtm-core/src/spawn_context.rs:46-64). `capture_env_from()` drops denied keys (crates/rtm-core/src/spawn_context.rs:69-80). The exact denylist includes runtime coordination keys (crates/rtm-core/src/spawn_context.rs:10-20), and the denylist prefixes include `CLAUDE_CODE_` and `CLAUDE_PLUGIN_` (crates/rtm-core/src/spawn_context.rs:25-25). Therefore a caller environment variable named `CLAUDE_CODE_OAUTH_TOKEN` is intentionally stripped unless it is named explicitly with `--env CLAUDE_CODE_OAUTH_TOKEN` or set literally with `--env CLAUDE_CODE_OAUTH_TOKEN=...`.

After the launcher receives the request, the Claude launcher returns `crate::runtime_env(request)` unchanged except for normal launcher additions (crates/rtm-launchers/src/claude.rs:14-20). `runtime_env()` starts from `request.env.clone()` and upserts `HELIOY_SESSION_ID`, `HELIOY_RUNTIME`, `RTM_SESSION_ID`, and `RTM_RUNTIME_KIND` (crates/rtm-launchers/src/lib.rs:55-74). Those additions do not shadow `CLAUDE_CODE_OAUTH_TOKEN`.

The daemon stores the `LaunchSpec` for the shim without filtering it (crates/rtm-daemon/src/server/spawn.rs:39-45). The shim later asks for the launch spec by session id and receives that same stored value (crates/rtm-daemon/src/server/spawn.rs:112-122). The runtime process is created from the launch spec: `runtime_command()` builds `Command::new(launch.command()?)`, adds args, applies launch env and cwd, then spawns (crates/rtm-cli/src/cli/shim.rs:92-98, crates/rtm-cli/src/cli/shim.rs:33-42). `apply_launch_env_cwd()` calls `env_clear()` and then writes every `LaunchSpec.env` entry into the runtime `Command` (crates/rtm-cli/src/cli/shim.rs:125-131). There is no allowlist or auth scrub at this step.

For tmux targets, only the shim env travels through tmux `respawn-pane`; runtime env travels later through the daemon socket as the stored `LaunchSpec`. The tmux shim env contains only `RTM_SOCKET_PATH` (crates/rtm-daemon/src/shim_socket.rs:139-147), and `respawn-pane` appends only that provided shim env (crates/rtm-platform/src/tmux.rs:201-222). The runtime env is still applied by the shim after `ShimLaunch`.

Conclusion for host isolation: `CLAUDE_CODE_OAUTH_TOKEN` reaches the spawned `claude` process if and only if it is explicit in the spawn request. It is stripped from implicit host env capture by the `CLAUDE_CODE_` denylist prefix.

## 2. Env-passthrough audit, docker

Docker isolation starts with no inherited env and then applies explicit `--env` overrides (crates/rtm-cli/src/cli/spawn.rs:74-83). The request sent to the daemon includes that `env` vector without any Docker specific transform in the CLI (crates/rtm-cli/src/cli/spawn.rs:38-72).

The Docker launch wrapper receives the launcher env through `LaunchSpec.env`. `docker_run_argv()` builds the base Docker argv, adds `--init` unless the `own-init` profile is selected, appends env args, then appends the image (crates/rtm-daemon/src/docker_argv.rs:48-64). `append_env_args()` emits a `--env` flag for every `LaunchEnv` entry and formats it as `KEY=value` (crates/rtm-daemon/src/docker_argv.rs:128-133). The fixed cwd bind mount and workdir are separate Docker args (crates/rtm-daemon/src/docker_argv.rs:66-89). There is no auth key filter in the Docker argv builder.

The existing regression test already covers this path. `docker_spawn_env_flag_reaches_container_and_runtime` passes `CLAUDE_CODE_OAUTH_TOKEN`, waits until Docker container env contains it, then waits until the runtime output contains it (crates/rtm-cli/tests/spawn_target.rs:196-259). It also proves duplicate explicit env takes the last value and that host `HOME`, `USER`, and `SHELL` are not implicitly inherited in Docker isolation (crates/rtm-cli/tests/spawn_target.rs:227-248).

Conclusion for Docker isolation: explicit `--env CLAUDE_CODE_OAUTH_TOKEN=...` reaches Docker as `--env CLAUDE_CODE_OAUTH_TOKEN=...`. No rtm code strips or renames it.

## 3. Empirical sentinel test

I ran an isolated `target/debug/rtm` daemon with a temporary socket, database, and home, then spawned Docker isolation into a temporary tmux pane using a sentinel value. The real token was never used.

Command shape:

```bash
sentinel='sentinel-marker-12345'
work="$(mktemp -d /tmp/rtm-auth-token-codex.XXXXXX)"
export RTM_SOCKET_PATH="$work/sock"
export RTM_DB_PATH="$work/db.sqlite"
export RTM_HOME="$work/home"
export RTM_SHIM_PATH="$PWD/target/debug/rtm"
export RTM_DOCKER_ALLOW_ARM64_MANIFEST_ESCAPE=1
export RTM_DOCKER_ALLOW_ROOT_IMAGE_USER=1
./target/debug/rtm daemon start >"$work/daemon.log" 2>&1 &

session_id="$(uuidgen | tr '[:upper:]' '[:lower:]')"
tmux new-session -d -s "rtm-auth-token-codex-top-$$" 'sleep 600'
target="$(tmux display-message -p -t "rtm-auth-token-codex-top-$$" '#S:#I.#P')"
./target/debug/rtm spawn \
  --runtime claude \
  --session-id "$session_id" \
  --target "tmux:$target" \
  --isolation docker \
  --image runtime-matters-claude:local \
  --cwd "$PWD" \
  --env "CLAUDE_CODE_OAUTH_TOKEN=$sentinel"
container="rtm-$session_id"
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container" \
  | grep '^CLAUDE_CODE_OAUTH_TOKEN='
docker top "$container" eww | awk 'NR==1 || /CLAUDE_CODE_OAUTH_TOKEN=/'
```

Result:

```text
session_id=7170559d-eec0-4da9-a4cf-c0b157349a64
container=rtm-7170559d-eec0-4da9-a4cf-c0b157349a64
inspect_env=CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345
docker_top_env_lines:
PID TTY STAT TIME COMMAND
37641 ? Ss 0:00 /sbin/docker-init -- claude ... CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345 ... HOME=/home/rtm
37662 ? Rl+ 0:00 claude ... CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345 ... HOME=/home/rtm
```

The sentinel was present in the container config and in the live `claude` process environment. Cleanup killed the rtm session, Docker container, tmux session, and temporary daemon.

## 4. What `claude` does with `CLAUDE_CODE_OAUTH_TOKEN`

Local binary inspected:

```text
/Users/alphab/.local/bin/claude -> /Users/alphab/.local/share/claude/versions/2.1.149
file: Mach-O 64-bit executable arm64
version: 2.1.149 (Claude Code)
```

The binary is not an unpacked JS file on this host. `strings -a /Users/alphab/.local/share/claude/versions/2.1.149` still exposes auth source names. Relevant patterns found:

- `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR` appears near `OAuth token`, `CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR`, `CLAUDE_CONFIG_DIR`, and secure storage strings.
- `CLAUDE_CODE_OAUTH_TOKEN` appears in auth source lists beside `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR`, `CCR_OAUTH_TOKEN_FILE`, `profile`, and `claude.ai`.
- Nearby strings include `tokenSource`, `subscription`, and managed login errors that mention env var tokens and missing `user:profile` scope.
- The binary also contains `No OAuth token available`, `OAuth token has been revoked`, and bearer auth strings.

Empirical consumption test with an empty temp config:

```bash
HOME="$tmp" CLAUDE_CONFIG_DIR="$tmp/config" \
CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345 \
/Users/alphab/.local/bin/claude -p ping
```

Result:

```text
exit=1
stdout=Failed to authenticate. API Error: 401 Invalid bearer token
stderr=
```

This proves the local Claude binary reads `CLAUDE_CODE_OAUTH_TOKEN` at startup and sends it as an OAuth bearer credential. A placeholder Keychain shaped JSON string in the same env var produced the same `401 Invalid bearer token` result, which is consistent with the env var being a bearer token input, not a credentials JSON input.

## 5. Keychain shape, metadata only

Metadata command, without `-w`:

```bash
security find-generic-password -s 'Claude Code-credentials' -a alphab
```

Result shape:

```text
keychain: "/Users/alphab/Library/Keychains/login.keychain-db"
class: "genp"
"acct"<blob>="alphab"
"svce"<blob>="Claude Code-credentials"
"type"<uint32>=<NULL>
created: 20260517194635Z
modified: 20260522041137Z
```

I also ran a local redacted shape check that read the password value but printed only structure, not secret values. It reported an 831 byte JSON object with top level keys:

```text
claudeAiOauth,mcpOAuth
```

The `claudeAiOauth` object contains:

```text
accessToken: string
refreshToken: string
expiresAt: int
scopes: list[str]
subscriptionType: string
rateLimitTier: string
```

No token value was printed or written to disk.

## 6. Diagnosis

The rtm env plumbing works for explicit env. Host isolation only strips `CLAUDE_CODE_OAUTH_TOKEN` when it is inherited implicitly from the caller env, because implicit host capture denies the `CLAUDE_CODE_` prefix (crates/rtm-core/src/spawn_context.rs:25-25, crates/rtm-core/src/spawn_context.rs:69-80). Explicit `--env CLAUDE_CODE_OAUTH_TOKEN=...` or `--env CLAUDE_CODE_OAUTH_TOKEN` is reinserted after that filter (crates/rtm-cli/src/cli/spawn.rs:74-83, crates/rtm-cli/src/cli/spawn.rs:85-99). Docker isolation starts empty and forwards explicit env as Docker `--env` flags (crates/rtm-cli/src/cli/spawn.rs:74-83, crates/rtm-daemon/src/docker_argv.rs:128-133). The sentinel test confirmed the variable in the live Docker `claude` process.

The likely failure is value shape. The macOS Keychain item is a JSON credentials blob with `claudeAiOauth.accessToken`, `refreshToken`, `expiresAt`, and other metadata. `CLAUDE_CODE_OAUTH_TOKEN` is consumed by Claude as a bearer token. Passing the whole Keychain JSON blob, or a stale `accessToken`, will not authenticate. Mounting `~/.claude` into Docker also does not provide the macOS Keychain secret, so it does not skip login by itself.

Other possible failure modes:

1. The access token is expired. The Keychain JSON has `expiresAt`, but a raw env bearer does not include refresh behavior.
2. The token lacks scopes required by managed org checks. Claude binary strings mention failures when an env token cannot fetch profile information or lacks `user:profile` scope.
3. Interactive mode may present a login prompt for an invalid env token, while `claude -p` reports `401 Invalid bearer token`. Both point to auth rejection, not rtm env loss.

## 7. Smallest fix

Do not pass the whole Keychain password JSON as `CLAUDE_CODE_OAUTH_TOKEN`. Pass only the raw access token nested at `claudeAiOauth.accessToken`.

For a one off spawn, the shape is:

```bash
CLAUDE_CODE_OAUTH_TOKEN="$(
  security find-generic-password -s 'Claude Code-credentials' -a alphab -w \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["claudeAiOauth"]["accessToken"])'
)"
rtm spawn ... --env CLAUDE_CODE_OAUTH_TOKEN
```

The command above is shape only. Do not paste the resulting value into chat, logs, git, or a shared `agent.toml`.

If using `agent.toml` and it only supports literal `[env]`, the smallest config shape is:

```toml
[env]
CLAUDE_CODE_OAUTH_TOKEN = "<claudeAiOauth.accessToken only, not the full JSON blob>"
```

That is operationally fragile because the access token expires. A safer implementation is to compute the env at spawn time from Keychain, parse `claudeAiOauth.accessToken`, and avoid writing the token to disk. If long running sessions need refresh, a raw access token env may still fail after expiry; then the correct fix is an explicit credential bridge that can refresh or a container native Claude login, not a static env copy.

## Verification

- `fmm validate` passed: all 135 indexed files are current.
- Repo remained read only: `git status --short` was clean.
- Docker sentinel test used only `sentinel-marker-12345`.
- Keychain output in this document contains metadata and structural field names only, not secret values.
