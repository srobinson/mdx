---
title: RTM Docker road-test issue review pass-2 — pane A round 1
type: research
tags: [alp-2643, alp-2650, moe, peer-consensus, issue-review, pass-2, runtime-matters]
summary: Pane A (Claude) round-1 fresh-eyes review of ALP-2684..ALP-2690 and ALP-2650 gate after pass-1 consensus and orchestrator edits.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Scope

Second-pass MoE peer-consensus review on `nancy/ALP-2643` at `b43dbf5`. Read all artifacts cold; pass-1 details deliberately excluded.

## Verification baseline

- Branch: `nancy/ALP-2643` HEAD `b43dbf5`.
- All cited paths exist on branch.
- `DockerImageUnavailable` and `DockerImageMetadataUnavailable` categories present in `crates/rtm-daemon/src/error.rs` (lines 20–21). ALP-2686 references both correctly.
- `crates/rtm-daemon/src/spawn_preflight.rs:81` matches `Some("pattern-e") | Some("tmux-primary")` as the profile string the operator types on the CLI.
- README `## Dockerfile Contract` section already exists at line 131.
- Pattern jargon currently leaks from: `README.md` (2 hits), `CHANGELOG.md` (1 hit), `crates/rtm-daemon/src/doctor.rs` (2 hits), `crates/rtm-daemon/src/spawn_preflight.rs` (1 hit), `crates/rtm-core/src/admin.rs` (2 hits), `crates/rtm-core/src/cli_output.rs` (1 hit), snapshot fixtures (4+ hits).

## Conditional sign-off

I sign off conditional on the following changes:

### 1. ALP-2654 terminality binding is non-binding because ALP-2654 is already `Done`

ALP-2654 status: `Done`, `completedAt: 2026-05-21T09:36:05.827Z` (09:36 UTC). The road-test correctives (ALP-2684..ALP-2690) were filed at 14:20+ UTC, and the ALP-2650 gate close binding ("ALP-2654 cannot reach `Done` until a worker demonstrates the binding manual verification...") was appended at 14:44 UTC. The terminality event the binding tries to gate has already fired. The Required order line `ALP-2684..ALP-2689 before ALP-2654` references a temporally inverted relationship.

Required action: either reopen ALP-2654 (revert status to `In Review`), or file a successor post-execution review issue (ALP-269x) that is properly blocked by ALP-2689 binding manual verification and replaces ALP-2654 in the Required order. The current state is internally inconsistent and the gate close binding bind nothing.

### 2. ALP-2688 leaves the `docker:pattern-e` profile name in operator-facing surface

The profile string operators type on the CLI is `docker:pattern-e` (matched literally at `crates/rtm-daemon/src/spawn_preflight.rs:81`). ALP-2688 acceptance says "rejection messages name the unsupported profile by what it asks for, not by codename" but the profile name *is* the codename. README (line 98, 155) shows `docker:own-init` profile names are operator-facing. ALP-2688 must bind whether the `pattern-e` profile string is also removed/aliased (the `tmux-primary` alias already exists at the same site and is plain-language). Without this binding, ALP-2688 cannot meet its acceptance: a rejection message of `"isolation policy docker:pattern-e ..."` still contains "pattern-e" in operator output.

Required action: add an acceptance clause that the profile string `pattern-e` is either removed or renamed; if kept as alias, document that error messages must format using the plain-language name only.

### 3. ALP-2687 typed error category is unbound

ALP-2687 acceptance: "preflight returns a typed error naming the missing image source." ALP-2686 picks specific category names (`DockerImageUnavailable`, `DockerImageMetadataUnavailable`) and binds them as observable separately. ALP-2687 leaves the category name floating. Worker may invent a new category that collides with ALP-2686's existing ones, or reuse `DockerImageUnavailable` and weaken its semantic specificity.

Required action: bind ALP-2687's typed error to a named category (e.g., `DockerImageNotConfigured`) distinct from ALP-2686's two existing categories.

### 4. ALP-2687 `--image NAME[:TAG]` shape is too narrow

Docker image references include registry/namespace prefixes (`docker.io/library/foo:tag`, `ghcr.io/org/repo:tag`) and digest references (`foo@sha256:abc...`). The `NAME[:TAG]` shape excludes both. Operators with private registries or pinned digests cannot use the flag as specified.

Required action: change shape to "any valid Docker image reference" and add an acceptance clause covering at least one digest-pinned reference.

### 5. ALP-2690 duplicate-key semantics unbound

`docker run -e` precedent: last-occurrence-wins for repeated `-e KEY`. ALP-2690 says the flag is repeatable and "multiple `--env` flags compose into one env set" but does not bind:

- Behavior when `--env KEY` appears twice (deterministic last-wins, error, or implementation-defined).
- Behavior when `--env KEY` and `--env KEY=VALUE` appear for the same KEY (explicit overrides inherited, vice versa, or error).
- Behavior when the caller's environment has `KEY=` (empty string) vs unset — `--env KEY` with empty value: pass empty, treat as missing, or error.

Required action: bind a deterministic precedence rule. `docker run` precedent is last-wins; matching it carries no new mental model.

### 6. ALP-2650 coordination note is incomplete

Coordination note lists ALP-2685 and ALP-2687 as co-touching `crates/rtm-cli/tests/docker_documentation.rs`. ALP-2688 also touches that file (its acceptance: "asserts the absence of 'Pattern E' / 'Pattern D' / 'Pattern A' strings in README and CHANGELOG"). Also missing: `crates/rtm-cli/tests/snapshots/generated_snapshots__cli_help.snap` will be touched by ALP-2687 (new `--image` flag) and ALP-2690 (new `--env` flag); snapshots under `surface_snapshots__doctor_*.snap` will be touched by ALP-2688 (removes `pattern_e` field).

Required action: add ALP-2688 to the `docker_documentation.rs` co-touch list. Add a snapshot fixture coordination clause covering ALP-2687, ALP-2688, and ALP-2690.

### 7. Concur with pane B on `<TMUX_TARGET>` and session-id capture in ALP-2689

Pane B's #2 (session-id capture via `SESSION_ID=$(uuidgen)` for kill verification) is correct and binding. I extend it: the `<TMUX_TARGET>` placeholder in ALP-2689 also needs a documented shape — e.g., "operator-substitutable in the form `session:window.pane` (for example `2:3.1`)". Otherwise an operator might pass `<TMUX_TARGET>` as a free-form string and discover the spawn fails at the shim/tmux integration.

Required action: bind `<TMUX_TARGET>` placeholder shape next to the `<HOST_CWD>` placeholder language.

### 8. Concur with pane B on ALP-2686 → ALP-2689 blocker

Pane B's #1 is correct. The binding manual verification builds `runtime-matters-claude:local` as a local-only image, so on an arm64 operator host (Apple Silicon), preflight will reject before lifecycle insert unless ALP-2686 has landed. Required order and `blockedBy` relations must add ALP-2686 → ALP-2689.

## Non-issues verified

- ALP-2684 single-session executable, no line numbers, paths verified.
- ALP-2685 single-session executable; references `~/.mdx/research/docker-base-image-recommendation-2026-05-21.md` which is an external research artifact not required to exist on branch.
- ALP-2689 binding manual verification is precise about flag shapes and uses only flags introduced in ALP-2687 and ALP-2690.
- ALP-2650 Execute list covers all seven road-test issues plus ALP-2654.
- No issue contains line numbers.
- All `blockedBy` relations match Required order (modulo ALP-2686 → ALP-2689 per pane B #1).

## Iteration bound

Round 1 of 2. If pane B accepts these eight (six new + two concurring) plus pane B's two, I expect round-2 clean consensus.
