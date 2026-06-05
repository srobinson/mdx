# Plan: plumb `--isolation` and `--image` through `sm`

**Author:** `session-matters:helioy-tools:codebase-analyst:2:3.1` (Claude pane of MoE pair)
**Source synthesis:** `~/.mdx/projects/agent-config-analysis--{claude,codex}.md`, `~/.mdx/projects/rtm-mount-analysis--{claude,codex}.md`, `~/.mdx/projects/auth-token-debug--{claude,codex}.md`, plus direct re-reads of source @ HEAD `b919b3d` (release 0.2.5)
**Repo:** `littleorgans/session-matters`
**Status:** independent draft for orchestrator synthesis with Codex peer

## Pre-flight context

littleorgans (the four sibling repos: identity-matters, session-matters, runtime-matters, transport-matters) is pre-release with **zero downstream users**. Breaking changes are welcome and expected. `MEMORY.md` records this stance explicitly: "drop deprecation shims by default". Do not propose backward-compat shims, additive-only schemas, or staged deprecations for compat reasons. Where the cleanest change is breaking, take the breaking change. The sm-core wire `SpawnRequest` and sm-driver `SpawnLaunch` are internal types with no external consumers; extending them with required-default fields is free.

## Goal

Make `sm run claude --isolation docker --image runtime-matters-claude:local …` produce a Claude TUI inside a runtime-matters-supplied docker container. The work is **entirely sm-side**: rtm already implements isolation and image end-to-end (verified in `~/.mdx/projects/rtm-mount-analysis--claude.md` §1-3 and `~/.mdx/projects/auth-token-debug--codex.md` §2-3 — including a passing regression test at `crates/rtm-cli/tests/spawn_target.rs:196-259` that proves env passthrough through `docker run --env`). Bump the rtm wire dep, add the two fields to the sm-side request and driver carrier, expose them on the CLI and MCP surfaces, prove end-to-end.

## Scope — in

1. **Bump `lilo-rm-client` / `lilo-rm-core` 0.6.1 → 0.6.3** so the wire types carry `isolation: IsolationPolicy` and `image: Option<String>`.
2. **Add `isolation` and `image` to `sm-core::SpawnRequest`** as wire fields.
3. **Add `isolation` and `image` to `sm-driver::SpawnLaunch`** and forward both through `RtmdDriver::spawn` into the outbound `lilo_rm_core::SpawnRequest`.
4. **Add `--isolation` and `--image` clap flags** to `SessionCreateArgs` so both `sm run` and `sm create session` accept them.
5. **Extend `tools/run.toml`** with `isolation` and `image` params; regenerate MCP schemas, generated help, and snapshot assertions.
6. **Extend `agent_run`/`session_run` MCP handler** in `mcp_tools.rs` to read the two new arguments.
7. **CLI integration test** that drives the exact acceptance command end-to-end through `DaemonFixture` to a fake runtime that records the wire payload.

## Scope — out

- **No rtm changes.** rtm-core 0.6.3 already exposes `IsolationPolicy::{Host, Docker(IsolationProfile { name })}` (`lilo-rm-core-0.6.3/src/isolation.rs:9-13, 60-63`), `--image` is parsed and routed (`docker_runtime.rs`, `docker_argv.rs:48-64`), and the preflight allow-list at `crates/rtm-daemon/src/spawn_preflight.rs:75-101` already gates the docker profile names. Nothing to add upstream.
- **No mount field.** Bind-mounting host paths into the container is a separate concern (see `rtm-mount-analysis`); it is not on the acceptance path because the existing fixed `--mount type=bind,src={cwd},dst={cwd}` at `crates/rtm-daemon/src/docker_argv.rs:80-81` already gives the spawned runtime access to the caller cwd, which is what the acceptance command needs.
- **No schema expansion for `agent.toml`** to set defaults for `isolation`/`image` (or `role`/`runtime`/`dir`/`target`). Defer until a named caller wants it; the acceptance command supplies these via CLI flags.
- **No `Session.isolation` / `Session.image` persistence.** The wire carries them; observability via `sm get session` can land as a follow-up. Persistence requires a SQLite migration, a `Session` struct field, and renderer updates — none on the critical path.
- **No bare `docker:` value alias.** `IsolationPolicy::FromStr` at `lilo-rm-core-0.6.3/src/isolation.rs:36-58` already accepts `host`, `docker`, and `docker:PROFILE`. Reuse it; do not invent a sm-side parser.

## Steps

### Step 1 — Bump rtm wire deps 0.6.1 → 0.6.3

**File:** `Cargo.toml:31-32`.

Change `lilo-rm-client = "0.6.1"` and `lilo-rm-core = "0.6.1"` to `"0.6.3"` at the workspace deps. This makes `lilo_rm_core::SpawnRequest` carry `isolation: IsolationPolicy` and `image: Option<String>` (verified at `lilo-rm-core-0.6.3/src/types/spawn.rs:76-101`) and re-exports `IsolationPolicy`/`IsolationProfile` (`lilo-rm-core-0.6.3/src/isolation.rs:9-13, 60-63`).

Expected fallout: `crates/sm-driver/src/rtmd.rs:60-68` will **stop compiling** because the exhaustive struct literal there omits the two new fields. Steps 2-3 fix the compile error; do not patch with `..Default::default()` as a band-aid — fix the carrier types so the data flows from CLI to rtmd.

**Acceptance test.** `cargo check --workspace` fails at `crates/sm-driver/src/rtmd.rs:60-68` with E0063 (missing fields `isolation`, `image`). This is the only desired regression from Step 1 in isolation.

### Step 2 — Add `isolation` and `image` to the sm wire

**Depends on:** Step 1.

**File:** `crates/sm-core/src/proto.rs:17-38`.

Extend `SpawnRequest` with two fields, mirroring the rtm side's serde shape:

- `#[serde(default)] pub isolation: lilo_rm_core::IsolationPolicy` — defaults to `Host` via the rtm-core `#[derive(Default)]`.
- `#[serde(default, skip_serializing_if = "Option::is_none")] pub image: Option<String>`.

Re-export the type out of `sm_core` so consumers can name it without depending on `lilo-rm-core` directly (this avoids leaking the crate name across module boundaries that already abstract over rtm via `sm_core::RuntimeKind`).

Update the round-trip test at `crates/sm-core/src/proto.rs:405-449` to cover the new fields. The legacy-payload decoder at lines 429-449 should still parse a v0.2.5 payload (both new fields default), and a payload with `"isolation": {"type":"docker","payload":{"name":"locked"}}` and `"image":"runtime-matters-claude:local"` should round-trip.

**Acceptance test.** New unit test `spawn_request_round_trips_with_isolation_and_image` next to `spawn_request_round_trips_as_tagged_json` at `crates/sm-core/src/proto.rs:405-427`, plus a legacy-payload test confirming default `IsolationPolicy::Host` and `None` for `image` when the fields are absent.

### Step 3 — Plumb through `SpawnLaunch` and `RtmdDriver::spawn`

**Depends on:** Step 2.

**Files:** `crates/sm-driver/src/driver.rs:21-28`, `crates/sm-driver/src/rtmd.rs:48-80`, `crates/sm-daemon/src/handler.rs:606-641`.

Three coupled touches that all live or die together; file them as one sub-issue.

1. `SpawnLaunch` at `driver.rs:21-28` gains `pub isolation: lilo_rm_core::IsolationPolicy` and `pub image: Option<String>`. The trait `SpawnDriver` (lines 88-122) does not change shape — `SpawnLaunch` is the carrier.
2. `RtmdDriver::spawn` at `rtmd.rs:48-80` adds the two fields to the outbound `lilo_rm_core::SpawnRequest` construction at lines 60-68: `isolation: launch.isolation.clone()`, `image: launch.image.clone()`. This is the line that drops to defaults today even though the wire type accepted them once we bump deps.
3. `spawn_launch` at `crates/sm-daemon/src/handler.rs:606-641` populates the two new `SpawnLaunch` fields from `request.isolation` and `request.image`. No defaulting logic; the wire `SpawnRequest` default already gave us `Host` / `None`.

Update the rtmd driver test at `crates/sm-driver/tests/rtmd_spawn.rs` (cited at line 23-70 in Codex's agent-config-analysis §7) to populate `isolation` and `image` in the constructed `SpawnLaunch` and assert the wire `SpawnRequest` round-trips them to the fake rtmd.

**Acceptance test.** Existing daemon test `agent_config_env_reaches_spawn_driver` at `crates/sm-daemon/tests/handler.rs:95-149` continues to pass with `isolation = Host`, `image = None` defaults. New test alongside it that constructs a `SpawnRequest` with `isolation = Docker(IsolationProfile { name: None })` and `image = Some("runtime-matters-claude:local")`, asserts the values arrive at the fake spawn driver's `SpawnLaunch`.

### Step 4 — Add `--isolation` and `--image` to the CLI

**Depends on:** Step 2.

**Files:** `crates/sm-cli/src/cli/cli_def.rs:94-107`, `crates/sm-cli/src/cli/run.rs:38-55`.

Add two clap fields to `SessionCreateArgs` (lines 94-107). Placement after `agent_config` keeps the `--help` output aligned with the agent-config and target/force clustering at `tools/run.toml:115-137`:

- `pub isolation: Option<lilo_rm_core::IsolationPolicy>` with `#[arg(long, value_parser = clap::value_parser!(lilo_rm_core::IsolationPolicy), help = generated_help::SESSION_RUN_ISOLATION_HELP)]`. The type implements `FromStr` (`lilo-rm-core-0.6.3/src/isolation.rs:36-58`) — clap derives the parser from that.
- `pub image: Option<String>` with `#[arg(long, help = generated_help::SESSION_RUN_IMAGE_HELP)]`. No type validation at clap; the daemon side does not need it either.

In `spawn_session` at `run.rs:38-55`, pass them into the `SpawnRequest` construction. `args.isolation.unwrap_or_default()` for the wire field (preserves the `IsolationPolicy::Host` default explicitly).

Inheritance: `RunArgs.session: SessionCreateArgs` at `cli_def.rs:79-80` already flattens the new flags into `sm run` automatically. The `Create::Session(SessionCreateArgs)` variant at `cli_def.rs:170-174` does the same for `sm create session`.

**Acceptance test.** Existing help-surface assertion at `crates/sm-cli/tests/cli_help_surface_test.rs:41-59` is extended to assert `--isolation` and `--image` appear in `sm run --help`. The brief's acceptance command parses to `Ok(_)` (the empirical failure mode today is `error: unexpected argument '--isolation' found`).

### Step 5 — Extend `tools/run.toml`, regenerate schemas, snapshots

**Depends on:** Step 4.

**Files:** `tools/run.toml` (source), `crates/sm-cli/src/cli/generated_help.rs` (regenerated), `crates/sm-cli/src/mcp/generated_schema/{session_run,agent_run}.json` (regenerated), `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@*.snap` (insta-accepted).

Append two `[[tools.session_run.params]]` entries to `tools/run.toml` between the existing `agent_config` block (lines 115-121) and the `target` block (lines 123-129):

```toml
[[tools.session_run.params]]
name            = "isolation"
type            = "string"
required        = false
mcp_description = "Runtime isolation policy. host (default) runs the runtime as a normal process; docker[:PROFILE] runs it inside a runtime-matters-supplied container."
cli_help        = "Runtime isolation policy. host (default), docker, or docker:PROFILE."
cli_flag        = "--isolation"

[[tools.session_run.params]]
name            = "image"
type            = "string"
required        = false
mcp_description = "Container image reference used when isolation is docker[:PROFILE]. Required for docker isolation; ignored for host."
cli_help        = "Container image reference used with --isolation docker. Required for docker isolation; ignored for host."
cli_flag        = "--image"
```

The `tools/run.toml` param entries drive `build.rs` (cited at `crates/sm-cli/build.rs:201-224` in the agent-config-plan), which regenerates `generated_help.rs` constants `SESSION_RUN_ISOLATION_HELP` / `SESSION_RUN_IMAGE_HELP` (Step 4 references these) and the MCP JSON schemas. `cargo insta accept` updates the two snapshots that pin `session_run` and `agent_run` (the alias at `tools/run.toml:139-141` means both get the new params automatically).

**Acceptance test.** `cargo insta test --review` passes cleanly. `cargo run --bin sm -- run --help` shows the two new flags with the help text from `tools/run.toml`. The MCP schema JSON files contain both `isolation` and `image` under `properties`.

### Step 6 — Wire the MCP handler

**Depends on:** Step 2.

**File:** `crates/sm-daemon/src/mcp_tools.rs:116-152`.

In `agent_run` (which the `session_run` MCP tool dispatches into via the alias), add two argument reads alongside the existing optional reads at lines 127-135:

- `let isolation = optional_string(arguments, "isolation").map(IsolationPolicy::from_str).transpose()?.unwrap_or_default();`
- `let image = optional_string(arguments, "image").map(ToString::to_string);`

Insert into the constructed `SpawnRequest` (lines 140-152) at the natural alphabetical / logical position next to `agent_config`. Surface a structured error if `IsolationPolicy::from_str` fails (today's helper returns `IsolationPolicyParseError` from `lilo-rm-core-0.6.3/src/isolation.rs:65-67`; convert to `anyhow!` to keep parity with the existing handler error idiom).

**Acceptance test.** MCP-level smoke via `crates/sm-cli/tests/cli_get_test.rs` style: an MCP `session_run` call with `"isolation": "docker", "image": "runtime-matters-claude:local"` reaches the fake spawn driver with the corresponding `SpawnLaunch` fields populated. A malformed `"isolation": "kubernetes"` returns an MCP-level error.

### Step 7 — CLI end-to-end integration test for the acceptance command

**Depends on:** Steps 1-6.

**File:** new test in `crates/sm-cli/tests/cli_get_test.rs` or a sibling like `crates/sm-cli/tests/cli_isolation_test.rs`.

Use the existing `DaemonFixture` plumbing (cited at `crates/sm-cli/tests/common/mod.rs:27-65, 207-228` in Codex's agent-config-analysis §7) with a fake runtime that records `SpawnLaunch.isolation` and `SpawnLaunch.image` into a temp file. Invoke the exact acceptance command shape:

```
sm run claude --target tmux:3:1.1 --role pm --label app=nginx \
    --isolation docker --image runtime-matters-claude:local \
    --agent-config <stubbed-toml-path>
```

(The integration test uses an explicit `--agent-config` path to a stub TOML in a tempdir, since `~/.agm/auth-passthrough` is operator state.) Assert: exit zero, the fake runtime captured `Docker(IsolationProfile { name: None })` and `Some("runtime-matters-claude:local")`, and the `SpawnLaunch.env` includes the `[env]` keys from the stub `agent.toml`.

This is the only test that proves the whole chain (CLI → sm wire → SpawnLaunch → outbound rtm wire) is bytes-correct for both fields simultaneously.

**Acceptance test.** This step *is* the acceptance test for the plan.

## Cross-plan dependency on agent-config-plan

**Independent.** The two plans share `crates/sm-cli/src/cli/cli_def.rs:94-107` (`SessionCreateArgs`) and `tools/run.toml` as touch points but at non-overlapping additions. agent-config-plan tightens `is_path_like`, lifts a predicate to `sm-core`, adds a typed `AgentConfigToml` struct in `crates/sm-daemon/src/agent_config.rs`, and edits `agent_config`'s help text. This plan adds two unrelated params (`isolation`, `image`) and threads them through the wire and driver. No serialization or resolution dependency runs between them.

Order: either plan can land first. If both land, the resulting `tools/run.toml` lists `agent_config`, `isolation`, `image`, `target`, `force` in source order — the regenerated `session_run.json` and `agent_run.json` snapshots will combine cleanly. If they overlap in time, expect a trivial conflict in `tools/run.toml` and in `crates/sm-cli/src/cli/cli_def.rs:94-107` resolvable in seconds.

## Acceptance signal

The brief's exact command:

```
sm run claude --target tmux:3:1.1 --role pm --label app=nginx \
    --isolation docker --image runtime-matters-claude:local \
    --agent-config auth-passthrough
```

succeeds end-to-end:

- The spawned session reaches a Claude TUI in tmux pane `3:1.1`, running inside a docker container from `runtime-matters-claude:local`.
- The container inherits the env keys defined in `~/.agm/auth-passthrough/agent.toml` (e.g. `CLAUDE_CODE_OAUTH_TOKEN`, verified to passthrough by the rtm regression test at `crates/rtm-cli/tests/spawn_target.rs:196-259` and the sentinel test in `~/.mdx/projects/auth-token-debug--codex.md` §3).
- `sm get session id:<uuid>` returns the new session record. (`isolation` and `image` are not persisted in v1 — see Scope — out.)
- `cargo check --workspace`, `cargo test --workspace`, and `cargo insta test --review` all pass cleanly.

## Non-goals & known follow-ups

- **Persist `isolation` and `image` on `Session`.** Add columns via the existing migration pattern at `crates/sm-store/src/sqlite/migrations.rs:90-94` (the `add_tmux_and_agent_config_columns` precedent), surface in `sm get session` output. Useful for debugging, not on the critical path.
- **Bind-mount support.** rtm-side `--mount` is not yet implemented (see `~/.mdx/projects/rtm-mount-analysis--claude.md` §5 for the smallest-delta design). Until then, only the caller cwd is mounted into the container; host `~/.claude` is not.
- **agent.toml schema expansion.** Let `~/.agm/<name>/agent.toml` set defaults for `isolation`, `image`, `role`, `runtime`, `dir`, `target` so a named profile carries more than env. This is the right design after this plan lands and a named caller asks for it.
- **rtm docker profile allow-list reach.** The rtm preflight gate at `crates/rtm-daemon/src/spawn_preflight.rs:75-101` rejects unknown profile names. If a caller passes `--isolation docker:custom`, the spawn fails at rtm preflight, not at the sm wire. Surfacing that error path cleanly through sm is operator-friendly but not blocking.
- **`Codex` profile parity.** `agent_config` today special-cases `claude_config_dir` (`crates/sm-daemon/src/agent_config.rs:73-96`). No equivalent shortcut exists for Codex. Independent of this plan.
- **`RunArgs.detach` parse-but-ignore.** Documented in agent-config-analysis as a separate adjacent issue at `crates/sm-cli/src/cli/cli_def.rs:88-89` vs `crates/sm-cli/src/cli/run.rs:12-14`. Unrelated.

## Filing

After clean consensus sign-off, file as a Linear sub-parent under the relevant session-matters parent (`ALP-…`), with one sub-issue per step (1-7). Step ordering matters: Step 1 (dep bump) before Step 2-3 (wire + driver), Step 2 before Step 4-6 (CLI / MCP both reference the new sm-core wire type), Step 7 last. Each sub-issue references this doc and cites file:line for the change site. Apply the `helioy-tools:linear-workflows` skill at filing time.

## Verification notes

- Cargo.toml dep pin verified: `lilo-rm-client = "0.6.1"` and `lilo-rm-core = "0.6.1"` at `Cargo.toml:31-32`. The brief's claim of "0.6.3" describes the *target* of Step 1, not present state.
- 0.6.1 `SpawnRequest` shape (no isolation, no image): `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/lilo-rm-core-0.6.1/src/types.rs:273-285`.
- 0.6.3 `SpawnRequest` shape (with isolation, with image): `lilo-rm-core-0.6.3/src/types/spawn.rs:76-101`.
- 0.6.3 `IsolationPolicy` FromStr accepting `host` / `docker` / `docker:PROFILE`: `lilo-rm-core-0.6.3/src/isolation.rs:36-58`.
- `crates/sm-driver/src/rtmd.rs:60-68` SpawnRequest construction with exactly 7 fields verified by direct read.
- `crates/sm-driver/src/driver.rs:21-28` SpawnLaunch struct with 6 fields (no isolation, no image) verified by direct read.
- `crates/sm-core/src/proto.rs:17-38` sm wire SpawnRequest with 12 fields (no isolation, no image) verified by direct read.
- `crates/sm-cli/src/cli/cli_def.rs:94-107` SessionCreateArgs with 6 clap fields (no --isolation, no --image) verified by direct read.
- `crates/sm-cli/src/cli/run.rs:38-55` spawn_session SpawnRequest construction verified by direct read.
- `crates/sm-daemon/src/handler.rs:606-641` spawn_launch carrying 6 fields into SpawnLaunch verified by direct read.
- `crates/sm-daemon/src/mcp_tools.rs:116-164` agent_run/session_run handler reading individual arguments verified by direct read.
- `tools/run.toml:80-141` MCP param source-of-truth verified by direct read.
- rtm-side claims (existing `--env` plumbing, image routing, profile allow-list, regression test) sourced from `~/.mdx/projects/rtm-mount-analysis--claude.md`, `~/.mdx/projects/auth-token-debug--{claude,codex}.md`; not re-verified here because no rtm change is in scope.

Read-only audit on session-matters. No repo writes.
