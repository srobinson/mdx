---
title: Peer review — littleorgans transport capture synthesis (claude backend-engineer)
type: review
tags: [backend, security, durability, operations, transport, capture, peer-review]
summary: Hostile enterprise/security/durability/ops peer review of littleorgans-transport-capture--synthesis.md; verdict CORRECTION REQUIRED, highest severity P0
status: complete
source: backend-engineer
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

Verdict: CORRECTION REQUIRED

Reviewer: claude helioy-tools:backend-engineer, independent, read-only. No file in either repository was modified; the synthesis was not edited.

Scope reviewed: `~/.mdx/projects/littleorgans-transport-capture--synthesis.md` (434 lines, Status COMPLETE).

Pins validated: littleorgans at `98d8928941b5b5db670ed73ed06af57f61dcfa0a` (confirmed `git rev-parse HEAD`); transport-matters research evidence at `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55` (confirmed present; repo HEAD is `ed09933`, all citations below read via `git show a252df2:<path>`). `transport-matters/NOTES/` was not read or cited.

Governing constraints honoured in this review: mandatory native capture, zero `tm` dependency. No finding below proposes invoking, packaging, versioning against, or porting `tm`.

## Findings

### P0-1. The captured subject is the same UID as the evidence owner, so "evidence is immutable" and "evidenced by construction" are false as written

**Evidence.** Authorization collapses to a single local UID with no role distinction. `crates/lilo-im-core/src/types.rs::Principal` has exactly one usable variant, `Principal::Local(u32)`, a bare uid. `crates/lilo-im-core/src/audit.rs` lines 19 to 29 grant `Self::Allow` for every `Action` when `Principal::Local(uid)` matches `local_uid`, and deny otherwise. `crates/lilo-im-core/src/types.rs::Action` (the `define_actions!` list, lines 147 to 160) has no role dimension at all. The agent process launched by `lilo run` executes under that same uid, and the synthesis deliberately hands it the socket, the id, and a read verb (section 12: `lilo transport show $LILO_AGENT_SESSION_ID`).

Filesystem authority has the same shape. Capture roots are specified `0700`/`0600` under `~/.lilo` (section 9), owned by the operator uid. The agent runs as that uid, so it can `unlink`, `truncate`, or rewrite its own capture directory directly, with no RPC involved. Section 14 R14 explicitly refuses capturing agent-run shell commands, so this path is unobserved by design.

**Why the claim fails.** Section 2 principle 7 ("Evidence is attributed and immutable once created"), section 2 job 6 ("Prove what happened"), and section 14 ("every agent action on this host is evidenced by construction: who authorized it, what was sent, what came back, whether a human touched it") are integrity claims against an adversary. The only adversary that matters for those claims, the agent, sits inside the trust boundary with full write authority over the evidence and over the audit rows. Section 9's "operator calls require the operator principal" is not expressible in the current identity model. Gate 4 repair 2 scopes a one-use launch capability, which closes shim impersonation only; it does not separate operator from agent for read, export, retention change, or delete.

**Required correction.** Either (a) state explicitly in section 9 and section 14 that the v1 threat model is a non-adversarial operator observing their own agents, that evidence is tamper-evident at best and not tamper-proof, and strike "immutable" and "by construction" from enterprise copy; or (b) introduce a real agent principal distinct from the operator principal (process-bound capability at launch, same mechanism as repair 2, carried on the read path), gate delete/export/retention on operator-only, and place the integrity anchor outside the uid's reach (hash chain with checkpoints signed by a key the agent cannot read, or a separately owned append-only sink). Do not ship (a) and enterprise copy from (b). This must be settled at Gate 0, not deferred: it changes what the product is allowed to claim, and section 14 already treats the claim as the sale.

### P0-2. Section 9 and section 12 specify mutually exclusive read paths, and the section 12 form voids the entire capture authorization and audit story

**Evidence.** Section 9: "No new listener doors: capture adds no HTTP server; reads go through the existing socket and typed RPC." Section 12: "Reads come off tier-1 disk; no database read path required for v1." Section 5 keeps `internal/wire/src/lib.rs::LilodRpc` (verified: exactly `Session` and `Runtime`) as the composition point with an additive third variant, which implies daemon-mediated reads. The `lilo` CLI is a separate process. If it opens the capture files itself, no `Action` is evaluated, `internal/identity/service/src/client.rs::IdentityClient::authorize_in_tx` never runs, and section 9's "Identity gates capture inspection, raw access, export, retention changes, deletion" plus section 14 gate item "authorized audited reads" are unimplementable. Combined with P0-1 the gap is total: raw evidence is readable by anything running as that uid with no audit record.

**Required correction.** State in one place which process performs the file read. If it is the daemon, say so in section 12 and accept the RPC payload consequences (see P1-5). If it is the CLI, delete the audited-raw-read claim from section 9 and from the section 14 gate set, and record in the ledger that v1 raw reads are unauthorized and unaudited by design.

### P0-3. "Mandatory" is not enforceable by env injection, and two of the three escape routes are already open in the ledger

**Evidence.** E7 locks interposition by env at the runtime launch seam. The seam is real and single: `internal/runtime/daemon/src/api.rs::spawn_domain` line 81 materializes argv once and `internal/runtime/daemon/src/backend.rs::prepare_launch` is the rewrite point (verified, Docker dispatches there). Env injection binds the harness process. It does not bind the agent as a principal. Three bypasses: U10/X7 background-agent supervisor env inheritance (named, open), U8/X8 container netns reachability (named, open), and a third the synthesis never names, the agent spawning any subprocess with `ANTHROPIC_BASE_URL` cleared or invoking the provider by direct HTTP, which R14 places outside capture scope. Section 4 invariant 2, "The agent cannot send provider traffic before capture is armed for its `SessionId`", is therefore false for the agent and true only for the managed harness's own inference channel.

**Required correction.** Restate invariant 2 and section 3's minimum-v1 sentence as scoped to the managed harness inference channel. Extend section 7's published exclusion list (currently fast-mode checks, WebFetch preflight, telemetry, plugin downloads) with agent-spawned subprocesses carrying modified environments and direct agent network egress. Record in the ledger that construction-level enforcement requires egress control at the network layer and is out of v1 scope. Section 14's enterprise sentence must be rewritten with the same scope or it will not survive first contact with a security reviewer.

### P1-4. The durability barrier is specified on macOS semantics that do not exist, and its cost is prejudged

**Evidence.** Section 10 makes a durable tier-1 commit of the outbound request the pre-release barrier and characterises it as "(small, pre-stream, fsync-class latency)". Section 8 crash contract item 1 requires "temp, fsync, rename; parent directory sync". Nothing in the repository or the synthesis names `F_FULLFSYNC`: a workspace grep for `FULLFSYNC|F_FULLFSYNC|full_fsync` across `*.rs` and `*.md` returns zero hits, and the only durability calls present are `internal/runtime/daemon/src/event_log.rs` line 364 `sync_data()` and line 385 `sync_all()`, plus `internal/session/app/src/cli/config.rs` line 77. On APFS, `fsync(2)` (which `File::sync_all` maps to) does not flush the drive write cache; only `fcntl(F_FULLFSYNC)` does. The primary development and target platform is macOS. Under power loss the barrier therefore does not hold, and the entire crash matrix in section 8 and gate 1 of section 14 rests on an unproven primitive.

Separately, "small" is wrong for the workload. Claude Code re-sends the full conversation prefix every turn; request bodies grow monotonically within a session and reach hundreds of kilobytes to megabytes with file content and images. The barrier is O(context size) synchronous work on every turn, and `F_FULLFSYNC` costs milliseconds to tens of milliseconds per call.

**Required correction.** Name the platform primitive explicitly in section 8 (F_FULLFSYNC on macOS, fsync plus parent-directory fsync on Linux, and whether the same guarantee is claimed on both). Strike "small" from section 10. Require X6 and the Gate 2 exit to measure against a real request-size distribution (multi-turn, cached prefix, image attachment) with a stated p95 budget, and to measure with the correct primitive. A measurement taken with plain `fsync` on macOS is not evidence for U3.

### P1-5. Availability: mandatory plus launch-fail-closed makes Postgres and disk headroom hard dependencies of the platform's core verb, with no bounded budget and no escape

**Evidence.** Section 10 sequence steps 1 to 6: a Postgres composite-intent commit and a capture readiness proof gate every spawn; failure aborts the spawn (E9). Today no such coupling exists; `spawn_domain` proceeds without any capture dependency. The added work is a DB transaction plus a listener bind plus a durable header write plus a readback on the launch hot path, inside a CLI that already carries a 10 second `ShimReady` ceiling (`internal/runtime/daemon/src/api.rs`, `tokio::time::timeout(Duration::from_secs(10), begin.ready)`). Section 10 names `capture_start_timeout` but no value, and never relates it to that ceiling. Section 14 defines no latency or availability target anywhere; E6's 1/5/20 concurrent-stream envelope has no pass or fail threshold, so Gate 2 cannot fail on performance.

Consequence for a local developer tool: Postgres container down, disk full, or a wedged capture worker equals total work stoppage, and section 10 forbids a break-glass path without an explicit operator setting that is not specified.

**Required correction.** Attach numbers to Gate 2 exit: added p95 launch latency budget, `capture_start_timeout` value and its relation to the 10s ShimReady ceiling, and the per-turn overhead ceiling at which E6 fails. Specify the break-glass setting concretely (name, default off, audit action, doctor surfacing) or record in the ledger that none exists and that capture unavailability bricks the host.

### P1-6. Retention has a self-wedging exhaustion path with no eviction valve

**Evidence.** Section 11: "Retention can never delete an active capture", retention is age and size bounded with "generous but finite defaults", values deferred to U11 (Stuart, Phase 4). Section 10: storage failure after delivery has begun follows the mid-run loss policy (U1, undecided). Compose the three: long-lived active sessions accumulate; the sweeper cannot reclaim them; free space reaches zero; in-flight captures fail their writes and take the mid-run branch; new launches fail readiness (P1-5). Nothing in the design refuses new work before existing work fails, and there is no per-session ceiling, so a single runaway session can consume the host.

**Required correction.** Define the exhaustion order of operations in section 11: a free-space reserve, a warning threshold surfaced in doctor before incident, refusal of new launches while existing captures continue, and a per-session byte ceiling whose breach produces typed truncation evidence rather than a capture fault. Bring the reserve and the per-session ceiling into the same release as capture (E14 already requires this), not into U11 at Phase 4.

### P1-7. Hostile-workload gap: no request-size ceiling and no defined spool-exhaustion policy

**Evidence.** Section 10 requires "a bounded spool, never an unbounded memory buffer" for responses. The bound is never given, and the behaviour at exhaustion is never stated. Both available behaviours are already prohibited elsewhere: dropping capture while the stream continues is silent fail-open (R10, and the rejected research shape `exchange_recorder/__init__.py::persist_http_provisional_exchange`, verified at the pin to `return None` on the failure path), and killing the stream makes the observer break the run (the U1 question, unresolved). On the request side there is no size ceiling at all, so an oversized body is an fsync-amplified local denial of service through the barrier itself. Section 14 gate 2's hostile-workload list includes compression bombs and stream floods but not these two.

**Required correction.** Add a request-size ceiling and a spool bound with explicit values to section 10, and add the exhaustion policy to the ledger as a named decision rather than leaving it implied by two mutually exclusive prohibitions.

### P1-8. Digest and attestation domain is undefined, and write-time redaction makes the section 8 "exact octets" root of trust unverifiable

**Evidence.** Section 8 reserves "wire bytes" for exact octets and names `client_body_bytes` as the root of trust, immutable. Section 9 and E11 redact or tokenize credential headers before bytes reach disk. Both cannot hold for the same artifact: what is persisted is a modified derivative, so the immutable root of trust does not exist on disk. Section 3 ENT tier and section 8 both promise digests as evidence. The synthesis never states what the digest covers. Over verbatim bytes it is unverifiable, because the verbatim bytes were never written; over the redacted artifact it cannot attest to what was actually sent, which is the evidentiary claim. U13 correctly isolates the body posture but never notices that header redaction already breaks the section 8 vocabulary.

**Required correction.** In section 8, define the digest domain explicitly: digest over the canonical redacted artifact, plus a separately recorded keyed fingerprint (HMAC, not a bare hash, which is an offline verification oracle for a credential) if credential identity must be provable. Reconcile the section 8 "exact octets" definition with E11 by naming the persisted artifact something other than wire bytes, exactly as the section 8 evidence-naming rule demands of every other class.

### P1-9. The capture-fault surface toward the harness is undefined, and the harness retries

**Evidence.** Section 10: "Before provider delivery: request persistence failure fails the request and surfaces a typed capture fault." Section 7 requires forwarding error bodies unmodified because retry logic matches upstream wording. The response shape for a capture fault is never specified. Claude Code retries on 429 and 5xx, so a 5xx-shaped capture fault produces N identical failures, and any shape that looks like a rate limit produces backoff the operator will misread as a provider problem. Section 8 forbids auto-resend and exposes Delivery Unknown, which is correct after delivery, and does not address the pre-delivery retry amplification.

**Required correction.** Specify the capture-fault response: status, body shape, and whether it is deliberately chosen to be non-retryable by the harness, plus the operator-visible mapping. This belongs in the section 10 contract, not in implementation.

### P2-10. Release gates omit artifact-format compatibility and migration-chain contention

**Evidence.** Section 10 commits "a versioned capture header", and section 12 commits an export bundle "with versions and manifest". No item in the section 13 release-gate list or the section 14 gate set proves that a run directory written by an earlier adapter revision is still readable after an adapter revision lands. L4 mandates one migration chain; capture adds a migration train landing concurrently with session and runtime work, and no gate covers chain-ordering conflict.

**Required correction.** Add two gates: read an older pinned run-directory fixture with the current reader, and prove migration-chain linearity in CI.

### P2-11. Doc-repair list is correct but slightly under-specified

**Evidence.** Verified at the pin: `docs/reference/env-vars.md` line 81 does state "spawn UUIDv7" for `LILO_AGENT_SESSION_ID` (contradicting the v4 lock), and `internal/session/core/src/proto/doctor.rs` line 11 does carry `pub runtime_matters: RuntimeDoctorReport`. Both repairs named in section 5 are real. The doctor field is a wire-visible response field, so the fix is a protocol-surface change, not a rename; section 5 lists it as naming residue without saying so.

**Required correction.** Note the doctor field as a wire-contract change in the Gate 0 exit criteria.

## Claims checked and upheld

These load-bearing claims were verified independently and are accurate.

- Zero-`tm` baseline: a workspace grep for `ANTHROPIC_BASE_URL|transport-matters|mitm` across `*.rs`, `*.toml`, `*.sh`, `*.yml` under `crates`, `internal`, `tools`, `scripts`, `.github` returns zero hits. Section 5's verified-negative baseline holds.
- Unauthenticated read before peer credentials: `internal/session/app/src/compose.rs::handle_connection` reads `read_optional_json_line::<_, LilodRpc>` at line 212 and only then calls `peer_creds::extract` at line 226, and `crates/lilo-rm-core/src/proto.rs::read_async_json_line` uses an unbounded `read_until(b'\n')` with no cap. Repair 1 is correctly stated and correctly sequenced before capture.
- Same-UID shim authority: `internal/runtime/daemon/src/identity.rs::authorize_shim_callback` authorizes on `Action::ShimCallback` alone for any local peer that knows a pending `SessionId`. Repair 2 is correctly stated. See P0-1 for why its scope is too narrow.
- Secrets in durable state: `internal/session/store/src/postgres/spawn_intents.rs` serializes the whole `SpawnRequest` into `spawn_request_json` (line 283), and `internal/runtime/daemon/src/docker_argv.rs::append_env_args` renders `--env KEY=VALUE` into argv. Repair 3 is correct.
- Event-log rejection: `internal/runtime/daemon/src/event_log.rs` syncs with `sync_data()` inside append (line 364) and `sync_all()` in compaction (line 385) with no parent-directory sync. The section 5 rejection and the two salvaged idioms are correctly characterised.
- `lilo logs` gap: `internal/session/core/src/paths.rs::lifecycle_transcript_path` returns `None` for `TmuxPaneSnapshot` and `Unavailable`. Section 1's premise holds.
- Research rejection 1 (silent fail-open): `exchange_recorder/__init__.py::persist_http_provisional_exchange` at the pin returns `None` on the outbound refresh failure path while the flow proceeds. Accurate.
- Research rejection 2 (unbounded buffer): `response_stream.py` accumulates the whole body into a `bytearray` held in `flow.metadata` and assigns it to `flow.response.raw_content`. Accurate.
- Interposition seam: `internal/runtime/daemon/src/api.rs::spawn_domain` line 81 is the single argv materialization and `backend.rs::prepare_launch` dispatches Host and Docker. E7's seam claim is correct.
- Additive extension points: `internal/wire/src/lib.rs::LilodRpc` has exactly `Session` and `Runtime`; `crates/lilo-rm-core/src/version.rs::RuntimeCapability` is an additive enum. Section 5's reshape column is accurate.
- Path policy gap: `crates/lilo-paths/src/lilo.rs::LiloHome::from_path` validates only non-emptiness, no mode or ownership. Repair 5 is correct.

## Worker Status

- Reviewer: littleorgans:helioy-tools:backend-engineer:5:2.1, read-only, no nested agents spawned.
- Inputs: the synthesis at the path above; littleorgans working tree at `98d8928` (only `LESSONS.md` modified, untouched by this review); transport-matters research files read via `git show a252df2:<path>`.
- Method: adversarial read of the synthesis, then independent verification of every load-bearing repository claim against the pins. Findings are stated only where verification succeeded or where the synthesis contradicts itself.
- Not reviewed: `transport-matters/NOTES/` (prohibited), the thirteen phase-one artifacts (reviewed the synthesis as delivered), external vendor primary sources cited via the protocol research artifact.
- Limits: no code executed, no proxy or latency measurement performed. P1-4's macOS claim rests on documented APFS `fsync` semantics and the verified absence of `F_FULLFSYNC` in the workspace, not on a measurement.

Verdict: CORRECTION REQUIRED. Three P0 findings, six P1, two P2. The design is sound in its architecture, its bounded-context split, and its durability model. Its failures are claim-level: the enterprise sentence promises tamper-evidence the identity model and filesystem authority cannot deliver, the read path is specified two incompatible ways with a security consequence, and "mandatory" overreaches what env injection can enforce. All three are correctable in prose and ledger entries at Gate 0, before any capture code exists.
