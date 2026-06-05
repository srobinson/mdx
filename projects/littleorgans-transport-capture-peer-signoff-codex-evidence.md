# littleorgans Transport Capture: Codex Evidence Delta Signoff

Status: COMPLETE

Worker Status: No nested workers. Delta review was performed directly. Only this signoff report was edited.

## Scope and baseline

- Corrected canonical: `/Users/alphab/.mdx/projects/littleorgans-transport-capture--synthesis.md`, 543 lines, SHA-256 `47403b80dc7c626a989146db030089805619958bc9e20fc8cb5f50203fd22b31`
- Archived v1: `/Users/alphab/.mdx/projects/.archive/littleorgans-transport-capture--synthesis.v1.md`, 434 lines, SHA-256 `d3200b2eb0f4e81c106a8b5bc02ba82289cdd2da724a61493d79ab89c583bdf4`
- Peer consensus: `/Users/alphab/.mdx/projects/littleorgans-transport-capture-peer-consensus.md`, 147 lines, SHA-256 `1a0245e8a7eb4d9edb81c867f4c43c934a893900912820f64f29a4de802bd25a`
- Canonical status is COMPLETE. Its line count is below 700. Its em dash count is zero.
- The archive remains a distinct, intact v1 baseline. The canonical delta is confined to the synthesis.

## Per-correction results

| Correction | Result | Evidence |
|---|---|---|
| CS-1 integrity honesty | PASS | Lines 47, 59, 63, 278 to 289, 377, 394, and 403 define the shared UID v1 threat model, remove the immutable and construction claims, require a distinct principal and external integrity anchor for enterprise, and add hostile direct-file tests. |
| CS-2 daemon-mediated read path | PASS | Lines 80, 281, 348, 470, and 512 make the daemon the reader, apply Identity authorization and access audit, and remove `lilo transport paths` from v1. |
| CS-3 managed-inference scope | PASS | Lines 9, 37, 63, 83, 109 to 119, 394, and 511 narrow the claim to managed model inference, enumerate bypasses, exclude construction-level coverage, and separate Running from the first exchange receipt. |
| CS-4 spawn coverage matrix | PASS | Lines 85 to 96 provide the normative grouped matrix, state that every grouped mode expands to both cells, require CAPTURED or REJECTED BEFORE SHIM SPAWN, add launcher conformance, make capability reporting runtime and backend specific, and exclude shell resume. Open choices are owned at lines 423, 479, and 483. |
| CS-5 evidence vocabulary and digest domain | PASS | Lines 9, 73 to 76, 251 to 262, and 368 to 371 name four artifact directions, reserve wire octets, record transforms, define the canonical redacted digest domain, require keyed HMAC for credential identity, and split the fidelity suite. E4 remains the artifact-first ordering at line 456, as consensus required. |
| CS-6 authority split | PASS | Lines 240 to 274 distinguish filesystem content authority, authoritative transactional control state, and rebuildable projections. Lines 266 to 272 define recovery precedence for all five consensus disagreement classes. E5 is corrected at line 457. |
| CS-7 durability physics and bounds | FAIL | Lines 244 and 308 claim power-loss survival and prohibit any measured loss window. Lines 307 and 421 nevertheless permit and test up to 1 MiB of unsynchronized response bytes. Unsynchronized bytes can be lost on power failure, so the corrected contract still contains the contradiction CS-7 required it to remove. The OS primitives, request ceiling, spool bound, exhaustion policy, and p95 budgets are otherwise present at lines 244, 303, 307 to 312, and 421. |
| CS-8 availability and break glass | PASS | Lines 303 and 421 set the 3 second capture timeout, its sequencing against the 10 second ShimReady timeout, launch and per-turn p95 limits, and target platforms. Lines 303 and 447 explicitly choose no break glass and reject managed launches on unavailability. |
| CS-9 retention exhaustion valve | PASS | Lines 320 to 327 define warning, reserve, new-launch refusal, reserved capacity for active captures, a mandatory per-session ceiling, typed truncation, and hold behavior. Lines 423 and 486 honestly ledger Stuart's numerical values while requiring them before release. |
| CS-10 deletion semantics and closure | PASS | Line 168 adds the current `delete_one` behavior to the rewrite list. Lines 329 to 343 define terminate then erase, idempotent repeated delete, the separate-verb decision, every required replica class, external authority boundaries, and surviving audit fields. Line 388 gates full lineage closure. |
| CS-11 coordinator, lease, and readiness | PASS | Lines 121 and 295 to 301 define one Session app coordinator, one dependency direction, prepare before `begin_spawn`, one-use lease material, cancellation or finalization on every Runtime result, and fault injection through the first request. Lines 421, 459, and 477 preserve the gate and topology ownership. |
| CS-12 listener and credential threat model | PASS | Lines 278 to 289 distinguish the data-plane listener from management, bind it to the expected process or session, constrain host, path, size, concurrency, and deadlines, add hostile sibling tests, and enumerate prohibited credential operations plus the canonicalization boundary. |
| CS-13 redirect feature regression | PASS | Lines 214 and 226 record Remote Control and MCP tool search regressions, require the complete harness feature matrix and disclosure, and assign U15. Lines 388, 419, 453, and 490 carry the release gate and conditional E1 posture. |
| CS-14 legal-risk downgrade | PASS | Line 65 uses inference marking, removes the unsupported country list, requires counsel and jurisdiction-specific primary authority, and blocks enterprise managed deployment. Lines 406, 423, and 484 retain the enterprise gate and U9. |
| CS-15 capture-fault response | PASS | Line 309 specifies HTTP 422, the provider-shaped body, stable code, non-retryable intent, and daemon, CLI, and doctor mapping. Line 388 requires one harness failure, zero upstream requests, and zero retry amplification. |
| CS-16 compatibility and contract gates | PASS | Line 169 treats the doctor rename as a versioned wire-contract repair. Lines 356 to 362 define versioning, bounded pagination, payload limits, errors, orphan selectors, authorization, and MCP ownership. Lines 383 to 388, 410 to 411, 417, and 427 gate retained adapter fixtures, one linear migration chain, typed RPC, generated CLI JSON, and Gate 5 publication. |

## Accepted finding coverage

All 28 adjudicated findings map to the correction results above:

- C-P0-1, A-P1-3, and E-P1-5 map to CS-1, CS-2, and CS-12: PASS.
- C-P0-2 maps to CS-2: PASS.
- C-P0-3, A-P0-1, and E-P1-1 map to CS-3 and CS-4: PASS.
- C-P1-4, C-P1-7, and A-P1-5 map to CS-7: FAIL for the remaining unsynchronized-byte contradiction.
- C-P1-5 maps to CS-8: PASS.
- C-P1-6 maps to CS-9: PASS.
- C-P1-8, A-P0-2, and E-P1-2 map to CS-5: PASS. The partially rejected request to reopen E4 was not reintroduced.
- C-P1-9 maps to CS-15: PASS.
- C-P2-10, C-P2-11, and A-P2-1 map to CS-16: PASS.
- A-P1-1 and A-P2-2 map to CS-11: PASS.
- A-P1-2 and E-P1-3 map to CS-6: PASS.
- A-P1-4 and E-P1-7 map to CS-10: PASS.
- E-P1-4 maps to CS-3: PASS.
- E-P1-6 maps to CS-13: PASS.
- E-P1-8 maps to CS-14: PASS.

## Remaining findings

### S-P1-1: The power-loss contract still permits an unsynchronized response window

Consensus CS-7 requires removal of the measured-loss option whenever power-loss durability is claimed. Canonical line 244 claims process, kernel, and power-loss survival and says the measured loss-window option is removed. Line 308 repeats that incompatibility. Line 307 then permits 1 MiB of unsynchronized response bytes, and Gate 2 at line 421 explicitly tests that window. A power failure can destroy unsynchronized bytes.

Resolve the contract in one direction. Either require the strict platform barrier before corresponding downstream response delivery, or narrow the power-loss claim and describe the bounded response-loss window. The existing text cannot promise both.

No P0 remains. No other accepted correction gap and no new P0 or P1 finding was found.

Verdict: FAIL
