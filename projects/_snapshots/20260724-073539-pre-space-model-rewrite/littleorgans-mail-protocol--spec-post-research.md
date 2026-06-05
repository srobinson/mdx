---
title: littleorgans mail protocol spec — post-research revision
status: draft
date: 2026-05-31
builds_on: littleorgans-mail-protocol--spec.md
research: deep-research run wf_d7ebf36b-5aa (2026-05-31), 23 sources, 25 claims verified, 20 confirmed
---

# littleorgans mail protocol spec — post-research revision

## Purpose

This revision layers a 2026-05-31 deep-research pass onto the base spec
(`littleorgans-mail-protocol--spec.md`). The base spec's seven dimensions
stand. This document records what the research validated, the one thing it
changes about the design language, and the new options it opened, each with a
decision. The driving question was whether the durable-mail plus A2A framing is
the right paradigm for single-host inter-agent comms, or whether an IRC-style
channel model fits better.

The research surveyed four layers: coordination semantics, wire transports,
real agent frameworks, and the classic agent-communication-language lineage. It
judged each against four properties: simplicity on one host, durability and
auditability, liveness, and the addressing model. Conclusions below are
primary-sourced where marked; single-host fitness calls extrapolated from
scale-oriented sources are flagged as inference.

## Research verdict

The durable-mailbox plus lightweight-nudge split the base spec already commits
to is the strongest single-host fit, and a major lab converged on the same
shape independently. Google A2A framing is overkill for this bounded context.
The IRC question dissolves: lilo's existing label selector grammar already
provides channel-equivalent addressing, so no new channel primitive is
warranted.

## What the research validates (base spec unchanged)

- **Mailbox-centric ownership (base §0).** Anthropic's own multi-agent feature,
  Claude Code agent teams, ships a first-class mailbox plus a shared task list
  persisted to local files under `~/.claude/`, with file-locking for task
  claims and no database, no broker, and no network IPC. Direct-by-name
  addressing plus idle notifications. That is the base spec's recipient-mailbox
  aggregate plus nudge, arrived at independently. Caveat: that feature is
  experimental and disabled by default, so it is corroborating signal, not a
  settled standard. (`code.claude.com/docs/en/agent-teams`)
- **Mail and nudge decoupled (base §5).** The field separates durable
  message-passing from ephemeral liveness signalling. The base spec's
  durable-mail plus best-effort `notify` composition matches this.
- **Selector addressing and point-to-point reads (base §3).** Direct and
  label-scoped addressing over a persisted store is the dominant single-host
  model. Frameworks that drop addressing entirely use a blackboard instead
  (see additions below); they do not use a heavier addressing grammar.
- **SQLite plus append-only log as the substrate.** Durable-message-queue-on-
  SQLite is an established practitioner pattern for agent orchestration, and
  LangGraph's checkpointed shared state maps naturally onto a single SQLite DB.
  The base spec's `session_mail` table plus JSONL audit log needs no wire to be
  durable or auditable.

The frameworks diverge rather than converge: AutoGen v0.4 uses an actor model
with async message-passing and broadcasts each turn to the whole group;
LangGraph uses checkpointed shared state; CrewAI uses orchestrator-mediated
role delegation with no peer bus; Claude Code agent teams use an explicit
filesystem mailbox. lilo's mailbox sits squarely inside this design space.

## What the research changes: drop the A2A framing

This is the one substantive change, and it is to the design language, not the
mechanics.

**Decision: remove Google-A2A and FIPA-ACL framing from the mail protocol's
ubiquitous language.** Do not describe lilo mail as "A2A," do not adopt
AgentCards, a task-state machine, JSON-RPC envelopes, performatives, or a
discovery registry.

Rationale, primary-sourced:

- A2A's own specification states it is for "independent, potentially opaque AI
  agent systems" that collaborate "without needing to share their internal
  thoughts, plans, or tool implementations" over HTTP with JSON-RPC 2.0, SSE
  streaming, and webhook push, with a nine-state task lifecycle and a discovery
  registry. Every one of those constructs pays to cross a process, trust, and
  network boundary. lilo has one operator, one host, one daemon, and a shared
  SQLite database. There is no boundary to cross, so the framing imports cost
  with no matching reason. (`a2a-protocol.org/latest/specification/`)
- A survey of agent interop places A2A at stage 3 of a four-stage ladder
  (MCP for tools, ACP for rich interaction, A2A for enterprise collaboration,
  ANP for open agent markets). Single-host sits below that ladder. The "below
  the ladder" reading is inference from a scale-ordered source, not an explicit
  single-host prohibition, but it is directionally sound.
  (`arxiv.org/html/2505.02279v1`)
- The lineage A2A descends from accretes ceremony rather than shedding it.
  KQML's performative set was "overly large and not standardized," producing
  non-interoperable implementations; FIPA-ACL's response was to add modal-logic
  rigor. Borrowing that vocabulary pulls the design toward heaviness over time.
  (`gki.informatik.uni-freiburg.de/.../06_communication.pdf`)

This aligns with the prior decision to stop treating helioy-bus as the
reference baseline. lilo mail is a co-located cooperative-agent channel, not a
networked-interop protocol, and its ubiquitous language should say so.

## What the research adds (new options, each decided)

### A. IRC-style channels: already covered by label selectors

No surviving research claim evaluated IRC or IRCv3 directly, so this is
engineering judgment, not a research finding. IRC contributes two separable
things: an addressing model (channels as topics, nicks as direct, JOIN/PART as
presence) and a wire (an ephemeral socket server). The wire is a poor fit: it
re-adds durability lilo already has from SQLite and runs a socket server
between processes that share a filesystem and a database. The addressing model
is a good conceptual fit, but lilo already has it.

A label in the base spec's selector grammar (`label:<key>=<value>`,
`label:<key> in (v1, v2)`) is functionally an IRC channel: a topic-style
multicast target. `role:<name>` and `namespace:<slug>` are further channel-like
groupings. A raw session id is the nick. The base spec already rejects "a
separate mail addressing grammar," and the research gives no reason to overturn
that.

**Decision: do not add an IRC-style channel primitive. Treat label selectors as
the channel model.** The one IRC concept labels do not cover is presence
(JOIN/PART). Presence is a Runtime liveness concern (active sessions, nudge
reachability), not a Mailbox aggregate concern, so it stays out of the mail
protocol and maps to runtime status plus the nudge channel. If named, durable,
membership-bearing rooms are ever needed, that is the base spec's stated
trigger for extracting a Channels context (a durable model no longer centered
on the recipient session mailbox), and it returns as a v2 question.

### B. Blackboard / shared-state: a separate primitive, out of mail scope

Several frameworks coordinate through shared state instead of messages
(LangGraph's checkpointed state, the pure blackboard pattern where "agents
communicate solely through the blackboard without any direct contact" and a
control unit selects the next agent by content). This maps naturally onto
lilo's single SQLite database. It is a genuine alternative coordination
semantic, but it is not a mail concern.

**Decision: keep blackboard out of the mail protocol.** If agents need a shared
scratchpad, model it as its own session-owned table and coordination verb, not
as a mode of the Mailbox aggregate. Mail stays point-to-point durable
message-passing. Recording the option here so it is not relitigated as a mail
feature. (`arxiv.org/html/2507.01701v1`)

### C. NATS as the throughput escape hatch, explicitly out of v1

If a single-host fleet ever outgrows a SQLite mailbox for broadcast or
worker-pool throughput, NATS is the lowest-ceremony wire that natively provides
publish/subscribe (broadcast), request-reply (RPC), and load-balanced queue
groups (worker pool), with durable replay available as opt-in JetStream. Kafka
and Pulsar require app-level request-reply correlation; gRPC is at-most-once
only. (`docs.nats.io/nats-concepts/overview/compare-nats`)

**Decision: NATS stays out of v1 and out of this protocol.** It adds a broker
daemon, which is strictly heavier than SQLite plus JSONL, and is justified only
past a throughput or agent-count threshold the research could not pin down.
Record it as the named escape hatch so the v1 design is not pre-distorted to
anticipate it.

## Decisions delta (additions to base spec §Decisions)

| Fork | Chosen | Rationale | Rejected |
| --- | --- | --- | --- |
| Design language | Drop A2A and FIPA-ACL framing; mail is a co-located cooperative-agent channel. | A2A's own spec targets remote, opaque, cross-vendor agents over HTTP; lilo has no boundary to cross. The ACL lineage accretes ceremony. | Describing lilo mail as "A2A"; AgentCards; task-state machine; performatives; discovery registry. |
| IRC channels | Treat label selectors as the channel model; add no channel primitive. | A label is a topic-style multicast target; the base grammar already spans channel, role, and namespace groupings. | A separate IRC-style channel grammar; an ephemeral socket wire between co-located processes. |
| Presence | Out of mail scope; maps to runtime status plus nudge. | Presence is a Runtime liveness concern, not a Mailbox aggregate invariant. | Folding JOIN/PART presence into the mail protocol. |
| Blackboard | Out of mail scope; a separate shared-state primitive if needed. | Mail is point-to-point durable message-passing; shared state is a distinct coordination semantic. | Adding a blackboard mode to the Mailbox aggregate. |
| Higher-throughput wire | NATS named as a v2-only escape hatch. | A broker daemon is heavier than SQLite plus JSONL and is justified only past an unestablished throughput threshold. | Adding a broker in v1; pre-shaping the v1 design around one. |

## Open questions (research-flagged, unresolved)

- Mailbox-over-SQLite versus a shared-state table over SQLite for replay and
  auditability: no source compared the two for lilo's exact target. The base
  spec commits to the mailbox; option B above keeps shared-state available as a
  separate primitive if a workflow demands it.
- The right liveness/nudge transport on one host (filesystem watch, unix-socket
  notify, SQLite notification, or lightweight pub/sub), and whether nudge needs
  its own wire at all given everything is co-located. The base spec leaves
  nudge as a Runtime adapter action without fixing the transport.
- The concrete agent-count or throughput threshold at which a SQLite plus JSONL
  mailbox stops sufficing and a broker is warranted.
- Whether durable, membership-bearing named rooms ever become a real lilo
  requirement; that is the base spec's stated trigger for a Channels context.

## Sources

Primary: `a2a-protocol.org/latest/specification/`,
`arxiv.org/html/2505.02279v1`, `arxiv.org/html/2507.01701v1`,
`code.claude.com/docs/en/agent-teams`,
`microsoft.com/.../autogen-v0-4-reimagining-the-foundation-of-agentic-ai...`,
`docs.nats.io/nats-concepts/overview/compare-nats`,
`gki.informatik.uni-freiburg.de/teaching/ws1011/imap/06_communication.pdf`.
Secondary corroboration: DataCamp framework comparison, Wikipedia ACL entry.
Refuted (no surviving support): the claim that a lightweight central-broker IPC
beats a mailbox for a cooperative fleet was killed 0-3 on quote-accuracy
grounds, so this revision does not lean on it.
