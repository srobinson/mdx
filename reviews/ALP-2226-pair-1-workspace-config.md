# ALP-2226 Post Execution Review — Pair 1: ALP-2237 + ALP-2238

Reviewer: nancy-ALP-2212:helioy-tools:code-reviewer:4:4.1
Branch: nancy/ALP-2212
Worktree: /Users/alphab/Dev/LLM/DEV/TMP/nancy-worktrees/nancy-ALP-2212
Date: 2026-05-02

## Summary

Verdict: **Accept** with one Minor finding.

Both issues meet their full acceptance criteria. The Cargo workspace skeleton (ALP-2237) compiles cleanly, exposes only `setup` and `go` as recognized subcommands, rejects unknown commands with a typed error, leaves the Bash bridge default off, and stays under the repo LOC limit. The config primitives (ALP-2238) load `.nancy/config.json` into typed structs, accept the `provider` alias used by Bash, detect the legacy shape (missing `agents` or incomplete agent entries), surface a typed `MissingConfig` error that `go` routes to `setup`, and ship five unit tests plus a Bash-vs-Rust setup parity test that asserts byte-for-byte JSON equality.

Verification run during review:

* `cargo check -p nancy-live` → clean.
* `cargo test -p nancy-live --lib -- config:: workspace::` → 9 tests pass (5 config, 4 workspace).
* `nancy-live unsupported` → exits 2 with `Unsupported nancy-live subcommand: unsupported`.
* `nancy-live` (no args) → exits 2 with `Missing nancy-live subcommand`.
* `live::bridge_enabled` returns false when `NANCY_RUST_LIVE_ENABLED` is unset.

LOC budget: largest file is `src/go.rs` at 696 lines, under the 700 cap. All other crate files are well under.

## Per-Issue Findings

### ALP-2237 — Cargo workspace skeleton

| AC | Status | Evidence |
|---|---|---|
| `cargo check -p nancy-live` passes | Met | Verified locally; `Finished dev profile`. |
| `nancy-live setup` and `nancy-live go` parse as recognized subcommands | Met | `crates/nancy-live/src/lib.rs:118-124` |
| Unsupported subcommands fail with a clear error | Met | `crates/nancy-live/src/lib.rs:42-44` and runtime check above. |
| Bash bridge remains default off | Met | `src/live/bridge.sh:6-11`; default `0` returns `1`. |
| No new files under Bash `src/` or `tests/`; LOC under repo rules | Met | All Rust lives under `crates/`; max LOC 696. |
| Module stubs for `config`, `workspace`, `linear`, `selector`, `prompt`, `gate`, `task`, `supervisor` | Met (with addition) | `crates/nancy-live/src/lib.rs:5-15`; an additional `worktree` module is present, introduced by later authorized work (ALP-2239). |

Notes:

* `Cargo.toml` uses `resolver = "3"` and `edition = "2024"`. Compatible and idiomatic for the toolchain in use.
* `LiveError` correctly aggregates `CliError`, `GoError`, `SetupError` with `From` impls and `source()` chain.
* `next_required_arg` and `reject_extra_args` cover the `go <id>` arity contract; extra args after `setup` are silently ignored, which matches Bash `cmd::setup "${@:2}"` behavior.
* `main.rs` exits with code `2` on any error, including missing/unsupported subcommand. Bash uses `1` for similar errors. The bridge is opt-in and downstream callers do not currently inspect the code, so this is a quiet difference, not a functional break.

### ALP-2238 — Config loading primitives

| AC | Status | Evidence |
|---|---|---|
| Load current `.nancy/config.json` into typed structs | Met | `crates/nancy-live/src/config.rs:121-149`; test `load_config_reads_current_config_shape`. |
| Detect legacy shape lacking required agent entries | Met | `config.rs:181-215`; tests `load_config_detects_legacy_config_shape` and `load_config_detects_incomplete_agent_entries`. |
| Agent selection reads worker/reviewer CLI plus model without shell parsing | Met | `config.rs:62-75` (`agent`, `worker_agent`, `reviewer_agent`); used in `go.rs:332-398`. |
| Missing config produces a typed error that callers can route to setup | Met | `ConfigError::MissingConfig` at `config.rs:46-47`; `go::ensure_setup` at `go.rs:315-330` matches both `MissingConfig` and `LegacyAgentShape` and re-runs setup. |
| Tests cover current, legacy, and missing config | Met | Five unit tests in `config.rs:251-374`. |

Notes:

* `RawConfig` reads `cli // provider` for both top-level and per-agent, mirroring `src/config/config.sh:15-24` and `src/config/config.sh:53-72`. Provider fallback test at `config.rs:291-318`.
* `require_agent` rejects missing fields and empty strings (`config.rs:202-215`), aligning with Bash `config::has_agent_shape` (`config.sh:162-175`).
* `DEFAULT_TOKEN_THRESHOLD = 0.20` matches Bash default at `config.sh:21-23`.
* `setup_parity` integration test (`tests/setup_parity.rs:80-121`) asserts `assert_eq!(read_config(rust), read_config(bash))`, which is the strongest possible parity contract for the config write side.
* Top-level `cli`, `model`, and `git.auto_commit` are loaded into the struct but not consumed by the runtime. This faithfully mirrors the Bash codebase, where `auto_commit` is also written by setup and never read. Preserving the shape is required by the AC ("preserve current `.nancy/config.json` behavior").

## Cross-Issue Notes

The horizontal seam between the two issues is exercised by the setup parity test and by `go::ensure_setup`:

* `setup` writes to `paths.nancy_dir.join("config.json")` (`setup.rs:298`), which composes via `WorkspacePaths::from_roots` (`workspace.rs:54-64`) using `NANCY_DIR_NAME = ".nancy"`.
* `load_config` reads from `project_root.join(CONFIG_RELATIVE_PATH)` where `CONFIG_RELATIVE_PATH = ".nancy/config.json"` (`config.rs:7`, `config.rs:117-119`).

These independently encoded paths happen to compose to the same on-disk location today, but the two constants are not coupled. See **F1** below.

`go::ensure_setup` correctly routes both `MissingConfig` and `LegacyAgentShape` back through `run_setup_from_env`, then re-loads. Other `ConfigError` variants (read failure, invalid JSON) propagate up. This matches the Bash flow in `cmd::go` (`src/cmd/go.sh:11-27`).

## Severity Index

| ID | Severity | Title | File:Line |
|---|---|---|---|
| F1 | Minor | `.nancy` directory name is independently encoded in `workspace.rs` and `config.rs` | `workspace.rs:7`, `config.rs:7` |

### F1 — Minor: `.nancy` path is independently encoded in two crate constants

**Where**

* `crates/nancy-live/src/workspace.rs:7` defines `NANCY_DIR_NAME = ".nancy"`, used to build `WorkspacePaths::nancy_dir = project_root.join(".nancy")`.
* `crates/nancy-live/src/config.rs:7` defines `CONFIG_RELATIVE_PATH = ".nancy/config.json"`, used by `config_path` and `load_config`.

**Why it matters**

`setup` writes via `paths.nancy_dir.join("config.json")`, which composes through the workspace constant. `load_config` reads via the config constant. They land on the same file today only because both literals contain `.nancy`. If `NANCY_DIR_NAME` is ever renamed (parallel to a Bash change in `nancy:11` `NANCY_DIR_NAME=".nancy"`), `setup` will write to the new location while `load_config` continues reading the old one, with no compile-time signal. Bash avoids this by composing `NANCY_CONFIG_FILE=$NANCY_DIR/config.json` from a single source (`nancy:20-22`).

**Suggested fix**

Have `config.rs` derive its path from the workspace constant rather than re-encoding it. One small option: replace `CONFIG_RELATIVE_PATH` with a function `config_path(workspace: &WorkspacePaths)` that returns `workspace.nancy_dir.join("config.json")`. Callers that already have `WorkspacePaths` (`go::ensure_setup`, future setup parity work) pass it in; tests that build a synthetic project root can call a thin helper that constructs `WorkspacePaths::from_roots`.

**Severity rationale**

Minor because the bug is latent (only triggers on a future rename) and the test suite would catch it quickly. Worth tightening because the AC for ALP-2238 explicitly calls out preserving `.nancy/config.json` behavior, and a single source of truth for that path keeps the contract visible.

## Out of Scope For This Pair

The following observations belong to later pairs in the ALP-2226 review fan-out and are not filed here:

* `worktree.rs` in the module list belongs to ALP-2239 path discovery review.
* `go.rs` at 696 LOC is close to the 700 cap; future additions in that file should refactor first. Belongs to a later pair.
* `SETUP_TOKEN_THRESHOLD` is hardcoded at `setup.rs:12` (Bash uses a per-CLI map at `setup.sh:13-16`). Both supported CLIs map to `0.30` today, so there is no current divergence. Belongs to ALP-2240 (setup command parity) review if that pair surfaces it.
