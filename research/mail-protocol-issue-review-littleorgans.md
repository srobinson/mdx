---
title: Mail Protocol Issue Review for littleorgans
type: research
tags: [littleorgans, mail-protocol, linear, issue-review, moe]
summary: Pass 1 found five gaps; pass 2 found one retention decision and verified clean after live Linear edits.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Executive Summary

The ALP-2906 issue tree implements the signed off littleorgans mail protocol spec through six workers plus a post execution review. Live Linear and the current repo support the broad worker order. Pass 1 found five design and reviewability gaps that were later verified clean after Linear edits. Pass 2 found one remaining substantive retention decision around explicit `context_id` transcript purge; the gate and worker issues now bind the v1 retention scope and both review panes have cleanly signed off.

## Project Metadata

- Language: Rust.
- Workspace: Cargo workspace orchestrated by Moon and the root justfile.
- Indexed navigation: `.fmm.db` and `.fmmrc.toml` are present. `fmm validate` passed for 373 indexed files on 2026-06-01.
- Key verification surface: `just check && just build && just test`; surface refresh also requires `fmm generate && fmm validate`.
- Relevant Linear tree fetched live on 2026-06-01: master ALP-2906, gate ALP-2915, Backlog ALP-2907, workers ALP-2908 through ALP-2913, PER ALP-2914.

## Architecture

The current mail path is still the legacy single table model. Core wire types live in `internal/session/core/src/proto/messaging.rs`, where `MailSendRequest` still carries `from` at lines 7 to 11. The current core mail row type lives in `internal/session/core/src/mail.rs`, where `Mail` has `sender_id`, `recipient_id`, `content`, `sent_at`, `read_at`, and derived status at lines 41 to 58.

Persistence is in `internal/session/store/src/sqlite/mail.rs`. `SqliteStore::insert_mail`, `count_unread_mail`, and `read_unread_mail` query `session_mail` directly at lines 24 to 93. Namespace deletion currently deletes mail by `sender_id = ? OR recipient_id = ?` inside `delete_sessions_by_namespace` at `internal/session/store/src/sqlite/namespaces.rs:67-97`.

The daemon path is in `internal/session/daemon/src/handler/messaging.rs`. `DaemonState::mail_send` still accepts client asserted `from` and maps absent senders to `Uuid::nil()` at lines 17 to 30. Authorization is inline through `self.identity.authorize` at lines 131 to 137, 159 to 165, and 190 to 196. Nudge already goes through an injected runtime port with `self.runtime.nudge` at lines 198 to 201.

The CLI and generated source of truth are split across `internal/session/app/src/cli/mail.rs`, `internal/session/app/src/cli/cli_def.rs`, `internal/session/app/src/cli/output.rs`, `internal/session/app/tools/mail.toml`, and `internal/session/app/src/cli/generated_help.rs`. The authored `mail.toml` still declares `from` for `mail_send` at lines 25 to 31, declares selector based `mail_read` and `--peek` at lines 41 to 72, and declares `mail_stop_check` at lines 99 to 122.

## Key Patterns

- Current handler seams already use `RuntimePort` for runtime operations. `DaemonState` stores `runtime: Arc<dyn RuntimePort>` in `internal/session/daemon/src/handler/state.rs:10-16`, and the trait defines `nudge` in `internal/session/driver/src/port.rs:18-53`.
- The generated surface is data driven. `internal/session/app/tools/mail.toml` is the authored surface, with exact parameter `name` and `cli_flag` values that feed MCP and CLI generation.
- Namespace scoping already has an `all_namespaces` JSON key and `--all-namespaces` CLI flag. `read_namespace_scope` reads `all_namespaces` in `internal/session/daemon/src/mcp_tools/args.rs:37-59`, while `NamespaceScopeArgs` exposes `--all-namespaces` in `internal/session/app/src/cli/selector_scope.rs:10-20`.

## Detailed Findings

### F C1: ALP-2910 is stale against the current runtime seam

Evidence:

- `internal/session/daemon/src/handler/state.rs:10-16` already stores `runtime: Arc<dyn RuntimePort>`.
- `internal/session/driver/src/port.rs:18-53` already defines `RuntimePort`, including `nudge` at lines 40 to 44.
- `internal/session/daemon/src/handler/messaging.rs:198-201` already calls `self.runtime.nudge`.
- `internal/session/driver/src/in_process.rs:139-156` implements `RuntimePort::nudge` by calling the runtime service.

Risk: ALP-2910 asks the worker to introduce a Runtime or Delivery port where the current module seam already exists. That can create a duplicate parallel port instead of extending the existing seam for `Wait` or `Steer` mode and presence.

Required change sent on bus: revise W3 to extract only the missing Identity port and either reuse or explicitly extend `RuntimePort` for Wait, Steer, and presence, or fold delivery mode extension into W5.

### F C2: idempotency key spelling is not self contained in the workers

Evidence:

- The signed spec binds `idempotency_key` as the JSON field in `~/.mdx/projects/littleorgans-mail-protocol--spec.md:353-354`.
- `internal/session/app/tools/mail.toml:16-39` shows authored params use exact `name` and `cli_flag` fields for generated MCP and CLI contracts.
- ALP-2908 and ALP-2913 describe only an optional idempotency key or flag, not the exact JSON key and CLI flag spelling.

Risk: workers can choose `client_idempotency_key`, `idempotency_key`, or another CLI spelling, and the PER cannot falsify stable generated surface compliance from the issue body alone.

Required change sent on bus: bind `idempotency_key` JSON and `--idempotency-key` CLI spelling in W1 and W6, or add the binding to the gate and restate it in both workers.

### F C3: operator origin read receipts have no bound target semantics

Evidence:

- `internal/session/core/src/mail.rs:41-48` has `recipient_id` as a session UUID in the current model.
- ALP-2909 defines `message_deliveries` as rows keyed by message and recipient session.
- ALP-2911 states the operator has no mailbox and is not an addressable recipient.
- ALP-2912 states draining unread mail emits one `system` receipt per reader to the original sender.

Risk: operator origin mail creates an unbound receipt target. The original sender can be operator, but the model has no operator delivery row or drain path. A worker could invent log only receipts, suppress receipts, or try to create an operator mailbox.

Required change sent on bus: add a binding for operator origin read receipts, either transcript only system metadata with no `message_delivery` row, or no operator receipt. Then make W5 and PER verify that rule.

### F C4: ALP-2914 PER does not mirror worker acceptance bullet for bullet

Evidence:

- ALP-2914 asks for one review bullet per authorized worker.
- ALP-2908 through ALP-2913 each contain multiple acceptance bullets that need separate falsifiable review checks.

Risk: a PER reviewer can pass a worker without checking each acceptance claim, especially cross worker invariants such as projection reuse, breaker receipt exemption, and generated surface drift.

Required change sent on bus: expand ALP-2914 to mirror every worker acceptance bullet one for one, grouped by worker, with command or observation proof for each.

### F C5: stop check JSON is required but missing from ALP-2913 acceptance

Evidence:

- `internal/session/app/tools/mail.toml:99-122` defines the current `mail_stop_check` authored tool surface.
- `internal/session/app/src/cli.rs:73-82` currently rejects JSON for the whole `mail` command.
- The signed spec requires stable JSON for `mail send`, `mail read`, `mail check`, and `mail stop-check` at `~/.mdx/projects/littleorgans-mail-protocol--spec.md:196-197`.
- ALP-2913 capability mentions stop check JSON, but acceptance lists only send, read, and check.

Risk: stop check JSON can be missed even though it is in the authored surface and required by the spec.

Required change sent on bus: add `mail stop-check --output json` to ALP-2913 acceptance and to the PER mirror.

## Dependencies

- `lilo-session-core`: wire and projection types.
- `lilo-session-store`: SQLite persistence.
- `lilo-session-daemon`: request handling, MCP tools, identity calls, runtime port use.
- `lilo-session-app`: CLI, output, generated help, authored tool surface.
- `lilo-runtime-daemon`: tmux gateway and runtime service.
- `lilo-sys`: process, process exit, and IPC OS seams.

## Relevance to Helioy

This issue tree gates the v1 local first mail substrate for littleorgans. The review keeps the Linear plan selector compatible and execution safe before Nancy workers start implementation.

## Open Questions

- Await peer pane findings and agreement on topic `mailspec-review-pass1`.
- If peer accepts C1 through C5, the orchestrator should batch one Linear edit pass, then issue VERIFY.
- If peer rejects C3, the unresolved decision is the exact receipt semantics for operator origin mail.

## Peer Reconciliation Update

Peer pane `littleorgans:helioy-tools:codebase-analyst:5:2.1` independently verified the same two primary findings as F1 and F2:

- F1 converges with C1: ALP-2910 misdescribes the runtime seam because `RuntimePort` already exists and is already used for nudge. The issue should reuse or extend that seam and make IdentityClient extraction the new port seam.
- F2 converges with C4: ALP-2914 summarizes PER coverage instead of mirroring worker acceptance bullet for bullet.

The peer accepted C2, C3, and C5. No disputes or escalations remain. I sent the A/S response on bus topic `mailspec-review-pass1` with conditional signoff on five edits:

1. Edit ALP-2910 to reuse or extend existing `RuntimePort` and scope new extraction to IdentityClient.
2. Bind `idempotency_key` JSON and `--idempotency-key` CLI spelling in ALP-2908 and ALP-2913.
3. Bind operator origin read receipt semantics in ALP-2911 and ALP-2912, then verify in PER.
4. Add `mail stop-check --output json` to ALP-2913 acceptance.
5. Expand ALP-2914 to mirror every worker acceptance bullet, including the new C2, C3, and C5 bindings.

## Pass 1 Closure Update

Peer pane `littleorgans:helioy-tools:codebase-analyst:5:2.1` sent `V | CONVERGED` on 2026-06-01. Both panes conditional-signed on the identical five-edit set with no rejects, missing probes, or escalation:

1. C1/F1: ALP-2910 must reuse or extend existing `RuntimePort`; IdentityClient extraction is the real new port seam.
2. C2: ALP-2908 and ALP-2913 must bind `idempotency_key` JSON and `--idempotency-key` CLI spelling.
3. C3: ALP-2911 and ALP-2912 must bind operator-origin read receipt semantics; PER must verify it.
4. C5: ALP-2913 must add `mail stop-check --output json` to acceptance.
5. C4/F2: ALP-2914 must mirror every worker acceptance bullet, including C2, C3, and C5.

Agreed clean surfaces: anchors resolve, `blockedBy` graph equals gate `Required order` and `Execute` set including W6 to PER, selector grammar matches spec section 3, and `all_namespaces` is an existing scope-layer mechanism rather than a W1 gate gap. Orchestrator owns applying deltas to ALP-2908, ALP-2910, ALP-2911, ALP-2912, ALP-2913, and ALP-2914, then flipping gate ALP-2915.

## Verify Update: Remaining Gap

On 2026-06-01, orchestrator sent `VERIFY v1` saying all five consensus edits were applied. I re-read live Linear for ALP-2908, ALP-2910, ALP-2911, ALP-2912, ALP-2913, ALP-2914, and ALP-2915.

The five intended edits were present, but ALP-2910 introduced one malformed entry point path: `internal/session/daemon/src/n`. I sent `E` on topic `mailspec-review-pass1` requesting replacement with `internal/session/daemon/src/identity_client.rs` and a fresh VERIFY.

## Verify Update: Second ALP-2910 Path Typo

Peer pane `2.1` agreed with the existing `E` and found a second malformed ALP-2910 entry point path. I verified both paths locally on 2026-06-01:

- Missing: `internal/session/daemon/src/n`; correct path: `internal/session/daemon/src/identity_client.rs`.
- Missing: `internal/session/daemon/tests/port_conformance.rs`; correct path: `internal/session/driver/tests/port_conformance.rs`.

I sent an updated `E` to both peer and orchestrator on topic `mailspec-review-pass1`. Both are mechanical entry point fixes only; the C1 through C5 content otherwise verifies clean.

## Final Verify and Clean Signoff

On 2026-06-01, orchestrator re-issued VERIFY after fixing both ALP-2910 path typos. I re-read live ALP-2910 and verified the relevant paths locally:

- `internal/session/daemon/src/identity_client.rs`
- `internal/session/driver/src/port.rs`
- `internal/session/driver/tests/port_conformance.rs`
- `internal/session/daemon/src/handler/messaging.rs`
- `internal/session/daemon/src/handler/state.rs`

ALP-2910 now correctly frames IdentityClient extraction as the real new seam and reuses the existing RuntimePort. I sent `V|I sign off on the littleorgans mail protocol v1 issue set as currently filed` to both peer pane `2.1` and orchestrator `5:1.1`.

Peer pane `2.1` then also sent clean V after re-reading live ALP-2910. Both panes are clean. MoE pass 1 is closed from the review panes; orchestrator can proceed with the gate action.

## Pass 2 Review Update

On 2026-06-01, pass 2 re-read live Linear for ALP-2906, gate ALP-2915, Backlog ALP-2907, workers ALP-2908 through ALP-2913, and PER ALP-2914. It also checked current source, generated surface anchors, command definitions, and package names.

### Verified clean in pass 2

- Verification commands are realistic: `justfile:16-30` defines `build`, `justfile:35-49` defines `test`, and `justfile:148` defines `check` as fmt, clippy, LOC, provenance, and seam checks.
- The package names used by workers resolve: `internal/session/core/Cargo.toml:1-14` defines `lilo-session-core`, `internal/session/store/Cargo.toml:1-14` defines `lilo-session-store`, and `internal/session/daemon/Cargo.toml:1-14` defines `lilo-session-daemon`. `cargo test -p ... --no-run` completed for all three packages.
- fmm is current: `fmm generate --dry-run && fmm validate` reported all files up to date and all 373 files indexed.
- Existing cited tokens resolve: `Action::MailSend`, `Action::MailRead`, and `Action::Nudge` are in `crates/lilo-im-core/src/types.rs:149-155`; `RuntimePort` methods are in `internal/session/driver/src/port.rs:18-53`; `wait_for_terminal` is a free helper over the port in `internal/session/driver/src/port.rs:55-75`; `IdentityClient` is re-exported through `internal/session/daemon/src/identity_client.rs`; `all_namespaces` is implemented in `internal/session/daemon/src/mcp_tools/args.rs:37-59` and `internal/session/app/src/cli/selector_scope.rs:10-20`; `mail_stop_check` is authored in `internal/session/app/tools/mail.toml:99-122`; `print_mail` is in `internal/session/app/src/cli/output.rs:44-55`; the legacy `session_mail` delete by `sender_id OR recipient_id` is in `internal/session/store/src/sqlite/namespaces.rs:85-89`.
- File cap trajectory is acceptable if workers follow their own constraint. Current LOC: `handler/messaging.rs` 230, `core/src/mail.rs` 65, `core/src/proto/messaging.rs` 79, `store/sqlite/mail.rs` 210, `store/sqlite/namespaces.rs` 230, `app/src/cli/mail.rs` 136, `app/src/cli/cli_def.rs` 336, `app/src/cli/generated_help.rs` 117, `app/src/cli/output.rs` 55. `scripts/check-loc-limit.sh:4-20` enforces 700 lines, and `just check` runs that guard.
- Linear structure is coherent: ALP-2915 `Execute:` lists ALP-2908 through ALP-2914, the `blockedBy` graph matches the required order, PER remains in the execute set, and the gate has single canonical Outcome, Authorized execution parent, Execute, and Required order lines.

### Pass 2 substantive finding: explicit transcript purge is unscoped

Peer pane 2.1 found the one substantive gap, and I accepted it. The signed spec requires message log GC by explicit operator transcript purge: `~/.mdx/projects/littleorgans-mail-protocol--spec.md:302-311` says a message row is GC'd only by explicit `context_id` purge or owning sender deletion with zero surviving deliveries, and operator and system origin messages are host anchored until explicit purge. The same rule is ratified again at `~/.mdx/projects/littleorgans-mail-protocol--spec.md:525-529`.

Live Linear does not assign that purge path to a worker. ALP-2909 scopes the two table model and cascade split, but not a delete by `context_id` store operation. ALP-2913 scopes operator `peek`, `check`, and `tail`, but not a purge verb. The current authored mail surface only has send, read, check, and stop check in `internal/session/app/tools/mail.toml:1-122`, and `rg purge|by_context_id internal/` found no existing implementation anchor.

Risk: operator and system origin messages have no v1 GC trigger if explicit purge remains out of scope, since they are not deleted through owning sender deletion.

Required change accepted on bus topic `mailspec-review-pass2`: either add W2 store delete by `context_id`, a W6 operator purge verb, acceptance bullets, and PER mirrors, or add a gate Design call resolution deferring explicit purge to a later wave and explicitly acknowledging the v1 retention consequence.

### Pass 2 cosmetic item

Peer pane 2.1 also noted ALP-2910 describes `wait_for_terminal` as if it were a `RuntimePort` method. Current source has `wait_for_terminal` as a free helper over `RuntimePort` at `internal/session/driver/src/port.rs:55-75`, while the trait methods are at lines 18 to 53. I rejected this as cosmetic because the symbol resolves and the worker remains executable. Optional wording can relabel it as a helper over the port.

## Pass 2 Bus State

I sent `A|accept:F2` and a conditional `S` to both peer pane `littleorgans:helioy-tools:codebase-analyst:5:2.1` and orchestrator `littleorgans:general:5:1.1` on topic `mailspec-review-pass2`. Peer pane 2.1 also sent a conditional `S` on the same F2. No `VERIFY` has arrived yet in this session.

## Pass 2 Final Verify and Clean Signoff

On 2026-06-01, orchestrator sent `VERIFY v1 (pass 2)` after applying the pass 2 findings. I re-read live Linear for ALP-2915, ALP-2909, ALP-2913, ALP-2910, and ALP-2914.

Verified changes:

- ALP-2915 now has `Design call resolution: message-log retention and GC scope`, binding v1 to owning-sender deletion with zero surviving deliveries as the sole automatic message-log GC trigger, while deferring explicit operator purge-by-`context_id` post-v1.
- ALP-2909 now scopes the owning-sender deletion GC path in capability, constraints, acceptance, and out-of-scope text.
- ALP-2913 now marks explicit operator transcript purge by `context_id` out of scope per the gate retention binding.
- ALP-2910 now labels `wait_for_terminal` as a free helper over `RuntimePort`, while preserving the existing RuntimePort reuse requirement.
- ALP-2914 now mirrors the W2 retention check, the gate-bound retention cross-cutting check, and the file cap gate note that `just check` runs `check-loc`.

I sent `V|I sign off on the littleorgans mail protocol v1 issue set as currently filed` to peer pane `littleorgans:helioy-tools:codebase-analyst:5:2.1` and orchestrator `littleorgans:general:5:1.1` on topic `mailspec-review-pass2`. Pass 2 is clean from this pane.
