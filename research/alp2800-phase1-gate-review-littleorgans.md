---
title: ALP 2800 Phase 1 gate review for littleorgans
type: research
tags: [littleorgans, alp-2800, linear, moe-review, phase-1, monorepo]
summary: Live MoE reviews of ALP 2800 Phase 1 found gate defects across selector shape, scaffold contract, tool preflight, and pass 3 verification safety.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

A live mail directive requested a codebase grounded MoE review of the ALP 2800 Phase 1 scaffold gate. I checked live Linear issues ALP 2800 through ALP 2811, the current monorepo directory, the synthesis artifact, local tool availability, fmm state, and GitHub repo access, then sent four `F` findings on bus topic `alp2800-review-pass1`.

The current repo is still an empty seed: `README.md` has one line, `NOTES/v1-v2-strategy.md` has the v1 to v2 strategy, and fmm has no supported source files yet. The gate has real pre execution defects around PER ordering, locked Phase 1 file coverage, a just recipe count mismatch, and missing local Moon tooling.

## Project Metadata

- Project: `littleorgans` private monorepo seed.
- Path: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`.
- Current source state: no Rust source files yet. `fmm_list_files` returned zero indexed files and `fmm validate` reported no supported source files.
- Current tracked style: root `README.md` is only `# littleorgans` at `README.md:1`.
- Current design note: `NOTES/v1-v2-strategy.md` defines v1 as local first and v2 as Kubernetes shaped at `NOTES/v1-v2-strategy.md:12-17`, with K8s mapping guidance at `NOTES/v1-v2-strategy.md:39-53`.
- Planned language and build system: Rust workspace, resolver 3, edition 2024, Rust 1.90 from synthesis `§2` at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:283-290`.
- Local tool check during review:
  - Present: `cargo`, `rustc`, `just`, `fmm`, `gh`, `jq`, `git`.
  - Missing: `moon`, while W1 and W8 both require `moon ci`.
- GitHub access: `gh auth status` was authenticated as `srobinson`; `gh repo view littleorgans/littleorgans` returned an existing private repo with default branch `main`.

## Architecture

Phase 1 is intended to create only the scaffold for the monorepo. The locked target layout includes workspace roots, `crates/`, `internal/`, `tools/`, `tests/`, `docs/`, reserved app and package directories, and GitHub workflows at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:239-280`.

The future binary surface is `lilo`, with kubectl shaped user verbs, operator namespaces, hidden runtime shim, and a top level `doctor` command at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:293-304`. The data root is `~/.lilo/`, with `LILO_HOME`, `LILO_SOCKET_PATH`, and `LILO_LOG` as the only relevant overrides at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:328-353`.

The current execution graph in Linear is master ALP 2800, gate ALP 2811, backlog ALP 2801, workers ALP 2802 through ALP 2809, and PER ALP 2810. The gate body authorizes all workers plus PER and states the required order, including ALP 2809 before ALP 2810.

## Key Patterns

- Linear is the source of truth for selector order. Prose `Required order` must match the actual `blockedBy` graph before execution starts.
- Worker bodies must be self sufficient and must not require workers to author files outside their declared capability.
- Generated or local navigation state is treated as derived. Existing `.fmm.db` is present, but the real Phase 1 proof is `fmm generate && fmm validate` after supported source files exist.
- Local first does not mean dependency free. The gate depends on host tools, especially Moon, and the issue text should make those preconditions executable.

## Detailed Findings

### C1, PER relation missing ALP 2809 blocker

- Issue: ALP 2810.
- Class: 1, structural integrity.
- Evidence: ALP 2811 `Required order` says ALP 2809 before ALP 2810. Live ALP 2810 relations showed `blockedBy: []`.
- Risk: Nancy selector can treat the post execution review as eligible before the W8 acceptance gate is complete.
- Required change sent on bus: add ALP 2809 as ALP 2810 `blockedBy`, or add the reciprocal ALP 2809 `blocks` ALP 2810 relation.

### C2, locked Phase 1 outputs omitted from worker and staging lists

- Issues: ALP 2802, ALP 2809, ALP 2810.
- Class: 9, code contract mismatch.
- Evidence:
  - The synthesis target layout includes root `moon.yml` at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:246`.
  - Phase 1 mechanics list `docs/provenance/imported-repos.md` and `LICENSE` as files to add at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:433-434`.
  - ALP 2802 Capability does not include those three outputs.
  - ALP 2809 explicit `git add` list does not include those three outputs.
- Risk: Phase 1 cannot satisfy the locked synthesis without a worker authoring or staging files outside its declared lane, which the PER explicitly rejects.
- Required change sent on bus: add those outputs to W1 Capability, W8 staging, and PER review focus, or amend the gate to remove them from Phase 1.

### C3, ALP 2802 recipe count mismatch can miss `check-loc`

- Issue: ALP 2802.
- Class: 9, code contract mismatch.
- Evidence: ALP 2802 Capability lists seven just recipes: `fmt`, `fmt-check`, `clippy`, `build`, `test`, `check-loc`, `check`. ALP 2802 Acceptance says `just --list` shows all six recipes.
- Risk: Review can pass a scaffold missing `check-loc`, weakening the 700 line file cap gate.
- Required change sent on bus: change Acceptance to all seven recipes and verify recipe names explicitly.

### C4, Moon missing from local PATH while W1 and W8 require `moon ci`

- Issues: ALP 2802, ALP 2809.
- Class: 7, implicit preconditions.
- Evidence: local PATH check found `cargo`, `just`, `fmm`, `gh`, `jq`, `git`, and `rustc`, but `command -v moon` failed. W1 verification and W8 gate both require `moon ci`. Synthesis also makes Moon part of CI and orchestration at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:378` and Phase 1 exit criteria at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:470`.
- Risk: The first executable worker or final gate can fail on `command not found` before the scaffold is tested.
- Required change sent on bus: pin a Moon installation or preflight in W1 or W8, then make `moon ci` verification depend on that preflight.

## Dependencies

Critical dependencies for Phase 1:

- `cargo` and `rustc`: local Rust build and test gates. Present locally, though current installed version is 1.95 while the locked toolchain file should pin 1.90.
- `just`: local task runner for scaffold commands. Present locally.
- `moon`: workspace orchestrator required by synthesis and W1/W8. Missing locally during this review.
- `fmm`: structural navigation DB generation and validation. Present locally, but current seed has no supported source files.
- `gh`: repo existence, private remote, push and workflow checks. Present and authenticated.
- `jq`: JSON smoke validation for `lilo doctor --output json`. Present locally.

## Relevance to Helioy

The Phase 1 gate is the first executable slice of the broader Helioy to littleorgans monorepo consolidation. The findings are mostly selector hygiene and contract fidelity issues, but they matter because this gate sets the pattern for later substrate import waves. If the first gate allows prose order to drift from Linear relations, or allows workers to author outside declared lanes, later high blast radius import phases will become harder to review and automate.

## Open Questions

- Whether the peer pane accepts C1 through C4 or rejects any as non blocking.
- Which Moon installation path should be pinned for local execution and CI.
- Whether `moon.yml`, `LICENSE`, and `docs/provenance/imported-repos.md` truly belong in Phase 1, or whether the synthesis should be amended before authorization.
- Whether PER ALP 2810 should also explicitly review `moon.yml`, `LICENSE`, and provenance if they remain Phase 1 outputs.

## Verification Log

- Checked inbox with `get_messages`; received MoE pass card on topic `alp2800-review-pass1`.
- Used fmm first for structural orientation. `fmm_list_files(group_by: subdir)` returned zero files. Fallback shell inspection was required.
- Read current local seed files: `README.md`, `NOTES/v1-v2-strategy.md`.
- Read targeted synthesis sections and decision log lines, not the full 595 line document.
- Fetched live Linear details for ALP 2800 through ALP 2811 with relations.
- Listed live children under ALP 2800 and ALP 2801.
- Listed comments on ALP 2800 and ALP 2811. Both were empty.
- Checked local tool availability and GitHub auth/repo status.
- Sent bus message `3e5a3996-08d9-4cb8-af2a-011434ebba34` with four `F` findings to `littleorgans:general:9:2.1`.

## Peer Reconciliation, Round 1

After receiving the peer pane findings on topic `alp2800-review-pass1`, I verified the disputed surfaces against live Linear, the synthesis file, and GitHub state.

Agreement line sent as bus message `2cea3b38-024e-4746-9ece-9082b28bd7fe`:

```text
A|accept:F1,F2,F4,F5|reject:F3:live `gh repo view littleorgans/littleorgans` succeeds and shows the private repo exists on main, so org and repo existence are already proved|missing:none
```

Conditional signoff sent as bus message `918acb88-d21b-4e1e-952d-89eb0a8243d4`:

```text
S|I sign off conditional on the following changes: C1/F1 add ALP-2809 as ALP-2810 blockedBy; C2 add `moon.yml`, `LICENSE`, and `docs/provenance/imported-repos.md` to W1 Capability, W8 staging, and PER focus, or remove them from Phase 1; C3 fix ALP-2802 Acceptance to all seven just recipes and verify names; C4 pin a Moon install or preflight before `moon ci`; F2 align ALP-2808 top note with rev06 G3 or record rev09; F4 drop the false under-8-min §5 §6 citation or record rev09; F5 require `[workspace.package].version = "0.8.0"` in W1 with a metadata check
```

Accepted peer findings:

- F1 duplicates C1. ALP 2810 lacks the blocker relation required by gate prose.
- F2 is valid. ALP 2808's verbatim top note differs from the locked rev06 G3 text at synthesis line 44.
- F4 is valid as a source fidelity defect. ALP 2807 cites an under 8 minute target to §5 §6, but a targeted search found no matching budget in the synthesis.
- F5 is valid. Synthesis §2 requires `version.workspace = true`, while §4 locks first monorepo release version `0.8.0`; W1 does not require `[workspace.package].version = "0.8.0"` even though W8 verifies `lilo 0.8.0`.

Rejected peer finding:

- F3 was rejected because current live GitHub state proves the precondition. `gh repo view littleorgans/littleorgans --json nameWithOwner,isPrivate,url,defaultBranchRef` returned `littleorgans/littleorgans`, private, default branch `main`.

## Verify Nudge, Round 2

Received `VERIFY v1` on topic `alp2800-review-pass1`, then re-fetched live Linear for ALP 2802, ALP 2807, ALP 2808, ALP 2809, and ALP 2810 with relations.

Verified applied cleanly:

- ALP 2810 now has `blockedBy: ALP-2809`; ALP 2809 now blocks ALP 2810.
- ALP 2807 dropped the false under 8 minute line and now states wall-clock budget enforcement is out of scope.
- ALP 2809 now treats `github.com/littleorgans/littleorgans` as pre-created and only asserts then pushes.
- ALP 2802 now requires `[workspace.package].version = "0.8.0"` and adds a `cargo metadata | jq` version check.
- ALP 2802, ALP 2809, and ALP 2810 now include `moon.yml`, `LICENSE`, `CHANGELOG.md`, and `docs/provenance/imported-repos.md`.
- ALP 2802 now reconciles the just recipe count to seven and adds a `just --show` loop.

Sent `E` instead of `V` as bus message `6cd74eab-3fcc-44cd-87ac-6b01e75a7627`:

```text
E|VERIFY failed: ALP-2802 C4 still points Moon install at synthesis §5 §6 even though live §5 §6 has no Moon install method; ALP-2808 F2 still verifies the top note without the backticks around `~/.claude/CLAUDE.md` that synthesis rev06 G3 contains.
```

Remaining blockers:

1. **Moon install preflight is still underspecified.** ALP 2802 says to install Moon per synthesis §5 §6, but live synthesis §5 §6 only lists standards and CI shape. It does not define a Moon install method.
2. **ALP 2808 exact top-note verification still omits Markdown path backticks.** Live synthesis rev06 G3 says `follows global rules in `~/.claude/CLAUDE.md`, items below are monorepo-specific additions`; ALP 2808's grep verifies the variant without the path backticks.

## Verify Nudge, Round 3

Received `VERIFY v2` on topic `alp2800-review-pass1`, then re-fetched live Linear for ALP 2802 and ALP 2808.

Verified applied cleanly:

- ALP 2808 now verifies the synthesis rev06 G3 top note with backticks around `~/.claude/CLAUDE.md`.
- ALP 2802 no longer claims synthesis §5 §6 defines the Moon install method. It notes that §5 §6 does not pin one.
- ALP 2802 changed `CHANGELOG.md` to a keep-a-changelog skeleton with `## [Unreleased]` only and no hand-authored `## [0.8.0]` entry.

Sent `E` instead of `V` as bus message `201fd5fd-a54b-438f-bad4-b83e6f9c9c3d`:

```text
E|VERIFY failed: ALP-2802 Moon preflight fallback is invalid on current host: `command -v proto` fails and `cargo info moon-cli` returns could not find `moon-cli` in crates.io; replace with a valid Moon install path or make W1 install proto before `proto install moon`.
```

Remaining blocker:

- ALP 2802 prescribes `proto install moon` with `cargo install moon-cli` fallback. On the current host, `proto` is absent and `moon-cli` is not a crates.io package, so the fallback path is not executable. The issue should either require installing `proto` first, or replace the fallback with a verified Moon install path.

## Verify Nudge, Round 4

Received `VERIFY v3` on topic `alp2800-review-pass1`, then re-fetched live Linear for ALP 2802.

Verified applied cleanly:

- ALP 2802 removed `proto install moon` and `cargo install moon-cli`.
- ALP 2802 now lists `brew install moonrepo/moonrepo/moon` as the preferred macOS Homebrew path and `bash <(curl -fsSL https://moonrepo.dev/install/moon.sh)` as the POSIX fallback.

Local command verification:

- `command -v brew` returned `/opt/homebrew/bin/brew`.
- `brew install moonrepo/moonrepo/moon` failed because the `moonrepo/moonrepo` tap is not present. Homebrew reported that the tap must be added explicitly with `brew tap moonrepo/moonrepo`.
- `curl -fsSL https://moonrepo.dev/install/moon.sh` returned the official moon install script header and installer logic.

Sent `E` instead of `V` as bus message `4c4a9538-2311-4e1f-8fce-9606ea4b82cf`:

```text
E|VERIFY failed: ALP-2802 preferred Homebrew command is still not executable on this host as written; `brew install moonrepo/moonrepo/moon` returns no available formula and requires `brew tap moonrepo/moonrepo` first. Add the tap step or use the verified official curl installer path as the primary method.
```

Remaining blocker:

- ALP 2802's preferred Homebrew path needs the explicit tap step, or the issue should make the verified official curl installer the primary method.

## Verify Nudge, Round 5

Received `VERIFY v4` on topic `alp2800-review-pass1`, then re-fetched live Linear for ALP 2802.

Verified applied cleanly:

- ALP 2802 now uses `brew install moon` as the preferred macOS path.
- ALP 2802 states that the Homebrew core `moon` formula is moonrepo's tool.
- ALP 2802 retains the official cross-platform installer fallback: `bash <(curl -fsSL https://moonrepo.dev/install/moon.sh)`.

Local command verification:

- `brew info moon` returned `moon: stable 2.2.5`, description `Task runner and repo management tool for the web ecosystem, written in Rust`, homepage `https://moonrepo.dev/moon`, formula path in `Homebrew/homebrew-core`.

Sent `V` as bus message `f4b3c821-d461-4070-9222-aeb9f0e36c1d`:

```text
V|I sign off on ALP-2802 as currently filed
```

## Pass 3, Round 1

Received a fresh MoE pass card on bus topic `alp2800-review-pass3` from `littleorgans:general:9:2.1`. Scope was ALP 2800 master, ALP 2811 gate, ALP 2801 backlog, ALP 2802 through ALP 2809 workers, and ALP 2810 PER.

### Current artifact state checked

- Live Linear direct children under ALP 2800 are only ALP 2811 gate and ALP 2801 Backlog.
- Live Linear children under ALP 2801 are ALP 2802 through ALP 2810, with no extra unauthorized backlog issue.
- ALP 2811 `Execute:` authorizes ALP 2802 through ALP 2810.
- Live relation graph matches the ALP 2811 required order after prior pass amendments: ALP 2802 gates ALP 2803 through ALP 2808 and ALP 2809; ALP 2804 gates ALP 2803; ALP 2803 gates ALP 2807; ALP 2802 through ALP 2808 gate ALP 2809; ALP 2809 gates ALP 2810.
- Comments on ALP 2800, ALP 2811, ALP 2801, and ALP 2810 were empty.
- Current repo seed still contains only `README.md`, `NOTES/v1-v2-strategy.md`, and generated `.fmm.db*` files outside `.git`.
- fmm was tried first. `fmm_list_files(group_by: subdir)` returned zero files, and `fmm validate` reported no supported source files. Shell inspection was required for current local state.

### Findings sent

Bus message `2bfa54b6-bb33-4ab6-9027-5dc73b2a7650` sent four findings:

```text
F|C1|ALP-2802, ALP-2810|class9|repro: cargo metadata with a member using edition.workspace=true and root [workspace.package] missing edition exits 101: workspace.package.edition was not defined; ALP-2802 capability names [workspace.package].version only while all stubs use edition.workspace=true|W1 can author the filed root manifest literally and fail the first cargo metadata gate|Add [workspace.package].edition = "2024" explicitly to ALP-2802 root Cargo.toml capability plus W1/PER acceptance mirror.
F|C2|ALP-2809|class2|ALP-2809 Verification prints ./target/debug/lilo --version, git log -1 --oneline, gh repo view littleorgans/littleorgans, and gh run list --limit 1 without test/jq assertions|W8 can appear green while version text, pushed commit, repo privacy, or latest CI conclusion are wrong|Replace decorative checks with exit-status assertions for exact version, fixed commit subject, gh repo isPrivate/commit evidence, and latest workflow status=completed conclusion=success.
F|C3|ALP-2806|class2|ALP-2806 Verification uses cargo xtask codegen ; test $? -eq 2 pattern for intentional failures; shell repro bash -ec 'f(){ return 2; }; f ; test $? -eq 2' exits before the test|Any executor running the block under set -e treats the expected code 2 as a verification failure and the block still does not prove the deferral text printed|Rewrite the three xtask checks to capture status and output with set +e or an if block, then assert status 2 and grep the deferral message.
F|C4|ALP-2800|class1|ALP-2800 Scope still summarizes W1 as Cargo.toml/rust-toolchain/justfile/.moon/.gitignore/.fmmrc.toml, while live ALP-2802 and ALP-2810 also require moon.yml, LICENSE, CHANGELOG.md, docs/provenance/imported-repos.md, reserved dirs, and compileable per-crate stubs|Master description no longer reflects the authorized Phase 1 artifact after amendments, so reviewers and future agents can miss amended W1 outputs from the durable parent|Update ALP-2800 W1 scope summary to include the amended root files, provenance doc, reserved placeholders, and W1 stub-authoring boundary.
```

### Evidence notes

- C1 was proved with a temporary workspace: root `[workspace.package]` containing only `version = "0.8.0"`, member `version.workspace = true`, and member `edition.workspace = true`. `cargo metadata --no-deps --format-version=1` exited 101 with `workspace.package.edition was not defined`.
- C2 came from the live ALP 2809 Verification block. The block prints state but does not assert exact `lilo 0.8.0`, the fixed Phase 1 commit subject, GitHub repo privacy, commit presence, or the latest workflow run conclusion.
- C3 was proved with a shell reduction. `bash -c 'f(){ return 2; }; f ; test $? -eq 2'` exits 0, while `bash -ec 'f(){ return 2; }; f ; test $? -eq 2'` exits 2 before the assertion.
- C4 came from drift between ALP 2800's durable scope summary and the amended ALP 2802 and ALP 2810 worker or PER content.

### Round status

After sending F, I checked the pass 3 topic twice and the full inbox once. No peer F, A, S, V, or E message had arrived yet. No agreement or signoff message was sent for pass 3 in this session.

## Pass 3, Peer Reconciliation

Received forwarded peer findings on topic `alp2800-review-pass3` from `littleorgans:general:9:2.1`. The peer surfaced seven findings.

Agreement message sent as bus message `1569a33a-3540-4466-b306-1dd84f364d53`:

```text
A|accept:F1,F2,F3,F4,F5,F6,F7|reject:none|missing:none
```

Conditional signoff sent as bus message `55ad005b-88df-4a32-a0c6-7daadef43af3`:

```text
S|I sign off conditional on the following changes: C1/F1 add [workspace.package].edition = "2024" plus authors where appropriate and edition metadata assertion; C2 make ALP-2809 verification assert exact version, commit subject, repo privacy/commit evidence, and latest CI success; C3 rewrite ALP-2806 xtask expected-failure checks to work under set -e and assert deferral text; C4/F2 refresh ALP-2800 W1 scope for amended files and stubs or point to ALP-2802 as exhaustive; F3 replace ALP-2811 citation inventory with all worker Entry-points citations or a generic all-citations check; F4 remove ALP-2802 line-pinned synthesis cite; F5 make Moon installer prose match shell semantics or use curl pipe to bash; F6 add explicit jq, gh auth, and fmm preflights in the responsible workers; F7 fix ALP-2803/2804/2805 citation misattributions.
```

Accepted peer findings:

- F1 duplicates C1 and adds the authors inheritance point from rev06 Q10.
- F2 duplicates C4 with the same stale-master-scope defect.
- F3 is valid: ALP 2811 citation inventory omits citations that now appear in worker Entry-points blocks, including §5 §2, §5 §5, §4, C12, rev04, and the direction-doc decision.
- F4 is valid: ALP 2802 uses a line-pinned `line 377` synthesis citation, which violates the label or text-anchor review probe.
- F5 is valid: `bash <(curl -fsSL ...)` uses process substitution parsed by the invoking shell, so the prose claim "Any POSIX shell with curl" is false.
- F6 is valid as an implicit-precondition defect: jq, gh auth, and fmm are execution preconditions, even if they belong in the responsible workers rather than all in W1.
- F7 is valid: ALP 2803, ALP 2804, and ALP 2805 carry source misattributions for rev05 d7, the §5 §6 exit-code table, and §5 §5 data layout respectively.

## Pass 3, Verify v1

Received `VERIFY v1` on topic `alp2800-review-pass3`. Re-fetched live Linear for the required nine IDs: ALP 2800, ALP 2802, ALP 2803, ALP 2804, ALP 2805, ALP 2806, ALP 2809, ALP 2810, and ALP 2811.

Verified applied cleanly:

- ALP 2800 W1 scope summary now includes amended workspace files, root config, reserved placeholders, `.cargo/config.toml`, and per-crate stubs.
- ALP 2802 now requires `[workspace.package].version = "0.8.0"`, `[workspace.package].edition = "2024"`, and `[workspace.package].authors = ["Stuart Robinson"]`.
- ALP 2802 stubs now inherit `version.workspace`, `edition.workspace`, and `authors.workspace`.
- ALP 2802 acceptance and ALP 2810 PER now include the edition metadata `jq` assertion.
- ALP 2802 preflight now covers `moon`, `jq`, `gh`, `gh auth status`, and `fmm`, and the Moon curl fallback uses a pipe form rather than process substitution.
- ALP 2803 citation now points user verbs and substrate-boundary rule at rev05 d7.
- ALP 2804 citation now points exit code semantics at synthesis §5 §6.
- ALP 2805 citation now points `LILO_SOCKET_PATH` and data layout at synthesis §5 §5.
- ALP 2809 verification now asserts exact or prefix version, JSON parsing, fmm initialization, fixed commit subject, remote HEAD parity, repo privacy, and latest CI success.
- ALP 2811 now uses a broader citation inventory with an explicit anti line-pin note.

Sent `E` instead of `V` as bus message `40f6a17f-12d9-473f-8685-96aa0a76caca`:

```text
E|VERIFY failed: ALP-2806 xtask loop is still not robust under set -e. Live block uses `out=$(cargo xtask "$verb" 2>&1); status=$?`; under `set -e` a command substitution assignment returning 2 aborts before `status=$?`. Repro: `bash -ec 'out=$(sh -c "echo Phase; exit 2" 2>&1); status=$?'` exits 2. ALP-2810 mirrors this as robust under set -e, so C3 remains unresolved.
```

Remaining blocker:

- ALP 2806 and the ALP 2810 W5 mirror still claim the xtask verification pattern is robust under `set -e`, but the live loop aborts before status capture on the expected exit code 2. The fix should wrap each expected-failure command in `set +e` / `set -e`, or use an `if out=$(cmd 2>&1); then status=0; else status=$?; fi` form.

## Pass 3, Verify v2

Received `VERIFY v2` on topic `alp2800-review-pass3`. The nudge said only ALP 2806 had been reapplied and required live reread of ALP 2806 only.

Verified applied cleanly:

- ALP 2806 now uses an `if out=$(cargo xtask "$verb" 2>&1); then ... else status=$? ... fi` pattern.
- The issue explicitly explains why the prior `out=$(cmd); status=$?` pattern aborts under `set -e`.
- The verification block now asserts status 2 and greps the deferral message for all three placeholder verbs.

Local shell proof:

```bash
bash -ec 'for verb in codegen; do if out=$(sh -c "echo Phase deferral; exit 2" 2>&1); then echo unexpected >&2; exit 1; else status=$?; test "$status" -eq 2; echo "$out" | grep -qF Phase; fi; done'
```

The command exited 0, proving the replacement pattern captures expected nonzero status under `set -e`.

Sent `V` as bus message `1fa03c12-fde0-4c3e-89c2-052a905c0d05`:

```text
V|I sign off on ALP-2800 Phase 1 gate as currently filed
```

## Pass 3, Verify v3

Received `VERIFY v3` on topic `alp2800-review-pass3`. The nudge said cascade fixes were applied for peer flagged E1, E2, and E3, and required live reread of ALP 2809 and ALP 2811 only.

Verified applied cleanly:

- ALP 2809 now checks local vs remote HEAD parity with `git ls-remote origin HEAD | cut -f1`, avoiding the earlier `gh repo view --json defaultBranchRef` projection issue.
- ALP 2809 now waits for CI completion with `gh run watch "$run_id" --exit-status`, so the verification is an exit-status assertion rather than a decorative status print.
- ALP 2809 step 13 prose now says to wait for the `pr.yml` workflow run triggered by the push to complete green.
- ALP 2811 citation inventory now includes `rev03`, which ALP 2809 still cites.
- ALP 2811 removed `C9`, which no worker cites by label.
- ALP 2811 retains the generic instruction to confirm all citations referenced in worker Entry-points blocks by label or text anchor.

Sent `V` as bus message `3529f2bb-76da-487c-9353-93345367d734`:

```text
V|I sign off on ALP-2800 Phase 1 gate as currently filed
```

