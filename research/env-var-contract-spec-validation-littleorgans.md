---
title: Env Var Contract Spec Validation for littleorgans
type: research
tags: [littleorgans, env-vars, spec-validation, codebase-analysis]
summary: Validated the environment variable contract spec and gave clean signoff after the six converged changes were applied.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-03
updated: 2026-06-03
---

## Executive Summary

`docs/reference/env-vars.md` was validated against the locked plan, detector output, peer review, and live Rust source. After the orchestrator applied the six converged changes, Codex re-read the live file and sent the clean signoff phrase.

## Project Metadata

- Language: Rust monorepo.
- Build and gate surface: Cargo, Just, Moon.
- Rust toolchain: 1.95 from `.moon/toolchains.yml:1-2`.
- fmm status: indexed and usable. Initial topology: 383 indexed files, 55,090 LOC, with most source under `internal/` and `crates/`.
- Primary verification commands:
  - `scripts/check-env.sh`
  - `scripts/check-env.sh --check`
  - fmm outlines, symbol reads, and dependency graphs for env related source files.
  - `rg` for raw legacy tokens and detector blind spots after fmm orientation.

## Architecture

The environment contract crosses six implementation seams:

1. `crates/lilo-paths/src/lilo.rs`: owns state root and socket path resolution today. It is also the target home for the future all variable registry.
2. `crates/lilo-common/src/logging.rs`: owns log filter and current format selection for the top level `lilo` binary.
3. `crates/lilo-build-support/src/lib.rs`: owns shared version and git SHA build helpers.
4. `internal/runtime/daemon/src/*`: owns runtime daemon env reads for Docker, reconcile timing, and tmux label.
5. `crates/lilo-rm-core/src/spawn_context.rs`, `internal/session/daemon/src/handler/spawn.rs`, and `internal/runtime/launchers/src/lib.rs`: capture, strip, and inject process env for spawned agents.
6. `scripts/check-env.sh`, `justfile`, and `moon.yml`: target enforcement surfaces for naming and legacy removal.

Data flow is split by class:

- Operator env is read at process start or daemon configuration construction.
- Build env is consumed in `build.rs`, emitted as `cargo:rustc-env`, then read with `env!`.
- Agent contract env is injected as `LaunchEnv` during session or runtime spawn.
- Caller env is captured by `capture_caller_env`, filtered by denylist rules, then merged with child identity values.

## Key Patterns

- Namespace by ownership: `LILO_*` for littleorgans owned vars, `HELIOY_*` for cross agent runtime contract, upstream names for OS, toolchain, and third party runtime vars.
- Delete legacy names rather than aliasing them. This aligns with the no legacy pre release rule.
- Use a central registry plus a central gate rather than per variable deletion guard tests.
- Treat log filtering and log rendering as separate concerns. `LILO_LOG_FORMAT` is the new explicit rendering knob, while `--output json` remains a convenience tier when the env knob is unset.

## Detailed Findings

### Final clean signoff

After the orchestrator rewrote `docs/reference/env-vars.md`, Codex re-read the live file and sent: `I sign off on the env-vars spec as currently filed`. The six conditional changes that enabled the clean signoff were:

> I sign off conditional on the following changes:

1. Keep `LILO_LOG_FORMAT` in the spec as a real NEW target feature, not a live implemented reader. Make the row/prose honest that `select_format` or a new resolver must be changed to read `LILO_LOG_FORMAT`, `LogFormat::Compact` and `.compact()` wiring are new, and `LILO_LOG_JSON` is the only logging env deletion.
2. Fix HELIOY inheritance prose: document the current split and state the target contract that shared caller env/runtime launch paths strip all `HELIOY_SESSION_*` before injecting child identity. This matches the new plan Item 13 defect.
3. Reframe registry and gate enforcement as TARGET/acceptance until Items 10/11 land. The filed spec must not imply current enforcement.
4. Strengthen the gate target language to require raw legacy token scanning across all authored files, wrapper/string/arg/OsString coverage, exact bare `RTM`/`SM`/`AGM`, non Rust scan scope, and real inline `#[cfg(test)]` masking before claiming the gate proves the contract.
5. Classify `SHELL_RESUME_SENTINEL` in the spec: rename it to `LILO_*`/neutral if it is a test sentinel, or give it a `LILO_*` row if it is a real contract.
6. Correct the small spec drift: `LILO_GIT_SHA` default chain is `LILO_GIT_SHA` > `GITHUB_SHA` > `git rev-parse --short=7 HEAD`, and the foreign allowlist should align with the detector/denylist, including `CLAUDECODE` if denylist literals are covered.

### Finding 1: `LILO_LOG_FORMAT` is a real new feature, but the spec must be honest about target implementation

Initial source reading showed a contradiction with the earlier locked plan. The orchestrator then injected owner context and updated the locked plan. Current ground truth now keeps `LILO_LOG_FORMAT`.

Evidence:

- The updated plan says Item 8 is `Introduce LILO_LOG_FORMAT, drop LILO_LOG_JSON`: `~/.mdx/projects/littleorgans-env-config-cohesion-plan.md:141-153`.
- The same plan says Q4 is owner override to introduce `LILO_LOG_FORMAT`: `~/.mdx/projects/littleorgans-env-config-cohesion-plan.md:217-219`.
- The spec row lists `LILO_LOG_FORMAT` as `new`, with values `auto`, `pretty`, `json`, and `compact`: `docs/reference/env-vars.md:38`.
- The spec log precedence section matches the target design: `docs/reference/env-vars.md:108-118`.
- Live source still has only `LogFormat::Json` and `LogFormat::Pretty`: `crates/lilo-common/src/logging.rs:11-14`.
- `output_json_requested` reads CLI args, not env: `crates/lilo-common/src/logging.rs:34-48`.
- `select_format` is pure and returns JSON when `output_json` is true or stderr is not a terminal: `crates/lilo-common/src/logging.rs:50-56`.
- Subscriber setup only calls `.json()` and `.pretty()`: `crates/lilo-common/src/logging.rs:58-71`.
- `LILO_LOG_FORMAT` appears only in the dead no effect test today: `crates/lilo-common/src/logging.rs:102-124`.

Required spec change: keep `LILO_LOG_FORMAT`, but make clear that `select_format` or a resolver is the target reader and that `Compact` plus `.compact()` are not implemented yet. Delete only `LILO_LOG_JSON` and the dead no effect test during implementation.

### Finding 2: HELIOY inheritance wording overclaims `spawn_context`

Evidence:

- The spec says `spawn_context` strips these on re spawn so a child never inherits parent identity: `docs/reference/env-vars.md:61-64`.
- The spec later names the caller env denylist as the stripping mechanism: `docs/reference/env-vars.md:105-106`.
- Live `CALLER_ENV_DENYLIST` strips only `HELIOY_SESSION_ID` and `HELIOY_RUNTIME` from the HELIOY family: `crates/lilo-rm-core/src/spawn_context.rs:10-19`.
- Session backed spawn separately drops all `HELIOY_SESSION_*` before injecting child `HELIOY_SESSION_ID`, `HELIOY_SESSION_ROLE`, and `HELIOY_SESSION_WORKSPACE`: `internal/session/daemon/src/handler/spawn.rs:392-403`.
- Raw runtime host spawn captures caller env through `capture_caller_env`: `internal/runtime/app/src/cli/spawn.rs:84-93`.
- Runtime launcher then upserts only `HELIOY_SESSION_ID` and `HELIOY_RUNTIME`; it does not strip stale role or workspace vars: `internal/runtime/launchers/src/lib.rs:96-115`.
- The updated plan now has Item 13 to fix this defect: `~/.mdx/projects/littleorgans-env-config-cohesion-plan.md:197-206`.

Required spec change: document the current split and state the target contract that shared caller env or runtime launch paths strip all `HELIOY_SESSION_*` before injecting child identity.

### Finding 3: registry and gate enforcement are coherent target architecture, not current source

Evidence:

- The spec says a `lilo-paths` registry and `scripts/check-env.sh` gate enforce the document: `docs/reference/env-vars.md:5-6`.
- It says the gate consumes the registry, traces const indirected reads, masks inline tests, and scans beyond Rust: `docs/reference/env-vars.md:120-128`.
- Current `lilo-paths` only has the home and socket constants, plus `HOME`: `crates/lilo-paths/src/lilo.rs:8-10`.
- Current `scripts/check-env.sh` roots are `crates`, `internal`, `tools`, and `apps`: `scripts/check-env.sh:35`.
- Current detector patterns are literal Rust patterns only: `scripts/check-env.sh:38-47`.
- Current scanner iterates `*.rs` files only: `scripts/check-env.sh:96-124`.
- `just check` does not run `check-env`: `justfile:148`.
- `moon.yml` task `check` does not include `check-env`: `moon.yml:103-109`.
- The locked plan requires hardening and wiring the gate, plus adding the registry, in Items 10 and 11: `~/.mdx/projects/littleorgans-env-config-cohesion-plan.md:162-183`.

Required spec change: label registry and gate claims as target or acceptance behavior until Items 10 and 11 land.

### Finding 4: current gate misses real legacy and misclassifies tests

Peer Claude found several holes, and Codex verified them against the live tree.

Evidence:

- Reconcile timing legacy reads are wrapper string arguments, not detected by the current site regexes: `internal/runtime/daemon/src/reconcile.rs:27,29,33`.
- `RTM_TEST_PRINT_ENV` is embedded in `.arg("RTM_TEST_PRINT_ENV=1")`, not detected by current patterns: `internal/runtime/app/tests/spawn_target.rs:170,286`.
- `RTM_TEST_BAD_BYTES` is created through `OsString::from`, not detected by current patterns: `crates/lilo-rm-core/src/spawn_context.rs:182,184`.
- Bare `RTM` appears in fixture and test support surfaces: `crates/lilo-rm-core/tests/fixtures/v0_5/shim_launch.json:1`, `crates/lilo-rm-core/tests/fixtures/v0_5/CAPTURE.md:87`, `crates/lilo-rm-core/tests/support/mod.rs:42`, and `crates/lilo-rm-core/tests/wire_compat.rs:266`.
- Current `check-env.sh` classifies only `RTM_`, `SM_`, and `AGM_` prefixes as legacy: `scripts/check-env.sh:49-93`.
- Current `is_test_path` is path based. Inline `#[cfg(test)]` blocks are not masked: `scripts/check-env.sh:71-77`.
- The current scan scope excludes docs, fixtures, and justfile: `scripts/check-env.sh:35`, `96-106`.

Required spec change: strengthen target gate language so it cannot be read as satisfied by the current detector.

### Finding 5: `SHELL_RESUME_SENTINEL` is an unclassified owned env var

Evidence:

- `SHELL_RESUME_SENTINEL` is injected as a launch env in shim test code: `internal/runtime/app/src/cli/shim.rs:316`.
- The test asserts the child sees it: `internal/runtime/app/src/cli/shim.rs:328`.
- It is a littleorgans defined env var with no `LILO_` prefix and is absent from the spec tables.

Required spec change: classify it. If it remains a test sentinel, add it to the rename to `LILO_*` or neutral list. If it is real contract, give it a `LILO_*` row.

### Finding 6: small spec drifts

Evidence:

- `LILO_GIT_SHA` explicit override falls back to `GITHUB_SHA` before git HEAD: `crates/lilo-build-support/src/lib.rs:84-103`.
- The spec row names only `git rev-parse --short=7 HEAD` as the default: `docs/reference/env-vars.md:56`.
- The foreign list includes OS, third party, and toolchain vars: `docs/reference/env-vars.md:94-106`.
- The detector has its own third party and OS classifications: `scripts/check-env.sh:53`, `56-59`.
- `CALLER_ENV_DENYLIST` includes `CLAUDECODE`: `crates/lilo-rm-core/src/spawn_context.rs:10-19`.

Required spec change: include the `GITHUB_SHA` fallback tier and align the foreign allowlist with the detector and denylist, including `CLAUDECODE` if denylist literals are in scope.

### Table row validation summary

Rows that matched source and plan, excluding the six conditions above:

- `LILO_HOME`: constant at `crates/lilo-paths/src/lilo.rs:8`; `LiloHome::from_env` reads it and falls back to `$HOME/.lilo` at `crates/lilo-paths/src/lilo.rs:18-25`.
- `LILO_SOCKET_PATH`: constant at `crates/lilo-paths/src/lilo.rs:9`; `socket_path()` overrides only the socket path at `crates/lilo-paths/src/lilo.rs:97-99`.
- `LILO_LOG`: constant at `crates/lilo-common/src/logging.rs:7`; read with default `info` at `crates/lilo-common/src/logging.rs:25-32`.
- Docker rename rows: legacy constants and reads at `internal/runtime/daemon/src/docker_preflight.rs:9-11` and `21-30`; truthy parsing at `internal/runtime/daemon/src/docker_preflight.rs:188-192`.
- Reconcile timing rename rows: current legacy reads at `internal/runtime/daemon/src/reconcile.rs:25-37`; defaults at `internal/runtime/daemon/src/reconcile.rs:13-15`; millisecond parsing at `internal/runtime/daemon/src/reconcile.rs:239-259`.
- `LILO_TMUX_SERVER_LABEL`: constant at `internal/runtime/daemon/src/server/config.rs:10`; read at `internal/runtime/daemon/src/server/config.rs:91-95`.
- `LILO_CLI_VERSION`: top level `lilo` already emits and reads it at `crates/lilo/build.rs:1-3` and `crates/lilo/src/main.rs:10`; runtime and session app still use legacy names at `internal/runtime/app/build.rs:7-8`, `internal/runtime/app/src/lib.rs:13`, `internal/session/app/build.rs:38`, and `internal/session/app/src/lib.rs:18`.
- `LILO_GIT_SHA` and `LILO_VERSION_INCLUDE_GIT_SHA`: build support constants and readers at `crates/lilo-build-support/src/lib.rs:7-8`, `71-78`, and `84-110`; `lilo-rm-core` still uses bespoke `RTM_GIT_SHA` at `crates/lilo-rm-core/build.rs:21-30` and `crates/lilo-rm-core/src/version.rs:44-46`.
- `HELIOY_SESSION_ID` and `HELIOY_RUNTIME`: runtime launcher injects both at `internal/runtime/launchers/src/lib.rs:96-115`; in repo readers exist at `internal/session/app/src/mcp/server.rs:7-20` and `internal/session/app/src/cli/mail.rs:19`, `260-273`.
- `HELIOY_SESSION_ROLE` and `HELIOY_SESSION_WORKSPACE`: session daemon injects both at `internal/session/daemon/src/handler/spawn.rs:397-403`.
- `LILO_LOCAL_BIN`: just recipe variable at `justfile:3` and install target usage at `justfile:76-88`.
- `LILO_BENCH_BIN`: test helper read at `internal/session/app/tests/common/mod.rs:182-187`.
- `LILO_BENCH_SAMPLES`: test helper read at `internal/runtime/app/tests/common/mod.rs:48-54`.
- `LILO_TEST_BIN`: test helper read at `internal/session/app/tests/common/mod.rs:294-299`.
- `LILO_FAULT_NAMESPACE_BINDING_CLEAR`: debug fault injection read at `internal/session/app/src/cli/delete.rs:106-112`.
- `LILO_TEST_PRINT_ENV`: listed as rename target for current `RTM_TEST_PRINT_ENV`, matching current refs in `internal/runtime/app/tests/spawn_target.rs:170`, `286` and fake runtime script at `internal/runtime/app/tests/common/harness.rs:352`.

Completeness against `scripts/check-env.sh` output:

- Current detector reported 13 owned `LILO_*` vars, four `HELIOY_*` vars, three third party vars, four build or CI vars, five OS vars, and six unclassified vars.
- Every live owned `LILO_*` detector entry is represented in the spec or migration text.
- `LILO_LOG_FORMAT` is represented as a new feature, which is correct after owner override.
- All four detected `HELIOY_*` vars are represented.
- The detector omits non Rust authored files and several non literal Rust forms. Spec enforcement claims must be target wording until the gate is hardened.

## Dependencies

Critical dependencies involved in this validation:

- `tracing-subscriber`: provides the current `.json()` and `.pretty()` subscriber paths in `lilo-common`; target implementation will use `.compact()`.
- `uuid`: underlies session and runtime identifiers in the HELIOY contract surface.
- `clap`: drives CLI args used by `--output json`, although `output_json_requested` currently reads `std::env::args_os` directly.
- `tokio`, `sqlx`, and `serde`: broader runtime and session substrate dependencies, not directly changed by the env spec.

## Relevance to Helioy

The `HELIOY_*` env namespace is the cross agent contract that lets spawned agents and the human UI correlate process runtime state to control plane sessions. The raw runtime inheritance gap matters beyond littleorgans because stale `HELIOY_SESSION_ROLE` or `HELIOY_SESSION_WORKSPACE` can confuse any future Helioy component that starts treating those variables as authoritative agent context.

## Open Questions

1. Implementation still needs to land the target contract: `LILO_LOG_FORMAT`, gate hardening, env registry, and `HELIOY_SESSION_*` denylist fix.
2. `SHELL_RESUME_SENTINEL` still needs implementation cleanup to match the newly filed rename note.
3. The detector sets still need reconciliation with the filed foreign allowlist during Items 10 and 11.
