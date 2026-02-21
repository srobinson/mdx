# Plan: `sm run --agent-config` honest & debuggable

> **Status:** 2026-05-22 planning snapshot. Superseded by the live Linear tree under master `ALP-2763` (workers `ALP-2765`-`ALP-2771`, PER `ALP-2772`, gate `ALP-2773`). Subsequent MoE peer-consensus passes extended scope (MCP-side canonicalization, direct serde dep on sm-daemon, full build.rs output lockstep) and refined acceptance/verification. Linear is authoritative; this document is preserved as the planning-time consensus.

**Author:** orchestrator (`session-matters:general:2:2.1`)
**Source synthesis:** `~/.mdx/projects/agent-config-analysis--{claude,codex}.md`
**Repo:** `littleorgans/session-matters` @ `b919b3d`
**Status:** consensus-revised — both MoE panes signed off conditional on this revision; awaiting clean re-sign-off

## Pre-flight context

littleorgans (the four sibling repos: identity-matters, session-matters, runtime-matters, transport-matters) is pre-release with **zero downstream users**. Breaking changes are welcome and expected. `~/.claude/projects/.../memory/MEMORY.md` records this stance explicitly: "drop deprecation shims by default". Do not propose backward-compat shims, additive-only schemas, or staged deprecations for compat reasons. Where the cleanest change is breaking, take the breaking change.

## Goal

Turn `--agent-config` from "small, intentional, undebuggable" into "small, intentional, debuggable, and correct" in one cohesive change. Keep the feature shape (env mutation only — no runtime/role/dir defaults yet); fix the rough edges that make it hard to use and verify today.

## Scope — in

1. **Persist the resolved path on `Session.agent_config`.**
2. **Tighten `is_path_like` and lift the predicate** into `sm-core` so CLI and daemon share one source of truth.
3. **CLI-side path canonicalization** against caller cwd, before crossing the smd wire.
4. **Typed `AgentConfigToml` schema** replacing hand-walked `toml::Value`.
5. **MCP schema truthfulness** — `dir` required to match the handler; drop the `workspace` input alias entirely.
6. **CLI help parity** with the MCP description (`~/.agm/<name>/agent.toml`), sourced from `tools/run.toml`.
7. **CLI integration test** for the not-found error render path.

## Scope — out

- Schema expansion to set defaults for `role`, `runtime`, `dir`, `target`, `isolation`, `image`, `labels`. Defer until we have one named caller asking for it.
- Seeding `~/.agm/` from `sm doctor` or shipping `examples/agent.toml`. Follow-up.
- Fixing the adjacent `RunArgs.detach` parse-but-ignore bug (`crates/sm-cli/src/cli/cli_def.rs:88` vs `crates/sm-cli/src/cli/run.rs:12-14`). Separate issue.
- Anything in runtime-matters.

## Steps

### Step 1 — Replace `Session.agent_config` with the resolved path

**File:** `crates/sm-daemon/src/handler.rs:176`, `crates/sm-core/src/session.rs:83`.

`Session.agent_config: Option<String>` currently stores `request.agent_config` verbatim. Change it to store the **resolved filesystem path** (`agent_config.path.display().to_string()`). The verbatim request is recoverable from the path; the path is not recoverable from a bare name. This is a breaking semantic change on the persisted field shape and on `sm get session` output. Acceptable.

Touch:

- `crates/sm-daemon/src/handler.rs:176` — set from `resolved.path` when present, else `None`.
- SQLite store + read paths (`crates/sm-store/src/sqlite/sessions.rs:31-55,271-298`) — no schema change; column type stays `TEXT`.

No new column. No additive `agent_config_path` field.

**Acceptance test (new).** Add a daemon-level test that resolves a **named** config (`~/.agm/<name>/agent.toml`, prepared in a tempdir with `HOME` overridden) and asserts `Session.agent_config` persists as the *resolved* path (`<tempdir>/.agm/<name>/agent.toml`), not the bare name. The existing tests at `crates/sm-daemon/tests/handler.rs:130-133` (explicit-path input — old and new behavior identical) and `crates/sm-cli/tests/cli_get_test.rs:182` (no `--agent-config` — both compared fields are `null`) do not prove the change and must not be relied on as the acceptance signal.

### Step 2 — Tighten `is_path_like` and lift the predicate to `sm-core`

**File:** `crates/sm-daemon/src/agent_config.rs:56-61`. New home: `sm-core` (shared by daemon resolution and CLI normalization in Step 3).

Drop the `ends_with(".toml")` clause. Path mode iff: contains `MAIN_SEPARATOR`, starts with `~`, or starts with `.`.

Side effect: `--agent-config tools.toml` now resolves as a **name** under `~/.agm/tools.toml/agent.toml`, not as a relative path. This is a behavior break for the (likely-empty) set of callers passing bare filenames. Acceptable per pre-flight context.

Add unit tests covering: `tools.toml` → name; `./tools.toml` → path; `/abs/x.toml` → path; `~/x.toml` → path; bare `demo` → name.

**Step 2 must land before Step 3** — Step 3 reuses this predicate from `sm-core`. Workers must not re-implement the predicate in the CLI before this step lifts it. If steps are filed as parallel sub-issues, declare Step 3 as blocked on Step 2 explicitly.

### Step 3 — Canonicalize relative `--agent-config` paths in the CLI

**Depends on:** Step 2 (predicate lifted to `sm-core`).

**File:** `crates/sm-cli/src/cli/run.rs:36-47`.

Today the CLI sends the raw string. If the user passes `./demo.toml`, the daemon resolves against **its own cwd**, not the caller's. Fix CLI-side: in `spawn_session`, when `args.agent_config` is path-like by the `sm-core` predicate from Step 2, canonicalize against caller cwd; pass an absolute path. Names (no separator, no leading `.`, no `~`) pass through unchanged.

Expected shape: a CLI-side helper like `normalize_agent_config_arg(value: Option<&str>) -> Result<Option<String>>`. Expand `~` and `~/...` using the caller's HOME, then `fs::canonicalize` if the file exists; if not, leave absolutized-but-unverified so the daemon produces the existing not-found error with a useful path.

### Step 4 — Typed `AgentConfigToml` schema

**File:** `crates/sm-daemon/src/agent_config.rs:35-96`.

Replace the hand-rolled `toml::Value` walking in `agent_env` (lines 73-96) with a typed deserialize:

- Optional top-level `claude_config_dir: String`, optional `env: BTreeMap<String, String>`.
- `serde(deny_unknown_fields)` is intentional — silent ignoring of unknown top-level keys is a footgun for callers experimenting with future schema. Better to fail loudly than silently drop a typo'd `clade_config_dir`. This is a breaking change relative to today's permissive parse; per pre-flight context, fine.

Preserve the current error messages where possible (callers might grep them in tests).

**Preserve env-key precedence (critical).** Current `agent_env` semantics: `[env].CLAUDE_CONFIG_DIR` **overrides** the top-level `claude_config_dir` because top-level is inserted into the BTreeMap first and `[env]` writes after, last-write-wins. A naïve deserialize that flattens both into a single output map could silently invert this if the implementation merges in the wrong order. The typed rewrite must preserve "top-level inserted first, `[env]` inserted after (and therefore wins on collision)".

**Acceptance test (new).** Unit test that loads an `agent.toml` with both top-level `claude_config_dir = "A"` and `[env]\nCLAUDE_CONFIG_DIR = "B"`, and asserts the resulting `LaunchEnv` for `CLAUDE_CONFIG_DIR` carries `"B"`.

### Step 5 — MCP `session_run` schema: drop `workspace`, require `dir`, regenerate both aliases

**Files:** `tools/run.toml` (source), `crates/sm-cli/src/mcp/generated_schema/session_run.json`, `crates/sm-cli/src/mcp/generated_schema/agent_run.json`, `crates/sm-daemon/src/mcp_tools.rs:123-126`.

Two changes, applied together:

1. Mark `dir` as required in `tools/run.toml`. Schema currently lists only `runtime` + `role`, but the handler at `crates/sm-daemon/src/mcp_tools.rs:121-126` rejects requests without `dir` (or the deprecated `workspace`). Make the schema match handler truth.
2. **Drop the `workspace` MCP input alias entirely** at `crates/sm-daemon/src/mcp_tools.rs:123-126` (the handler fallback that accepts `workspace` when `dir` is missing). Per pre-flight stance, the alias is dead-compat surface. `SpawnRequest.workspace` may remain as an internal core field if `agent_run`/`session_run` still populate it from `dir`, but the MCP input field is gone.

Regenerate **both** `session_run.json` and `agent_run.json` — `agent_run` is a `session_run` alias per `tools/run.toml:139-141`, so any required-field change must reach both generated artifacts. Re-run `cargo insta accept` on both insta snapshots that pin these schemas.

### Step 6 — CLI help text parity via source of truth (`tools/run.toml`)

**Files:** `tools/run.toml:116-121` (source), `crates/sm-cli/build.rs:201-224` (generator), `crates/sm-cli/src/cli/generated_help.rs` (generated — **do not edit directly**), `crates/sm-cli/tests/cli_help_surface_test.rs:41-59` (assertions).

Update the `cli_help` field for `--agent-config` in `tools/run.toml` to mention the `~/.agm/<name>/agent.toml` convention and the accepted TOML keys:

> Agent config name resolved as `~/.agm/<name>/agent.toml`, or an explicit `agent.toml` path. TOML keys: `claude_config_dir` (string), `[env]` (table of strings).

Then regenerate via the existing `build.rs` flow, which writes `generated_help.rs`, generated templates, and README sections. Update help-surface assertions at `crates/sm-cli/tests/cli_help_surface_test.rs:41-59` to match. **No direct edit to `generated_help.rs`** — it is build output.

### Step 7 — CLI integration test for the not-found error

**File:** new test in `crates/sm-cli/tests/cli_get_test.rs` or a sibling module.

Use the existing `DaemonFixture` plumbing. Invoke `sm run claude --role x --dir $tmp --agent-config does-not-exist`, assert exit non-zero, assert stderr contains `agent config not found: does-not-exist` and the resolved-path hint. This is the only currently untested path from `RpcResponse::Error` to user-visible CLI render.

## Acceptance

- `cargo check --workspace` clean.
- `cargo test --workspace` clean — including the new Step 1 named-config persistence test, Step 2 predicate unit tests, Step 4 env-precedence test, and Step 7 not-found integration test.
- `cargo insta accept` on both `session_run` and `agent_run` MCP schema snapshots (Step 5), plus any help-text snapshots affected by Step 6.
- Manual smoke: both named and explicit-path invocations succeed and the runtime env shows `CLAUDE_CONFIG_DIR` plus `[env]` keys (same as Codex's smoke log from the analysis pass).
- `sm get session id:<uuid>` shows the **resolved path** (not the bare name) in the `agent_config` field.

## Non-goals & known follow-ups

- `~/.agm/` bootstrap UX (`sm doctor` reporter + ship `examples/agent.toml`).
- Schema expansion: defaults for `role`/`runtime`/`dir`/`target`/`isolation`/`image`/`labels`. Brainstorm first.
- `RunArgs.detach` parse-but-ignore. Separate ticket.
- Codex parity for the `claude_config_dir` ergonomic hint — defer until Codex profile use cases land.

## Filing

After clean consensus sign-off, file as a Linear sub-parent under the relevant session-matters parent (`ALP-…`), with one sub-issue per step (1-7). Step 3 carries an explicit dependency on Step 2 in its description. Each sub-issue references this doc and cites file:line for the change site. Apply the `helioy-tools:linear-workflows` skill at filing time.

## Consensus change log

Revision applied 2026-05-22 from MoE peer-consensus pass on `agent-config-signoff` topic:

1. Reordered: predicate tightening + sm-core lift is now Step 2; CLI canonicalization is now Step 3 with explicit dependency declared.
2. Step 1 acceptance now requires a named-config persistence test rather than the two pre-existing tests, which proved nothing about the semantic change.
3. Step 4 adds explicit preservation + test for `[env].CLAUDE_CONFIG_DIR` overriding top-level `claude_config_dir`.
4. Step 5 drops the MCP `workspace` input alias and the `mcp_tools.rs:123-126` handler fallback, requires `dir`, regenerates **both** `session_run` and `agent_run` schemas and snapshots.
5. Step 6 now edits `tools/run.toml` as source of truth and regenerates `generated_help.rs` via `build.rs`, rather than editing the generated file directly.
