---
title: ALP-2812 Phase 2 identity import gate review
type: research
tags: [littleorgans, alp-2812, phase-2, identity, moe-review, linear]
summary: Pass 3 review found four substantive proof gaps, resolved one verify residual, and closed clean on bilateral verify signoff.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Executive Summary

The ALP-2812 Phase 2 plan imports the three `identity-matters` published crates and adds an internal `lilo-identity-service` factory crate. Live Linear and current source review found the issue set mostly aligned with the monorepo shape, source paths, target paths, and current doctor JSON contract, but W5 and PER still have four substantive proof gaps: remote push proof, repo-native justfile proof, dist target proof after adding rusqlite bundled SQLite, and fmm presence checks that use the wrong `list-files --group-by=subdir` shape.

Findings were sent on helioy-bus topic `alp2812-review-pass3`. My findings message was `e7c748fc-75e5-4a4e-a2db-c7e8e804cd33`. I accepted peer finding `P3-K1` in message `7f6663d0-9e3a-409e-a3c7-422a5f344cdd`, sent conditional signoff in message `231ea8a5-47ed-455c-9d4d-48ff4be29a47`, accepted the peer refinement of `P3-C3` in message `82dbc529-e602-412d-8944-4ecda0990b7b`, sent clean verify signoff in message `969a6bbf-2f68-4e62-997f-d6adb7d9b3f0`, then reopened on residual `P3-K1` in message `ad29a2a7-7ef2-44eb-bdc1-a80a5d526c8b`, accepted final apply with V in message `8048f8cf-2e47-4a84-971f-e58302bc2c73`, and observed peer final V in message `69489fad-8fd2-4a4f-9776-2248b4f94f72`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Branch during review: `chore/justfile-playbook-parity`
- fmm: `.fmmrc.toml` present, `fmm validate` passed for 11 indexed files.
- Language: Rust 2024 workspace, Rust toolchain `1.90` from `.moon/toolchains.yml`.
- Build orchestration: root `justfile`, Cargo workspace, Moon CI, cargo-dist metadata.
- Current workspace members before Phase 2: `crates/lilo`, `crates/lilo-common`, `crates/lilo-paths`, `tools/xtask` in `Cargo.toml:1-7`.
- Configured dist targets: linux gnu, linux musl, and darwin targets in `Cargo.toml:42-52`.

## Architecture and Current Source Fit

Phase 2 targets are absent in the monorepo before execution:

- `crates/lilo-im-core/`
- `crates/lilo-im-store/`
- `crates/lilo-im-stub/`
- `internal/identity/service/`

The source identity repo exists at `../identity-matters`, and `git -C ../identity-matters rev-parse HEAD` returned the expected frozen SHA `e01affa2a6400f3194e1ae236aee04019c1dd3e6`.

The current `lilo doctor` implementation is still an empty structural status. `DoctorCommand::run` renders `DoctorStatus::empty()` in `crates/lilo/src/cli/doctor.rs:13-22`. The JSON shape is `daemon`, `substrates`, and `warnings` from `crates/lilo/src/cli/doctor.rs:25-30`, with a stable unit test at `crates/lilo/src/cli/doctor.rs:63-70`. Phase 2 should not change this shape, and the W5/PER assertions that identity remains absent from doctor output fit the current source.

The CLI version/display contract is current. Clap uses `name = "lilo"`, `display_name = "littleorgans"`, and `version = crate::VERSION` in `crates/lilo/src/cli/mod.rs:43-52`.

## Key Patterns

- The monorepo contract requires the root `justfile` as the operator proof surface. `AGENTS.md:134-140` states `just check && just build && just test` is required before every commit, with raw Cargo commands reserved for Phase 1 acceptance and diagnosing Moon behavior.
- Closeout proof is stricter than narrow worker proof. `AGENTS.md:168-171` repeats `just check && just build && just test`, plus issue-specific checks and `fmm generate && fmm validate` when navigation state changes.
- Current `just test` is not equivalent to raw `cargo test`. The justfile runs `cargo nextest run --workspace` at `justfile:16-17`.
- Current `just check` includes the LOC cap gate through `check-loc` at `justfile:69-72`.
- `fmm list-files --group-by=subdir` at repository root emits top-level buckets only. To prove nested crate roots, scope the command to `crates/` or `internal/`, or drop grouped mode and grep per-file output.

## Detailed Findings

### P3-C1: W5 remote proof is copy-paste unsafe

Evidence:

- Live Linear ALP-2827 Verification ends with `git status -sb | head -1 | grep -E 'main\.\.\.origin/main'`.
- Git status headers with `[ahead 1]` or `[behind 1]` still contain `main...origin/main`, so the command does not prove that push succeeded or that local and remote SHAs match.
- PER requires the stronger outcome: remote `main` at the same SHA as local.

Risk: W5 can pass after a failed or skipped push, while PER later expects a stronger remote-state proof.

Required change: replace the final W5 proof with `git push origin main` followed by SHA equality, for example `test "$(git rev-parse main)" = "$(git rev-parse origin/main)"`, or an exact clean tracking assertion that cannot match ahead or behind state.

### P3-C2: W5 omits the repo-native just gate before commit

Evidence:

- `AGENTS.md:134-136` requires `just check && just build && just test` before every commit.
- `AGENTS.md:168-171` repeats the normal proof and adds generated-navigation refresh when applicable.
- `justfile:16-17` runs `cargo nextest run --workspace` for `just test`, which is not the same as ALP-2827's raw `cargo test --workspace`.
- `justfile:69-72` includes `check-loc` in `just check`, but ALP-2827 Acceptance does not include the root just gate before commit and push.

Risk: Phase 2 can commit with a weaker proof set than the monorepo contract, including missing pre-commit LOC and nextest proof.

Required change: add `just check && just build && just test` to ALP-2827 Acceptance and Verification before commit and push. Keep the narrower cargo metadata, fmm, provenance, version, doctor, and remote-state checks as additional proof.

### P3-C3: Dist target proof is missing after introducing bundled rusqlite

Evidence:

- The monorepo declares cargo-dist targets for linux gnu, linux musl, and darwin in `Cargo.toml:42-52`.
- The identity source workspace declares `rusqlite = { version = "0.37", features = ["bundled"] }` in `../identity-matters/Cargo.toml:23-33`.
- `lilo-im-store` depends on `rusqlite.workspace = true` in `../identity-matters/crates/im-store/Cargo.toml:18-27`.
- The store integration test drives a tempfile SQLite database through `SqliteAuditSink` and `StubAuthorizer` in `../identity-matters/crates/im-store/tests/audit.rs:13-45`.
- The Phase 2 dist binary does not currently depend on `lilo-im-store`; `crates/lilo/Cargo.toml:15-19` depends only on clap, `lilo-common`, serde, and serde_json.
- Live Linear ALP-2827 and ALP-2828 do not include target-specific proof for the new rusqlite-backed published crate.

Risk: Phase 2 can sign off host-platform tests while downstream consumers, or a later Phase 8 publish gate that exercises `lilo-im-store` itself, may fail on musl or aarch64 due bundled SQLite C build or link prerequisites. A plain `cargo dist plan` would test the binary axis, not the published store crate axis.

Required change: use the peer refinement. Add an explicit PER Out of scope bullet that cross-compilation of `lilo-im-store` to `aarch64-unknown-linux-musl`, `x86_64-unknown-linux-musl`, and other `workspace.metadata.dist.targets` is deferred to Phase 8 mirror-publish gates. Add an ALP-2824 audit marker such as `missing-proof:rusqlite-bundled-on-musl-aarch64-deferred-to-phase-8` so the residual risk is visible.

### P3-K1: W5 and PER use an fmm presence check that cannot prove nested crate indexing

Evidence:

- Current `fmm list-files --group-by=subdir` output from repository root is only:
  - `crates/ 10 files · 1,066 LOC`
  - `tools/ 1 files · 41 LOC`
- `fmm list-files --group-by=subdir | grep -F 'crates/lilo'` exits with no match on current HEAD.
- `fmm list-files crates/ --group-by=subdir` does emit nested crate buckets such as `crates/lilo/`, `crates/lilo-paths/`, and `crates/lilo-common/`.
- Live Linear ALP-2827 and ALP-2828 expect root grouped output to contain `crates/lilo-im-core`, `crates/lilo-im-store`, `crates/lilo-im-stub`, and `internal/identity/service`.

Risk: The W5 fmm checks will fail regardless of whether Phase 2 roots are indexed, or they will be rewritten ad hoc by the executor. PER cannot distinguish an indexed import from a bad proof command.

Required change: fix W5 and PER fmm checks by either scoping grouped list output to parent dirs, for example `fmm list-files crates/ --group-by=subdir | grep -qF 'crates/lilo-im-core/'` and `fmm list-files internal/ --group-by=subdir | grep -qF 'internal/identity/service/'`, or by dropping grouped mode and grepping per-file output such as `fmm list-files | grep -qF 'crates/lilo-im-core/src/lib.rs'`.

## Verify Round Outcome

Post-apply live Linear re-read covered ALP-2812, ALP-2829, and ALP-2823 through ALP-2828 with `includeRelations=true`. P3-C1, P3-C2, and P3-C3 landed cleanly. The verify round then reopened P3-K1 for a residual fmm path-depth defect on the `internal/` check:

- P3-C1: ALP-2827 and ALP-2828 now require `git push origin main` plus `test "$(git rev-parse main)" = "$(git rev-parse origin/main)"`.
- P3-C2: ALP-2827 now requires `just check && just build && just test`; ALP-2828 mirrors the pre-commit just gate and preconditions for `just` and `cargo-nextest`.
- P3-C3: ALP-2824 and ALP-2828 now carry the `missing-proof:rusqlite-bundled-on-musl-aarch64-deferred-to-phase-8` marker and explicit Phase 8 cross-target deferral.
- P3-K1 residual: ALP-2827 and ALP-2828 currently use `fmm list-files internal/ --group-by=subdir | grep -qF 'internal/identity/service/'`, but fmm groups one segment below the supplied prefix. Current evidence: `fmm list-files crates/lilo/ --group-by=subdir` buckets `crates/lilo/`, `crates/lilo/src/`, and `crates/lilo/tests/`; `fmm list-files crates/lilo/src/ --group-by=subdir` buckets `crates/lilo/src/` and `crates/lilo/src/cli/`.

Residual amendment applied: the fourth fmm check in ALP-2827 Acceptance/Verification and ALP-2828 W5 mirror now uses `fmm list-files internal/identity/ --group-by=subdir | grep -qF 'internal/identity/service/'`. The three `crates/` lines remain unchanged. Bus escalation sent in message `ad29a2a7-7ef2-44eb-bdc1-a80a5d526c8b`; peer accepted in message `88f58e24-c033-4151-a5c6-9b3cde83e2bc`. Post-apply verify passed. I sent clean V to the orchestrator in message `8048f8cf-2e47-4a84-971f-e58302bc2c73`; peer sent clean V in message `69489fad-8fd2-4a4f-9776-2248b4f94f72`. Pass 3 closes on bilateral V.

## Non-findings Checked

- PER mirroring: ALP-2828 mirrors the worker Acceptance bullets for ALP-2823 through ALP-2827 closely enough to preserve review coverage. Extra PER checks are stricter, not contradictory.
- W4 service factoring: current source supports the filed factory shape. `StubAuthorizer` borrows an `AuditSink`, and `SqliteAuditSink` owns the database path, so the issue correctly tells the worker to avoid a self-referential struct and choose a compiling composition.
- Doctor JSON: Phase 2 does not need to change doctor output. Current source and test lock the empty JSON shape.
- Source and target paths: source identity crates exist, target Phase 2 paths do not exist yet, and the source repo HEAD matches the recorded provenance SHA.

## Dependencies

Critical imported dependencies from `identity-matters`:

- `rusqlite` with `bundled`, introduced by `lilo-im-store`.
- `async-trait`, `chrono`, `nix`, `tokio`, `uuid`, `insta`, and `tempfile` from the identity workspace dependency set.
- `lilo-im-core`, `lilo-im-stub`, and `lilo-im-store` become workspace path dependencies at version `0.8.0`.

## Relevance to Helioy

The findings protect the autonomous execution handoff. They keep Nancy's closeout proof aligned with the monorepo operator contract, prevent false remote completion, catch invalid generated-navigation assertions, and surface release-target risk before identity becomes a substrate dependency for later runtime and session imports.

## Open Questions

- Should Phase 8 mirror-publish gates include target-specific `lilo-im-store` build proof for the configured musl and aarch64 targets?
- Should W5 split commit and push into separate explicit acceptance bullets so a push failure cannot be conflated with fmm, build, or test failure?
