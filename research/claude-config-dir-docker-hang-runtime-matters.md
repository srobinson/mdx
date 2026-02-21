---
title: CLAUDE_CONFIG_DIR docker spawn hang in runtime-matters — root cause and structural LOE
type: research
tags: [runtime-matters, docker, isolation, claude, env-passthrough, mount-spec, spawn-hang, moe-peer-consensus]
summary: rtm spawn with --isolation docker and --env CLAUDE_CONFIG_DIR=<host-path> hangs forever because the host path does not exist inside the container and claude stalls before first render. Fix is layered docs + soft warn for v1; structural mount-declaration support is Linear-scoped at ~400-800 LOC across 18-25 files.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

# CLAUDE_CONFIG_DIR docker spawn hang in runtime-matters

## Executive Summary

`rtm spawn --runtime claude --isolation docker --env CLAUDE_CONFIG_DIR=/Users/alphab/.claude ...` hangs indefinitely with no output. Root cause is a host/container path namespace mismatch in env passthrough: rtm plumbs `--env` unfiltered to the container, but only the spawn cwd is bind-mounted. The host path `/Users/alphab/.claude` does not exist inside the container, and is uncreatable by the container user `rtm` (uid 1001) because docker creates `/Users/alphab/` as a root-owned intermediate when establishing the cwd mount. Claude's TUI stalls before first render. The trap generalizes to ~16 path-shaped `CLAUDE_*` env vars and beyond.

This document records the converged findings of a mixture-of-experts peer-consensus investigation between two codebase-analyst panes (Claude and Codex) under topics `claude-config-hang-signoff` (root cause + immediate fix) and `claude-config-hang-loe` (structural fix sizing). Both topics reached unconditional convergence within 2 rounds.

Companion artifact: `~/.mdx/research/docker-mount-loe-runtime-matters.md` (Codex-authored LOE focus). This document supersedes the prior narrower root-cause-only version at this path and is the broader investigation record.

## Project Metadata

- **Repo**: `runtime-matters` at `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters`
- **Language**: Rust (workspace)
- **Crates**: `rtm-core`, `rtm-cli`, `rtm-daemon`, `rtm-client`, `rtm-platform`, `rtm-store`, `rtm-paths`, `rtm-launchers` (135 files, 18,774 LOC)
- **HEAD as of 2026-05-23**: commit `e138cb5 refactor: post-review architectural cleanup (#47)`
- **Public crates.io surface**: `lilo-rm-core`, `lilo-rm-client` (PROJECT.md lines 220-228)
- **Build**: `just check`, `just build`, `just test`; toolchain pinned in `rust-toolchain.toml`
- **fmm status**: `.fmm.db` present and indexed at session start; fmm tools dropped from this session mid-investigation, falling back to Bash/Read/grep for the LOE phase.

## Symptom

```bash
rtm spawn --runtime claude --session-id "$(uuidgen)" \
  --target tmux:3:3.2 \
  --isolation docker \
  --image runtime-matters-claude:local \
  --cwd ~/Dev/LLM/ \
  --env CLAUDE_CONFIG_DIR=/Users/alphab/.claude
```

Hangs indefinitely with no first frame rendered in the target tmux pane. Removing only the `--env CLAUDE_CONFIG_DIR=...` argument produces the claude welcome/theme screen immediately.

Live reproduction (Codex pane, round 1):

```bash
timeout 8s docker run --rm -it \
  --env CLAUDE_CONFIG_DIR=/Users/alphab/.claude \
  runtime-matters-claude:local
# → no first frame, times out at 8s
```

Same command without the env: welcome renders immediately. With `--env CLAUDE_CONFIG_DIR=/home/rtm/.claude` and that directory pre-created in the image: welcome renders immediately.

## Root Cause

Three structural facts compose the bug:

1. **Docker env passthrough is unfiltered.** `crates/rtm-daemon/src/docker_argv.rs:128-133` (`append_env_args`) appends every `LaunchEnv` entry as `--env KEY=VALUE` to `docker run`. The caller-env denylist at `crates/rtm-core/src/spawn_context.rs:10-25` (blocking `CLAUDECODE`, `TMUX`, `RTM_*`, `HELIOY_*`, and the prefixes `CLAUDE_CODE_`, `CLAUDE_PLUGIN_`) does NOT include `CLAUDE_CONFIG_DIR` and only filters auto-captured caller env, not user `--env` overrides. User overrides bypass it entirely (`crates/rtm-cli/src/cli/spawn.rs:79-81`).

2. **Only the cwd is bind-mounted.** `crates/rtm-daemon/src/docker_argv.rs:80-81` mounts `type=bind,src={cwd},dst={cwd}`. There is no companion mount for any other host path, so `/Users/alphab/.claude` does not exist inside the container. Docker mount intermediate-path creation does make `/Users/alphab/` exist as a root-owned empty directory; the container user `rtm` uid 1001 (`examples/dockerfiles/claude.Dockerfile:5-9`) lacks write permission there.

3. **`claude` performs file operations on `CLAUDE_CONFIG_DIR` before first stdout.** Strings extracted from the host-installed bun-compiled claude binary `/Users/alphab/.local/share/claude/versions/2.1.149`:
   - `Failed to create config dir or update lock file:`
   - `Could not acquire credentials lock at`
   - Lockfile basenames `.oauth_refresh.lock`, `.update.lock`
   - Retry telemetry events: `tengu_oauth_token_refresh_lock_retry`, `tengu_oauth_token_refresh_lock_retry_limit_reached`, `tengu_wif_user_oauth_lock_retry`, `tengu_wif_user_oauth_lock_retry_limit`
   - Container-specific hint: `"sessionStore with custom spawnClaudeCodeProcess: ensure the subprocess CLAUDE_CONFIG_DIR matches the parent... or transcript_mirror frames will be dropped"` and `" -- subprocess CLAUDE_CONFIG_DIR likely differs from parent (custom spawnClaudeCodeProcess / container?)"`

The container's npm-installed `@anthropic-ai/claude-code` shares this code path. When the config dir is uncreatable, OAuth refresh and update paths retry with backoff before claude reaches its first user-visible output.

### Symmetric explanation

- **Without `CLAUDE_CONFIG_DIR`**: claude defaults to `$HOME/.claude` = `/home/rtm/.claude`, owned by `rtm`, mkdir + lockfile creation succeed, claude proceeds to first render.
- **With `CLAUDE_CONFIG_DIR=/Users/alphab/.claude`**: lock acquisition retries against an uncreatable path; visible as a "hang" until the retry budget exhausts or the user gives up.

## Class of Related Env Vars (path-shaped trap)

The trap generalizes. Path-shaped `CLAUDE_*` envs read at startup (from binary strings):

| Env var | Shape |
| --- | --- |
| `CLAUDE_CONFIG_DIR` | directory (the trigger case) |
| `CLAUDE_PROJECT_DIR` | directory |
| `CLAUDE_JOB_DIR` | directory |
| `CLAUDE_TMPDIR` | directory |
| `CLAUDE_ENV_FILE` | file |
| `CLAUDE_BG_AUTH_SNAPSHOT_PATH` | file |
| `CLAUDE_SECURESTORAGE_CONFIG_DIR` | directory |
| `CLAUDE_SESSION_INGRESS_TOKEN_FILE` | file |
| `CLAUDE_CODE_DEBUG_LOGS_DIR` | directory |
| `CLAUDE_CODE_DIAGNOSTICS_FILE` | file |
| `CLAUDE_CODE_EXECPATH` | executable path |
| `CLAUDE_CODE_GIT_BASH_PATH` | executable path |
| `CLAUDE_CODE_PLUGIN_CACHE_DIR` | directory |
| `CLAUDE_CODE_PLUGIN_SEED_DIR` | directory |
| `CLAUDE_CODE_REMOTE_MEMORY_DIR` | directory |
| `CLAUDE_CODE_TMPDIR` | directory |

Broader: `HOME`, `XDG_*`, `AWS_SHARED_CREDENTIALS_FILE`, `SSH_AUTH_SOCK`, any env carrying a host path under docker isolation without a covering mount.

## Architecture Walk

### Spawn pipeline (docker path)

1. `rtm spawn` CLI parses args at `crates/rtm-cli/src/cli/spawn.rs:14-36`.
2. `spawn_env` (`:74-83`) builds the env vector. Critical asymmetry:
   - Host isolation starts with `lilo_rm_core::capture_caller_env()` (denylist-filtered)
   - Docker isolation starts with `Vec::new()` (no inherited env)
   - Both then layer user `--env` overrides via `upsert_launch_env`
3. Request goes to rtmd via `RuntimeClient::new(socket_path).spawn(SpawnRequest { ... })`.
4. Daemon's `spawn_preflight.rs:60-67` runs `check_isolation_policy`. For docker, only profile-name allow-list + image metadata checks (no env validation).
5. Backend dispatches to docker_runtime. `prepare_launch` builds a `LaunchSpec` via the launcher (`rtm-launchers`), then calls `docker_run_launch` (`crates/rtm-daemon/src/docker_argv.rs:14-46`) to wrap argv in `docker run ...`.
6. `docker_run_argv` (`:48-64`) builds the base argv, appends `--init` (unless `own-init` profile), appends `--env KEY=VAL` for each `LaunchEnv` (`:128-133`), then the image and command.
7. `docker_run_base_argv` (`:66-89`) mounts the cwd `type=bind,src={cwd},dst={cwd}`, sets `--workdir {cwd}`, adds TTY flags if the target is tmux.
8. For tmux targets, the whole `docker run -d ...` is wrapped in `/bin/sh -c "container_id=$(docker run -d...); exec docker attach --detach-keys '' --sig-proxy=false $container_id"` (`:91-101`).

### Caller-env denylist

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

Applies only to auto-captured caller env (host isolation start state), NOT to user `--env` overrides. Both isolation modes pass user overrides unfiltered.

### Launcher path

`crates/rtm-launchers/src/lib.rs::resolve_binary` runs `which claude` on the host. Returns `/Users/alphab/.local/bin/claude` (macOS arm64 Mach-O). Then `container_command` at `docker_argv.rs:103-112` strips absolute path to basename `claude`, so the container's npm-installed claude is what actually runs. Binary resolution is fine.

### Image contract

`examples/dockerfiles/claude.Dockerfile`:
- Base: `mcr.microsoft.com/devcontainers/base:ubuntu`
- User: `rtm` (uid 1001), home `/home/rtm`
- WORKDIR: `/workspace` (overridden at runtime to `--workdir {host_cwd}`)
- Installs `@anthropic-ai/claude-code` globally via npm
- CMD: `["claude"]` (overridden by docker_run argv)

### PROJECT.md doc-drift (orthogonal follow-up)

PROJECT.md lines 127-129 claim `/workspace` is the canonical workspace path inside the container. The code mounts `cwd:cwd` and sets `--workdir {cwd}` at runtime. Image contract section (line 155) says "create `/workspace` and make it writable by the runtime user" but `/workspace` is unused at runtime. Flagged for separate resolution. Persisted in cm as observation `019e525d-27f9-74e3-83f8-9955d578afe7`.

## Converged Fix (Immediate, MoE-Doable In-Session)

Both panes signed off conditional on identical 5-item change set (round 3 of `claude-config-hang-signoff`):

1. **PROJECT.md §Credentials extension** with "Host paths in env values" subsection. State that absolute `--env` values are passed verbatim to the container; under docker isolation only the spawn cwd is bind-mounted; host paths in env values without a covering mount can cause silent stalls (not fast errors). List the 16 path-shaped CLAUDE_* envs as known traps.
2. **Document the workaround**: omit the env, set it to a path that exists/is-writable inside the container, or build/profile the image so the matching path exists with correct ownership for `rtm`.
3. **Optional v1 daemon log warning**. From `crates/rtm-daemon/src/spawn_preflight.rs` under `IsolationPolicy::Docker(_)`, iterate `request.env` and emit `tracing::warn!` for each known path-shaped Claude env key with an absolute-path value. Strictly rtmd-log-only via `tracing::warn!`; NOT a `RuntimeEvent`. The durable event log carries only `Running | Terminated | Lost` (`crates/rtm-core/src/types/lifecycle.rs:188-204`) and has no warning channel; `SpawnedPayload` (`crates/rtm-core/src/proto.rs:128-134`) has no warning slot. Adding event-log warning would be a protocol/schema change explicitly NOT bundled.
4. **Defer the structural fix** (mount declarations + path-shaped env coverage validation) to separate Linear work.
5. **Follow-up doc-drift cm note** for PROJECT.md `/workspace` vs `cwd:cwd` (persisted in cm).

Size: ~100 LOC, 3 files, no protocol change.

### Anti-patterns explicitly rejected by sign-off

- **Auto-mounting host paths from env values**: silently widens docker isolation and leaks host secrets.
- **`CLAUDE_*_DIR` / `CLAUDE_*_PATH` denylist** for docker isolation: punishes operators who DO bake matching paths into their images.
- **Hard-reject preflight without escape hatch**: today no mount declaration exists, so unconditional reject is observationally equivalent to a denylist.

## Linear-Scoped Structural Fix (LOE Sizing)

Both panes filed unconditional sign-off (round 3 of `claude-config-hang-loe`) on **(c) Hybrid** verdict.

### Size envelope

| Scope choice | LOC | Files |
| --- | --- | --- |
| Lower bound: same-destination-only mounts, fail-fast preflight | ~400 | ~18 |
| Upper bound: host→container env value rewrite | ~800 | ~25 |

The spread depends on **the gating spec decision**:
- **(A) Same-destination only**: only accept mounts where the env value points at the mount target; or require operator to set `CLAUDE_CONFIG_DIR=/home/rtm/.claude` and `--mount /Users/alphab/.claude:/home/rtm/.claude:ro`. Simpler, ergonomically clunky.
- **(B) Env value rewrite**: daemon rewrites host paths in known path-shaped env values to container paths based on declared mount mappings. More ergonomic, more invasive.

### Files touched

**Core types**:
- `crates/rtm-core/src/types/spawn.rs` — add `MountSpec` and `SpawnRequest.mounts: Vec<MountSpec>` with `#[serde(default, skip_serializing_if = "Vec::is_empty")]`
- `crates/rtm-core/src/lib.rs` — re-export
- `crates/rtm-core/src/version.rs` — capability/version bump

**CLI**:
- `crates/rtm-cli/src/cli/spawn.rs` — `--mount SRC:DST[:ro]` flag and parser

**Daemon argv**:
- `crates/rtm-daemon/src/docker_argv.rs` — emit `--mount` for each declared mount alongside the existing cwd self-mount (`:80-81`)
- `crates/rtm-daemon/src/backend.rs` — pass `request.mounts` from `prepare_launch` to docker layer
- `crates/rtm-daemon/src/docker_runtime.rs` — accept mounts param

**Daemon preflight**:
- `crates/rtm-daemon/src/spawn_preflight.rs` — validate mount sources exist, target shape, path-shaped env coverage

**Struct literal fallout (~10 files mechanical, 1-5 LOC each)**:
- `crates/rtm-client/tests/typed_helpers.rs`
- `crates/rtm-cli/examples/support/spawn.rs`
- `crates/rtm-cli/benches/spawn_latency.rs`
- `crates/rtm-daemon/src/docker_preflight.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-daemon/src/doctor.rs`
- `crates/rtm-launchers/src/lib.rs`
- `crates/rtm-launchers/tests/conformance.rs`
- `crates/rtm-cli/tests/spawn_target.rs`

**Tests (mandatory)**:
- `crates/rtm-core/tests/serde_snapshots.rs` — additive only; existing no-mount snapshots are byte-identical with `skip_serializing_if = "Vec::is_empty"`; new explicit-mount round-trip cases needed
- `crates/rtm-daemon/src/spawn_preflight/tests.rs` — 4-6 new cases (~150-250 LOC)
- `crates/rtm-cli/tests/spawn_target.rs` — 1-2 docker integration cases (~80 LOC)
- `crates/rtm-daemon/src/docker_argv.rs::tests` — 2-3 new cases (~50 LOC)
- `crates/rtm-cli/tests/docker_e2e.rs` — mount coverage E2E proof

**Docs**:
- `PROJECT.md` — §Credentials extension replacing aspirational `[docker.credentials]` TOML fragment (lines 179-186) with real CLI shape

### Files NOT touched (converged architecture call)

- `crates/rtm-core/src/launcher.rs` — NO. Mounts are docker-isolation-specific input, not launcher-shaped. They stay on `SpawnRequest` and flow directly to `docker_argv` via `backend.rs::prepare_launch`, never threading through `LaunchSpec` or the host shim path.
- `crates/rtm-cli/src/cli/shim.rs` — NO. Host shim untouched.
- `SpawnedPayload`, durable event log, lifecycle DB — NO. Mounts are spawn-time input only.

### Protocol/schema impact

- **Wire**: `SpawnRequest.mounts` is additive serde field. With `skip_serializing_if = "Vec::is_empty"`, existing snapshots are byte-identical (NO regen). Only new explicit-mount round-trip cases needed.
- **Rust API**: `MountSpec` is a new public type on the `lilo-rm-core` crate. All `SpawnRequest { ... }` literal call sites need the new field (or migration to a builder pattern, itself a refactor).
- **Cross-repo**: `session-matters` per PROJECT.md line 232 is the primary upstream consumer compiling against `lilo-rm-core`. Even an additive `mounts` field requires coordinated minor-version bump. Spec must capture whether session-matters surfaces mount declarations end-to-end or treats them as rtm-internal.
- **Capability/version**: `crates/rtm-core/src/version.rs` bump for mount-aware spawn surface.

### Gating spec sub-issue decisions

The Linear parent issue's first sub-issue must be a spec deciding:

1. **(A) Same-destination-only vs (B) host→container env value rewrite.** THE invasive design axis.
2. **Policy ownership for the 16-key path-shaped CLAUDE_* env list.** Lives in `rtm-core` or `rtm-daemon`? Refreshed how?
3. **Host-isolation semantics.** Converged: CLI rejects `--mount` with `--isolation host` (CLI has both values); direct RPC no-ops with `tracing::warn!` to avoid protocol-level reject error variant.
4. **Protocol/version bump shape.** Wire capability flag or numeric protocol minor?
5. **Relationship to PROJECT.md aspirational `[docker.credentials]` operator TOML config (lines 179-186).** Does not exist in code; daemon has only env-var-driven config (`crates/rtm-daemon/src/docker_preflight.rs:19-29`). Replace or coexist.

### Implementation order

1. Spec sub-issue gates everything else.
2. `rtm-core` types + version bump.
3. `rtm-cli` `--mount` flag + parser.
4. `rtm-daemon` argv emission.
5. `rtm-daemon` preflight validation.
6. Struct-literal fallout (mechanical).
7. Docs + serde additions.
8. Optional follow-up: env value rewrite if v1 picked (A).

### Splitting recommendation

If (B) is chosen, ~800 LOC + spec-bearing decisions + cross-repo coordination argues for splitting into two PRs: ship v1 as (A) same-destination + fail-fast preflight; ship env-rewrite as separate ergonomic upgrade.

## Persisted Context

cm entries written at scope `global/project:helioy/repo:runtime-matters`:

- **`019e525c-f757-77d0-a46e-6da782bf42dc`** (fact) — Root cause + converged immediate fix + anti-patterns rejected.
- **`019e525d-27f9-74e3-83f8-9955d578afe7`** (observation) — PROJECT.md `/workspace` doc-drift follow-up.
- **`019e5270-f441-7761-82fa-093267bb6bc3`** (decision) — LOE sizing for structural fix, supersedes the deferral-only treatment in `019e51fa-cc89-7bc1-951b-6104d3843e7f`.

Related pre-existing entries:
- **`019e51fa-cc89-7bc1-951b-6104d3843e7f`** (fact) — rtm docker argv single construction site + profile-name allow-list gate; original deferral pointer for mount support.
- **`019e5204-eded-7d93-9ff8-a38e247c211b`** (fact) — `CLAUDE_CODE_OAUTH_TOKEN` setup-token vs Keychain OAuth shape mismatch (related to claude auth env-var family).

## Open Questions

1. **Exact mechanism inside claude binary**: binary strings strongly suggest a lock-acquisition retry path (`Could not acquire credentials lock at`, lockfiles `.oauth_refresh.lock` / `.update.lock`, retry telemetry events), but no live stack trace was captured. The Codex pane's live reproduction confirmed the SHAPE (no first frame, timeout) without nailing the precise syscall that blocks. Not required for the fix — the structural fact (uncreatable config dir + claude stalls before output) is sufficient.

2. **PROJECT.md `/workspace` vs `cwd:cwd` direction**: should the daemon migrate to `/workspace` mounting (matching docs) or should docs migrate to `cwd:cwd` (matching code)? Each has implications. A `/workspace` mount strategy would avoid creating the host-path-prefix intermediate that contributes to the current failure shape.

3. **Aspirational `[docker.credentials]` TOML operator profile** (PROJECT.md lines 179-186): does Helioy want this layer at all, or is per-spawn `--mount` sufficient? Affects size envelope upper bound.

4. **Session-matters mount surface**: should the cross-repo consumer (`session-matters`) expose mount declarations to its callers, or treat mounts as rtm-internal and never set them? Spec-level decision.

## Process Notes

- Both panes converged within the orchestrator's 2-round iteration bound on each topic.
- Codex's live reproduction in round 1 of `claude-config-hang-signoff` was the strongest single piece of evidence and replaced speculative mechanism claims with empirical confirmation.
- Codex's round-2 catch on env-rewrite-vs-same-destination in `claude-config-hang-loe` was the key correction — a mount alone does NOT fix the bug; the env value still points at a non-existent path unless rewritten or the mount uses same-destination. Without this distinction the LOE numbers are wrong by 2x.
- Both panes maintained adversarial discipline: each round found at least one substantive issue with the peer's filing or positively justified "none found."
- Write boundary held: no source files edited; all changes proposed for orchestrator-applied implementation.
