---
title: Schedule Matters Restart Policy Reverification for littleorgans
type: research
tags: [littleorgans, schedule-matters, restart-policy, code-review, moe]
summary: Fresh re-verification found the restart ownership line is consistent, but P1 resume and several citations need correction before sign-off.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-31
updated: 2026-05-31
---

## Executive Summary

The schedule-matters spec consistently separates static restart reconciliation from higher controller policy. The load-bearing gap is resume feasibility: the spec and build plan require P1 `Always` restart to relaunch with native `--resume`, but the live repo does not yet persist a native resume id or produce adapter resume argv.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Indexed topology: fmm reported 365 files, 48,763 LOC: `crates/` 67 files, `internal/` 293 files, `tests/` 4 files, `tools/` 1 file.
- Primary language: Rust.
- Build system: Cargo workspace with Moon orchestration and root `justfile` gates.
- Reviewed artifacts:
  - `/Users/alphab/.mdx/projects/littleorgans-schedule-matters-spec.md`, 436 lines.
  - `/Users/alphab/.mdx/projects/littleorgans-build-plan.md`, 174 lines.

## Architecture

schedule-matters is specified as the placement authority for tmux topology and occupant to pane bindings. It requests execution through runtime-matters rather than shelling out to tmux directly. Current code confirms the pre-schedule state:

- `internal/wire/src/lib.rs:5-8` has only `LilodRpc::Session` and `LilodRpc::Runtime`; schedule is not wired yet.
- `internal/session/core/src/proto/rpc.rs:16-36` owns current session verbs, including `Spawn`, mail, nudge, capture, logs, wait, and MCP bridge.
- `internal/runtime/platform/src/tmux.rs:19-114` centralizes tmux nudge, respawn, liveness, and capture operations.
- `internal/session/driver/src/port.rs:18-53` defines the current session-local `RuntimePort` with spawn, reap, capture, terminate, nudge, status, poll events, doctor, and terminate all.

## Key Patterns

- The shared database pattern is real: `LiloDb` has one `SqlitePool` at `internal/db/src/lib.rs:16-18`, with `identity_pool`, `session_pool`, and `runtime_pool` all returning `&self.pool` at lines 58-68.
- The session store wrapper pattern is real: `SqliteStore` holds a cloned pool from `db.session_pool()` at `internal/session/store/src/sqlite.rs:22-47`.
- Runtime terminal evidence already supports clean versus failure discrimination through `RuntimeEvent::Terminated` and lifecycle state, but no schedule-specific consumer exists yet.

## Detailed Findings

### 1. Restart ownership line is internally consistent

No contradiction was found between schedule owning declared restart reconciliation and not owning controller policy.

Evidence:

- Spec line 18 says schedule owns reconciliation between desired topology, runtime liveness, stored bindings, and declared `restartPolicy`, including `Always` replacement.
- Spec line 26 keeps workflow, orchestration policy, and controller decisions above schedule.
- Spec line 29 defines the boundary as reconciliation of declared intent rather than authorship.
- Spec lines 233-235 repeat that `Always` or `OnFailure` replacement follows the stored policy, while backoff, max retries, and role replacement stay above schedule.
- Spec lines 271-281 make the same split in §6.

### 2. P1 resume contract is not grounded in current code

The spec and build plan assume native CLI resume in P1:

- Spec line 233 says schedule asks runtime to relaunch the CLI with `--resume` from the stored session id.
- Spec lines 277 and 279 call native `--resume` the resurrection mechanism.
- Spec line 412 requires relaunch with `--resume` from the stored session id for `Always` acceptance.
- Build plan lines 80-83 require `Always` or `OnFailure` to re-place into a new pane plus runtime `--resume`.

Live repo evidence does not currently support that assumption:

- Spec `OccupantBinding.session_id` at line 60 is described as a session join key by line 63, not as a native CLI transcript or resume id.
- `Session` has `runtime_session: Option<String>` at `internal/session/core/src/session.rs:80`, but `SessionDraft::running_session` writes `runtime_session: None` at `internal/session/store/src/sqlite/spawn_intents.rs:117`.
- Runtime launchers return only the binary at `internal/runtime/launchers/src/lib.rs:47-49`; they do not synthesize `--resume` arguments.
- `RuntimeLauncher::launch_spec` forwards only `request.shell_resume` at `crates/lilo-rm-core/src/launcher.rs:73-79`.
- `capture_shell_resume` captures a shell command at `crates/lilo-rm-core/src/spawn_context.rs:95-104`.
- `exec_shell_resume` and `shell_resume_command` exec that shell at `internal/runtime/app/src/cli/shim.rs:105-121`.
- The current user path only sets `shell_resume` for an existing tmux target at `internal/session/app/src/cli/run.rs:53-60`.

Recommended doc fix: keep basic Always/resume in P1 per the locked decision, but add a Phase 1 prerequisite that stores a native resume identity or resume argv per occupant, separates it from the logical lilo session id, and proves the runtime adapter produces the correct CLI resume invocation.

### 3. OnFailure needs terminal evidence semantics

Runtime can distinguish clean and failure exits today:

- `RuntimeEvent::Terminated` carries `exit_code`, `signal`, and evidence at `crates/lilo-rm-core/src/types/lifecycle.rs:194-199`.
- `LifecycleState::Exited(RuntimeExit)` carries exit evidence at `crates/lilo-rm-core/src/types/lifecycle.rs:13-18` and `RuntimeExit` carries `code` and `signal` at lines 122-125.
- Runtime store encoding persists exit code and signal at `internal/runtime/store/src/sqlite/lifecycle/codec.rs:62-78` and `127-137`, then decodes them at lines 139-152.
- `RuntimeEvent::Lost` has only lost evidence at `crates/lilo-rm-core/src/types/lifecycle.rs:200-203`; `LostEvidence` has no exit code at lines 146-150.

Recommended doc fix: in §4.3, §6, and §8.7, state that `OnFailure` restarts on terminal failure evidence, such as nonzero exit code or signal. `Lost` or missing exit evidence should orphan unless policy is `Always`.

### 4. Identity citation path is wrong

Spec line 418 cites `lilo-im-core/src/types.rs:147-177`. The live repo path is `crates/lilo-im-core/src/types.rs:147-177`.

The corrected lines support the claim:

- `Action` variants at `crates/lilo-im-core/src/types.rs:147-160` include Spawn, Kill, List, Read, Logs, MailSend, MailRead, Nudge, Link, Doctor, Daemon, and ShimCallback, with no schedule variants.
- `ResourceSpec` at `crates/lilo-im-core/src/types.rs:171-177` has workspace, role, runtime, session_id, and labels, with no schedule resource ids.

### 5. Neutral runtime port existence claim is false

Spec line 314 says `internal/runtime/port` already exists. The live repo has no `internal/runtime/port` directory and no Cargo member matching `runtime/port` or `lilo-runtime-port`.

Recommended doc fix: change the text to say Phase 1 creates a neutral runtime port crate, or remove the parenthetical existence claim.

### 6. Build plan launch boundary conflicts with the spec

Build plan line 117 says launch stays with schedule-matters. The spec keeps process launch and adapters in runtime:

- Spec line 24 assigns process launch internals and shim behavior to runtime-matters.
- Spec lines 142-155 state runtime owns tmux execution and schedule drives topology verbs through runtime.
- Spec line 204 says runtime spawn still owns process launch.
- Spec line 312 says schedule decides, runtime executes.

Recommended doc fix: change build plan line 117 to say schedule requests placement and spawn while runtime launch adapters execute.

## Dependencies

Critical current dependencies for the reviewed area:

- `lilo-db`: shared SQLite pool and schema accessors.
- `lilo-session-store`: current session persistence idioms and spawn intent pattern.
- `lilo-session-driver`: current holder of `RuntimePort`, pending rehost.
- `lilo-rm-core`: runtime protocol types, lifecycle events, launch specs, spawn targets, and tmux address shape.
- `lilo-runtime-platform`: tmux execution layer.
- `lilo-im-core`: identity action and resource shape that must grow schedule verbs or define a lossless mapping.

## Relevance to Helioy

This review protects the monorepo migration contract: schedule can own placement only if process launch, native resume, identity audit, and runtime topology are clearly separated. The strongest implementation risk is accidentally encoding native resume as a logical lilo session id, which would couple schedule to session semantics and still fail to relaunch the actual CLI transcript.

## Open Questions

1. What exact native resume identity should be stored for Claude and Codex: CLI conversation id, transcript path, adapter-owned resume argv, or a typed `NativeResumeRef`?
2. Should `OnFailure` treat signal termination as failure for all runtimes, and should missing exit code orphan by default?
3. Should `runtime_session` in `Session` be revived and populated, or should schedule store a separate per-occupant resume field to avoid mixing session-matters state with schedule placement state?

## Coordination Status

Initial findings were sent to the Claude peer and orchestrator on topic `spec-plan-reverify-signoff`. The orchestrator reported that receipt was not peer agreement and directed a resend to the Claude analyst as the routed peer with orchestrator CC. The 5 point conditional proposal was re-sent directly to `littleorgans:helioy-tools:codebase-analyst:9:4.1` with `helioy:general:9:3.1` CC.

The Claude peer independently verified and converged on all five conditional changes, with one sharpening: P1 owns the mechanical native resume id persistence/injection and adapter test, while the build-plan P2 gate still owns deeper continue-vs-fork jsonl semantics. The peer withdrew the possible §1 contradiction and agreed the static policy reconciliation versus controller policy boundary is clear. Final conditional sign-off was emitted to the peer with orchestrator CC.

Final sign-off text sent:

> I sign off conditional on the following changes:
> 1. Ground the P1 resume contract: P1 must persist and inject a native CLI resume id or resume argv, distinct from the logical lilo session_id UUIDv7; add adapter tests proving `--resume <native-id>` or equivalent is produced; keep P1 to mechanical resume launch and leave continue-vs-fork jsonl semantics to the build-plan P2 gate.
> 2. Make `OnFailure` evidence precise: terminal failure evidence, defined as nonzero exit code or signal, restarts; `Lost` or no-code evidence orphans unless policy is `Always`.
> 3. Fix and normalize identity/crate citation paths: add the `crates/` prefix for `crates/lilo-im-core/src/types.rs:147-177` and any other bare `lilo-*-core` citations.
> 4. Fix the neutral runtime-port claim: remove the false `internal/runtime/port already exists` wording and add the new runtime-port crate to the §3.1 and §9 workspace-wiring checklist.
> 5. Align build-plan launch boundary lines 116 to 118 so schedule requests placement and spawn, while runtime-matters owns and executes launch adapters.

## Final Sign-off Re-read, 2026-05-31

The orchestrator applied the five consensus changes and requested a final clean sign-off against the live files. I re-read the live spec and build plan sections.

Verified as applied:

1. `OccupantBinding` now includes `native_resume_ref` distinct from logical `session_id` at `littleorgans-schedule-matters-spec.md:60`.
2. The P1 native resume prerequisite and P2 continue-vs-fork jsonl split are present in spec lines 280-281, acceptance lines 410 and 417, and build-plan lines 80-89 plus the P2 gate at lines 106-107.
3. `OnFailure` terminal evidence precision is present in spec lines 233-234, 278, and 419, and build-plan lines 80-83.
4. The identity citation is normalized to `crates/lilo-im-core/src/types.rs:147-177` at spec line 423.
5. The neutral runtime-port crate is described as not existing yet and is added to workspace wiring at spec lines 138, 155, 317, and 436.
6. The build-plan launch boundary now says schedule requests placement and spawn while runtime-matters owns and executes launch adapters at build-plan lines 122-124.

First final pass escalated one remaining stale sentence:

- Spec line 29 still said `Always or OnFailure re-places and relaunches with --resume` when a pane dies. That stale sentence conflicted with the agreed and applied OnFailure precision in §4.3, §6, and §8.7 because it omitted the terminal failure evidence condition.

Resolved final pass:

- The orchestrator fixed spec line 29. It now says `Never` reports the orphaned occupant and stops, `Always` re-places and relaunches through the native resume mechanism, and `OnFailure` does so only on terminal failure evidence.
- I re-read live line 29 and scanned the live spec and build plan for restart/resume wording. No stale incorrect Always/OnFailure lumping remained. Every `--resume` mention is either native-resume framed as `--resume <native-id>` or scoped to the P2 continue-vs-fork jsonl gate.
- I sent the final clean sign-off phrase to `helioy:general:9:3.1`: `I sign off on the schedule-matters spec and build plan as currently filed`.
