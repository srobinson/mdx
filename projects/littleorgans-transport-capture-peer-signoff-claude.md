---
title: Delta sign-off — littleorgans transport capture synthesis corrections (claude backend-engineer)
type: review
tags: [backend, security, durability, operations, transport, capture, signoff]
summary: Delta sign-off of the corrected synthesis against archived v1 and the 16-item consensus; verdict FAIL on one new P1 introduced by CS-15
status: complete
source: backend-engineer
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

Verdict: FAIL

One new P1 defect was introduced by the CS-15 correction itself. All sixteen consensus corrections and all eleven of my accepted findings are otherwise resolved or honestly ledgered. The failure is narrow, cheap, and confined to one bullet in section 10.

## Worker Status

- Reviewer: littleorgans:helioy-tools:backend-engineer:5:2.1. Read-only, no nested agents spawned.
- Scope: delta only. Corrected `~/.mdx/projects/littleorgans-transport-capture--synthesis.md` (543 lines) against archived `~/.mdx/projects/.archive/littleorgans-transport-capture--synthesis.v1.md` (434 lines) and the 16-item Bounded Correction Specification in `littleorgans-transport-capture-peer-consensus.md`.
- Archive integrity confirmed: the archived v1 is byte-consistent with the document I reviewed in round one (434 lines, identical opening block, and every passage I quoted in `littleorgans-transport-capture-peer-review-claude.md` is present there and changed in the corrected file).
- Neither repository nor the synthesis was edited. No rejected item reopened. No scope broadened: every finding below sits inside a correction the consensus already ordered.
- Not re-verified: repository claims already verified at pin `98d8928` in round one and unchanged by the delta. Re-verified only where the correction introduced a new repository citation.
- Mechanical checks: 543 lines (under 700), zero em dashes, Status COMPLETE, zero `tm` invocation or dependency proposals, `transport-matters/NOTES` still uncited.

## Per-correction verification

| # | Verdict | Evidence in the corrected document |
|---|---|---|
| CS-1 integrity honesty | PASS | Section 9 opens with a `**[F] V1 threat model**` block naming the shared UID, citing `crates/lilo-im-core/src/audit.rs::AuditDecision::evaluate_local`, and stating evidence is tamper-evident at best with no tamper-proof claim. Principle 7 (line 47) rewritten to "append-only by application contract ... tamper-evident at best". Section 14 states v1's shared-UID posture cannot carry enterprise copy and names the distinct-principal, process-bound-capability, signed-checkpoint precondition. The hostile same-UID direct-file test appears in the acceptance work. Pairing of v1 posture with enterprise copy is explicitly blocked |
| CS-2 read-path declaration | PASS | Section 9: all product reads daemon-mediated through the Transport `LilodRpc` variant, daemon reads disk after Identity authorization and records access audit. `lilo transport paths` removed from v1 with the reason stated; verb set is now `list \| show \| export` in sections 1, 3, 12, and the implementation phase. New ledger entries E18 and R16 record the decision and the rejection. My "mutually exclusive" framing was correctly adjudicated down to underspecification; the resolution chosen is the one that preserves the audited-read claim |
| CS-3 mandatory-scope honesty | PASS | Section 1 rewritten to "managed agent-to-provider model inference traffic". Invariant 1 is now "captured or rejected before shim spawn"; invariant 2 is the capture-lease formulation; invariant 3 separates Running from provider response. Minimum-v1 sentence ends with the exclusion of agent-spawned processes with modified environments, direct egress, and post-agent shell resume. Section 14's enterprise sentence no longer says "every agent action" or "whether a human touched it"; line 63 states the exclusions affirmatively. A `first_exchange_observed` receipt replaces the launch-truth overreach |
| CS-4 spawn coverage matrix | PASS | Normative matrix over {session run/create, raw runtime spawn} x {Claude, Codex, `RuntimeKind::Other`} x {host, docker}, every cell CAPTURED or OPEN-with-named-owner, with "no uncaptured-success state" stated. Conformance iterates `registered_launchers` requiring adapter or pre-spawn refusal; shell resume excluded with the `shell_resume_command` citation. Gate 3 exit requires every OPEN cell to resolve |
| CS-5 evidence vocabulary and digest domain | PASS | Line 260 reserves `wire octets` for capture points that observe octets and forbids application HTTP artifacts inheriting the name. Line 262 defines the unkeyed digest domain as the versioned canonical redacted artifact plus transform manifest, requires a keyed HMAC over credential-bearing source fields with an Identity key outside the agent principal's reach, and prohibits bare hashes as an offline verification oracle. Section 13 splits fidelity into relay, persisted body, structural round-trip, and intentional secret omission with an independent client-and-upstream oracle. E4's ordering is preserved, matching the consensus partial rejection |
| CS-6 authority split | PASS | Line 240 splits filesystem authority (content, transcripts, compatibility, launcher facts) from an authoritative transactional Postgres control ledger (authorization audit, access audit, lifecycle rows, tombstones, holds, deletion outcomes), leaving only indexes, cursors, and read models rebuildable, with "a rebuild cannot infer, resurrect, or erase control facts". A recovery-precedence table covers missing rows, missing directories, staged deletes, holds, and `InDoubt` audit outcomes. E5 rewritten |
| CS-7 durability physics and bounds | PASS with a residual (see F-2) | Line 244 names `fcntl(F_FULLFSYNC)` before rename on macOS APFS and file-plus-parent `fsync` on Linux, states the claimed failure domain as process, kernel, and power loss, and removes the measured loss window. "Small" is gone. Explicit numbers: 64 MiB request ceiling, 1 MiB unsynchronized, 8 MiB queued spool, 5 second backpressure then typed Interrupted. X6 measures with the correct primitive against multi-turn, cached-prefix, image, and production-shaped streams |
| CS-8 availability budgets and break-glass | PASS | Line 303: `capture_start_timeout` 3 seconds, sequential with and distinct from the existing 10 second ShimReady wait at `internal/runtime/daemon/src/api.rs::spawn_domain`, 500 ms p95 added launch, E6 failure thresholds at 1/5/20 streams and 10 ms p95 chunk latency, measured on macOS and Linux at Gate 2. No break-glass in v1, stated affirmatively with doctor reporting the reason. Gate 2 exit carries the same numbers, so the gate can now fail |
| CS-9 retention exhaustion valve | PASS | Ordered valve: doctor warning at `warning_bytes` above `reserve_bytes`; at `reserve_bytes` new launches rejected with `capture_space_reserve` while existing captures keep reserved capacity; retention never erases an active capture; holds override expiry. Reserve, warning threshold, and session ceiling are mandatory release fields with only their values at U11, which is exactly the split the correction required |
| CS-10 deletion semantics and closure | PASS | `internal/session/daemon/src/handler/sessions.rs::delete_one` added to the delete-and-rebuild list. Section 11 defines terminate-then-erase ordering, the idempotent `already_deleted` response after the row is gone, and routes the terminate-only verb to U16. A data-lineage table covers transcripts, quarantine and dead-letter, exports, staged dirs, blobs, and external copies with per-class delete, hold, and authority disclosure. Release assertion now reads "closes every daemon-owned lineage root and index while preserving the enumerated audit fields" |
| CS-11 coordination seam and readiness | PASS | Section 10 makes the Session app coordinator the single owner, introduces a one-use capture lease carrying child launch material, holds the lease through shim start, child start, and first request, and requires every Runtime outcome to cancel or finalize it. Fault injection is required at every interval between prepare, readiness, shim start, child start, first request, and first response chunk. Invariant 2 is now expressed as lease coverage rather than process existence. E7 remains the injection carrier; U2 closes at Gate 2 |
| CS-12 listener and credential threat model | PASS | Section 9 replaces the blanket claim with "the per-session loopback endpoint is a data-plane listener; Transport adds no management listener", then bounds it: expected adapter host and path only, session or process binding, connection, byte, expansion, and stream caps, header/idle/total deadlines, TLS validation, CONNECT rejection, and hostile same-UID sibling tests for connection theft, capability replay, host and path confusion, slowloris, and limit exhaustion. Transient-processor credential definition enumerates the prohibited operations |
| CS-13 redirect feature regression | PASS | Line 214 records the confirmed regression with the version (Claude Code 2.1.196) and both effects. E1 demoted to conditional with the reason in its basis column. X1 expanded to the full feature matrix including Remote Control and MCP tool search; Gate 1 exit requires the recorded outcomes and a published operator disclosure list; U15 added for Stuart at Gate 3; a release assertion covers regression testing and disclosure |
| CS-14 legal downgrade | PASS | Line 65 is now `**[I]**`, the DE/NL/AT/SE list is gone, jurisdiction-specific primary-authority review by counsel is required, and enterprise managed deployment cannot release before U9 closes. U9 restated accordingly; gate 9 carries the counsel requirement |
| CS-15 capture-fault response | FAIL (see F-1) | Status codes, retry posture, and operator mapping are correctly specified, and the release assertion proves one harness failure with zero upstream requests and zero retry amplification. The response body chosen is provider-schema-shaped, which introduces a new defect |
| CS-16 gate additions | PASS | Gate 5 exit requires earlier adapter fixtures to read with the current reader and CI to prove one linear migration chain, and requires the typed Transport RPC plus generated CLI JSON contract with pagination, payload limits, stable errors, versioning, orphan-capture selectors, per-view authorization, and MCP ownership before closure. Gate 0 exit records the `runtime_matters` doctor repair as a generated wire-contract change with compatibility review |

My round-one findings map cleanly: P0-1 to CS-1, P0-2 to CS-2, P0-3 to CS-3, P1-4 to CS-7, P1-5 to CS-8, P1-6 to CS-9, P1-7 to CS-7, P1-8 to CS-5, P1-9 to CS-15, P2-10 and P2-11 to CS-16. Ten of eleven are resolved. P1-9's correction is the one that failed.

## Remaining findings

### F-1 (P1, new, introduced by CS-15). The capture-fault response fabricates a provider-schema error, which lands in the evidence record

**Evidence.** Section 10: "A persistence or quota fault before upstream delivery returns HTTP 422 with the provider-shaped body `{"type":"error","error":{"type":"invalid_request_error","message":"lilo capture unavailable; code=<stable_code>"}}`", and 413 with the same envelope. Only the free-text `message` discloses local origin. The `type` and `error.type` discriminants are Anthropic's error schema, so any consumer that switches on `error.type`, which is the normal way to classify these, attributes a littleorgans-generated fault to the provider.

**Why it is a defect.** Section 2 principle 4 is "Provider truth over harness self-report". The harness records this response in its transcript, and the transcript is one of the two authoritative streams under E12 and an input to the future relay-versus-transcript diff. A capture fault by definition produces no wire counterpart, so the resulting evidence is a transcript-only provider-typed error the provider never sent, indistinguishable by type from a real one. This also sits four lines above section 10's own "the proxy never fabricates a provider response" (that sentence is scoped to the after-delivery branch, so this is adjacent-scope rather than a direct self-contradiction, but the principle it encodes is global). CS-5 spent an entire correction establishing that every artifact must declare what it is and what transformed it; a synthetic response in the provider's own schema is the same overclaim in the opposite direction.

**Required correction, narrow.** Keep 422 and 413 and keep the non-retryable posture, which are correct. Change the envelope so origin is machine-readable, not prose: a lilo-namespaced discriminant (for example `error.type` of `lilo_capture_error`, or a sibling `"source":"lilo"` field) verified to remain non-retryable under the harness retry contract in the same X1 feature matrix that already runs. Require the capture record and the CAPTURE state to mark the exchange as locally generated so no downstream fidelity or derivation logic can attribute it to the provider. Add one release assertion: a pre-delivery capture fault produces no provider-attributed error in any persisted artifact.

### F-2 (P2, residual inside CS-7). macOS cannot deliver the directory half of the rename durability the power-loss claim depends on

**Evidence.** Line 244 promises power-loss survival, then specifies macOS as `fcntl(F_FULLFSYNC)` before rename plus "the strongest supported directory synchronization after rename". APFS provides no directory-entry equivalent of `F_FULLFSYNC`; the hedge is doing real work. A rename whose directory entry is not durable can lose an otherwise durable file, so the barrier's guarantee on the primary development platform is weaker than the sentence above it.

**Why it is only P2.** The claim is now explicit enough to be falsified, and Gate 2's X6 runs power-loss injection on macOS specifically. The document routes its own failure.

**Required correction.** State the macOS directory-entry limitation in section 8 rather than hedging it, and either scope the macOS power-loss claim to what APFS can prove, or restructure so the barrier does not depend on a post-barrier rename (pre-create and synchronize the exchange directory before the barrier, then synchronize only the file). Gate 2 should record which of the two it chose.

### F-3 (P2, completeness inside CS-2 and Gate 0). Removing `lilo transport paths` leaves a stale verb list outside the delete-and-rewrite list

**Evidence.** R16 now rejects `lilo transport paths` and the verb set is `list | show | export`. The monorepo `CLAUDE.md` documents the transport namespace as holding "inspection and ops verbs (`list`, `paths`, `show <session>`)". Section 5's delete-and-rewrite list covers the `CLAUDE.md` launch-chain prose, the `env-vars.md` UUIDv7 line, and the doctor naming residue, but not this verb list.

**Required correction.** Add the `CLAUDE.md` transport verb list to the section 5 delete-and-rewrite list and to the Gate 0 exit criteria, so the removal of `paths` is not contradicted by the governing instruction file.

## What the delta got right beyond the letter of the corrections

Three changes exceed what was ordered and are worth recording. The availability contract (line 303) attaches falsifiable numbers to a gate that previously could not fail. The recovery-precedence table under CS-6 answers each file-versus-ledger disagreement class individually rather than stating a principle. The spawn matrix under CS-4 encodes "no uncaptured-success state" as a structural property of the table, so a future OPEN cell cannot quietly resolve to silence.

## Verdict

FAIL. One new P1 (F-1), introduced by the CS-15 correction, places a provider-schema-shaped synthetic error into the evidence record the product exists to make trustworthy. Two P2 residuals (F-2, F-3) sit inside corrections that otherwise pass. All sixteen consensus corrections and ten of my eleven round-one findings are resolved with substance rather than acknowledgement, and the remaining fix is one bullet in section 10 plus one release assertion.
