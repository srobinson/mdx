---
title: Phase 4 session import issue review for littleorgans
type: research
tags: [littleorgans, linear, session-import, moe-review, fmm]
summary: Live MoE reviews of ALP-2814 found pass 1 source contract defects and pass 2 operator gate, LOC policy, and PER reopen defects.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Executive Summary

ALP-2814 is the Phase 4 plan to import `session-matters` into the littleorgans monorepo. Pass 2 found three execution blocking defects in the current Linear issues: W4 omits the repo native `just` gate, W4 states an impossible literal LOC cap, and the gate lacks late arrival PER reopen language.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Source repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`
- Source branch and HEAD: `main`, `abed9b8d6cdc2a2ac9ea694773a76874c5cd70af`
- fmm status: both repositories have `.fmm.db`; `session-matters` passed `fmm validate` across 159 files
- Linear scope: ALP-2814, ALP-2845, ALP-2846, ALP-2847, ALP-2848, ALP-2849, ALP-2850, ALP-2851
- Local platform used for command checks: macOS Darwin 25.5, `/bin/bash` 3.2.57, `/usr/bin/grep` BSD grep 2.6.0 compatible mode

## Architecture

Phase 4 imports the session substrate into the monorepo:

- `sm-paths` folds into `crates/lilo-paths` via ALP-2846.
- `sm-core`, `sm-store`, `sm-driver`, `sm-daemon`, and `sm-cli` become internal crates under `internal/session/{core, store, driver, daemon, app}` via ALP-2847.
- `session-matters/MAP.md` and `PROJECT.md` merge into `docs/architecture/session.md` via ALP-2848.
- ALP-2849 performs acceptance, fmm regeneration, provenance refresh, commit, and push.
- ALP-2850 reviews worker outcomes before Phase 4 closeout.

The filed Linear relation chain matches the gate order: ALP-2846 before ALP-2847 before ALP-2848 before ALP-2849 before ALP-2850.

## Key Patterns

- Use fmm first for topology and source contracts. The monorepo index currently reports 174 files and 23,632 LOC across `internal/`, `crates/`, and `tools/`.
- Treat verification commands as executable contracts. A command that can pass while skipping the repo native gate is a gate defect.
- Keep LOC policy tied to the canonical script. In this repo, `scripts/check-loc-limit.sh` owns prunes, extensions, and the 700 line threshold.

## Detailed Findings

### Pass 2 F1: W4 omits the repo native `just` gate

Evidence:

- `justfile:10-17` defines the canonical `build` and `test` targets. `just test` runs `cargo nextest run --workspace`, which is not the same surface as `cargo test --workspace`.
- `justfile:69-75` defines `check-loc`, `check-provenance`, and `check`; `just check` includes `fmt`, `clippy-fix`, `fmt-check`, LOC, provenance, and final clippy.
- ALP-2849's current verification block uses direct `cargo fmt`, `cargo clippy`, `cargo build`, `cargo test`, `cargo doc`, and `moon ci` commands. It does not run `just check && just build && just test`.

Impact:

W4 can commit without proving the required operator gate. The current issue misses `check-provenance` and the `nextest` test surface, both of which are repo native closeout checks.

Required change:

Add `just check && just build && just test` to ALP-2849 acceptance and verification before commit, or replace it with exact justfile equivalent proof that includes `check-provenance` and `nextest`.

### Pass 2 F2: W4 states an impossible literal LOC cap

Evidence:

- ALP-2849 says no file outside `target/` or `.git/` exceeds 700 LOC.
- Current files outside those directories already exceed that literal statement: `Cargo.lock` is 2,762 LOC, `.moon/cache/schemas/project.json` is 2,177 LOC, and `.moon/cache/schemas/tasks.json` is 1,714 LOC.
- `scripts/check-loc-limit.sh:15-19` prunes `.git`, `.moon/cache`, `.nancy`, and `target`, then checks only authored source extensions: `*.rs`, `*.ts`, `*.tsx`, `*.js`, `*.jsx`, and `*.py`.

Impact:

The reviewer cannot falsify the stated cap consistently. The ad hoc W4 `find ... wc ... awk` proof can disagree with the repo native LOC policy and with files that already exist before Phase 4.

Required change:

Align W4 acceptance and verification to `scripts/check-loc-limit.sh`, plus explicit checks for docs introduced by W3. Alternatively, restate the cap as authored source files covered by the repo LOC script.

### Pass 2 F3: Gate lacks late arrival PER reopen language

Evidence:

- ALP-2851 currently authorizes `Execute: ALP-2846, ALP-2847, ALP-2848, ALP-2849, ALP-2850`.
- ALP-2851 does not state that a future Execute set amendment after ALP-2850 reaches `Done` must reopen ALP-2850 and add matching review bullets.
- ALP-2850 says corrective issues are created, appended to the gate `Execute:` line, and linked via `blocks`, but the gate does not protect the after closure case.

Impact:

A late corrective or added worker after PER closure can be authorized without a mirrored PER review surface. That makes the new wave structurally unreviewable by Nancy's selector and review lifecycle.

Required change:

Add gate language that any future Execute set amendment after ALP-2850 is `Done` must reopen ALP-2850 and add matching acceptance bullets before execution.

## Verified Non Findings From Pass 2

- W3 source LOC claims are accurate: `session-matters/MAP.md` is 480 LOC and `PROJECT.md` is 51 LOC.
- `docs/architecture/runtime.md` contains the expected sections at `docs/architecture/runtime.md:11`, `:29`, `:55`, `:100`, `:121`, `:149`, `:162`, and `:175`.
- Current `crates/lilo-paths/src/` is split into `runtime.rs` at 393 LOC, `lilo.rs` at 324 LOC, and `lib.rs` at 15 LOC. Folding the 331 LOC `sm-paths` source into a new session module is plausible under the 700 LOC cap.
- The tested BSD command surfaces behaved as expected on macOS: BSD `grep` accepted `--include` and `--exclude-dir`, Bash 3.2 expanded `internal/session/{app,core,daemon,driver,store}`, and BSD `wc -l` emitted a `total` row for the multi file LOC command.

## Earlier Pass 1 Findings Kept For Continuity

The prior pass found and the orchestrator amended source contract and verification defects:

- Remove claims that fmm indexes Markdown docs. Verify `docs/architecture/session.md` with file, line count, and grep checks instead.
- Bind the W2 daemon adapter to actual source exports: `run_daemon(paths: SmPaths)` and preserved `send_request`.
- Aggregate jq dependency checks with a single `all()` assertion across all `lilo-session-*` packages.
- Move daemon Insta snapshot review to the app surface.
- Enumerate W2 workspace dependency additions and version or feature policies.

## Dependencies

Critical dependencies and tools reviewed:

- Linear live issues for ALP-2814 and children.
- fmm MCP and CLI for topology, source outlines, and symbol checks.
- `justfile` and `scripts/check-loc-limit.sh` for repo native verification policy.
- macOS BSD shell tools for copy paste safety checks.
- `session-matters` source at `abed9b8d6cdc2a2ac9ea694773a76874c5cd70af`.

## Relevance to Helioy

These findings protect Nancy execution from ambiguous or impossible gates. The reusable rule is to keep issue verification anchored to repo native operator commands and to encode PER reopen behavior whenever a gate's authorization list can be amended after review closure.

## Peer Consensus Status For Pass 2

The peer pane reported no additional substantive findings after probing BSD command behavior, `lilo-paths` cap pressure, implicit preconditions, and W3 source claims. It independently accepted C9-1, C6-1, and C5-1 as substantive. This pane sent `A|accept:none-substantive|reject:none|missing:none` and then signed off conditional on the three edits.

## Verification After Pass 2 Amendment

The orchestrator applied the pass 2 edits and requested `VERIFY v1` for ALP-2849, ALP-2850, and ALP-2851. Live Linear was reread for all three issues. ALP-2849 now anchors on `just check`, `just build`, and `just test`, adds `bash scripts/check-provenance.sh`, keeps `moon ci` as the CI gate, and preserves supplementary `--all-features` cargo proofs. ALP-2849 and ALP-2850 now bind LOC review to `scripts/check-loc-limit.sh` and explicitly exclude generated, lock, and cache files from the LOC claim. ALP-2851 now carries a binding `Late-arrival PER reopen` section, and ALP-2850 cross-references it in the corrective outcome path.

A clean `V|I sign off on ALP-2849, ALP-2850, ALP-2851 as currently filed` was sent on `ALP-2814-review-pass2`.

## Open Questions

- Whether future MoE passes should explicitly include `justfile` parity in the standard probe list for every phase acceptance worker.
