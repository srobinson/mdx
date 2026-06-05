---
title: Why CLAUDE_CODE_OAUTH_TOKEN passthrough fails to skip Claude login
type: research
tags: [runtime-matters, claude, oauth, env-passthrough, auth, denylist, alp-2643, moe, claude-pane]
summary: Plumbing is sound for explicit `--env` overrides; CLAUDE_CODE_OAUTH_TOKEN is a long-lived setup-token (inference-only). Keychain stores a different OAuth session JSON. Root cause is a shape mismatch and a mode mismatch, not a passthrough bug.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

# Why CLAUDE_CODE_OAUTH_TOKEN passthrough fails to skip Claude login

Pane A (Claude) of MoE pair. Peer is Codex. Independent analysis. Read-only on repos; sentinel-only secret values.

## TL;DR

- **Plumbing is correct** for explicit `--env CLAUDE_CODE_OAUTH_TOKEN=…` in both host and docker isolation. No filter strips it on the way to the runtime process.
- **Caller-env capture is denylisted** (`CLAUDE_CODE_*` prefix dropped) so the rtm CLI's own shell env never carries the token into LaunchSpec.env — only the explicit `--env` override does.
- **`CLAUDE_CODE_OAUTH_TOKEN` is a long-lived "setup-token"**, not the OAuth session credential stored in the macOS Keychain. The Keychain entry `Claude Code-credentials` holds a JSON blob `{accessToken, refreshToken, expiresAt, scopes, subscriptionType, rateLimitTier}`. Passing the Keychain's `accessToken` (or the JSON itself) as `CLAUDE_CODE_OAUTH_TOKEN` is a **shape mismatch**.
- Even when the env var is correctly populated by `claude setup-token`, the binary explicitly limits it to **inference-only** mode — interactive TUI features and Remote Control still want the full OAuth login flow.
- **Smallest fix**: in `agent.toml [env]`, set `CLAUDE_CODE_OAUTH_TOKEN` to the output of `claude setup-token` (run once on the host, captured as a 1-year token). For interactive spawns that need a full login, env-var auth will not skip the login screen by design.

---

## 1. Env-passthrough audit (host isolation)

### Capture path

`crates/rtm-cli/src/cli/spawn.rs:74-83` — `spawn_env`:

```rust
fn spawn_env(isolation: &IsolationPolicy, overrides: Vec<String>) -> Result<Vec<LaunchEnv>> {
    let mut env = match isolation {
        IsolationPolicy::Host => lilo_rm_core::capture_caller_env(),
        IsolationPolicy::Docker(_) => Vec::new(),
    };
    for value in overrides {
        upsert_launch_env(&mut env, parse_spawn_env(value)?);
    }
    Ok(env)
}
```

For host isolation: the caller's shell env is captured first, then `--env` overrides are layered on top via `upsert_launch_env`.

### Denylist applied during caller-env capture

`crates/rtm-core/src/spawn_context.rs:10-25`:

```rust
pub const CALLER_ENV_DENYLIST: &[&str] = &[
    "CLAUDECODE", "TMUX", "TMUX_PANE",
    "RTM_SOCKET_PATH", "RTM_DB_PATH",
    "HELIOY_SESSION_ID", "HELIOY_RUNTIME",
    "RTM_SESSION_ID", "RTM_RUNTIME_KIND",
];

pub const CALLER_ENV_DENYLIST_PREFIXES: &[&str] = &["CLAUDE_CODE_", "CLAUDE_PLUGIN_"];
```

`is_denied` (`spawn_context.rs:82-89`) filters by exact name AND by prefix. **Any caller env var starting with `CLAUDE_CODE_` is dropped during automatic capture** — including `CLAUDE_CODE_OAUTH_TOKEN`. This is intentional: prevents the calling Claude instance from leaking its own session into a spawned runtime.

### Override path bypasses the denylist

`crates/rtm-cli/src/cli/spawn.rs:85-99` — `parse_spawn_env`:

```rust
fn parse_spawn_env(value: String) -> Result<LaunchEnv> {
    if let Some((key, explicit_value)) = value.split_once('=') {
        return spawn_env_entry(key, explicit_value);
    }
    if value.is_empty() {
        bail!("spawn env key cannot be empty");
    }
    let caller_value = std::env::var_os(&value)
        .ok_or_else(|| anyhow::anyhow!("spawn env {value} is not set in caller environment"))?;
    Ok(LaunchEnv::new(value, caller_value.to_string_lossy().into_owned()))
}
```

No denylist check. `--env CLAUDE_CODE_OAUTH_TOKEN=…` and `--env CLAUDE_CODE_OAUTH_TOKEN` (read-from-caller) both bypass the prefix filter.

`upsert_launch_env` (`crates/rtm-core/src/launcher.rs:22-28`):

```rust
pub fn upsert_launch_env(env: &mut Vec<LaunchEnv>, next: LaunchEnv) {
    if let Some(existing) = env.iter_mut().find(|entry| entry.key == next.key) {
        *existing = next;
    } else {
        env.push(next);
    }
}
```

Pure upsert by key. No filter. The override lands in LaunchSpec.env.

### Shim env application

`crates/rtm-cli/src/cli/shim.rs:118-131` — `apply_launch_env_cwd`:

```rust
fn apply_launch_env_cwd(command: &mut Command, launch: &LaunchSpec) {
    command.env_clear();
    for env in &launch.env {
        command.env(&env.key, &env.value);
    }
    command.current_dir(&launch.cwd);
}
```

`env_clear()` wipes inherited env, then `launch.env` is layered exactly. Doc comment (`shim.rs:118-124`):

> Without this, the runtime would inherit the shim's bootstrap env (`RTM_SOCKET_PATH`) and the daemon's process env, defeating the denylist applied at capture time. **LaunchSpec.env is the authoritative source of truth for the runtime.**

There's a regression test at `shim.rs:206-243` (`apply_launch_env_cwd_clears_pre_existing_env_on_command`) that proves: sentinel env in `LaunchSpec.env` reaches the child; pre-existing process env does not.

### Launcher additive keys

`crates/rtm-launchers/src/lib.rs:55-74` — `runtime_env`:

```rust
pub(crate) fn runtime_env(request: &SpawnRequest) -> Vec<LaunchEnv> {
    let mut env = request.env.clone();
    upsert_launch_env(&mut env, LaunchEnv::new("HELIOY_SESSION_ID", ...));
    upsert_launch_env(&mut env, LaunchEnv::new("HELIOY_RUNTIME", ...));
    upsert_launch_env(&mut env, LaunchEnv::new("RTM_SESSION_ID", ...));
    upsert_launch_env(&mut env, LaunchEnv::new("RTM_RUNTIME_KIND", ...));
    env
}
```

Only adds 4 keys (`HELIOY_SESSION_ID`, `HELIOY_RUNTIME`, `RTM_SESSION_ID`, `RTM_RUNTIME_KIND`). No subtraction, no rename.

### Verdict: host

`--env CLAUDE_CODE_OAUTH_TOKEN=…` survives all the way to the spawned claude process. **No filter strips it.** The user's prior empirical observation that `CLAUDE_CONFIG_DIR` survives (per the brief) is consistent: that key is not on the denylist, and the override path doesn't filter regardless.

## 2. Env-passthrough audit (docker isolation)

### Capture path

Same `spawn_env` as above (`crates/rtm-cli/src/cli/spawn.rs:74-83`). The crucial branch:

```rust
IsolationPolicy::Docker(_) => Vec::new(),
```

For docker, the caller env is **not** captured at all — LaunchSpec.env starts empty. **The denylist is irrelevant on the docker path** because there's nothing to filter; only `--env` overrides populate the request env.

### Argv assembly

`crates/rtm-daemon/src/docker_argv.rs:48-64` — `docker_run_argv` (the consumption site for `LaunchSpec.env`):

```rust
fn docker_run_argv(
    session_id: Uuid,
    profile: &IsolationProfile,
    image: &str,
    launch: &LaunchSpec,
    tmux_target: bool,
    docker_command: &str,
) -> Vec<String> {
    let cwd = path_arg(&launch.cwd);
    let mut argv = docker_run_base_argv(session_id, cwd, tmux_target, docker_command);
    if profile.name.as_deref() != Some("own-init") {
        argv.push("--init".to_owned());
    }
    append_env_args(&mut argv, &launch.env);
    argv.push(image.to_owned());
    argv
}
```

`append_env_args` (`crates/rtm-daemon/src/docker_argv.rs:128-133`):

```rust
fn append_env_args(argv: &mut Vec<String>, env: &[LaunchEnv]) {
    for entry in env {
        argv.push("--env".to_owned());
        argv.push(format!("{}={}", entry.key, entry.value));
    }
}
```

Every LaunchEnv entry becomes a `--env KEY=VALUE` flag on `docker run`. **No filter, no rename.** This is the same site I documented in `~/.mdx/projects/rtm-mount-analysis--claude.md` from the prior task.

### Container env behavior

`docker run --env KEY=VALUE` injects KEY into the container process env. Confirmed in §3 below.

### Verdict: docker

`--env CLAUDE_CODE_OAUTH_TOKEN=…` lands as `--env CLAUDE_CODE_OAUTH_TOKEN=…` on `docker run`, which lands in the container's process env. **No filter strips it.**

## 3. Empirical sentinel test

Sentinel value: `sentinel-marker-12345`. Real token was never read or transcribed.

```sh
$ docker run --rm --env CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345 \
    alpine sh -c 'env | grep CLAUDE_CODE_OAUTH'
CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345
```

`--env` passthrough to docker container process: **confirmed**.

For host path, the shim's unit test (`crates/rtm-cli/src/cli/shim.rs:206-243`) is itself an empirical sentinel proof: it spawns `/usr/bin/env` with a sentinel `RTM_ALLOWED_SENTINEL=present` in `LaunchSpec.env`, asserts the value appears in stdout, and asserts a pre-existing parent env does NOT appear. Same code path as production spawn. No additional run needed.

**Conclusion**: env reaches both `docker run` argv and the host-spawned runtime process. The plumbing is not the bug.

## 4. What `claude` does with `CLAUDE_CODE_OAUTH_TOKEN`

The binary at `/Users/alphab/.local/share/claude/versions/2.1.149` is a bundled Mach-O Node executable (211 MB). `CLAUDE_CODE_OAUTH_TOKEN` appears as a literal string 50 times. Relevant excerpts from `strings` output (no source path available — it's a sea-of-strings bundle):

### Recognition

```
ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN env var is required
```

Auth providers chain. Either env var satisfies the inference requirement.

### Long-lived nature

```
Long-lived tokens (from `claude setup-token` or CLAUDE_CODE_OAUTH_TOKEN)
are limited to inference-only for security reasons.
Run `claude auth login` to use Remote Control.
```

This is the smoking gun. `CLAUDE_CODE_OAUTH_TOKEN` is the **output of `claude setup-token`**, a 1-year long-lived token explicitly limited to inference. It is **not** the OAuth session credential issued by `claude auth login`.

### Setup-token command

```
setup-token
Create a long-lived token with your Claude subscription
Creating a long-lived token for GitHub Actions
This will guide you through long-lived (1-year) auth token setup for your Claude account.
```

Setup-token is the canonical generator. Stored sibling string:

```
Store this token securely. You won't be able to see it again.
Use this token by setting: export CLAUDE_CODE_OAUTH_TOKEN=<token>
```

### Auth precedence chain

Strings consistently group `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN` together:

```
ANTHROPIC_API_KEY
apiKeyHelper
none
ANTHROPIC_AUTH_TOKEN
CLAUDE_CODE_OAUTH_TOKEN
CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR
CCR_OAUTH_TOKEN_FILE
profile
claude.ai
```

Order suggests precedence: `ANTHROPIC_API_KEY` first, then `apiKeyHelper`, then OAuth/auth-token family, then "profile" (Keychain entry), then `claude.ai` (interactive login). The exact ordering is in the bundle JS and would need full decompilation to confirm, but the grouping is consistent across all 50 occurrences.

### Related env vars

Worth noting these adjacent keys (found in the bundle):

| Env var | Purpose (from string context) |
|---------|--------------------------------|
| `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR` | FD-based delivery alternative — avoids exposing the token in env |
| `CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR` | Same for API keys |
| `ANTHROPIC_AUTH_TOKEN` | Alternate auth-token env var |
| `CCR_OAUTH_TOKEN_FILE` | File-based delivery |

The FD/file variants let callers avoid putting the token in the env table directly. Worth considering for `runtime-matters` if leaking via `/proc/<pid>/environ` is a concern.

### Telemetry events

```
tengu_oauth_tokens_not_claude_ai
tengu_oauth_tokens_inference_only
tengu_oauth_tokens_saved
```

`tengu_oauth_tokens_inference_only` is the event emitted when the binary recognizes a setup-token-style credential and gates features accordingly.

## 5. Keychain shape (metadata only)

```
$ security find-generic-password -s 'Claude Code-credentials' -a alphab
keychain: "/Users/alphab/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="Claude Code-credentials"
    "acct"<blob>="alphab"
    "cdat"<timedate>=0x32303236303531373139343633355A00  "20260517194635Z\000"
    "mdat"<timedate>=0x32303236303532323034313133375A00  "20260522041137Z\000"
    "svce"<blob>="Claude Code-credentials"
```

Class `genp` (generic password). Created 2026-05-17, modified 2026-05-22 (consistent with active token refresh).

The stored secret was not extracted. But the binary's bundled JS reveals the shape of what gets *written* to this entry. From the bundle (around the `claudeAiOauth` storage function):

```js
let A = await z.mutate((Y) => {
    let w = Y.claudeAiOauth;
    return {
        ...Y,
        claudeAiOauth: {
            accessToken: _,
            refreshToken: q,
            expiresAt: K,
            scopes: O,
            subscriptionType: H.subscriptionType ?? w?.subscriptionType ?? null,
            rateLimitTier: H.rateLimitTier ?? ...,
        }
    }
});
```

The Keychain entry stores a JSON object with at least these fields:
- `accessToken` (string)
- `refreshToken` (string)
- `expiresAt` (number or ISO string)
- `scopes` (array)
- `subscriptionType` (string or null)
- `rateLimitTier` (string)

**This is a session OAuth credential** (refreshable, short-expiry, claude.ai scoped). It is fundamentally different from what `CLAUDE_CODE_OAUTH_TOKEN` expects (a single long-lived setup-token string).

## 6. Diagnosis

The login prompt continues to appear because of one or more of these reasons. Listed by likelihood given the brief's symptoms:

### Cause A (most likely): shape mismatch

The user is passing a value derived from the Keychain — either the `accessToken` field or the whole JSON — but `CLAUDE_CODE_OAUTH_TOKEN` expects the **opaque string output of `claude setup-token`**. The setup-token has a distinct format (looks like `sk-ant-oat-…` from the regex hint `sk-ant-?[\w-]{10,}` in the bundle). The Keychain's `accessToken` is a different OAuth flow's token, with different scopes.

If a Keychain-derived value is passed in, the binary may parse it as malformed, expired, or invalid-scope, and fall through to the login flow.

### Cause B: mode mismatch

Even with a correctly-shaped setup-token, the binary gates features:

> Long-lived tokens (from `claude setup-token` or `CLAUDE_CODE_OAUTH_TOKEN`) are limited to **inference-only** for security reasons.

For interactive TUI mode (which is what runs in a tmux pane), the binary may require full OAuth login regardless of `CLAUDE_CODE_OAUTH_TOKEN`. The env var skips login *for inference calls* (`-p`, headless) but not necessarily *for the interactive UI*. The brief says "Claude STILL shows the login prompt" — this is consistent with an interactive spawn.

### Cause C (ruled out): env not reaching the binary

§1, §2, §3 prove this is not the cause. Both isolation paths deliver `--env` overrides to the runtime process intact.

### Cause D (possible): expired or revoked token

If the user reused an old setup-token output, it may have hit its 1-year expiry or been revoked. The binary would surface this through a different code path (the `tengu_api_key_keychain_error` / `Unable to verify organization...` strings) but the visible symptom from a fresh terminal is the same login prompt.

### Cause E (unlikely given strings): companion env required

Some auth modes want `ANTHROPIC_AUTH_TOKEN` or `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR` instead. Less likely because the bundle string explicitly says either `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` is required (not both).

## 7. Smallest fix

### If the user wants inference / headless `-p` mode to work

```sh
# Run once on the host (outside rtm), interactively:
claude setup-token

# Output is a single token string. Capture it once.
# Then, in agent.toml [env] (or the equivalent `rtm spawn --env` flag):
[env]
CLAUDE_CODE_OAUTH_TOKEN = "<the output of claude setup-token>"
```

This is the *correct* shape. Headless `-p` invocations will skip login and run inference-only.

### If the user wants the interactive TUI to skip login (Remote Control / full features)

Env-var auth will **not** achieve this. The binary explicitly enforces this constraint. The only paths that give a spawned interactive Claude full-scope credentials are:

1. **Mount the host `~/.claude` directory into the spawned process's expected `$HOME/.claude`** — but this only works if the spawn runs as a user whose `$HOME/.claude` matches the mount target, AND if the Keychain is accessible (on macOS, the Keychain is per-user and tied to the login session, so a docker container cannot read it; a host-isolation spawn running as the same user *can*).
2. **Run `claude auth login` once inside the spawned environment** (one-time, persists via `~/.claude/.credentials.json` if Keychain unavailable, or via Keychain on host).

For docker spawns specifically, the Keychain is unreachable. The fallback for non-Keychain platforms is a `~/.claude/.credentials.json` file with the OAuth JSON. The cleanest production path:

- Inside the docker image, ensure `~/.claude` exists and is writable by the container user (`rtm`).
- Mount or copy a `credentials.json` file into `/home/rtm/.claude/credentials.json` containing the same JSON shape as the Keychain (`{accessToken, refreshToken, expiresAt, scopes, subscriptionType, rateLimitTier}`).
- This intersects with the bind-mount work from `~/.mdx/projects/rtm-mount-analysis--claude.md`: the bind-mount mechanism is exactly what's needed to deliver this file from host to container.

### Code change to `runtime-matters` to support this directly

None necessary. The plumbing is complete. The only `runtime-matters` change worth considering is whether to **automatically forward** `CLAUDE_CODE_OAUTH_TOKEN` from the rtm CLI's shell into the spawned env without requiring an explicit `--env` flag. This would mean **removing the `CLAUDE_CODE_` prefix from the denylist** at `crates/rtm-core/src/spawn_context.rs:25`. **Do not do this naively**: the denylist exists because forwarding caller `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_ENTRYPOINT`, etc. would actively confuse the spawned Claude about which session it belongs to. A more surgical change: replace the prefix denylist with an explicit denylist excluding specific session-context keys (`CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_ENTRYPOINT`, …) while preserving `CLAUDE_CODE_OAUTH_TOKEN`. That's a separate ALP-2643 task, not part of this debug.

---

## Verification: paths and line numbers

| Claim | File | Lines |
|-------|------|-------|
| `spawn_env` isolation-branch capture | `crates/rtm-cli/src/cli/spawn.rs` | 74-83 |
| `parse_spawn_env` (no denylist on overrides) | `crates/rtm-cli/src/cli/spawn.rs` | 85-99 |
| `CALLER_ENV_DENYLIST_PREFIXES` includes `CLAUDE_CODE_` | `crates/rtm-core/src/spawn_context.rs` | 25 |
| `is_denied` filter logic | `crates/rtm-core/src/spawn_context.rs` | 82-89 |
| `upsert_launch_env` (no filter) | `crates/rtm-core/src/launcher.rs` | 22-28 |
| Shim `apply_launch_env_cwd` (env_clear + layer) | `crates/rtm-cli/src/cli/shim.rs` | 118-131 |
| Shim env-passthrough regression test | `crates/rtm-cli/src/cli/shim.rs` | 206-243 |
| `runtime_env` launcher additive keys | `crates/rtm-launchers/src/lib.rs` | 55-74 |
| Docker `docker_run_argv` calling site | `crates/rtm-daemon/src/docker_argv.rs` | 48-64 |
| Docker `append_env_args` (no filter) | `crates/rtm-daemon/src/docker_argv.rs` | 128-133 |
| Sentinel test in container | (live run) | `CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345` echoed from `alpine` container env ✅ |
| Claude binary recognizes the env var | `/Users/alphab/.local/share/claude/versions/2.1.149` | 50 string occurrences |
| Inference-only constraint string | (binary strings) | "Long-lived tokens (from `claude setup-token` or CLAUDE_CODE_OAUTH_TOKEN) are limited to inference-only" |
| Keychain entry shape | macOS `security` output | `Claude Code-credentials` / `genp` / `alphab` |

Read-only audit on rtm repo. Sentinel-only secrets in any live command. No secret values transcribed or persisted.
