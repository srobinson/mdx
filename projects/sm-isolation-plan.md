# Plan: plumb `--isolation` and `--image` through `sm`

**Author:** orchestrator (`session-matters:general:2:2.1`), synthesizing MoE drafts at `~/.mdx/projects/sm-isolation-plan--{claude,codex}.md`
**Repo:** `littleorgans/session-matters` @ HEAD `b919b3d`
**Status:** consensus-revised — both MoE panes signed off conditional on this revision; awaiting clean re-sign-off

## Pre-flight context

littleorgans (the four sibling repos: identity-matters, session-matters, runtime-matters, transport-matters) is pre-release with **zero downstream users**. Breaking changes are welcome and expected. `MEMORY.md` records this stance explicitly: "drop deprecation shims by default". Do not propose backward-compat shims, additive-only schemas, or staged deprecations for compat reasons. Where the cleanest change is breaking, take the breaking change. `sm_core::SpawnRequest`, `SpawnLaunch`, and the rtm wire are all internal types with no external consumers; extending them with required-default fields is free.

## Goal

Make the user's command succeed end-to-end:

```sh
sm run claude --target tmux:3:1.1 --role pm --label app=nginx \
  --isolation docker --image runtime-matters-claude:local \
  --agent-config auth-passthrough
```

A Claude TUI lands inside a `runtime-matters-claude:local` docker container in tmux pane `3:1.1`, with the `[env]` keys from `~/.agm/auth-passthrough/agent.toml` reaching the container process.

**Env passthrough is the only filesystem-adjacent mechanism in scope.** `agent.toml`'s `claude_config_dir` becomes the `CLAUDE_CONFIG_DIR` env var inside the container; it does NOT mount the host's `~/.claude` directory. Container filesystem access to host paths requires bind-mount support, which is out of scope (see `~/.mdx/projects/rtm-mount-analysis--{claude,codex}.md`).

The work is **purely sm-side plumbing**. rtm already supports both fields end-to-end (verified empirically in `~/.mdx/projects/rtm-mount-analysis--{claude,codex}.md` and `~/.mdx/projects/auth-token-debug--{claude,codex}.md` — including a passing regression test at `runtime-matters/crates/rtm-cli/tests/spawn_target.rs:196-259` that proves `--env` passthrough into docker containers). No rtm changes needed.

## Scope — in

1. Bump `lilo-rm-{client,core}` 0.6.1 → 0.6.3, and add matching `isolation` + `image` fields to `sm_core::SpawnRequest` in one bundled step (cargo check stays green at every commit).
2. Carry `isolation` and `image` through `SpawnLaunch` → daemon `spawn_launch` → `RtmdDriver::spawn` into the outbound rtm-core `SpawnRequest`.
3. **Atomic public-surface step**: add `--isolation` / `--image` clap flags to `RunArgs` AND extend `tools/run.toml` AND regenerate generated help + MCP schemas + snapshots. These three changes are bound by the `build.rs` codegen pipeline and must land together to keep CI green.
4. Read the new MCP arguments in the daemon handler.
5. CLI surface regression test (worker-closeable). Real-rtmd smoke is at plan-level merge gate, not a per-step acceptance.

## Scope — out

- **No rtm changes.** rtm-core 0.6.3 already exposes `IsolationPolicy::{Host, Docker(IsolationProfile { name })}` and image routing; the preflight at `runtime-matters/crates/rtm-daemon/src/spawn_preflight.rs:75-101` already gates profile names.
- **No bind-mount support.** Separate concern; see `~/.mdx/projects/rtm-mount-analysis--{claude,codex}.md`. Acceptance command does not need it; the existing fixed `--mount type=bind,src={cwd},dst={cwd}` at `runtime-matters/crates/rtm-daemon/src/docker_argv.rs:80-81` gives the spawned runtime caller-cwd access. `agent.toml` does not gain mount semantics.
- **No agent.toml schema expansion** to set defaults for `isolation`/`image` (or `role`/`runtime`/`dir`/`target`). Defer until a named caller asks; the acceptance command supplies these via CLI flags.
- **No `Session.isolation` / `Session.image` persistence.** Wire and driver tests prove the launch path. SQLite migration + renderer updates can land as a follow-up.
- **No duplicate validation in sm.** rtm owns profile acceptance (`spawn_preflight.rs:75-101`). sm parses with `IsolationPolicy::from_str` and forwards; malformed profile names produce a rtm-side rejection at preflight, not an sm-side error.
- **No MCP `workspace` alias removal.** That belongs to the existing `agent-config-plan.md` Step 5.
- **No `RunArgs.detach` fix.** Adjacent parse-but-ignore bug noted in prior analyses; separate ticket.
- **No interactive auth bridge.** Whether Claude inside the spawned container can authenticate without showing a login prompt depends on its own auth logic and the shape of the `CLAUDE_CODE_OAUTH_TOKEN` value passed. Documented as a follow-up; this plan ships env-key delivery, not credential validity.

## Steps

### Step 1 — Bump rtm wire deps 0.6.1 → 0.6.3 + add `isolation`/`image` to `sm-core::SpawnRequest`

**Files:** `Cargo.toml:31-32`, `Cargo.lock` (regenerated), `crates/sm-core/src/proto.rs:16-38, 405-472`.

Bundle the dep bump with the sm-core wire field additions so the workspace builds at every commit. Bump `lilo-rm-client` and `lilo-rm-core` from `"0.6.1"` to `"0.6.3"`. Verify: 0.6.1's `SpawnRequest` lacks `isolation` and `image` (per `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/lilo-rm-core-0.6.1/src/types.rs:273-285`); 0.6.3's includes them (`lilo-rm-core-0.6.3/src/types/spawn.rs:76-101`). `IsolationPolicy` re-exports at `lilo-rm-core-0.6.3/src/isolation.rs:9-13, 60-63`.

Add to `sm_core::SpawnRequest`:
- `isolation: lilo_rm_core::IsolationPolicy` — defaults to `Host` via rtm-core's `#[derive(Default)]`. Use `#[serde(default)]`.
- `image: Option<String>` — defaults to `None`. Use `#[serde(default, skip_serializing_if = "Option::is_none")]`.

Re-export `IsolationPolicy` (and `IsolationProfile` if needed) from `sm_core` so downstream callers don't import `lilo-rm-core` directly. Mirrors how `sm_core::RuntimeKind` abstracts over rtm.

Update the round-trip serde tests at `crates/sm-core/src/proto.rs:405-472`: cover encode/decode of a Docker payload with image, and a legacy payload that omits both fields defaulting to `Host`/`None`.

**Acceptance test.** `cargo check --workspace` clean. `cargo tree -p sm-driver -i lilo-rm-core` shows 0.6.3. `cargo test -p sm-core spawn_request_round_trips_as_tagged_json` (or equivalent new test) covers a Docker + image payload. A new test confirms missing fields default to `IsolationPolicy::Host` + `image: None`.

### Step 2 — Carry through `SpawnLaunch`, `spawn_launch`, and `RtmdDriver::spawn`

**Depends on:** Step 1.

**Files:** `crates/sm-driver/src/driver.rs:21-28`, `crates/sm-daemon/src/handler.rs:606-641`, `crates/sm-driver/src/rtmd.rs:48-80`, `crates/sm-driver/tests/rtmd_spawn.rs:23-72`, `crates/sm-daemon/tests/handler.rs:94-197`, `crates/sm-daemon/tests/common/mod.rs:259-270` (fake `SpawnDriver`).

Add `isolation` + `image` to `SpawnLaunch`. In `spawn_launch`, copy from `request.{isolation,image}` (no defaulting logic — sm-core's wire defaults already handle absence). In `RtmdDriver::spawn`'s outbound `lilo_rm_core::SpawnRequest` construction (`rtmd.rs:60-68`), set `isolation: launch.isolation.clone()` and `image: launch.image.clone()`.

**No validation logic in sm.** rtm owns profile acceptance at `runtime-matters/crates/rtm-daemon/src/spawn_preflight.rs:75-101`; a malformed `docker:custom` produces a rtm preflight error surfaced through the normal `RpcResponse::Error` path. Do not pre-empt that boundary.

If multiple daemon tests need the same new field additions to their request literals, factor a local fixture helper rather than copy-paste.

**Acceptance test.** This step is where field-forwarding proof lives, at two layers:

1. **Daemon-internal fake `SpawnDriver`** (`MockDriver` at `crates/sm-daemon/tests/common/mod.rs:30-68`, used by `agent_config_env_reaches_spawn_driver` at `crates/sm-daemon/tests/handler.rs:95-149`): new test `isolation_and_image_reach_spawn_driver` constructs a `SpawnRequest` with `Docker(IsolationProfile { name: None })` + `Some("runtime-matters-claude:local")`, asserts both reach the fake driver's `SpawnLaunch` via its `launches()` accessor.
2. **Fake-rtmd server** (`crates/sm-driver/tests/rtmd_spawn.rs:23-72` precedent): extend `rtmd_spawn_forwards_env_shell_resume_and_force` (or sibling test) to assert isolation + image reach the fake rtmd server's recorded request.

Existing `agent_config_env_reaches_spawn_driver` continues to pass with default `Host` / `None`.

### Step 3 — `--isolation`/`--image` clap flags + `tools/run.toml` + regenerated MCP + help (atomic)

**Depends on:** Step 1.

**Files (must land together as one atomic filing pair to keep CI green):**

- `crates/sm-cli/src/cli/cli_def.rs:78-90` (RunArgs)
- `crates/sm-cli/src/cli/run.rs:12-55` (spawn_session)
- `tools/run.toml:22-25, 67-141` (source of truth)
- `crates/sm-cli/build.rs:19-39, 201-224, 227-288` (codegen)
- `crates/sm-cli/src/cli/generated_help.rs` (regenerated — do not edit directly)
- `crates/sm-cli/src/mcp/generated_schema/{session_run,agent_run}.json` (regenerated)
- `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@{session_run,agent_run}.snap` (insta-accepted)
- `crates/sm-cli/tests/cli_get_test.rs:58-88` (declarative/imperative split assertions)
- `crates/sm-cli/tests/cli_help_surface_test.rs:41-59` (help-surface assertions)
- `crates/sm-cli/tests/generated_surface_guard_test.rs:103-114` (constants-have-consumers)

**Why atomic.** Clap flags reference `generated_help::SESSION_RUN_{ISOLATION,IMAGE}_HELP` constants that `build.rs` generates from `tools/run.toml`. The constants-have-consumers test at `generated_surface_guard_test.rs:103-114` asserts every generated constant has a Rust consumer. So:

- `tools/run.toml` change alone → `generated_help_constants_have_source_consumers` fails (constants generated, no consumer).
- Clap field addition alone → `cargo check` fails (constants don't exist).

The agent-config-plan precedent already follows this codegen pattern. Land as one sub-issue / one PR.

**What.**

Add two `[[tools.session_run.params]]` entries between the existing `agent_config` block and the `target` block in `tools/run.toml`. String type for `isolation` with help text describing the three accepted shapes (`host`, `docker`, `docker:PROFILE`); do not enumerate only `host`/`docker` because rtm accepts profile names like `own-init`, `allow-root`, `arm64-manifest-escape`. Update the run-tool top-level description to mention Docker isolation and image selection.

Add two clap fields to `RunArgs` (alongside `--target`, `--force`, `--detach`), **NOT** to `SessionCreateArgs`. The existing imperative/declarative split is load-bearing: `sm run` is imperative (spawn now with full target controls); `sm create session` is declarative (record session intent with defaults). `--isolation` and `--image` are runtime controls; they belong with the imperative cluster. The existing assertion test `create_session_help_exposes_only_declarative_arguments` at `crates/sm-cli/tests/cli_get_test.rs:58-75` enforces this boundary and must continue to pass.

Field shapes:
- `isolation: Option<lilo_rm_core::IsolationPolicy>` — clap derives the parser from the rtm-core type's existing `FromStr` impl at `lilo-rm-core-0.6.3/src/isolation.rs:36-58` (`host` / `docker` / `docker:PROFILE`).
- `image: Option<String>` — no type validation at clap; rtm handles validation.

In `spawn_session` at `run.rs:38-55`, pass values into the outbound `SpawnRequest`: `args.isolation.unwrap_or_default()` and `args.image`. `create_session` calls `spawn_session(args, "headless", false)` (per `run.rs:12-14`) — its callers will not see `--isolation` / `--image` in clap, so the wire request will carry defaults from sm-core (`Host` / `None`), unchanged from today's behavior.

Regenerate via `build.rs`. `cargo insta accept` for both MCP schema snapshots — `agent_run` aliases `session_run` per `tools/run.toml:139-141`, so both snapshots update together.

**Acceptance test.**
- `sm run claude --isolation docker --image X --role x --dir /tmp` parses successfully (current failure is `error: unexpected argument '--isolation' found`).
- `sm create session --help` does NOT show the two new flags. `create_session_help_exposes_only_declarative_arguments` continues to pass.
- `run_help_describes_every_flag` (`cli_help_surface_test.rs:41-59`) extended to assert both new flags appear in `sm run --help`.
- `generated_help_constants_have_source_consumers` (`generated_surface_guard_test.rs:103-114`) passes — new constants have real Rust consumers.
- `mcp_each_tool_snapshot` passes after `cargo insta accept`.

### Step 4 — MCP handler reads the new arguments

**Depends on:** Steps 1 and 3 (the latter for the schema fields).

**File:** `crates/sm-daemon/src/mcp_tools.rs:116-152`.

In the `agent_run` handler (which `session_run` dispatches into), read:
- `isolation`: optional string parsed with `IsolationPolicy::from_str`; defaults to `Host` on absence; return a structured MCP error on parse failure (use the existing `anyhow!` idiom).
- `image`: optional string.

Populate alongside `agent_config`, `labels`, `target`, `force` in the constructed `SpawnRequest`.

**Acceptance test.** Daemon-level MCP handler test, NOT using `DaemonFixture` (which runs a real `rtmd`/`smd` pair and a PATH-shell-script fake runtime downstream of the spawn driver — cannot inspect `SpawnLaunch`). Use the daemon test harness's fake `SpawnDriver` at `crates/sm-daemon/tests/common/mod.rs:30-68` (the same precedent as `agent_config_env_reaches_spawn_driver` in Step 2). Invoke `mcp_tools::call_tool` directly at `crates/sm-daemon/src/mcp_tools.rs:16-41`. An `agent_run` invocation with `"isolation": "docker", "image": "runtime-matters-claude:local"` reaches the fake `SpawnDriver`'s recorded `SpawnLaunch` with those values populated. A malformed `"isolation": "kubernetes"` returns a structured MCP error pointing at the unknown isolation policy.

### Step 5 — CLI surface regression test (worker-closeable)

**Depends on:** Step 3.

**File:** new test in `crates/sm-cli/tests/cli_isolation_test.rs` (or sibling to `cli_get_test.rs`).

**Scope.** This step proves the CLI *surface* accepts the new flags and rejects malformed values. It does **not** attempt to observe `SpawnLaunch.isolation` or `SpawnLaunch.image` end-to-end from the CLI layer — that observation is not implementable with `DaemonFixture` + the fake-runtime PATH shell script, because the fake runtime runs *after* the driver has already forwarded the wire request. Field-forwarding proof lives in Step 2's daemon fake `SpawnDriver` test and the fake-rtmd-server test, plus Step 4's MCP-handler test.

**Acceptance test.**

1. `sm run claude --isolation docker --image runtime-matters-claude:local --role x --dir <tempdir>` parses successfully and reaches the daemon (or daemon fixture) without clap rejecting the flags. The fake runtime under `DaemonFixture` exits cleanly; the session is created.
2. Existing host-isolation host-spawn smoke (without `--isolation`/`--image`) still passes — defaults preserve today's behavior.
3. `sm run claude --isolation kubernetes --role x --dir <tempdir>` fails at clap with a parse error referencing the accepted shapes (`host`, `docker`, `docker:PROFILE`). This relies on `IsolationPolicy::from_str` returning `IsolationPolicyParseError`; the clap derive surfaces it as a parse error.

This step is closeable by any worker with the repo checked out and `cargo test` available. Real rtmd, real docker, and real auth state are not required — that lives in the plan-level Merge gate.

## Cross-plan dependency on agent-config-plan

**Independent.** This plan and `~/.mdx/projects/agent-config-plan.md` share `tools/run.toml` and `crates/sm-cli/src/cli/cli_def.rs` as touch points but at non-overlapping additions. agent-config-plan tightens `is_path_like`, lifts a predicate to `sm-core`, adds a typed `AgentConfigToml`, and edits `agent_config` help text. This plan adds two unrelated params (`isolation`, `image`) and threads them through wire + driver. Either can land first. If both land simultaneously, expect a trivial conflict in `tools/run.toml` and `cli_def.rs` resolvable in seconds.

## Acceptance signal (plan level)

### Per-step acceptance

Every step above has a worker-closeable acceptance test. When Steps 1-5 are all complete and their tests pass:

- `cargo check --workspace` clean.
- `cargo test --workspace` clean — including the new Step 2 daemon + driver field-forwarding tests, Step 3 help-surface + snapshot tests, Step 4 MCP-handler tests, Step 5 CLI surface regression.
- `cargo insta test --review` clean.

### Merge gate (operator-managed, not a per-step worker task)

Before the merged work ships, run the end-to-end smoke with the full operator stack:

**Provision.** Running `rtmd`, running `smd`, `runtime-matters-claude:local` image present locally, `~/.agm/auth-passthrough/agent.toml` configured with a valid `CLAUDE_CODE_OAUTH_TOKEN` (verified non-leak via `chmod 600`).

**Smoke command.**
```sh
sm run claude --target tmux:3:1.1 --role pm --label app=nginx \
  --isolation docker --image runtime-matters-claude:local \
  --agent-config auth-passthrough
```

**Pass criteria.**
- `sm run` returns a session id; `sm get session id:<uuid> --show-labels` shows running state with label `app=nginx`.
- The Docker container is alive (`docker ps` shows `rtm-<session-uuid>`).
- The container env contains the `[env]` keys from `~/.agm/auth-passthrough/agent.toml`, including `CLAUDE_CODE_OAUTH_TOKEN` (verifiable via `docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}'`).

**Out of scope for the merge gate.** Whether Claude inside the container reaches its main `›` prompt without showing a login screen depends on Claude's own auth logic and the validity / shape of the `CLAUDE_CODE_OAUTH_TOKEN` value — that's the credential-bridge follow-up. The merge gate proves **env-key delivery**, not credential acceptance. Filesystem access to host `~/.claude` is also out of scope — `agent.toml` does not mount host paths.

**No substitutes.** If the operator stack is unavailable, the merge gate has not run. Do not substitute a host-isolation smoke. The point of this plan is the docker path.

### Repo gate

`fmm validate` reports current. `just check && just build && just test` clean.

## Non-goals & known follow-ups

- Persist `isolation` + `image` on `Session` (SQLite migration following `crates/sm-store/src/sqlite/migrations.rs:90-94` precedent, plus renderer updates).
- Bind-mount support — see ranked options in `~/.mdx/projects/rtm-mount-analysis--{claude,codex}.md`. Until then, only caller cwd is mounted into the container.
- agent.toml schema expansion to let a named profile carry default `isolation`/`image`/`role`/`runtime`/`dir`/`target`.
- **Credential bridge** for interactive Claude auth — env passthrough works for inference per `~/.mdx/projects/auth-token-debug--{claude,codex}.md`, but interactive TUI auth in the spawned container may want mounted config or in-spawn `claude auth login`. Distinct concern from the env-key delivery this plan ships.
- MCP `workspace` alias removal — belongs to `agent-config-plan.md` Step 5.
- `RunArgs.detach` parse-but-ignore — adjacent bug, separate ticket.
- Codex parity for the `claude_config_dir` ergonomic shortcut — independent of this plan.

## Filing

After clean consensus sign-off, file as a Linear sub-parent with one sub-issue per step (1-5). Step ordering: 1 → 2 → 3 → 4 → 5. Step 2, Step 3, and Step 4 can be parallelized after Step 1 lands, with the constraint that Step 4 references the schema added in Step 3. Step 5 depends on Step 3 (clap flags must exist). The plan-level merge gate is the responsibility of the sub-parent issue, not any single sub-issue. Each sub-issue references this doc and cites file:line for the change site. Apply `helioy-tools:linear-workflows` at filing time.

## Consensus change log

Revision applied 2026-05-22 from MoE peer-consensus pass on `sm-isolation-signoff` topic:

1. Step 6's smoke gate moved out of per-step acceptance into a plan-level "Merge gate" subsection under "Acceptance signal". A step's acceptance must be worker-closeable; the smoke gate requires operator-managed state (running rtmd/smd, local docker image, valid OAuth token) and cannot be a sub-issue gate.
2. Step 6 rewritten as a CLI surface regression test (now Step 5). The original claim that `DaemonFixture` + fake-runtime PATH shell script could observe `SpawnLaunch.isolation`/`SpawnLaunch.image` was not implementable — the fake runtime runs downstream of driver forwarding. Field-forwarding proof relocated to Step 2's daemon fake-`SpawnDriver` test and the fake-rtmd-server test, plus Step 4's MCP-handler test.
3. Steps 3 (clap flags) and 4 (`tools/run.toml` + regen) merged into one atomic Step 3. The `tools/run.toml` → `generated_help.rs` → clap-consumer trio is bound by the `build.rs` codegen pipeline; either change alone breaks CI (`generated_help_constants_have_source_consumers` fails one direction; `cargo check` fails the other). Same precedent agent-config-plan already follows.
4. Plan-level acceptance and merge-gate wording tightened to env-key delivery only. Pre-empted any framing that implied filesystem `~/.claude` access through `agent.toml`. Mount support is out of scope; `agent.toml`'s `claude_config_dir` lands as a `CLAUDE_CONFIG_DIR` env var inside the container but does not mount the host path. The credential-bridge concern (whether Claude inside skips the login prompt with valid env auth) is documented as a follow-up, separate from env-key delivery.
