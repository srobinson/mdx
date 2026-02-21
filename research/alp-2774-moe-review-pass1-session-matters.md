---
title: ALP-2774 MoE Review Pass 1 Findings
type: research
tags: [session-matters, linear, moe-review, alp-2774, sm-isolation]
summary: Pass 1 review of the ALP-2774 Linear master found PER mirroring, smoke command, and snapshot verification gaps.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Executive Summary

ALP-2774 is the session-matters master for plumbing `--isolation`, `--image`, and `mounts` through the `sm run` spawn path into runtime-matters. The live Linear tree is selector compatible at the parent and worker level, but pass 1 found three substantive reviewability defects before execution: the PER is summary level, the master smoke command is not cold-copy executable, and the ALP-2778 verification order does not prove the final snapshot state.

## Project Metadata

- Language: Rust.
- Build system: Cargo workspace, with `just` gates in the repo.
- Key crates touched by the plan: `sm-core`, `sm-driver`, `sm-daemon`, `sm-cli`.
- External runtime boundary: `runtime-matters` via `lilo-rm-core` and `lilo-rm-client`.
- fmm index: present and usable. `fmm_list_files` reported 105 indexed files and 17,097 LOC under `crates/`.

## Architecture

- `sm-core` owns the daemon wire `SpawnRequest`, currently defined in `crates/sm-core/src/proto.rs:17`.
- `sm-cli` owns CLI argument shape. `RunArgs` is in `crates/sm-cli/src/cli/cli_def.rs:78`, and `SessionCreateArgs` is in `crates/sm-cli/src/cli/cli_def.rs:94`.
- `sm-cli` builds daemon spawn requests in `crates/sm-cli/src/cli/run.rs:23`.
- `sm-daemon` owns daemon spawn request handling and `SpawnLaunch` construction in `crates/sm-daemon/src/handler.rs:609`.
- `sm-driver` owns the runtime driver boundary. `SpawnLaunch` is in `crates/sm-driver/src/driver.rs:21`, and `RtmdDriver::spawn` builds the outbound runtime-matters request at `crates/sm-driver/src/rtmd.rs:48`.
- MCP `agent_run` is implemented in `crates/sm-daemon/src/mcp_tools.rs:117`.
- Public tool schema and generated help flow from `tools/run.toml`; the build script fanout is in `crates/sm-cli/build.rs`.

## Key Patterns

- Linear gate readiness is encoded by the accepted gate body, the execution parent, and issue relations. ALP-2782 is `Worker Done` and authorizes ALP-2775 with `Execute: ALP-2776, ALP-2777, ALP-2778, ALP-2779, ALP-2780, ALP-2781`.
- Worker order is represented structurally through Linear relations. Live relations matched the gate prose for ALP-2776 through ALP-2780: ALP-2776 blocks ALP-2777, ALP-2778, and ALP-2779; ALP-2778 blocks ALP-2779 and ALP-2780.
- Public surface changes must start in `tools/run.toml`, then regenerate generated help, MCP schemas, and insta snapshots together.
- PER criteria need to mirror worker acceptance bullet for bullet. Summary checks are too weak for autonomous closure.

## Detailed Findings

### C1: ALP-2781 PER summarizes worker acceptance instead of mirroring it

- Issue: ALP-2781.
- Class: PER scope mirroring.
- Evidence: ALP-2781 has generic review criteria plus cross-cutting checks. It does not provide per-worker subsections that mirror every acceptance bullet from ALP-2776 through ALP-2780.
- Risk: A reviewer can pass the PER without individually checking serde round trip and missing-field defaults from ALP-2776, fake-driver and fake-rtmd forwarding evidence from ALP-2777, generated help and schema snapshots from ALP-2778, structured MCP parse error behavior from ALP-2779, and valid, default, and malformed CLI cases from ALP-2780.
- Required change sent on bus: Add per-worker PER subsections that mirror every worker acceptance bullet and require evidence for each.

### C2: ALP-2782 master smoke command is not cold-copy executable

- Issue: ALP-2782.
- Class: Copy-paste safety and implicit preconditions.
- Evidence: The plan-level merge gate command is written as `sm run claude --target tmux:N:N.N --role pm --label app=nginx --isolation docker --image runtime-matters-claude:local --agent-config auth-passthrough`.
- Risk: `tmux:N:N.N` is a placeholder, and the gate does not bind the command to the freshly built `sm` binary from the current checkout. A cold executor can copy a command that targets no real pane or accidentally invokes a stale installed `sm` that still rejects `--isolation`.
- Required change sent on bus: Replace with a copy-paste-safe smoke snippet that derives or names a real tmux target and invokes the built `sm` for this checkout.

### C3: ALP-2778 verification does not prove the final snapshot state

- Issue: ALP-2778.
- Class: Copy-paste safety.
- Evidence: ALP-2778 verification is `cargo build -p sm-cli`, `cargo test -p sm-cli`, then `cargo insta accept`. There is no final `cargo test -p sm-cli` after accepting regenerated snapshots.
- Risk: The final working tree after snapshot acceptance is not proven by the listed commands. A worker could accept snapshots and stop without rerunning the test suite against the accepted artifacts.
- Required change sent on bus: Change verification to rerun `cargo test -p sm-cli` after snapshot acceptance.

## Dependencies

- `lilo-rm-core` and `lilo-rm-client`: runtime-matters wire types and client protocol.
- `clap`: CLI argument parsing for `RunArgs` and `SessionCreateArgs`.
- `serde`: wire serialization defaults for `SpawnRequest`.
- `cargo-insta`: snapshot acceptance for generated MCP schema tests.
- `tmux`: plan-level smoke target for live Claude TUI spawn.

## Relevance to Helioy

This review protects the Helioy agent execution loop from a high-blast-radius gate leaking into Nancy execution. The specific defects would cause weak review closure, stale-binary smoke tests, or unproven generated artifacts, all of which reduce confidence in autonomous worker execution.

## Peer Reconciliation

After the peer findings arrived on bus topic `2774-review-pass1`, I sent:

- `A|accept:F1,F2,F4,F5|reject:F3:cosmetic relatedTo cleanup does not affect selector authorization, worker executability, or PER closure|missing:none`
- Conditional signoff with five required edits:
  1. C1/F4: expand ALP-2781 into per-worker PER subsections that mirror every worker acceptance bullet, including MCP and CLI unknown-policy rejection surfaces.
  2. C2/F5: make the ALP-2782 merge-gate smoke copy-paste safe with setup, real tmux target, branch-built `sm`, and docker inspect container binding, or mark it operator-only with explicit handoff.
  3. C3: update ALP-2778 verification to rerun `cargo test -p sm-cli` after `cargo insta accept`.
  4. F1: add an ALP-2776 entry-point pointer for all `sm_core::SpawnRequest {` construction sites under `sm-daemon`, `sm-cli`, and `sm-core`.
  5. F2: update ALP-2778 to say `spawn_session` gains `isolation` and `image` parameters and `create_session` passes defaults, removing the `args.isolation` phrasing.

Rejected peer F3 as cosmetic: the residual `relatedTo` link to ALP-2798 may be tidy to remove, but it does not change selector authorization, worker executability, or PER closure.

## Verify After Orchestrator Edits

Received `VERIFY v1` on bus topic `2774-review-pass1` and re-read live Linear for ALP-2774, ALP-2776, ALP-2778, ALP-2781, and ALP-2782. Applied edits were visible for ALP-2774 related link removal, ALP-2776 construction-site coverage, ALP-2778 helper wording and verification order, and ALP-2781 per-worker PER mirroring.

Sent `E` rather than `V` because ALP-2782 still has a copy-paste unsafe image build precondition. The gate says to run `docker build -t runtime-matters-claude:local .` from the runtime-matters checkout, but the local runtime-matters root has no `Dockerfile`; the live Dockerfile is `examples/dockerfiles/claude.Dockerfile`. Required repair: use an explicit `docker build -f examples/dockerfiles/claude.Dockerfile ...` command, or make the prebuilt image an operator-owned handoff.

## Final Verify Signoff

Received the follow-up mail that the ALP-2782 image-build E was resolved. Re-read live ALP-2782 and confirmed precondition 3 now states that runtime-matters has no root Dockerfile and uses `docker build -t runtime-matters-claude:local -f examples/dockerfiles/claude.Dockerfile .` from the runtime-matters checkout root.

Sent final verify message on bus topic `2774-review-pass1`:

```
V|I sign off on ALP-2774 master tree as currently filed
```

## Open Questions

- Final verify signoff sent after ALP-2782 image build precondition was repaired.
