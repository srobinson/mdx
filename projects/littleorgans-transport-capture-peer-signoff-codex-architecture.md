---
status: complete
---

# Littleorgans Transport Capture Peer Sign-off: Architecture

Status: COMPLETE

Worker Status: No nested workers. Delta verification is being performed directly by the assigned Codex peer.

Verdict: PASS

## Delta scope

Reviewed:

- corrected canonical:
  `/Users/alphab/.mdx/projects/littleorgans-transport-capture--synthesis.md`
- preserved v1:
  `/Users/alphab/.mdx/projects/.archive/littleorgans-transport-capture--synthesis.v1.md`
- bounded correction specification:
  `/Users/alphab/.mdx/projects/littleorgans-transport-capture-peer-consensus.md`

The archive is a distinct preserved 434-line document. The corrected canonical
is 543 lines. The unified delta contains 19 bounded hunks across the sections
named by CS-1 through CS-16. The source pins, governing native Transport frame,
and zero `tm` dependency remain unchanged.

## Consensus correction verification

| Correction | Result | Evidence in corrected canonical |
|---|---|---|
| CS-1 integrity honesty | PASS | Sections 1, 2, 9, 13, and 14 define the shared-UID v1 threat model, limit v1 to tamper-evident evidence under normal operation, require a distinct enterprise agent principal and external signed checkpoint, and add hostile direct-file tests. |
| CS-2 read path | PASS | The taxonomy and sections 9 and 12 require daemon-mediated Transport RPC reads with Identity authorization and access audit. `lilo transport paths` is removed and R16 rejects direct path disclosure. |
| CS-3 mandatory scope | PASS | Sections 1, 3, 4, 7, and 14 narrow coverage to managed inference, enumerate subprocess and direct-egress exclusions, distinguish Running from first provider response, and remove every-agent-action copy. R15 records the egress-control boundary. |
| CS-4 spawn coverage | PASS | Section 3 contains the full surface, harness, backend, and target matrix. Every unresolved cell names a Gate 3 owner and permits only CAPTURED or REJECTED BEFORE SHIM SPAWN. The launcher conformance gate, runtime-specific capability and doctor output, and shell-resume exclusion are explicit. |
| CS-5 artifact vocabulary | PASS | Section 8 defines four HTTP artifact classes and their transforms, reserves `wire octets`, and defines canonical digest plus keyed HMAC domains. Section 13 splits relay, persisted body, structural, and secret-omission fidelity with an independent oracle. E4 remains artifact-first. |
| CS-6 authority split | PASS | Section 8 makes content and launch facts filesystem authority, makes audit, lifecycle, tombstone, hold, and deletion outcomes authoritative transactional control facts, and limits replay to derived indexes and read models. Its five-row precedence table covers every required disagreement. E5 matches. |
| CS-7 durability physics and bounds | PASS | Sections 8 and 10 name `F_FULLFSYNC` for macOS, file and parent `fsync` for Linux, and process, kernel, and power-loss scope. The loss-window option is removed. Request and spool ceilings, backpressure, typed outcomes, X6 distributions, and p95 limits are explicit. U3 now tests the strict contract. |
| CS-8 availability and break glass | PASS | Section 10 sets a 3 second capture timeout, distinguishes the existing 10 second ShimReady wait, caps launch and per-turn overhead, and defines failure thresholds. L9 records no v1 break-glass path. Gate 2 carries the measurements. |
| CS-9 retention exhaustion | PASS | Section 11 orders warning, reserve enforcement, new-launch refusal, existing-capture reservation, and per-session typed truncation. U11 owns only the concrete values, which must close at Gate 3 and ship with capture. |
| CS-10 deletion closure | PASS | Section 5 adds `delete_one` to the delete-and-rebuild list. Section 11 defines terminate-then-erase, idempotent tombstone response, U16, seven lineage classes, external-copy limits, and surviving audit fields. Sections 13 through 15 gate full owned-root closure. |
| CS-11 coordinator and lease | PASS | Sections 4, 5, and 10 define one Session app coordinator, Transport and Runtime ports, a one-use lease, preparation before `begin_spawn`, outcome cleanup, and provider-egress readiness through first request. Gate 2 requires interval fault injection. E7 and U2 distinguish the settled coordinator from the open worker topology. |
| CS-12 listener and credentials | PASS | Section 9 identifies the loopback endpoint as a data-plane listener, excludes only new management listeners, and defines binding, host and path validation, bounds, deadlines, and hostile sibling tests. Transport is explicitly a transient credential processor with named prohibited operations and a canonicalization boundary. |
| CS-13 redirect regression | PASS | Section 7 records Remote Control and MCP tool-search regressions, expands X1 into the required harness feature matrix, and requires disclosure. Gate 1, E1, and U15 keep redirect conditional until Stuart decides the tradeoff. |
| CS-14 legal downgrade | PASS | Section 2 uses an inference-level risk statement with no unsupported country list. Sections 14 through 16 require counsel and jurisdiction-specific primary authority before managed deployment or enterprise copy. U9 remains honestly open. |
| CS-15 capture-fault response | PASS | Section 10 defines HTTP 422 and 413 envelopes, stable codes, non-retryable intent, operator mapping, and no upstream delivery. Section 13 requires one harness failure and zero retry amplification. |
| CS-16 compatibility and contracts | PASS | Section 5 marks the doctor repair as a versioned wire change. Sections 12 through 15 require typed RPC and generated JSON schemas, bounded pagination and payloads, stable errors, versioning, orphan-capture selectors, per-view authorization, MCP ownership, retained-adapter fixtures, and a linear migration gate. |

## Architecture finding closure

| Accepted architecture finding | Result | Closure |
|---|---|---|
| A-P0-1 spawn surfaces outside capture | PASS | CS-4 matrix, conformance gate, Gate 3 owner decisions, U4 and U8 |
| A-P0-2 contradictory evidence root | PASS | CS-5 artifact classes, transforms, digest domains, four-part oracle |
| A-P1-1 `LaunchSpec` overstated as coordinator | PASS | CS-11 Session coordinator, Transport lease, `LaunchSpec` injection carrier |
| A-P1-2 control state falsely replayable | PASS | CS-6 split authority and recovery precedence |
| A-P1-3 same-UID paths bypass audit | PASS | CS-1 and CS-2 threat model, daemon reads, path removal, enterprise principal gate |
| A-P1-4 delete means terminate | PASS | CS-10 explicit semantic replacement, lineage closure, U16 |
| A-P1-5 durability window and unbounded hot path | PASS | CS-7 strict failure domain, platform primitives, bounds, backpressure, tests |
| A-P2-1 read verbs lacked a contract | PASS | CS-16 typed RPC, generated JSON, limits, selectors, errors, MCP ownership |
| A-P2-2 readiness was a snapshot | PASS | CS-11 live lease, provider-egress invariant, interval fault injection |

## Remaining findings

None.

The unresolved ledger items are honest product or experiment decisions rather
than residual review defects. Gate 3 must close every spawn-matrix cell, U1,
U4, U8, U9, U11, U13 through U16, and the named runtime and product tradeoffs
before implementation planning. Gate 2 closes U2 and U3 through measured
evidence. Gate 5 blocks program exit until the RPC, compatibility, migration,
authority, and deletion contracts are published and proven.

## Archive and boundary checks

- Corrected canonical status: COMPLETE.
- Archived v1 status: COMPLETE and preserved separately.
- Peer consensus status: COMPLETE.
- Canonical line count: 543, below the 700-line limit.
- Em dash scan: clean in the corrected canonical.
- Delta shape: 19 hunks, all within the consensus-named synthesis sections.
- Source pins remain
  `98d8928941b5b5db670ed73ed06af57f61dcfa0a` and
  `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`.
- Every `tm` or transport-matters mention remains research evidence,
  rejection, stale-doc withdrawal, or a zero-relationship gate.
- No transport-matters `NOTES` source was opened or cited.
- No repository, canonical synthesis, archive, or consensus artifact was
  edited during sign-off.
- The only repository worktree difference remains the pre-existing
  `LESSONS.md` modification.

## Final decision

The corrected synthesis resolves or honestly ledgers every accepted finding
and every CS-1 through CS-16 requirement. It introduces no new P0 or P1 defect.
The architecture is ready to proceed through its stated decision gates.
