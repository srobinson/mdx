---
title: littleorgans env config cohesion plan validation
type: research
tags: [littleorgans, env-vars, config, moe-review, rust]
summary: Live validation found detector blind spots, drove ten plan changes, and ended with clean MoE sign-off after re-read.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-03
updated: 2026-06-03
---

## Executive Summary

The original env-var and config cohesion plan needed ten corrections before execution: const-read-aware liveness, all-authored-reference gate coverage, logging cleanup, spawned-agent alias removal, fixture cleanup, and a minimal env const registry. After the orchestrator applied those changes, the live plan was re-read and clean MoE sign-off was sent with the exact phrase `I sign off on the env-config plan as currently filed`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Language: Rust workspace, edition 2024, workspace version `0.8.0` in `Cargo.toml:31-33`
- Rust version: `1.95` in `Cargo.toml:38` and `.moon/toolchains.yml:1-2`
- Build system: Cargo plus Moon. Root Moon CI runs `cargo build --workspace`, `cargo clippy --workspace --all-targets`, `cargo nextest run --workspace`, and local scripts in `moon.yml:46-111`
- Local operator surface: `justfile`, with `just check` at `justfile:144-148` and `just regression` at `justfile:150-161`
- fmm status: `.fmm.db` exists. fmm indexed 383 files and 55,090 LOC during this review

## Architecture

The env surface is scattered across small context-specific modules rather than one config layer.

- `crates/lilo-paths/src/lilo.rs` owns path roots and socket override. `LiloHome::from_env` reads `LILO_HOME` through `env_path(LILO_HOME_ENV)` at `lilo.rs:18-25`; `LiloPaths::socket_path` reads `LILO_SOCKET_PATH` at `lilo.rs:97-99`.
- `crates/lilo-common/src/logging.rs` owns logging. `log_filter` reads only `LILO_LOG` at `logging.rs:25-32`; format selection uses CLI output and tty state at `logging.rs:50-56`.
- `crates/lilo-build-support/src/lib.rs` owns build-time version helpers. It reads `LILO_VERSION_INCLUDE_GIT_SHA` at `lib.rs:71-77`, `LILO_GIT_SHA` at `lib.rs:84-92`, and generates seven-character git SHAs at `lib.rs:95-109`.
- `internal/runtime/daemon` owns runtime daemon knobs: Docker preflight in `docker_preflight.rs:21-30`, reconciliation intervals in `reconcile.rs:25-37`, and tmux server label in `server/config.rs:91-95`.
- `internal/runtime/launchers/src/lib.rs` injects runtime session identity into spawned agents at `runtime_env`, lines `96-115`.
- `crates/lilo-rm-core/src/spawn_context.rs` captures and filters caller env. `capture_caller_env` uses `std::env::vars_os()` at `spawn_context.rs:45-47`, and `CALLER_ENV_DENYLIST` includes both `HELIOY_*` and legacy `RTM_*` names at `spawn_context.rs:10-19`.
- `justfile` has env usage not visible to the detector: `LILO_LOCAL_BIN` at `justfile:3` and `LILO_VERSION_INCLUDE_GIT_SHA` assignments at `justfile:65,68`.

## Key Patterns

- Env names are often local private constants with indirect reads. The current detector records declarations, but not actual use through `env::var(CONST)`.
- Inline Rust test modules are common. Path-only test detection mislabels those references as production.
- Some env-like strings live in generated shell scripts or user-facing messages, not in `env::var` calls. A policy gate must scan all authored references, not only Rust env APIs.
- The code already has a good path model in `lilo-paths`: only `LILO_HOME` and `LILO_SOCKET_PATH` are active path controls, and all other paths are derived.

## Detailed Findings

### Detector result

Commands run:

- `scripts/check-env.sh`, full inventory. It reported 159 reference sites across 50 distinct vars.
- `scripts/check-env.sh --check`, gate mode. It failed with 15 legacy vars.
- `scripts/check-env.sh --prod`, prod mode. It still showed inline test env names as production due path-only classification.

### Finding 1: Item 8 is based on a false premise

The plan says `LILO_LOG_JSON` and `LILO_LOG_FORMAT` are overlapping live format knobs. Source shows the opposite.

- `select_format` uses only `output_json` and `stderr_is_terminal`, `crates/lilo-common/src/logging.rs:50-56`.
- `output_json_requested` parses `--output json` and `--output=json`, `logging.rs:34-48`.
- `LILO_LOG_JSON` and `LILO_LOG_FORMAT` appear only in the test `lilo_log_json_env_var_has_no_format_effect`, which sets them and asserts `Pretty`, `logging.rs:102-124`.

Plan change: reframe Item 8 as deletion of inert test-only env names. Do not introduce `LILO_LOG_FORMAT` as a new runtime knob.

### Finding 2: The detector misses const-indirected live reads

`check-env.sh` claims const declarations cover const-indirected reads at `scripts/check-env.sh:23-25`, but its regex set only records declarations at `scripts/check-env.sh:39-47`.

Live read examples missed or misclassified:

- `LILO_LOG_ENV` declared at `logging.rs:7`, read at `logging.rs:26`.
- `LILO_GIT_SHA_ENV` declared at `lilo-build-support/src/lib.rs:7`, read at `lib.rs:85`.
- `VERSION_INCLUDE_GIT_SHA_ENV` declared at `lib.rs:8`, read at `lib.rs:72`.
- `LILO_TMUX_SERVER_LABEL` declared at `runtime/daemon/src/server/config.rs:10`, read at `config.rs:92`.
- `RTM_DOCKER_IMAGE` and allow flags are declared at `docker_preflight.rs:9-11`, then read through constants at `docker_preflight.rs:23,27,28`.
- Reconcile env vars are read through helper calls at `reconcile.rs:27,29,33`.

Plan change: Item 12 must not classify declare-only inventory rows as dead. It must trace const reads or use a detector that does.

### Finding 3: Inline tests corrupt prod-only output

`is_test_path` checks only path segments and file names at `scripts/check-env.sh:71-77`. Inline `#[cfg(test)]` modules in production files are marked production.

Examples:

- `LILO_LOG_JSON` and `LILO_LOG_FORMAT` in `logging.rs:102-124`.
- `RTM_ALLOWED_SENTINEL` and `RTM_PRE_EXISTING_SENTINEL` in `internal/runtime/app/src/cli/shim.rs:274-310`.
- `RTM_TEST` in `internal/runtime/daemon/src/backend.rs:212-219`.
- `RTM_QUOTE` in `internal/runtime/daemon/src/docker_argv.rs:279-299`.

Plan change: prefer all-authored-reference gating over prod-only gating. If prod-only output remains, it needs syntax-aware test detection.

### Finding 4: Non-Rust and embedded env surfaces are missing

The current detector scans only Rust files under `crates`, `internal`, `tools`, and `apps`.

Missed live or policy-relevant surfaces:

- `justfile:3` reads `LILO_LOCAL_BIN` and falls back to `HOME`.
- `justfile:65,68` set `LILO_VERSION_INCLUDE_GIT_SHA` for local and release builds.
- `internal/runtime/daemon/src/error.rs:110` tells users to set `RTM_DOCKER_IMAGE`.
- `internal/runtime/app/tests/common/harness.rs:352` embeds a fake runtime shell script with `RTM_TEST_STDIO_SENTINELS`, `RTM_TEST_TUI_EXIT_WINDOW`, `RTM_TEST_PRINT_CWD`, and `RTM_TEST_PRINT_ENV`.
- `internal/runtime/app/tests/spawn_target.rs:170,286` injects `RTM_TEST_PRINT_ENV` via CLI args.
- `internal/runtime/app/tests/integration_pass5.rs:284` injects `RTM_TEST_TUI_EXIT_WINDOW`.
- `crates/lilo-rm-core/tests/fixtures/v0_5/CAPTURE.md:17-22` contains `RTM_HOME`, `RTM_DB_PATH`, `RTM_SOCKET_PATH`, `RTM_SHIM_PATH`, and `RTM_CAPTURE_OUT`.
- `crates/lilo-rm-core/tests/fixtures/v0_5/shim_launch.json:1` contains bare `RTM`, `RTM_SESSION_ID`, and `RTM_RUNTIME_KIND`.
- `crates/lilo-rm-core/tests/wire_compat.rs:266` and `tests/support/mod.rs:42` contain bare `RTM`, which does not match the current legacy prefix rule.

Checked clean or toolchain-owned surfaces:

- `.cargo/config.toml:1-5` has no env vars.
- `moon.yml:4-5` has only `CARGO_TERM_COLOR`.
- `.moon/toolchains.yml` and `.moon/workspace.yml` have no env vars.
- `.github/workflows/pr.yml:60-65` has no env declarations.

Plan change: Item 10 must extend the gate to authored non-Rust surfaces and embedded strings, or pair the detector with a targeted all-source legacy literal scan.

### Finding 5: Dead and redundant env kill list

Dead or remove-worthy:

1. `LILO_LOG_JSON`, zero live runtime reader. Test-only references at `logging.rs:108,114`; `select_format` ignores env at `logging.rs:50-56`.
2. `LILO_LOG_FORMAT`, zero live runtime reader. Test-only references at `logging.rs:109,115`; `select_format` ignores env at `logging.rs:50-56`.
3. `RTM_SESSION_ID`, write-only alias. Injected at `runtime/launchers/src/lib.rs:108`, denied at `spawn_context.rs:17`, asserted in old fixture tests at `wire_compat.rs:269`, no in-repo `env::var` reader found.
4. `RTM_RUNTIME_KIND`, write-only alias. Injected at `runtime/launchers/src/lib.rs:112`, denied at `spawn_context.rs:18`, asserted in old fixture tests at `wire_compat.rs:270`, no in-repo `env::var` reader found.
5. `RTM_TEST_PRINT_CWD`, embedded fake runtime branch with no in-repo injector. `rg RTM_TEST_PRINT_CWD` found only `internal/runtime/app/tests/common/harness.rs:352`.
6. `RTM_*`, `SM_*`, `AGM_*` legacy-ignored path tests at `lilo-paths/src/lilo.rs:291-299`. These are guard strings, not live reads, but the new policy is no legacy references.

Cleared as live:

- `LILO_BENCH_BIN` is read at `internal/session/app/tests/common/mod.rs:183`.
- `LILO_BENCH_SAMPLES` is read at `internal/runtime/app/tests/common/mod.rs:49`.
- `LILO_TEST_BIN` is read at `internal/session/app/tests/common/mod.rs:295`.
- `LILO_FAULT_NAMESPACE_BINDING_CLEAR` is read at `internal/session/app/src/cli/delete.rs:108`.
- `LILO_HOME` and `LILO_SOCKET_PATH` are live path controls, `lilo.rs:18-25` and `lilo.rs:97-99`.
- `LILO_GIT_SHA` and `LILO_VERSION_INCLUDE_GIT_SHA` are live build controls, `lilo-build-support/src/lib.rs:85` and `lib.rs:72`.
- `LILO_TMUX_SERVER_LABEL` is read at `runtime/daemon/src/server/config.rs:92`.

### Finding 6: Git SHA de-dup needs a new build-support API

Item 2 is directionally right, but the plan understates the implementation detail.

- `crates/lilo-rm-core/build.rs:21-30` emits `RTM_GIT_SHA` using `git rev-parse --short=12 HEAD`, with `unknown` fallback.
- `crates/lilo-rm-core/src/version.rs:45` expects a bare git SHA env value in `VersionInfo.git_sha`.
- `lilo-build-support::emit_cli_version` at `crates/lilo-build-support/src/lib.rs:10-18` emits a package version string, not a bare SHA.
- `lilo-build-support::build_git_sha` returns an `Option<String>` at `lib.rs:80-82`, using either explicit env or Git.
- `short_sha` standardizes seven hex chars at `lib.rs:105-109`.

Plan change: add a build-support function such as `emit_git_sha_env(name: &str)` that emits `cargo:rustc-env=<name>=<sha-or-unknown>`, plus rerun directives. Then `lilo-rm-core/build.rs` can call it with `LILO_GIT_SHA` or another agreed env name.

### Finding 7: Spawned-agent RTM aliases are safe to drop in-repo

In-repo evidence confirms the aliases are write-only.

- Injected by `runtime_env` at `internal/runtime/launchers/src/lib.rs:108,112`.
- Denied from caller env forwarding at `crates/lilo-rm-core/src/spawn_context.rs:17-18`.
- Asserted in `crates/lilo-rm-core/tests/wire_compat.rs:269-270` and fixture JSON.
- No Rust `env::var` or `env::var_os` reader for either alias was found in the current repo.
- Local search of `helioy-plugins` found no `RTM_SESSION_ID` or `RTM_RUNTIME_KIND` consumer.

Plan change: drop the aliases without a deprecation note. v1 is pre-release with zero external users. Clean old fixtures and snapshots in the same item.

### Open question adjudication

- Q1, SHA length: choose seven chars. `lilo-build-support` already standardizes seven, and the field is diagnostic, not protocol compatibility.
- Q2, external alias consumer: drop aliases. No live in-repo reader and no `helioy-plugins` consumer found.
- Q3, legacy-ignored path tests: delete. Keep positive `LILO_HOME` and `LILO_SOCKET_PATH` tests.
- Q4, logging: keep only `LILO_LOG`; format remains CLI output and tty driven.
- Q5, gate scope: all authored references, not prod-only.
- Q6, registry versus Config: use a minimal const registry, not a composed Config type. The likely home is `lilo-paths` because it is lowest dependency and already owns `LILO_HOME` and `LILO_SOCKET_PATH`, but Item 11 stays warroom-worthy because exported env constants widen public API.

### Warroom scoping after adjudication

- Item 1, CLI version unify: no warroom, mechanical rename.
- Item 2, git SHA de-dup: warroom yes, build-support API and SHA semantics.
- Item 3, Docker knobs rename: no warroom, but include `error.rs:110` in target scope.
- Item 4, reconcile knobs rename: no warroom.
- Item 5, drop RTM spawn aliases: warroom yes, contract surface and fixtures.
- Item 6, test sentinels and bare `RTM`: no warroom once targets include embedded fake runtime strings.
- Item 7, legacy-ignored tests: no warroom after Q3 is decided.
- Item 8, logging cleanup: no warroom after Q4 is decided.
- Item 9, documentation sync: no warroom.
- Item 10, gate wiring: no warroom only if the plan explicitly locks roots, prunes, and all-reference behavior.
- Item 11, central env registry: warroom yes.
- Item 12, dead env sweep: no warroom after this liveness pass locks the kill list.

## Dependencies

Critical dependencies for this plan:

- `lilo-build-support`, private build helper used by `crates/lilo`, `internal/runtime/app`, and `internal/session/app` through build dependencies.
- `lilo-paths`, published path contract crate that owns local state root and socket path resolution.
- `lilo-common`, logging and diagnostics crate, currently reads only `LILO_LOG` for logging filter.
- Moon and Just, both need env gate wiring for developer and CI surfaces.

## Relevance to Helioy

This review enforces the pre-release no-legacy rule. It also prevents the plan from creating a new config surface by accident: adding `LILO_LOG_FORMAT` would contradict the existing behavior and prior minimal logging contract. The right correction is deletion and centralization, not compatibility or new knobs.

## Convergence Result

The Claude peer concurred with the added deltas and both panes signed off conditionally on topic `lilo-envcfg-signoff`. The orchestrator then applied all ten consensus changes to `/Users/alphab/.mdx/projects/littleorgans-env-config-cohesion-plan.md` with status `moe-validated-pending-clean-signoff`. I re-read the live plan and confirmed each required change landed: Item 8 logging cleanup, Item 12 const-read-aware liveness and locked kill list, Item 2 `emit_git_sha_env(name)`, Item 3 `error.rs:110`, Item 5 fixture and alias cleanup, Item 6 bare `RTM` and sentinel cleanup, Item 9 docs updates, Item 10 all-reference detector hardening, Item 11 minimal `lilo-paths` const registry, and final warroom scoping. Final clean sign-off was sent to the orchestrator with the exact phrase `I sign off on the env-config plan as currently filed`.

## Open Questions

- Item 11 still needs an implementation design pass on public const placement and how `scripts/check-env.sh` consumes the same source of truth.
- During implementation, old `v0_5` fixtures must be updated or removed so the all-reference gate has no `RTM_*` literals to catch.
