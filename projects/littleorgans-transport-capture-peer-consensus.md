---
title: Peer consensus — littleorgans transport capture synthesis
type: consensus
tags: [transport, capture, peer-review, consensus, littleorgans]
summary: Adjudication of the three independent peer reviews of littleorgans-transport-capture--synthesis.md; verdict CORRECTION REQUIRED, 16 bounded corrections
status: complete
source: helioy-tools:research-synthesizer
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

Consensus Verdict: CORRECTION REQUIRED

## Worker Status

No nested workers. Consensus adjudicated directly by the assigned research-synthesizer peer. Read-only: neither repository nor the synthesis was edited. Governing constraints honoured: mandatory native capture, zero `tm` dependency, `transport-matters/NOTES` never read or cited.

## Inputs consumed

| Report | Status | Verdict | Findings |
|---|---|---|---|
| littleorgans-transport-capture-peer-review-claude.md | COMPLETE | CORRECTION REQUIRED | 3 P0, 6 P1, 2 P2 |
| littleorgans-transport-capture-peer-review-codex-architecture.md | COMPLETE | CORRECTION REQUIRED | 2 P0, 5 P1, 2 P2 |
| littleorgans-transport-capture-peer-review-codex-evidence.md | COMPLETE | CORRECTION REQUIRED | 0 P0, 8 P1 |

Adjudication target: `~/.mdx/projects/littleorgans-transport-capture--synthesis.md` (Status COMPLETE, 434 lines) at pins littleorgans `98d8928941b5b5db670ed73ed06af57f61dcfa0a`, transport-matters research `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`.

## Independent verification performed by this consensus

Multi-review claims were treated as cross-corroborated. Sole-source claims were independently verified before acceptance:

- Pin confirmed: `git rev-parse HEAD` = `98d8928...` in the littleorgans working tree.
- `crates/lilo-im-core/src/audit.rs::AuditDecision::evaluate_local`: `Principal::Local(uid)` matching `local_uid` yields `Allow` for every action; no role dimension. C-P0-1's identity-model premise holds.
- `internal/session/daemon/src/handler/sessions.rs::delete_one`: authorizes `Action::Kill`, returns early for terminated sessions, terminates the runtime, never deletes the Session row. A-P1's delete-semantics premise holds.
- `internal/runtime/launchers/src/lib.rs::registered_launchers` returns exactly Claude and Codex; generated help advertises both. The runtime-escape premise holds.
- `internal/runtime/app/src/cli/shim.rs`: `exec_shell_resume`/`shell_resume_command` exist, and the test `shell_resume_command_clears_pre_existing_env` confirms the shell-resume env path is independent of `LaunchSpec.env`.
- Primary source fetched 2026-07-31 (code.claude.com/docs/en/remote-control): "As of v2.1.196, Remote Control is also disabled when `ANTHROPIC_BASE_URL` points at a host other than `api.anthropic.com` ... Unset the variable to use Remote Control." The sole-source E-P1-6 regression claim is CONFIRMED.

## Adjudication of all 28 findings

Notation: C = claude review, A = codex-architecture, E = codex-evidence. Every finding classified individually; convergence noted, never merged blindly.

### Claude review (11 findings)

| Finding | Class | Reason |
|---|---|---|
| C-P0-1 same-UID agent owns the evidence; "immutable"/"by construction" false | ACCEPT | Verified identity model (allow-all for matching uid, no roles) plus 0700/0600 file authority under the same uid. Independently corroborated by A-P1 (same-UID paths bypass) and E-P1-5. Claim-level P0: changes what the product may say in section 14 |
| C-P0-2 sections 9 and 12 specify incompatible read paths | ACCEPT, framing adjusted | The two sentences are reconcilable if the daemon performs tier-1 disk reads over RPC ("no database read path" is disk-vs-Postgres, not CLI-vs-daemon), so "mutually exclusive" overstates. The defect stands at P0 as underspecification with a security consequence: the reading process is never named, and `lilo transport paths` definitionally enables unaudited direct reads, voiding the audited-read claims |
| C-P0-3 "mandatory" unenforceable by env injection; invariant 2 overreach | ACCEPT | Three escape routes, two already open in the ledger (U8, U10) and one unnamed (agent subprocess with cleared env / direct egress, unobserved per R14). Corroborated by E-P1-4's coverage-scope finding |
| C-P1-4 durability barrier assumes fsync semantics macOS does not provide; "small" wrong | ACCEPT | Documented APFS behavior: `fsync` does not flush the drive cache, only `F_FULLFSYNC`; zero `F_FULLFSYNC` hits in the workspace. Request bodies are O(context) per turn, not small. Corroborated by A-P1 (hot-path durability) |
| C-P1-5 availability: no latency/timeout budgets, unspecified break-glass | ACCEPT | Verified 10s ShimReady ceiling exists and section 10 names `capture_start_timeout` without a value or relation to it; E6 has no pass/fail threshold, so Gate 2 cannot fail on performance |
| C-P1-6 retention self-wedging exhaustion, no eviction valve | ACCEPT | Composition of three synthesis commitments (never delete active, values deferred to U11, mid-run policy open) produces the wedge; no per-session ceiling exists. Distinct from E-P1-7 (deletion closure); not merged |
| C-P1-7 no request-size ceiling, undefined spool exhaustion | ACCEPT | Both available exhaustion behaviors are already prohibited elsewhere (R10 vs U1), so the policy must be a named decision |
| C-P1-8 digest domain undefined; write-time redaction breaks "exact octets" | ACCEPT | Subsumed into the P0 evidence-vocabulary cluster (see A-P0-2). The HMAC-not-bare-hash requirement (bare digest of credential-bearing bytes is an offline verification oracle) is retained as a specific correction |
| C-P1-9 capture-fault response toward the harness undefined; retry amplification | ACCEPT | Section 7 itself establishes that the harness retry logic matches upstream wording; a 5xx-shaped capture fault multiplies failures. Contract-level gap |
| C-P2-10 no artifact-format compatibility or migration-chain gates | ACCEPT | Versioned header and export bundle are committed with no gate proving old fixtures stay readable; L4 single-chain plus a concurrent capture migration train is unguarded |
| C-P2-11 doctor `runtime_matters` fix is a wire-contract change, not a rename | ACCEPT | Verified field is a wire-visible response field; Gate 0 exit note |

### Codex-architecture review (9 findings)

| Finding | Class | Reason |
|---|---|---|
| A-P0-1 supported spawn paths escape mandatory capture; no coverage matrix | ACCEPT; remedy detail DEFER | Verified: both runtimes registered, `RuntimeKind::Other` accepted, raw spawn takes operator SessionId, Docker open (U8), raw posture open (U4), shell_resume env independent. L1 ("cannot ship without it") cannot coexist with an unruled surface. The matrix and conformance gate are required; the specific choice of which cells to disable versus require in v1 is Stuart's, at Gate 3, bound to the existing Codex-in-v1, U4, and U8 entries |
| A-P0-2 evidence root cannot be exact, redacted, and application-level at once | ACCEPT | Four incompatible synthesis claims quoted accurately; an application reverse proxy re-issues HTTP, so "passthrough-perfect by construction" and "exact wire bytes root of trust" cannot both survive write-time header redaction. Corroborated by E-P1-2 and C-P1-8. Severity ruled P0 (see contradiction resolutions) |
| A-P1-1 `LaunchSpec` is an injection seam, not the capture orchestration seam | ACCEPT | Verified `prepare_launch` is a pure synchronous rewrite; capture preparation is asynchronous with cancellation and finalization state. E7 stands as the injection carrier; the coordinator, dependency direction, and lease lifecycle must be defined before implementation. The review's seven-step lease design is a candidate input, not mandated verbatim |
| A-P1-2 authority model cannot replay deletion and governance state from files | ACCEPT | Tombstones, holds, and audit are independent authority by definition; drop-and-rebuild either resurrects deleted content or erases the proof of deletion. Corroborated by E-P1-3 |
| A-P1-3 same-UID files and `paths` bypass authorization and audit | ACCEPT | Same cluster as C-P0-1/C-P0-2; the hostile same-UID direct-file test (not only RPC authorization tests) is a distinct, retained requirement |
| A-P1-4 `lilo delete session` currently terminates; synthesis makes it erase | ACCEPT | Verified `delete_one` at the pin. Breaking semantic replacement, belongs on the explicit delete-and-rebuild list with a terminate-vs-erase verb decision |
| A-P1-5 hot-path durability contract still permits the loss it forbids | ACCEPT | The window option contradicts the before-delivery guarantee under power loss; the "small pre-stream request" assumption is unsupported. Merged operationally with C-P1-4/C-P1-7 into one correction, with the failure-domain framing (process/kernel/power) retained as this finding's contribution |
| A-P2-1 read contract is a list of verbs, not a contract | ACCEPT | Error shapes, pagination, limits, selector behavior for session-less captures, schema versioning, MCP ownership all undefined; Gate 5 exit requirement |
| A-P2-2 readiness is point-in-time; text promises a process invariant | ACCEPT | A capture worker can die between readiness commit and child start. Restate the invariant around provider egress and a live capture lease; narrow process-existence claims |

### Codex-evidence review (8 findings)

| Finding | Class | Reason |
|---|---|---|
| E-P1-1 release gate lets an advertised runtime escape the capture invariant | ACCEPT | Same defect as A-P0-1 viewed from the release gate; the per-launcher conformance gate (iterate `registered_launchers()`, require adapter or pre-spawn refusal) and runtime-specific capability reporting are retained as distinct requirements. Adjudicated severity: P0 as part of the coverage cluster |
| E-P1-2 evidence vocabulary and acceptance denominator overclaim byte fidelity | ACCEPT items 1-4; item 5 PARTIAL REJECT | Artifact naming, "wire octets" reservation, split acceptance suite, and independent byte oracle are accepted (cluster with A-P0-2). Item 5's demand to reclassify E4 is rejected in part: E4's substance is the raw-first versus IR-first ordering principle, which no fidelity finding falsifies. The correction renames the artifact vocabulary inside E4 and demotes "passthrough-perfect by construction" to an oracle-verified claim; the ordering decision is not reopened |
| E-P1-3 control state both authoritative and replayable | ACCEPT | Same cluster as A-P1-2; the recovery-precedence table (per disagreement class) and the "content half supported, control half unresolved" split of E5 are retained as this finding's contribution |
| E-P1-4 enterprise claim describes agent behavior Transport cannot evidence | ACCEPT | "Every agent action" and "what did my agent actually do" exceed inference-exchange evidence; R14 excludes shell capture by design. The launch-truth observation is verified against the synthesis text: section 1 promises "reached the provider and got a response" while section 10 commits Running at readiness, before any exchange. First-exchange receipt state or narrowed claim required |
| E-P1-5 credential transit, listener, audited access lack one threat model | ACCEPT | The per-session loopback listener is a new data-plane door; "no new listener doors" is internally contradicted by the launch sequence. "No new management listener" is the correct statement. Transient-processor credential definition and hostile-sibling tests retained |
| E-P1-6 redirect mode omits a confirmed product regression | ACCEPT, CONFIRMED | Verified today against the primary vendor source: Remote Control disabled under non-first-party `ANTHROPIC_BASE_URL` as of Claude Code 2.1.196; MCP tool search default-disabled per the env reference. The phase-one protocol report carried this and the synthesis dropped it. E1's "adoptable without further ceremony" cannot stand; mandatory enrollment silently removes an advertised harness capability |
| E-P1-7 deletion acceptance does not close every copy | ACCEPT | The release assertion covers only the primary row and directory; transcript snapshots, quarantine, dead-letter, exports, staged dirs, future blobs, and backups are uncovered. Distinct from C-P1-6; not merged |
| E-P1-8 jurisdiction-specific legal statement marked [F] without primary support | ACCEPT | R37's cited sources are secondary; EDPB and BetrVG support a narrower statement than the four-country claim. Downgrade to [I] legal risk; U9 stays open |

Tally: 27 ACCEPT (one with a partial rejection inside E-P1-2; one with remedy detail deferred inside A-P0-1), 0 findings rejected outright, 0 deferred outright.

## Contradiction resolutions

1. **Severity of the evidence-fidelity cluster** (A: P0; C and E: P1). Ruled P0. The overclaim undefines the subject of the section 13 fidelity oracle and the section 8 root of trust, which downstream gates build on. A correction to vocabulary is cheap, but the document cannot govern implementation while its central evidence artifact has no unique definition.
2. **Severity of the same-UID integrity cluster** (C: P0; A and E: P1). Ruled P0. Section 14 treats the enterprise sentence as the sale; a claim the identity model cannot deliver is a product-level defect, not an implementation detail.
3. **Codex-evidence reported zero P0.** No factual conflict; its P1-1 and P1-2 are the same defects the other reviews rank P0, reached with a stricter definition of P0. Subsumed into the P0 clusters above.
4. **C-P0-2's "mutually exclusive" framing.** Adjudicated as reconcilable (daemon-mediated disk reads satisfy both sentences); severity retained because the synthesis never names the reading process and ships `paths`.
5. **E-P1-2 item 5 versus ledger E4.** Rejected in part, as recorded above. No reviewer contradicts E4's ordering principle on the merits.

## Bounded Correction Specification

Sixteen corrections. Each names the exact synthesis sections and claims to change. No repository edits; all corrections are prose, ledger, and gate-criteria changes to `littleorgans-transport-capture--synthesis.md`. CS-1 through CS-5 are P0 and belong at Gate 0 (before the document governs any implementation); CS-6 through CS-15 are P1; CS-16 aggregates the P2 gate additions.

**CS-1 (P0). Integrity claim honesty.** Sections 2 (principle 7 "immutable once created"; job 6), 9, 14. State the v1 threat model explicitly: one non-adversarial operator observing their own agents, all under one UID; evidence is tamper-evident at best, not tamper-proof. Strike "immutable" and "by construction" from v1 and enterprise copy, or condition them on the enterprise tier delivering a distinct agent principal (process-bound capability carried on the read path) plus an integrity anchor outside the uid's reach (hash chain with checkpoints signed by a key the agent cannot read). Add the hostile same-UID direct-file test to section 13. Do not pair v1 posture with enterprise copy.

**CS-2 (P0). Read-path declaration.** Sections 9, 12, 14. Name the process that performs capture file reads. Recommended resolution: daemon-mediated reads via the `LilodRpc` Transport variant so Identity gating and audit hold; reword section 12's "reads come off tier-1 disk" to make clear the daemon reads the disk. `lilo transport paths` is either removed from v1 or ledgered as an explicit unaudited direct-access boundary. If CLI-direct reads are chosen instead, delete the audited-raw-read claims from sections 9 and 14 and record the consequence in the ledger.

**CS-3 (P0). Mandatory-scope honesty.** Sections 1, 3 (minimum-v1 sentence), 4 (invariant 2), 7 (exclusion list), 14. Rescope invariant 2 and the minimum-v1 sentence to the managed harness inference channel. Extend the published exclusion list with agent-spawned subprocesses carrying modified environments and direct agent network egress. Add a ledger entry: construction-level enforcement requires network egress control and is out of v1 scope. Rewrite the section 14 enterprise sentence as evidence of model inference exchanges, removing "every agent action" and "whether a human touched it". Narrow section 1's launch-truth claim: Running means process plus capture readiness; a positive provider response is later evidence (add a first-exchange receipt state or soften the sentence).

**CS-4 (P0). Spawn coverage matrix.** Sections 3, 4, 16 (L1, U4, U8, Gate 3). Add a normative matrix over {session run/create, raw runtime spawn} x {claude, codex, `RuntimeKind::Other`} x {host, docker} x {headless, tmux}: every cell reads CAPTURED or REJECTED BEFORE SHIM SPAWN. Add a conformance gate iterating `registered_launchers()` requiring a qualified adapter or pre-spawn refusal per entry; make capability and doctor reporting runtime-specific; exclude post-agent shell resume explicitly from the coverage claim. The disable-versus-require choice for Codex, Docker, and Other cells goes to Stuart at Gate 3, folded into the existing Codex-in-v1, U4, and U8 entries.

**CS-5 (P0). Evidence vocabulary and digest domain.** Sections 1, 3 (Wire and Fidelity rows), 8, 13. Replace generic "raw"/"wire bytes" claims with the artifact contract: named classes (inbound client headers/body, outbound provider headers/body, upstream and downstream response chunks) with each decoding, framing, and redaction transform recorded; reserve "wire octets" for capture points that observe octets. Define the digest domain: digest over the canonical redacted artifact, plus a keyed HMAC (never a bare hash) if credential identity must be provable. Demote "passthrough-perfect by construction" to a relay-fidelity claim verified by the X1/X3 oracle. Split section 13's fidelity class into relay fidelity, persisted body fidelity, structural round-trip, and intentional secret omission, with an independent client-and-upstream byte oracle. E4's raw-first ordering is not reopened.

**CS-6 (P1). Authority split.** Sections 8, 16 (E5). Content bytes and launch facts remain filesystem authority. Authorization audit, access audit, capture lifecycle rows, tombstones, holds, and deletion outcomes become a transactional control ledger that is authoritative, not replayable. Only derived search and read-model rows are declared rebuildable. Add a recovery-precedence rule for every file-versus-ledger disagreement (missing row, missing directory, staged delete, hold, incomplete audit outcome). Revise E5: content half stands, control half is superseded.

**CS-7 (P1). Durability barrier physics and bounds.** Sections 8, 10, 15 (Gate 2 exit), 16 (U3). Name the platform primitive per OS (`F_FULLFSYNC` on macOS APFS; `fsync` plus parent-directory fsync on Linux) and state the claimed failure domain (process crash, kernel crash, power loss); if power loss is claimed, the measured-window option is removed. Strike "small" from section 10. Add a request-size ceiling and a spool bound with explicit values, and name the exhaustion policy (backpressure, documented loss window, or fault) as a ledger decision. X6 must measure with the correct primitive against a real request-size distribution (multi-turn, cached prefix, images) with a stated p95 budget.

**CS-8 (P1). Availability budgets and break-glass.** Sections 10, 15 (Gate 2 exit). Attach numbers: added p95 launch latency budget; a `capture_start_timeout` value and its relation to the 10s ShimReady ceiling; the per-turn overhead ceiling at which E6 fails. Specify the break-glass setting concretely (name, default off, Identity-audited, doctor-surfaced) or ledger that none exists and capture unavailability stops all launches on the host.

**CS-9 (P1). Retention exhaustion valve.** Sections 11, 16 (U11). Define the exhaustion order of operations: free-space reserve, doctor warning threshold before incident, refusal of new launches while existing captures continue, per-session byte ceiling whose breach produces typed truncation evidence. The reserve and per-session ceiling ship in the same release as capture, not at U11/Phase 4.

**CS-10 (P1). Deletion semantics and closure.** Sections 5 (delete-and-rebuild list), 11, 12, 13. Add the current `delete_one` path to the explicit delete-and-rebuild list; define terminate-then-erase ordering, the idempotent response after the Session row is gone, and whether termination-without-erasure gets a separate verb. Add a data-lineage table covering every content class and replica (transcript snapshots, quarantine and dead-letter records, exports, staged delete dirs, future content-addressed blobs, backups) with per-class delete, expiry, hold, and erase semantics; state which exports and backups are outside daemon authority; test deletion closure across all owned roots and indexes; enumerate the surviving audit fields.

**CS-11 (P1). Capture coordination seam and readiness invariant.** Sections 4, 5, 15 (Gates 2 and 5), 16 (U2, E7). E7 stands as the injection carrier; add the requirement that one coordinator and one dependency direction be defined before implementation (the capture-lease pattern is the candidate design: prepare before `begin_spawn`, one-use lease carrying child launch material, cancel or finalize on every runtime outcome). Align the worker-topology decision (in-process task versus Runtime-owned child) with the ownership table. Restate the readiness invariant around provider egress: no provider request bypasses a live capture lease, held through child start, with fault injection at every interval between prepare, readiness, shim start, child start, and first request. Narrow process-existence claims accordingly.

**CS-12 (P1). Listener and credential threat model.** Section 9. Replace "no new listener doors" with "no new management listener" and threat-model the per-session loopback data-plane listener separately: process or session binding of accepted connections, host and path validation, connection and request limits, deadlines, hostile same-UID sibling tests. Define Transport as a transient processor of provider credentials with the prohibited operations enumerated (own, reuse, refresh, persist) and the write boundary that removes secrets named.

**CS-13 (P1). Redirect-mode feature regression.** Sections 7, 15 (Gate 1, X1), 16 (E1). Record the confirmed regression: as of Claude Code 2.1.196, Remote Control is disabled when `ANTHROPIC_BASE_URL` points off `api.anthropic.com`, and MCP tool search is default-disabled for a non-first-party base URL. E1 is demoted from "adoptable without further ceremony" to conditional: redirect mode remains the v1 lean, but the X1 exit gains a harness feature matrix (inference, streaming, tools, subagents, MCP tool search, resume, background work, Remote Control) and an operator disclosure list. Add a Stuart ledger entry (U15): whether Remote Control unavailability under mandatory capture is an accepted product tradeoff or requires mitigation.

**CS-14 (P1). Legal claim downgrade.** Sections 2 (line 65 [F]), 16 (U9). Downgrade the employment-consent and four-country works-council statement from [F] to [I] legal risk; remove the DE/NL/AT/SE list or attach jurisdiction-specific primary authority reviewed by counsel; make the enterprise managed-deployment legal posture a release gate. U9 remains open.

**CS-15 (P1). Capture-fault response contract.** Section 10. Specify the pre-delivery capture-fault response toward the harness: status code, body shape, deliberately chosen to be non-retryable by the harness retry logic, and the operator-visible mapping. This is contract, not implementation.

**CS-16 (P2). Gate additions.** Sections 13, 14, 15 (Gates 0 and 5). Add: (a) a fixture-compatibility gate proving a run directory written by an earlier adapter revision reads with the current reader; (b) a migration-chain linearity gate in CI; (c) the typed v1 Transport RPC and generated CLI JSON contract published before Gate 5 closes, including bounded pagination, payload limits, stable error codes, schema versioning, selector behavior for captures without Session rows, authorization per view, and MCP tool ownership; (d) a Gate 0 exit note that the doctor `runtime_matters` repair is a wire-contract change.

## What survives review unchanged

All three reviews independently upheld: the zero-`tm` boundary (verified negative at the pin by all three), Transport as a fourth bounded context, the `LaunchSpec` funnel as the interposition carrier, `SessionId` as the join key, the foundation-repair list (with the delete path added per CS-10), the experiment and stop-gate discipline, and the reject map. The architecture is sound; every accepted correction is claim-level, ledger-level, or gate-level. No correction reopens L1 through L8.

## Self-audit

- [x] All three reviews consumed only after each reached Status: COMPLETE
- [x] Every P0/P1/P2 finding (28 total) individually classified with reason; no blind votes or merges; one partial rejection and one remedy deferral recorded with grounds
- [x] Sole-source claims independently verified at the pin or against primary sources before acceptance; verification record included
- [x] Contradictions between reviews named and resolved with explicit reasoning (five resolutions)
- [x] Correction specification bounded: 16 corrections, each naming exact synthesis sections and claims
- [x] Mandatory native capture and zero `tm` dependency preserved; no correction introduces any tm relationship
- [x] `transport-matters/NOTES` never read or cited
- [x] No repository or synthesis edits performed
