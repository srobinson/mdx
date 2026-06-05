---
title: Littleorgans Issue 41 typed launch contract synthesis
type: design
tags: [littleorgans, issue-41, architect, synthesis, launch-attachment]
summary: Candidate scores, selected base, grafts, rejections, and verification for the Issue 41 typed launch contract.
status: active
project: littleorgans
confidence: high
created: 2026-08-17
updated: 2026-08-17
related: [littleorgans-issue41-typed-launch-contract, littleorgans-launch-attachment-contract, littleorgans-issue41-typed-launch-flow]
---

<!-- markdownlint-disable-next-line MD025 -->
# Issue 41 typed launch contract synthesis

## Scores

| Criterion | Candidate A | Candidate B |
| --- | ---: | ---: |
| Typed invariants and one parse boundary | 5 | 4 |
| Complete caller migration and legacy deletion | 5 | 4 |
| Redacted attachment and Runtime receipt boundary | 5 | 4 |
| Interface depth and persist versus execute equality | 5 | 2 |
| Recovery, parity, absence, and audit proof | 5 | 3 |
| Total | 25 | 17 |

## Selected base

Candidate A is the base. `RuntimePort::spawn` takes the complete Runtime
`SpawnRequest` by value. The Session handler constructs that request once,
persists a clone in Transaction A, and moves the original into the port. The
adapters forward the owned value to `RuntimeService::spawn` or
`RuntimeClient::spawn` without rebuilding it.

Candidate B keeps `spawn(SessionId, &SpawnLaunch)` and calls the request builder
for persistence and again in each adapter. The shared helper reduces field
mapping duplication. It leaves value pairing as a call site convention.

## Grafts from candidate B

1. Delete `internal/session/driver/tests/port_conformance.rs::spawn_request`.
2. Delete the local `parse_session_id` beside `FaultingRuntimePort` in
   `spawn_recovery.rs`.
3. Migrate the five named doubles in `events.rs`, handler spawn tests,
   `spawn_recovery.rs`, `mail_notify_concurrency.rs`, and `mail_safety.rs`.
4. Preserve `lilo_rm_core::ErrorCode::InvalidTarget`.
5. Set `launch_attachment: None` in
   `internal/runtime/app/src/cli/spawn.rs` and add no CLI flag.
6. Enforce the verified baseline line counts before any file crosses 700.
7. Return the existing `SpawnTargetParseError` directly from `spawn_launch`.
8. Keep the shared attachment fixture in Session test support. Export no test
   fixture from `lilo-rm-core`.

## Rejections

The synthesis rejects candidate B's piece based spawn, two request builder
calls, `SpawnLaunch` without `SessionId`, retained inherent `RtmdDriver` verbs,
and per crate attachment fixtures. It also rejects a borrowed complete request,
a shallow `PreparedSpawn` wrapper, persistence of `SpawnLaunch`, and any
fallback that maps a malformed present attachment to `None`.

Issue 41 excludes a Transport producer, a Schedule type, a Session protocol
field, child delivery, a store column, a protocol version bump, and a CLI
attachment flag. Production sets the attachment to `None`. Tests carry `Some`.

Only the Session driver parse faults leave `RuntimeFault`:
`InvalidSessionId`, `InvalidTarget`, and `InvalidSignal`. The duplicate inherent
`RtmdDriver` verbs also leave. Runtime's `ErrorCode::InvalidTarget` remains.

## Verification

- `git rev-parse HEAD` returned
  `8c211cb767554a3435ba6bfb8f27689473f9ce8c`.
- `git status --short` was empty before artifact creation. Both outputs live
  under `~/.mdx/design`, outside the repository.
- Source inspection confirmed that the handler builds a persisted Runtime
  request while both adapters rebuild another request at the selected baseline.
- Source inspection confirmed the three Session driver parse faults, the
  separate Runtime `ErrorCode::InvalidTarget`, the duplicate inherent
  `RtmdDriver` verbs, the five test doubles, the conformance helper, and the
  recovery test parser.
- The measured line counts match the judge's eight file inventory. The largest
  is `internal/runtime/daemon/src/api.rs` at 643 lines.
- FMM inspection was unavailable because this worktree has no `.fmm.db`.
  Generating one would write repository navigation state, outside this
  read only architecture task.
- Repository tests were not run because these artifacts change no repository
  source. Implementation proof remains the focused tests, architecture audit,
  `fmm generate && fmm validate`, root gate, and `git diff --check` specified in
  the main contract.
