---
title: littleorgans Evidence, Transcript, and Transport boundary
type: design
tags: [littleorgans, evidence, transcript, transport, canvas, bounded-context, issue-37, issue-48, issue-49]
summary: Locks Evidence as the single acceptance boundary for foreign bytes, Transcript as a downstream projection context, and Transport as a live acquisition adapter, replacing the Wire Evidence context question in issues 48 and 49.
status: draft
project: littleorgans
confidence: high
related: [littleorgans-monorepo-migration--synthesis]
---

# littleorgans Evidence, Transcript, and Transport boundary

**Status:** draft for Stuart's decision. Once accepted this splits into
repository documents and closes issues #48, #49, and #37.

**Supersedes:** the Wire Evidence context question in #49, the standalone
Transcript ownership question in #48, and ownership items 2 and 8 of
`docs/architecture/transport.md`.

**Carries forward:** the Issue 37 arena verdict at
`~/.mdx/TMP/pstack/issue37-system-design/judge.md`, pinned to `c2864d0`. Every
live capture ruling in that verdict survives this document. What changes is
where captured bytes live and who owns them.

## 1. The problem the arena did not see

The Issue 37 arena judged three designs for one writer: a live proxy observing
provider traffic. Its verdict gave Transport the capture leases, the provider
bodies, the interpretation, the edits, the forwarding, the disclosure policy,
and the commitment evidence. That verdict is sound for the case it examined.

Issues #48 and #49 then added a second and third writer that the arena never
weighed:

1. A fresh installation adopts an existing capture artifact with no Transport
   process, no lease, and no live traffic.
2. A fresh installation imports a Claude or Codex transcript with no
   `SessionId`, no Runtime, and no wire evidence.

Both writers need exactly what Transport already claimed to own: immutable
accepted bytes, a digest, a fidelity statement, a provenance record, and a
retention lifecycle. Issue #48 item 4 requires Transcript to own exact
immutable source bytes before accepting an import. Issue #49 item 2 gives
`EvidenceArtifactId` to one immutable accepted byte artifact. That is one
requirement written twice.

Building it twice produces two immutable byte owners, two fingerprint paths,
two retention roots, and two deletion orchestrations. The DRY rule in
`CLAUDE.md` forbids that outcome, and the design question is which single owner
absorbs all three writers.

## 2. The boundary rule

> **Nothing durable enters littleorgans except through Evidence acceptance.**

Evidence is the acceptance boundary for foreign bytes. Every path that brings
bytes we did not author into the system, whether a live proxy, an artifact
adoption, or a transcript import, terminates in an Evidence acceptance that
allocates an identity, owns immutable bytes, records a digest and length, and
states a fidelity class and a provenance claim.

Everything downstream is a projection over accepted artifacts, pinned to a
parser revision and a projection contract revision, and reproducible by
replaying the projection over the same immutable bytes.

Three consequences follow, and they are the substance of this document.

**Transport is an acquisition adapter, not a storage owner.** It keeps its
whole live model: interposition, lease, turn lifecycle, overlay validation,
transformation ordering, forwarding proof. It writes bytes through the Evidence
port instead of into its own payload table. The offline importer is the second
adapter with the same relationship. This is the same shape as `rtm-shim`
relative to Runtime, and a context owning a rich model and no table of its own
is normal.

**Transcript is downstream of Evidence, not a peer with a direct writer.** A
Claude Code JSONL file on a fresh install is a foreign artifact. Accept it,
fingerprint it, class its wire fidelity as not wire derived, then project a
Transcript from the owned bytes. Transcript keeps its independence from
Transport, Session, Runtime, and any local launch, which is what #48 actually
requires. It loses only independence from Evidence, which costs nothing and
buys one deletion root.

**Provider payload interpretation is a shared kernel.** Transport needs it to
edit and validate a held request. Transcript needs it to project a conversation
from either a live capture or an imported log. Neither context may own it, and
duplicating it is the worst option. The schema is imposed externally by
Anthropic and OpenAI, which is the textbook justification for a shared kernel:
a model neither party controls.

## 3. Context map

| Context | Owns | Does not own |
| --- | --- | --- |
| Identity | authorization, audit, service identity, RBAC shape | session meaning, placement, process execution |
| Session | logical sessions, operator verbs, intent, mail, nudge, labels | topology, provider payloads, process internals |
| Schedule | placement, desired topology, stable occupant bindings, reconciliation | agent meaning, launch internals, provider traffic |
| Runtime | process launch, shim behavior, platform execution, lifecycle evidence | placement decisions, session meaning, payload policy |
| **Evidence** | **acceptance of foreign bytes, immutable artifacts, capture continuity, grouping claims, fidelity and completion, disclosure policy, evidence links** | **provider semantics, live lifecycle, conversation meaning, placement, authorization** |
| **Transcript** | **conversation projection, snapshot revisions, parser and projection revisions, transcript continuity** | **byte ownership, acceptance, wire fidelity, live capture, forwarding** |
| Transport | wire interposition, capture lease, turn lifecycle, authorized transformation, forwarding proof, commitment evidence | byte ownership, retention, conversation meaning, placement, authorization |
| Provider adapters (shared kernel) | parse, preserve, validate, and serialize provider payloads | storage, lifecycle, policy, identity |

Canvas and Desktop remain one product surface rather than a bounded context.

Dependency direction, acyclic with Evidence as the sink:

```text
Canvas or lilo -> Session -> Schedule -> Runtime
                     |
                     +-> Transport ---+
                     |                |
                     +-> Transcript --+--> Evidence
                                      |
Import driver --------------------------+

Transport   -> Provider adapters
Transcript  -> Provider adapters
Evidence    -> lilo-common, lilo-db only

Identity authorizes Session, Schedule, Runtime, Transport, and Transcript
service actions.
```

Evidence depends on nothing above it. That is the property that makes the
acceptance boundary worth having, and any future edge out of Evidence is a
design error.

## 4. Evidence

### 4.1 Identity

| Identity | Meaning | Allocation and continuity |
| --- | --- | --- |
| `CaptureId` | One durable, refreshable acquisition source. A live capture lease, or an imported file's source binding. | Allocated on first acquisition. Preserved by an explicit refresh of the named capture, a matching stable source instance token, or explicit user rebind. Never preserved by locator, digest, or provider identifier alone. |
| `EvidenceArtifactId` | One immutable accepted byte artifact. | Allocated at acceptance. Never derived from a digest. |
| `ExchangeId` | One locally accepted grouping claim over artifacts. | Allocated only after a grouping basis exists: first party observation, accepted signer claim, or explicit user assertion. |
| `EvidenceLinkId` | One link from evidence to a `TranscriptId` or `SessionId`. | Allocated per link. Optional, plural, and never owning either endpoint. |

All four are allocated UUIDv4 through the `define_id!` family in
`lilo-common`, consistent with the locked typed id decision. A content digest
names one immutable blob and never names a Capture, Exchange, artifact,
manifest, projection, Transcript, Session, or link.

`define_id!` is currently a private `macro_rules!` at
`crates/lilo-common/src/id.rs:22` with no `#[macro_export]`, so these types are
added inside `lilo-common` rather than in the new crates.

### 4.2 Five independent claim axes

The single most common modelling error here is collapsing these. They answer
different questions and move at different times.

| Axis | Scope | Values |
| --- | --- | --- |
| Integrity | artifact | `Verified`, `Failed`. A recheck of owned bytes against the recorded digest and length. Says nothing about origin. |
| Origin confidence | artifact | `FirstPartyObserved`, `SignerClaimed`, `UserAsserted`, `Unknown`. |
| Wire fidelity | artifact | `ExactAtBoundary`, `BytePreservingContent`, `DecodedPayload`, `Transformed`, `Partial`, `NotWireDerived`, `Unknown`. Exhaustive. |
| Grouping basis | exchange | `FirstPartyObservation`, `SignedManifest`, `UserAssertion`. Pinned and always visible to consumers with its confidence. |
| Completion | exchange | `Provisional`, `Complete`, `TerminalIncomplete`. Monotonic, never regresses. |

`NotWireDerived` is added to the #49 list because the acceptance boundary now
takes harness side logs. A Claude Code JSONL import is `Verified` integrity,
`UserAsserted` origin, and `NotWireDerived` fidelity. Without that value the
import would have to lie in the fidelity field or force a second bytes owner,
which is the outcome this design exists to prevent.

A valid digest on each half of a request and response pair does not
authenticate their grouping. A signed manifest authenticates that its signer
made the recorded claim, and never asserts provider origin or co-occurrence.
Manifest signatures are seals over claim bytes and never become identity
values.

### 4.3 Artifacts, manifests, and revisions

An accepted artifact holds immutable bytes, exact length, digest with an
explicit fingerprint format revision, wire fidelity, origin confidence, and
provenance. It is never rewritten.

A manifest revision binds artifact ids, roles, directions, order, byte lengths,
digests, fidelity, completion claims, observation boundary, and its
predecessor. Bytes presented after a terminal completion create a conflicted
successor claim. They never reopen or overwrite the terminal revision.

Where the observation boundary exposes them, header bytes, framing,
compression, chunk boundaries, and body bytes are exact artifacts. Parsed,
decoded, and redacted forms are projections with independent revisions.

For live capture the canonical artifact set is provider payload body bytes plus
non secret HTTP facts, with the response held as ordered chunks. Credential
values are never stored. TLS records are out of scope. This is the arena
ruling, unchanged, and it now lands in Evidence rather than a Transport payload
table.

### 4.4 Adoption and idempotence

Adoption accepts and fingerprints each presented artifact before deriving any
relationship. Missing, substituted, truncated, duplicate, and conflicting
artifacts are all covered by immutable ownership plus idempotent adoption.

Two independently acquired byte identical captures keep different allocated
identities and become duplicate candidates. Content equality never merges
independent sources.

Adoption never creates a synthetic Session, Runtime, capture lease, or
Transcript record. Standalone evidence is readable through `lilod` before any
link exists.

### 4.5 Disclosure and lifecycle

One provider neutral disclosure policy covers headers and bodies and produces
the same result for Claude and Codex. Projections are derived on read under
that policy. There is no second persisted redacted payload authority.

Archive, detach, reproject, and evidence delete are independent lifecycle
operations. Evidence delete is the single root: deleting artifacts cascades to
every projection over them, in Transcript and in Transport turn evidence alike.
Owned bytes that match a deletion tombstone become a deleted evidence
candidate, and a new import allocates a new identity rather than resurrecting
the deleted one.

Canonical rows for a live capture live for the Session lifetime plus a proof
window and are removed through the Session delete orchestration calling the
Evidence port. Adopted evidence has no Session lifetime and is removed only by
explicit evidence delete.

## 5. Transcript

`TranscriptId` is an allocated UUIDv4 root over one independently refreshable
source. Provider native identifiers and content fingerprints stay as
provenance and never become identity roots. A provider identifier collision is
recorded as collided provenance and never merges independent sources.

Transcript reuses an identity only when the refresh names an existing Capture,
a stable source instance token matches, or the user explicitly rebinds. Content
comparison then runs against the latest accepted snapshot for that Capture:

| Comparison with latest snapshot | Verdict | Identity result |
| --- | --- | --- |
| Length and digest equal | Unchanged | Reuse `TranscriptId`, add no snapshot |
| Longer, prior snapshot is an exact prefix | Append | Reuse `TranscriptId`, add an immutable snapshot revision |
| Shorter, current bytes are an exact prefix of prior | Truncation | Preserve prior Transcript, allocate a new `TranscriptId` |
| Neither prefix relation holds | Rewrite | Preserve prior Transcript, allocate a new `TranscriptId`, record shared prefix length including zero |

`CaptureId` and `TranscriptId` are both required and are not redundant. They
diverge exactly at truncation and rewrite: the external source is still the
same refreshable object, so the Capture survives, while the transcript
continuity claim does not. Merging them would force one of those two rules to
break.

Transcript has no source binding table of its own. The Capture is the source
binding. That deduplication is the first concrete payoff of the acceptance
boundary rule, and losing it is the cost of rejecting the rule.

Every projection pins the snapshot, the parser revision, and the projection
contract revision. Every projected record points to its snapshot, byte start,
byte end, and raw record digest, so any record can be traced to owned bytes. A
parser upgrade adds a projection and retains the prior one. Historical readers
stay runnable.

Transcript to Session links are optional and plural, carry allocated link
identity, and pin one snapshot and one projection revision each. A link never
owns either endpoint. There is no link table in Session.

## 6. Provider adapters

One shared kernel crate holds provider payload interpretation:

1. Parse a provider payload into an immutable normalized model.
2. Preserve unknown provider fields opaquely through parse and serialize.
3. Locate a field by semantic identity, such as a tool by name.
4. Validate a modified payload against the provider contract.
5. Serialize a modified raw tree without disturbing untouched members.
6. Report field dispositions as `preserved`, `normalized`, `synthesized`,
   `reordered`, or `dropped`.

Transport consumes 1 through 6 for held request editing. Transcript consumes 1,
2, and 6 for projection. The kernel holds no storage, no lifecycle, no policy,
and no identity, so it cannot become a covert third context.

Shared kernel status carries a real obligation: a change to this crate requires
review from both consuming contexts. That cost is accepted because the model is
externally imposed and duplicating it is worse.

## 7. Transport

Transport keeps everything the arena verdict gave it except byte storage and
retention.

Owns: provider wire interposition, the standing loopback listener, capture
leases, turn lifecycle, request fingerprints and request scoped field
references, overlay validation and transformation ordering, provider valid
serialization after a real change, forwarding proof, commitment evidence, and
safe handling of Claude Messages and Codex Responses traffic.

Does not own: immutable bytes, digests, fidelity classes, retention, disclosure
policy, conversation meaning, authorization, placement, or process selection.

Ownership items 2 and 8 of the current `docs/architecture/transport.md` move to
Evidence. Item 3 splits: the normalized model moves to the provider adapter
kernel, and the decision to apply it stays with Transport.

### 7.1 Turn identity

A live turn is Transport's lifecycle state over exactly one Exchange, so the
turn row is keyed by `ExchangeId` and no separate `TurnId` exists. Allocation
is legal at capture time because first party observation is a grouping basis
under §4.2.

This removes `TurnId` and `RequestId` from the arena graft list. `RequestId` was
only ever a naming handle for operator commands, and the operator should name
the thing that persists. The CLI addresses a turn by `ExchangeId` prefix
through the existing `Selector` prefix variant.

### 7.2 State axes

Four separate axes, unchanged from the arena verdict:

```text
lease:      Prepared | Consumed | Aborted
turn phase: Captured | Held | Validating | Forwarding | Streaming | Terminal
mutation:   Unchanged | Edited
commitment: None | RequestStarted | RequestComplete | ResponseStarted | ResponseComplete
outcome:    Completed | FailedBeforeCommitment | FailedAfterCommitment | CommitmentUnknown
```

An invalid edit leaves the turn `Held` and returns a validation result.
Unchanged pass through is a mutation result. Neither belongs in the lifecycle
enum.

One proxy task owns each captured turn and receives edit, forward, and cancel
decisions over an in memory channel. RPC handlers authorize and submit
commands and never mutate the turn. On daemon restart, reconciliation resolves
non terminal turns from durable commitment evidence. No retry occurs.

### 7.3 Launch path

Adopted from the arena verdict, verified against `c2864d0`:

1. One standing loopback listener started in Transport build before Session
   accepts requests, address from `settings.toml [transport].listen` with a
   registered `LILO_TRANSPORT_LISTEN` override in the `lilo_paths::env`
   registry.
2. Correlation by a non secret `ANTHROPIC_CUSTOM_HEADERS` routing key merged
   with operator supplied headers and stripped before forward. Claude Code
   v2.1.227 or later is a pinned harness precondition proven by the first
   slice.
3. `prepare_in_tx(&mut LiloTransaction, PrepareCapture) -> CapturePreparation`
   is database pure and runs after `authorize_in_tx` inside
   `begin_spawn_intent`. Rollback leaves no lease. `abort_spawn_intent` aborts
   the lease in the same compensating transaction.
4. Prepare returns one opaque `LaunchAttachment` plus a Transport owned typed
   `LaunchEnv` patch. The attachment alone cannot route Claude because it stops
   at `RuntimeService::spawn`.
5. `PrepareCapture` carries `IsolationPolicy`. `Docker(_)` fails closed with an
   explicit unsupported isolation error, because Docker passes env with no
   `--network` or host gateway mapping and a loopback base URL is unreachable
   from the container.
6. The hold is bounded well below `API_TIMEOUT_MS`, default 600000 ms, and
   resolves to `FailedBeforeCommitment` on expiry. A duplicate arrival with the
   same fingerprint while `Held` attaches to the held turn; after terminal it
   passes through and records a `harness_retry` fact.
7. Shutdown order is listener, connections, Session, Runtime, Transport,
   socket, pid, database. Transport stops after Runtime.
8. `x-claude-code-session-id` is recorded as an observed harness identity
   claim.

Forwarding invariants are unchanged: forward original bytes exactly when the
interpreted request is unchanged, serialize only after an authorized
transformation, preserve unknown fields, validate before forwarding, record
original and forwarded and audit evidence in Evidence, never produce a
partially transformed request, and make capture failure explicit to Session.

## 8. Session and Canvas

Session gains no link tables. Evidence rows join by `SessionId` through
`EvidenceLinkId` rows that Evidence owns, and Session composes its joined read
model by calling the Evidence and Transcript ports.

Session delete orchestration calls the Evidence port to remove capture scoped
evidence for that session. It does not delete adopted evidence or transcripts
that merely link to the session.

Canvas consumes four read models through `lilod` and reads no substrate storage
directly:

1. Session list and logical session state.
2. Transcript projection at a pinned parser and projection revision.
3. Evidence artifacts and exchanges under the disclosure policy, including
   standalone evidence with no session.
4. Transport turn state, mutation, commitment, and audit evidence for live
   sessions.

Canvas local UI state stays in the client and is never authoritative. The same
read models render to standalone HTML for diagnostics and tests, and that HTML
artifact hosts no command endpoints.

## 9. Naming

The context is **Evidence**, not Wire Evidence. It accepts non wire artifacts
by design, so a wire qualifier in the context name would be false on its most
common import path.

`lilo-wire` already exists and means the daemon RPC envelope, `LilodRpc` at
`internal/wire/src/lib.rs`. Standing up a second meaning of "wire" in the same
workspace would put two unrelated concepts under one term in the ubiquitous
language. `internal/wire` keeps RPC.

## 10. Crate layout

```text
internal/evidence/{core,store}      lilo-evidence-core, lilo-evidence-store
internal/transcript/{core,store}    lilo-transcript-core, lilo-transcript-store
internal/provider/                  lilo-provider
internal/transport/{core,daemon}    lilo-transport-core, lilo-transport-daemon
```

Transport gets two crates with a private store module, per the arena rule that
a store crate is extracted only on a second consumer. Transport has one
consumer of its state.

Evidence and Transcript each get a store crate because each has three
consumers. Evidence is written by Transport and the import driver, read by
Transcript and Session, and deleted through the Session orchestration.
Transcript is written by the import driver and read by Session and Canvas. The
rule is met rather than waived.

The import driver is thin orchestration in the Transcript service, calling
Evidence accept and then Transcript project. It is not a fourth context.

All contexts share one `lilod` process and one Postgres pool. Evidence and
Transcript ports expose `*_in_tx` methods so a live capture write and its
Transport turn write commit together, following the existing
`identity.authorize_in_tx` and `LifecycleStore::insert_forking_in` precedent.

## 11. Repository document changes

| Document | Change |
| --- | --- |
| `docs/architecture/system.md` | Context table gains Evidence and Transcript. Dependency diagram and target direction updated. Launch attachment contract amended for the typed `LaunchEnv` patch and prepare inside Transaction A. Canonical evidence definition added. |
| `docs/architecture/evidence.md` | New. Sections 4 and 9. |
| `docs/architecture/transcript.md` | New. Section 5. |
| `docs/architecture/transport.md` | Rewritten. Ownership items 2 and 8 removed, item 3 split, section 7 adopted. |
| `docs/architecture/canvas.md` | Service boundary gains Transcript and standalone Evidence read models. |
| `CLAUDE.md` | Bounded contexts section gains Evidence and Transcript. Transport paragraph narrowed. Typed id family gains the four Evidence ids and `TranscriptId`. |

The `system.md` amendment is a blocker for every implementation issue. The
current text at lines 73 to 77 says `LaunchEnv` does not form a second
envelope, which forbids the only sanctioned route to the child process.

## 12. Product decisions for Stuart

Issue #37 lists seventeen decisions. Ten are architecture and this document
answers them. The remainder are product calls with a recommendation attached.

| Decision | Recommendation |
| --- | --- |
| Providers in the first proof | Claude only. Codex stays outside Transport. |
| Blocking or passive | Blocking hold on the first valid Claude Messages request, bounded at 120 s. |
| Edit lifetime | Request scoped only. No durable overlay. |
| Capture failure posture | Required, fail closed before Runtime spawn. Docker isolation fails closed. |
| Report opening | Explicit navigation, with `lilo run` printing the exact next command. |
| Evidence hierarchy | Interpreted first, raw body as drill down. |
| Retention | Live capture evidence until Session delete plus a proof window. Adopted evidence until explicit evidence delete. |
| HTML or Canvas first | HTML first, Canvas next, over identical read models. |
| Implementation language | Rust, in process in `lilod`. |

## 13. Implementation sequence

1. Close #39. Remove the second composition constructor before more services
   join `lilod`.
2. Amend the `system.md` governing text. Blocker for everything after.
3. Evidence foundation: the four ids, immutable artifacts, five claim axes,
   manifest revisions, disclosure policy, lifecycle operations. Proof is a
   fresh install adopting one request artifact without fabricating a response
   or an Exchange.
4. Provider adapter kernel and Transcript foundation: identity rules, snapshot
   revisions, projections pinned to parser and projection revisions, optional
   plural Session links. Proof is a fresh install importing a Claude JSONL
   through Evidence acceptance, then an append refresh that preserves the
   `TranscriptId`, then a truncation that does not.
5. Transport live proof: standing listener, prepare in Transaction A, hold,
   edit by tool name, validate, forward, write through the Evidence port.
6. HTML report over the shared read models.
7. Canvas over the same `lilod` contracts.

Evidence precedes Transcript because the projection is downstream of the
acceptance boundary. This reverses the order proposed before the boundary rule
was settled.

Issue #36 proceeds independently and blocks nothing here.

## 14. What this design refuses

The acceptance boundary is falsifiable. It is wrong if any of the following
turns out to be true, and each should be checked during step 3:

1. A durable writer exists that legitimately owns foreign bytes without an
   Evidence acceptance.
2. Live capture write throughput makes an Evidence port hop measurably costly
   against the Transport hold budget.
3. The disclosure policy cannot be stated provider neutrally across headers and
   bodies for both Claude and Codex, forcing per context policy.

Explicitly out of scope: general packet capture, TLS record capture, provider
replay, capture sharing, cloud synchronization, registry, signing, entitlement,
accepted cache, remote overlay distribution, reusable positional identities,
multiuser operation, a separate Inspector product, eval and compare, and
historical indexing beyond the proof.
