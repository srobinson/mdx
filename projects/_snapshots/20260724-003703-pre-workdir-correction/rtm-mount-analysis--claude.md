---
title: rtm docker isolation — smallest tweak to enable bind-mounts
type: research
tags: [runtime-matters, docker, isolation, mounts, alp-2643, moe, claude-pane]
summary: Smallest delta to support arbitrary `-v HOST:CONTAINER` bind-mounts in rtm docker spawns. One argv-construction site, one CLI flag, zero general-purpose mount field today.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

# rtm docker isolation — smallest tweak to enable bind-mounts

Pane A (Claude) of MoE pair. Peer is Codex. Independent analysis. Read-only, no repo writes.

## TL;DR

There is **no true 1-line tweak**, but there are two ~10-line deltas with very different trade-offs. The most surgical, wire-free path is **(c) env-var-driven mounts**: ~10 LOC, one file, daemon picks up `RTM_DOCKER_MOUNTS` at the existing argv-construction site. The cleanest user-facing path is **(b) a `--mount` CLI flag** plumbed through `SpawnRequest`: ~25 LOC across 4 files, no wire-schema break (just an additive field). Extending the `IsolationProfile` enum payload (option a) is the most disruptive and gains nothing the simpler options miss.

Critical gate to be aware of: the daemon's spawn preflight (`spawn_preflight.rs:75-101`) **allow-lists** the docker profile *name* against a fixed set (`None`, `default`, `own-init`, `allow-root`, `arm64-manifest-escape`). Any "smuggle through the profile string" approach would either be rejected or require extending that allow-list, which is a second change. Options (b) and (c) sidestep the gate entirely.

---

## 1. Where docker argv is built

Single construction site: `crates/rtm-daemon/src/docker_argv.rs`, function `docker_run_base_argv` at **lines 66–89**:

```rust
fn docker_run_base_argv(
    session_id: Uuid,
    cwd: String,
    tty: bool,
    docker_command: &str,
) -> Vec<String> {
    let mut argv = vec![
        docker_command.to_owned(),
        "run".to_owned(),
        "--rm".to_owned(),
        "--name".to_owned(),
        container_name(session_id),
        "--label".to_owned(),
        format!("{RTM_DOCKER_SESSION_LABEL}={session_id}"),
        "--mount".to_owned(),
        format!("type=bind,src={cwd},dst={cwd}"),  // ← line 80-81: only existing bind
        "--workdir".to_owned(),
        cwd,
    ];
    if tty {
        argv.extend(["-d".to_owned(), "-i".to_owned(), "-t".to_owned()]);
    }
    argv
}
```

The hardcoded bind at **lines 80–81** mounts the caller cwd to itself inside the container (`src={cwd},dst={cwd}`). That is the entire existing host-FS surface.

Call chain (all in `crates/rtm-daemon/src/`):

- `docker_argv::docker_run_base_argv` (`docker_argv.rs:66`)
- ← `docker_argv::docker_run_argv` (`docker_argv.rs:48-64`) — adds `--init`, env, image
- ← `docker_argv::docker_run_launch` (`docker_argv.rs:14-46`) — appends command + tmux attach wrapper
- ← `docker_runtime::docker_run_launch` (`docker_runtime.rs:12-27`) — resolves `docker` binary path
- ← `DockerRuntimeBackend::prepare_launch` (`backend.rs:76-88`) — picks docker vs host branch, plumbs `IsolationProfile` and image

All five points pass `&IsolationProfile` through; none pass mount specs.

## 2. What `IsolationPolicy::Docker` carries today

Type definition: `crates/rtm-core/src/isolation.rs:9-13`:

```rust
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "type", content = "payload", rename_all = "snake_case")]
pub enum IsolationPolicy {
    #[default]
    Host,
    Docker(IsolationProfile),
}
```

Profile struct: `crates/rtm-core/src/isolation.rs:60-64`:

```rust
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
pub struct IsolationProfile {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}
```

**One field, `name: Option<String>`.** No `mounts`, no `env`, no `extra_args`. The serde wire shape is confirmed by the round-trip snapshot in `crates/rtm-core/tests/serde_snapshots.rs:413-418`:

```rust
Some(&json!({
    "type": "docker",
    "payload": { "name": "locked" }
}))
```

Payload is just `{name}`. The brief's "earlier session-matters analysis showed payload empty in the wire" is essentially correct — the only payload key is `name`.

## 3. What `docker:PROFILE` actually does in current code

The suffix is parsed by `parse_docker_profile` at `crates/rtm-core/src/isolation.rs:48-58`:

```rust
fn parse_docker_profile(value: &str) -> Result<IsolationPolicy, IsolationPolicyParseError> {
    let Some(profile) = value.strip_prefix("docker:") else {
        return Err(IsolationPolicyParseError(value.to_owned()));
    };
    if profile.is_empty() {
        return Err(IsolationPolicyParseError(value.to_owned()));
    }
    Ok(IsolationPolicy::Docker(IsolationProfile {
        name: Some(profile.to_owned()),
    }))
}
```

The string after `docker:` is stored verbatim as `IsolationProfile.name`. **It is not a placeholder.** It is consumed in exactly two places downstream:

### Use #1 — `--init` gating (`crates/rtm-daemon/src/docker_argv.rs:58`):

```rust
if profile.name.as_deref() != Some("own-init") {
    argv.push("--init".to_owned());
}
```

`docker:own-init` suppresses the `--init` flag. That is the only argv-shaping effect of the profile name in the entire codebase.

### Use #2 — preflight allow-list (`crates/rtm-daemon/src/spawn_preflight.rs:75-101`):

```rust
match profile.name.as_deref() {
    None
    | Some("default")
    | Some("own-init")
    | Some("allow-root")
    | Some("arm64-manifest-escape") => {
        validate_docker_image_metadata_on_arch(...).await
    }
    Some("pattern-e") | Some("tmux-primary") => Err(unsupported_docker_behavior(
        "requests a multiplexer inside the container",
    )),
    Some("privileged") => Err(unsupported_docker_profile(
        profile,
        "requests privileged execution",
    )),
    Some(_) => Err(unsupported_docker_profile(
        profile,
        "is not an accepted Docker profile",
    )),
}
```

`allow-root` and `arm64-manifest-escape` toggle preflight validation behavior via `docker_root_allowed`/`docker_manifest_escape_allowed` (lines 150–161). Any name not in the allow-list is rejected before launch.

**There is no profile config loader, no config-file lookup, no mount-list capability behind the suffix.** It is a tiny enum encoded as a string. Trying to encode mount specs into the profile name (e.g. `docker:mounts=/foo:/bar`) would be rejected by the preflight gate.

There is, however, an env-var-driven config layer for docker behavior: `DockerPreflightConfig::from_env` at `crates/rtm-daemon/src/docker_preflight.rs:19-29` reads `RTM_DOCKER_IMAGE`, `RTM_DOCKER_ALLOW_ROOT_IMAGE_USER`, `RTM_DOCKER_ALLOW_ARM64_MANIFEST_ESCAPE` at daemon startup. This is the natural extension point for an env-var-driven mount list.

## 4. Ranked options

| Rank | Option | LOC | Files touched | Wire change | Bypasses preflight gate |
|------|--------|-----|---------------|-------------|------------------------|
| **1** | **(c)** Env-var `RTM_DOCKER_MOUNTS` at argv site | ~10 | 1 (`docker_argv.rs`) + 1 test | No | Yes (no profile string change) |
| 2 | (b) `--mount` CLI flag plumbed via `SpawnRequest` | ~25 | 4 (`spawn.rs`, `types/spawn.rs`, `backend.rs` or `docker_runtime.rs`, `docker_argv.rs`) | Additive field (back-compat default) | Yes |
| 3 | (a) Extend `IsolationProfile.mounts: Vec<MountSpec>` | ~50+ | 5+ (above + `isolation.rs` + parser + serde round-trip tests) | Yes — new payload field, new FromStr syntax to populate it | Yes |

### Why (c) wins on raw LOC

- Zero wire-schema change.
- Zero CLI surface change at the rtm crate boundary.
- One argv-site mutation in one function.
- Daemon already reads `RTM_DOCKER_*` env at boot (see `docker_preflight.rs:21-28`); the pattern is already established.

### Why (c) loses on UX

- The daemon process holds the env at startup. To change the mount set you restart the daemon, not the CLI client. For "one-shot user test" that's fine; for production, that's the wrong shape.
- Reading `std::env::var` *inside* `docker_run_base_argv` (rather than at daemon boot) breaks the pattern slightly — argv builders should be pure. Putting it in `DockerPreflightConfig` and plumbing it down is cleaner (~15 LOC).

### Why (b) is the right *production* answer

- Maps 1:1 to docker CLI semantics: `rtm spawn ... --mount $HOME/.claude:/home/rtm/.claude`.
- Per-spawn granularity. Daemon-restart-free.
- Additive `mounts: Vec<String>` field on `SpawnRequest` round-trips through serde without breaking existing clients (defaults to `Vec::new()` via `#[serde(default)]`, mirroring the existing `env: Vec<LaunchEnv>` pattern at `types/spawn.rs:84-85`).
- The preflight allow-list is profile-name-keyed and untouched.

### Why (a) is overkill

The brief asked whether mounts belong in `IsolationProfile`. They semantically *could*, but doing so means inventing a new FromStr syntax for the `--isolation` flag (current parser only knows `docker:NAME` — there is no room for `docker:mounts=A:B,C:D`), updating serde snapshots, updating preflight allow-list logic, and migrating any callers that match on `IsolationProfile { name }`. None of that buys anything (b) doesn't deliver in a third of the LOC.

## 5. Recommended smallest delta (production-shaped, option b)

A focused patch with ~25 LOC across 4 files. Here is the exact shape, file-by-file.

### 5a. CLI flag — `crates/rtm-cli/src/cli/spawn.rs` (after current line 30):

```rust
#[arg(long = "mount", value_name = "HOST:CONTAINER")]
mounts: Vec<String>,
```

And destructure + forward in `run()` (around `spawn.rs:38-68`) by adding `mounts` to the destructure and `mounts` to the `SpawnRequest` construction.

### 5b. Wire — `crates/rtm-core/src/types/spawn.rs` (add field to `SpawnRequest`, line 77-92):

```rust
#[serde(default, skip_serializing_if = "Vec::is_empty")]
pub mounts: Vec<String>,
```

Back-compat: existing JSON clients omit the field, deserialize defaults to empty Vec. Existing serializers omit on empty.

### 5c. Argv site — `crates/rtm-daemon/src/docker_argv.rs`:

Change `docker_run_argv` signature to take `mounts: &[String]` (currently lines 48-64), and inside, after the `--init` block at line 60, before `append_env_args` at line 61:

```rust
append_mount_args(&mut argv, mounts);
```

Add the helper next to `append_env_args` (after line 133):

```rust
fn append_mount_args(argv: &mut Vec<String>, mounts: &[String]) {
    for spec in mounts {
        let Some((host, container)) = spec.split_once(':') else { continue };
        argv.push("--mount".to_owned());
        argv.push(format!("type=bind,src={host},dst={container}"));
    }
}
```

### 5d. Plumb through — `crates/rtm-daemon/src/docker_runtime.rs:12-27` and `crates/rtm-daemon/src/backend.rs:76-88`:

Pass `&request.mounts` through `docker_runtime::docker_run_launch` (line 12) to `docker_argv::docker_run_launch` (line 14), which forwards to `docker_run_argv` (line 48). Three signature touches, one extra argument each.

### 5e. Tests:

- One unit test in `docker_argv.rs` confirming `--mount type=bind,src=...,dst=...` appears in argv when `mounts` is non-empty.
- One serde round-trip test in `crates/rtm-core/tests/serde_snapshots.rs` confirming `mounts` is omitted-on-empty.

### Total: ~25 LOC across 4 files + ~20 LOC tests.

**Actual single-line core**: the new helper call at the argv site is one line. Everything else is plumbing.

### Alternative if "one-line"-ness matters more than ergonomics (option c)

In `crates/rtm-daemon/src/docker_argv.rs`, after current line 84 (the `--workdir`):

```rust
append_env_mount_args(&mut argv);
```

with a new helper:

```rust
fn append_env_mount_args(argv: &mut Vec<String>) {
    let Ok(value) = std::env::var("RTM_DOCKER_MOUNTS") else { return };
    for spec in value.split(';').filter(|s| !s.trim().is_empty()) {
        let Some((host, container)) = spec.split_once(':') else { continue };
        argv.push("--mount".to_owned());
        argv.push(format!("type=bind,src={host},dst={container}"));
    }
}
```

User invocation:

```sh
RTM_DOCKER_MOUNTS="$HOME/.claude:/home/rtm/.claude" rtmd  # restart daemon
rtm spawn --runtime claude --session-id $(uuidgen) --target tmux:N:N.N \
    --isolation docker --image runtime-matters-claude:local --cwd ~/Dev/LLM/
```

~10 LOC in one file. Daemon-scoped — must restart daemon to change. Acceptable for "does this even work" testing; wrong shape for production. Cleaner version moves the parse to `DockerPreflightConfig::from_env` (mirroring `RTM_DOCKER_IMAGE`) and adds one parameter to `docker_run_argv` — ~15 LOC, 2 files.

## 6. What would break

### Preflight allow-list (`spawn_preflight.rs:75-101`)

Neither (b) nor (c) touches the profile name string, so the allow-list is unaffected. Option (a) would require either bypassing or extending the allow-list — second change.

### Existing single hardcoded bind (`docker_argv.rs:80-81`)

`src={cwd},dst={cwd}` mounts the caller cwd to its host path inside the container. Adding `~/.claude:/home/rtm/.claude` mounts host home-config to a fixed container path. These don't collide. But callers must know the container's user identity to pick the right `dst` — the brief notes "user `rtm`, workdir `/workspace`", which makes `/home/rtm/.claude` the right target (not `/root/.claude`). This is user education, not a code issue.

### No path-safety validation

The proposed helper does no validation of host paths (existence, symlink resolution, ownership). Existing argv code canonicalizes cwd at the CLI layer (`spawn.rs:113-115`) but `docker_argv.rs` itself does no validation. So this proposal is in line with existing behavior, but it does mean a malicious or sloppy caller can mount anything readable.

### Wire round-trip

For option (b), `SpawnRequest.mounts: Vec<String>` with `#[serde(default, skip_serializing_if = "Vec::is_empty")]` is fully back-compat with both directions: old clients send no field → daemon deserializes to `Vec::new()`; old daemons see field → ignore it (the serde `tag = "type"` enum on `IsolationPolicy` is the only strict-rejection path, and `mounts` is a flat field on `SpawnRequest` not inside the enum). Confirmed by the existing additive-field pattern at `types/spawn.rs:80-91` where `image`, `force`, and `shell_resume` all use the same `#[serde(default, skip_serializing_if = ...)]` pattern.

### Mount syntax

The 10-line helpers assume plain `host:container`. Real docker `-v` syntax allows trailing `:ro`, `:rw`, `:Z`, etc. For a v1 ("does Claude CLI pick up `~/.claude` if we mount it") that limitation is fine. Generalizing to full `--mount type=bind,src=...,dst=...,readonly` syntax is another ~5 LOC parse change.

### Container user mismatch

The brief says container entrypoint is `["claude"]`, user `rtm`, workdir `/workspace`. If the user mounts host `~/.claude` to `/root/.claude`, the Claude CLI inside the container (running as `rtm`) won't read it — Claude CLI checks `$HOME/.claude` which resolves to `/home/rtm/.claude`. The correct container path is `/home/rtm/.claude`. The proposed code does not enforce this; it is the caller's responsibility. Worth surfacing in CLI help text for `--mount` (option b).

---

## Verification: paths and line numbers re-confirmed

| Claim | File | Lines |
|-------|------|-------|
| `IsolationPolicy` enum | `crates/rtm-core/src/isolation.rs` | 9-13 |
| `IsolationProfile` struct | `crates/rtm-core/src/isolation.rs` | 60-64 |
| `parse_docker_profile` | `crates/rtm-core/src/isolation.rs` | 48-58 |
| `SpawnRequest` struct | `crates/rtm-core/src/types/spawn.rs` | 76-92 |
| Wire-shape snapshot | `crates/rtm-core/tests/serde_snapshots.rs` | 401-419 |
| `docker_run_base_argv` (the argv site) | `crates/rtm-daemon/src/docker_argv.rs` | 66-89 |
| Existing hardcoded `--mount` bind | `crates/rtm-daemon/src/docker_argv.rs` | 80-81 |
| `--init` profile-name gate | `crates/rtm-daemon/src/docker_argv.rs` | 58 |
| Preflight profile allow-list | `crates/rtm-daemon/src/spawn_preflight.rs` | 75-101 |
| `DockerPreflightConfig::from_env` (env pattern) | `crates/rtm-daemon/src/docker_preflight.rs` | 19-29 |
| `DockerRuntimeBackend::prepare_launch` | `crates/rtm-daemon/src/backend.rs` | 76-88 |
| CLI `SpawnArgs` struct | `crates/rtm-cli/src/cli/spawn.rs` | 14-36 |

Read-only audit. No repo writes performed.
