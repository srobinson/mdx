---
title: littleorgans mail protocol design spec
status: draft
date: 2026-06-01
supersedes: littleorgans-mail-protocol--spec.md (v2, archived), littleorgans-mail-protocol--spec-post-research.md
companion: littleorgans-agent-comm-protocol--spec.md (anti-ping-pong conduct + skill)
research: deep-research wf_d7ebf36b-5aa (2026-05-31, 23 sources); design conversation 2026-05-31
---

# littleorgans mail protocol design spec

Consolidated, post-research, post-pull-back. This folds the seven base
dimensions (warroom-signed), the 2026-05-31 research deltas, and the v1
additions agreed in design conversation. The anti-ping-pong communication
conduct, including its agent-facing skill and MCP resource, lives in the
companion spec and is referenced where the wire model touches it.

## For Stuart's evaluation

1. Durable mail stays a Session-owned aggregate. No Channels context, no named
   rooms in v1. Selectors are the channel model. Named, membership-bearing
   rooms remain the explicit v2 extraction trigger.
2. Drop the A2A and FIPA-ACL framing from the ubiquitous language. lilo mail is
   a co-located cooperative-agent channel, not a networked interop protocol.
3. Sender is server-derived: `session` through the MCP bridge, `operator` over
   the local socket, `system` for daemon-generated receipts. Public `from` is
   deleted.
4. At-least-once is a send-side guarantee through idempotency only. A client
   key, unique per sender, collapses an ambiguous resend. Persisting a message
   and its delivery rows in one transaction is delivery to the mailbox, so there
   is no delivery worker, no retry, and no dead-letter on durable mail. Reads are
   at-most-once self-drains with no selector; inspection is the separate
   non-mutating `peek` verb.
5. A mandatory circuit breaker with two independent ceilings: conversation depth
   per `context_id` (a depth trip stops that conversation) and send rate per
   `sender_ref` (a rate trip throttles that sender). Global, operator-
   configurable, `system` receipts exempt from both. On one host there is no
   external limiter, so this is the primary safety control.
6. Messages carry a `context_id` conversation tag and a minimal `intent`. The
   operator can peek and tail the durable message log read-only. Agents cannot
   tail.
7. Mail and nudge stay decoupled. Send takes opt-in `notify` with a `Wait` or
   `Steer` delivery mode. Presence and idle are Runtime liveness concerns, out
   of the mail aggregate.
8. v1 authz and audit stay uid-coarse and cooperative-trust. Per-agent identity
   isolation and impersonation are v2.

## Recommended design

### 0. Bounded context ownership

Keep durable mail under Session for v1. Session owns the Mailbox aggregate and
the recipient read model. Identity owns principal resolution, authorization,
and audit. Runtime owns nudge delivery and liveness. Session remains the
composition root for the user-facing mail and nudge verbs.

Session owns two distinct lifecycles here, not one. The recipient-mailbox
aggregate is per-recipient drain state: keyed by `session_id`, bound to the
session lifecycle, the core transition unread to read through `read_at` on the
delivery rows. The message log is a separate Session-owned lifecycle: an
append-only conversation transcript, sender- and `context_id`-scoped, shared
across the recipients of one send and read by the operator. A single message row
spans the N delivery rows of a fan-out, so it is not an entity inside any one
mailbox. Distinguishing the two is load-bearing for retention and cascade (§7)
and for the read-only observability invariant (§8). Recipient addressing is a
Session selector concern; drain is valid only against the Session keyspace and
active session lifecycle.

The sender is a provenance reference, not an addressable entity, and it has
three origins: a Session ref for an agent, an Identity operator principal for
the operator, and a daemon `system` origin for receipts. The first two are
Identity-owned principals; `system` is a daemon construct, not a `Local(uid)`
principal. Operator-origin mail uses a real operator principal, never a nil UUID
or a synthetic sender session.

Collaboration is made explicit through ports while ownership stays in Session:
an Identity port for principal, authorization, and audit decisions, and a
Runtime port for nudge delivery and presence. These ports also let the current
inline `authorize()` and inline nudge calls become testable seams, consistent
with the in-flight runtime-port migration.

The research confirmed this shape independently. A major lab's multi-agent
feature ships a first-class filesystem mailbox plus idle notifications, with no
broker and no network IPC. A future Messaging or Channels context becomes
justified only if the durable model stops being recipient-session-mailbox
centered: a sender-indexed outbox, durable named rooms with membership, or a
notification policy independent of a Session mailbox. None of those are v1.

### 1. Sender identity model

Delete the explicit public `from` field. Sender is derived only by the daemon
from the request context. A client cannot assert an arbitrary sender in
`MailSendRequest`, the MCP `mail_send` arguments, or the CLI send path.

The daemon resolves an effective sender:

- When the bridge forwards a caller session id, the sender is that session.
  Human output resolves it through the Session read model, role plus label.
  Machine output carries a stable sender kind and the session id.
- With no caller session, the sender is the operator over the local socket.
  Human output renders the fixed label `operator`. Machine output carries the
  kind and the underlying `Local(uid)` principal.
- Daemon-generated receipts use a `system` sender. This is new in this revision
  and supports automated read-receipts (see §8).

Deleting public `from` removes first-class sender spoofing. A narrower
assumption remains: the spawner-seeded session-id environment variable is
forwarded by the agent MCP bridge, and an agent can rewrite its own
environment. Agent sender attribution is therefore sound only inside the v1
single-operator cooperative local-host trust domain. Binding a connection
cryptographically to a session is v2 identity work, alongside impersonation.
Impersonation, if it ever returns, is a privileged audited Identity capability,
never a casual `from` field.

### 2. Message identity, verbs, and delivery semantics

Each mail id is a server-generated identifier for a created item. It belongs in
JSON output, audit, tests, logs, and machine correlation. It is not the primary
human send output, and no v1 human verb requires the operator to copy it into
another command.

`mail read` is the only mutating receive verb. It drains the caller's own
mailbox and takes no selector: draining is first-person, so there is nothing to
select. Inspection is non-mutating and lives on separate verbs: `mail peek`
looks without draining, `mail check` reports unread counts, and `mail tail`
follows live. Those carry an optional selector (see §3). No `mail ack`,
`mail read <id>`, or delete-by-id in v1; there is no consumer for them.

Two semantics on different layers, both true:

- Receive (read) is at-most-once per read call. When read drains unread mail,
  the daemon commits `read_at` for the returned set. `--peek` is the v1
  mitigation for a client that crashes between commit and display.
- Send is at-least-once at the API, through idempotency only. Persisting a
  message plus its delivery rows in one transaction is delivery to the mailbox,
  so there is nothing to retry and no delivery worker. A client idempotency key,
  unique per `(sender_ref, idempotency_key)`, collapses an ambiguous resend;
  reuse of a key with different content or recipients is a conflict, not a
  second send. Without a key, a resend mints a new id. See §7 for the store
  shape.

Read ordering is deterministic by `(sent_at, id)`. UUIDv7 gives a monotonic tie
break. Row materialization and mark-read must be atomic, one transaction or an
`UPDATE ... RETURNING` shape, so a selector or serialization error never marks
mail read when the item cannot be returned.

Messages carry a `context_id` conversation tag and a minimal `intent`
(`request`, `result`, `inform`, plus the system `receipt`). Here `intent` is an
inert wire tag only. Every reply rule and any machine enforcement live in the
parked companion conduct spec and must not leak a state machine into the mail
daemon or wire.

### 3. Addressing

Addressing is Session-owned. `to` and inbox selectors address recipient
sessions through the existing Session selector grammar. Sender is never
addressed.

The public selector grammar is exactly: `all`, raw `<uuid>`, `id:<uuid>`,
`role:<name>`, `namespace:<slug>`, `dir:<path>`, `label:<key>=<value>`, and
`label:<key> in (v1, v2)`. `Selector::And` is internal composition for
namespace scoping with no public syntax. `workspace:` stays unsupported.

Selectors are the channel model. A `label:` target is a topic-style multicast,
`role:` and `namespace:` are channel-like groupings, a raw session id is the
direct address. No separate mail addressing grammar and no IRC channel
primitive are added.

Send, peek, check, and tail share one namespace default; `mail read` is
self-only and has no namespace widening. A selector without explicit widening is
scoped to the caller namespace. `all` means all matching sessions in that
namespace, not host-wide. Cross-namespace widening requires explicit
`all_namespaces` or a namespace selector and is authorization-gated. This closes
the current asymmetry where MCP send resolves host-wide.

Mail is point-to-point. Draining is first-person: `mail read` always targets the
caller's own mailbox and takes no selector, so an agent cannot drain a peer and
the operator cannot consume an agent's mail. Selectors apply only to the
non-mutating observation verbs (`peek`, `check`, `tail`). For an agent those
default to self and are constrained to self until Identity grants a wider read
right. For the operator they are administrative, may target any mailbox,
namespace-scoped by default and widenable under authorization. The operator has
no mailbox of its own in v1: it is not an addressable recipient, so agents
cannot mail the operator, and the operator learns of agent output through tail,
peek, and session records. It sends and observes, it does not drain. Send
fan-out resolves the recipient selector once; unknown targets, inactive
recipients, authorization failures, and delivery failures return per-recipient
errors. Inactive recipients are explicit errors, never silent drops.

### 4. Output and rendering contract

One daemon-side read-model projection, rendered as human text or JSON. The Mail
aggregate stores durable facts; the MessageView projection enriches them with
resolved sender and recipient summaries.

Mail joins the `--output json` honoring set. `mail send`, `mail read`,
`mail check`, and `mail stop-check` have stable JSON shapes. Field names use
snake_case. Sum types use the existing internally tagged convention: `type`
with snake_case variants. No camelCase for mail.

The core message view contains `id`, `content`, `sent_at`, `read_at`, `status`,
`sender`, `recipient`, `context_id`, and `intent`. The sender view is a tagged
sum: `session` (with `session_id`, `role`, `display_label`, `labels`,
`namespace`), `operator` (with `principal` and `display_label: "operator"`),
and `system` (for receipts). The recipient view is a session summary. Count
views include `session_id`, `role`, `display_label`, `namespace`, and `unread`.

Resolution belongs in the daemon. It batch-loads session summaries for all
unique sender and recipient ids before returning, so MCP JSON, CLI JSON, and
human output consume one shape with no N+1 lookups. Human send output is a
concise delivery summary, never bare ids. Human read output is labeled records
or a table with sent time, sender, recipient, status, intent, and content.
Human check output shows total plus per-mailbox counts.

### 5. Mail and nudge relationship

Mail and nudge stay decoupled at the aggregate and handler boundaries. Mail is
the durable Session mailbox channel. Nudge is an ephemeral Runtime wakeup. They
compose in the Session app layer; nudge never joins the Mailbox aggregate.

Send takes opt-in `notify`, surfaced in the CLI as `--notify`. It means:
persist durable mail, then fire a nudge for each recipient whose item persisted.
The `Wait`/`Steer` mode is a property of the nudge, and `notify` forwards it.
Mail is pull-based store-and-forward and has no delivery timing of its own, so a
mode only governs the wake: `Wait` queues it until the recipient is idle (the
default), `Steer` interrupts now. The wake is a Runtime-port concern that reads
presence; the durable message is independent of whether the wake succeeds. The
standalone `nudge` verb carries the same mode; mail and receipts, being pull,
carry none.

The daemon composes: resolve recipients once, apply send addressing once,
persist mail per active recipient, then wake exactly those persisted recipients
when `notify` is set. Authorization is per recipient: persistence requires
MailSend; the wake additionally requires Nudge. A wake failure never rolls back
persisted mail. Per-recipient results expose `mail: "ok" | "err"` and
`notify: "ok" | "err" | "skipped"`. Wake outcome and any wake retry are reported
through these notify result fields and wake-attempt events, never persisted as
Mailbox aggregate state. Runtime absence or a headless runtime produces notify
warnings, never a mail send failure.

### 6. Authorization and provenance

Identity is the authorization and audit authority. Session calls Identity for
each mail and nudge decision using the existing actions on the recipient
session resource: `MailSend`, `MailRead`, and `Nudge`. Every send, read, and
nudge decision records actor, action, recipient resource, decision, timestamp,
and outcome.

The v1 story is uid-coarse by design. The audited actor is `context.principal`,
derived from Unix peer credentials (`lilo_im_core::peer_creds::extract`, the session daemon's principal path; `lilo_sys::creds` exposes only `current_uid()`) as `Local(uid)`. On one host the operator
and every spawned agent share that uid, so Identity authz and the audit actor
do not distinguish agents. Sender provenance and mailbox-read privacy both key
on the forwarded caller session id, which the agent can rewrite. These are
cooperative-trust boundaries, not hard boundaries against a hostile agent.

All three limits share one cause: v1 identity authenticates the local Unix
user, not a distinct agent session. v2 identity closes them together with an
effective principal that binds the connection to the caller session. Until
then, do not claim agent-level isolation from Identity authz.

### 7. Delivery durability, retention, and safety

The substrate is SQLite plus a JSONL audit log, with no broker and no wire.

Store shape: an append-only `messages` log plus per-recipient
`message_deliveries` rows. The message row holds the immutable content, the
sender reference, `context_id`, `intent`, the idempotency key, and `sent_at`. A
delivery row per recipient holds mailbox state only: `status` (`unread` then
`read`), `read_at`, and the (`message_id`, `recipient_session_id`) key. It
carries no wake, attempt, or dead-letter state. Persisting the message and its
delivery rows is one transaction, and that commit is delivery to the mailbox.
There is no delivery worker, no retry, and no dead-letter on durable mail: a
pull mailbox waits indefinitely for its own read. Wake state is not mailbox
state and lives outside this aggregate (§5).

Idempotency: the authoritative guard is a durable unique constraint on
(`sender_ref`, `idempotency_key`). It collapses a client's ambiguous resend;
reuse of a key with different content or recipients is a conflict, not a second
send. A bounded TTL cache, if used, is a hot-path optimization in front of that
constraint, never the source of truth.

Circuit breaker: the v1 safety headline, since one host has no external limiter.
Two independent ceilings, each with its own trip scope:

- Conversation depth per `context_id`. A depth trip rejects further sends on
  that one conversation.
- Send rate per `sender_ref` over a sliding window. A rate trip throttles that
  sender across all conversations, never penalizing one conversation for a
  sender's behaviour elsewhere.

A trip rejects or throttles further sends and emits an audit alert. It never
dead-letters already-persisted mail, which always waits for its pull. Both
ceilings are global and operator-configurable under `~/.lilo`, not per-role
(resolving a sender's role on the safety hot path would be an N+1 against the
read model; defer per-role carve-outs to v2). `system`-sender receipts are
exempt from both dimensions, so the daemon's own receipts never inflate depth or
trip the rate limit. Recommended v1 defaults, operator-tunable: depth 50
non-receipt messages per `context_id`, rate 30 non-receipt sends per
`sender_ref` per 60 seconds. The breaker is the enforcement backstop; the
companion conduct protocol is the prevention layer.

Retention and cascade: the two lifecycles of §0 are deleted on different
triggers. `message_deliveries` cascade-delete when the recipient session is
deleted, since the mailbox is gone and there is nothing to drain. `messages` are
not deleted by recipient deletion, or the operator transcript would evaporate
the moment a participant leaves. A message row is GC'd only on explicit operator
transcript purge by `context_id`, or when its owning sender session is deleted
and it has zero surviving delivery rows; operator- and system-origin messages
are host-anchored until an explicit purge. The migration must split today's
`namespaces.rs` `sender_id OR recipient_id` delete: recipient deletion drives
only the delivery-row cascade, never a message-log delete.

### 8. Conversation and observability

`context_id` is a lightweight conversation correlation tag, not a task state
machine and not a room. Messages in one exchange share it. It keys the breaker
depth and groups a transcript.

Operator observability: the operator can peek and tail the durable message log,
filtered by `context_id`, selector, or recipient. This is read-only and never
mutates delivery state: it does not set `read_at`, does not consume, and does
not feed the breaker. The transcript is a query over the message log, not a
stored room. Reuse the existing event stream for live tail (a message append
emits an event; tail follows events filtered by conversation) and the
MessageView projection for rendering, so no second observability pipeline is
built. This stays off transport-matters' wire-observation axis; the two
correlate in the cockpit by the UUIDv7 spawn id.

Agents do not tail. Observation is an operator privilege, consistent with the
mailbox-read privacy rule. Operator verbs are administrative and non-mutating:
list conversations and counts, `peek` for a point-in-time transcript, `tail` to
follow live.

Automated read-receipts: the daemon emits a `system`-sender receipt to the
original sender when a non-receipt message's `read_at` commits on drain (not on
`--peek`). The receipt is terminal, never generates a receipt for a receipt, and
never wakes the recipient. It is exempt from both breaker dimensions (§7), so
receipts neither inflate `context_id` depth nor count against the sender rate,
and it renders as system metadata: omitted from the default operator transcript
and surfaced only behind an explicit include flag, never as an agent message
line. For a multi-recipient send, each recipient's read produces one receipt
naming who read and when. This takes the acknowledgement out of the agent's
hands entirely; the conduct rules around it are in the companion spec.

### 9. Wire and contract compatibility

This is a breaking pre-release cleanup. No compatibility aliases. Delete the old
`from` contract and regenerate generated surfaces from the authored tool
definitions.

Wire shape changes:

- `MailSendRequest` drops public `from`; gains `notify` with a wake mode,
  `context_id`, `intent`, and an optional idempotency key unique per sender.
- Sender becomes a tagged reference: `session`, `operator`, or `system`.
- Storage moves from a single mail row to an append-only message log plus
  per-recipient delivery rows; delivery rows carry mailbox state only
  (`unread`/`read`, `read_at`), never wake or dead-letter state.
- Responses expose per-recipient `mail` and `notify` status, and the shared
  MessageView, SenderView, RecipientSummary, and CountView projections.
- JSON stays snake_case with `type`-tagged sum variants.

The A2A and FIPA-ACL vocabulary is removed from the ubiquitous language. No
AgentCards, no task-state machine, no JSON-RPC envelope, no performatives, no
discovery registry. v1 authz and audit compatibility is explicit: `authorize()`
stays unchanged, audit actor stays `context.principal`; per-agent attribution is
a v2 effective-principal change.

## Decisions and rationale

| Fork | Chosen | Rationale | Rejected |
| --- | --- | --- | --- |
| Ownership home | Keep mail in Session; no Channels context in v1. | Aggregate is the recipient mailbox; research corroborates the mailbox model; extraction trigger (named rooms) is not met. | Extracting `internal/channels`; promoting Channel to the aggregate. |
| Design language | Drop A2A and FIPA framing. | One operator, one host, one daemon, shared SQLite: no boundary to cross. The ACL lineage accretes ceremony. | Describing mail as A2A; AgentCards; performatives; task FSM; discovery. |
| Channel model | Selectors are the channel model. | A `label:` is a topic multicast; the grammar already spans channel, role, and namespace groupings. | A separate channel grammar; an IRC socket wire between co-located processes. |
| Sender source | Server-derived `session`/`operator`/`system`. | Deletes nil sender and first-class spoofing; receipts need a system origin. | Public `from`; nil sender; raw peer-credential principal only. |
| Receive semantics | At-most-once self-drain, no selector; `peek`/`check`/`tail` are the non-mutating selector verbs. | Draining is first-person, so the reader has nothing to select; selectors only suit observation. | Selector drain that lets the operator consume an agent's mailbox; ack ceremony; read-by-id. |
| Deliver semantics | At-least-once at the send API via sender-scoped idempotency; persist-equals-deliver, no delivery worker or dead-letter. | One composed process: the message-plus-delivery commit is delivery; only an ambiguous client resend needs collapsing. | A retrying delivery worker; dead-lettering undrained mail; server id as dedupe key. |
| Safety | Circuit breaker, two independent ceilings (depth per `context_id`, rate per `sender_ref`), `system` exempt, global and operator-configurable; a trip rejects sends, never dead-letters mail. | One host has no external limiter; the two dimensions need distinct trip scopes; receipts must not trip their own breaker. | One conflated ceiling; per-role keying on the hot path; counting receipts; dead-lettering persisted mail. |
| Conversation | `context_id` correlation tag. | Groups a transcript and keys breaker depth; no FSM, no room. | A task lifecycle; a named room aggregate. |
| Observability | Operator peek and tail over the log, read-only. | A transcript is a query over the log; cursors stay untouched. | Folding observation into agent reads; a second pipeline; agent tail. |
| Read-receipt | Automated `system` receipt from `read_at`. | The acknowledgement leaves the agent's hands; terminal and non-waking, so it cannot loop. | Agent-authored acks; receipts that nudge or beget receipts. |
| Mail and nudge | Decoupled; opt-in `notify` with `Wait`/`Steer`. | Mail is durable; nudge is an ephemeral wake; mode encodes the idle-versus-interrupt policy. | Client-side two-call compose; nudge failure rolling back mail. |
| Presence | Runtime concern, out of mail scope. | Liveness is a Runtime invariant, not a Mailbox one. | Folding JOIN/PART presence into mail. |
| Authz and audit | Existing decisions; v1 actor uid-coarse. | Authorization already records audit; effective actor is a v2 trigger. | Changing `authorize()` in v1; claiming per-agent fidelity. |
| Compatibility | Break contracts now; delete old paths. | Pre-release allows cleanup without aliases. | Compatibility shims; generated-surface hand edits. |

## Migration and blast-radius

Core protocol and model:

- `MailSendRequest`: remove `from`; add `notify` (with mode), `context_id`,
  `intent`, optional idempotency key.
- Replace the single `Mail` row with an append-only message log plus
  per-recipient delivery rows; sender becomes a tagged reference.
- New read-model types: MessageView, SenderView (now three variants),
  RecipientSummary, CountView, per-recipient send result.
- Responses return stable view types with snake_case fields.

Store and migration:

- Replace `session_mail` with the `messages` plus `message_deliveries` shape;
  map nil sender rows to operator sender.
- Add the (`sender_ref`, `idempotency_key`) unique constraint and an optional
  TTL hot-path cache; add breaker counters keyed by `context_id` (depth) and
  `sender_ref` (rate). No dead-letter state on durable mail.
- Split today's `internal/session/store/src/sqlite/namespaces.rs`
  `sender_id OR recipient_id` delete: recipient-session deletion cascades only
  `message_deliveries`, never `messages`; message-log GC is a separate, narrower
  path (§7 retention).
- Change unread ordering to `(sent_at, id)`; make mark-read atomic.

Daemon:

- Derive the effective sender from `RequestContext`; add the `system` sender.
- Extract Identity and Runtime ports from inline `authorize()` and inline
  nudge; route MCP send through the same namespace-scoped path as read/check.
- No delivery worker and no dead-letter: send idempotency plus the one-shot
  transactional persist is the delivery guarantee. Build the idempotency guard,
  the two-dimension breaker (depth and rate, `system` exempt), the
  message-append events for tail, and the read-receipt emit hook on read-commit.
- Build daemon-side MessageView projection with batched summary resolution;
  compose `notify` with the wake mode after persistence.
- The `DeliveryPort` adapter reads liveness through `lilo_sys::process` and wakes
  via the runtime's tmux gateway (`internal/runtime/daemon/src/tmux.rs`); the
  mail layer never touches OS seams directly.

CLI and generated surface:

- `mail.toml`: remove `from`; add `notify`/mode, `context_id`, `intent`,
  idempotency key; update output schemas for all mail tools.
- `cli_def.rs`/`generated_help.rs`/`mail.rs`/`cli.rs`: remove `--from`, remove
  `--selector` from `mail read` (self-drain only), promote `--peek` to a
  `mail peek` verb, add the new send flags, mark mail JSON-supported, render
  counts, replace `print_mail` with a shared MessageView formatter, add operator
  `peek`/`check`/`tail` selector verbs.
- Regenerate MCP schemas, generated help, snapshots, tool-contract registry,
  and drift guards from authored sources. Run `fmm generate && fmm validate`.

Tests:

- Handlers: derived sender, system receipt, namespace-scoped send, read drains
  only the caller's mailbox, operator observation is non-mutating,
  inactive-recipient errors, notify partials and modes, idempotent retry,
  notify wake diagnostics, breaker trip.
- Store: message-log plus delivery-row model, sender-ref and nil migration,
  namespace cleanup cascade, `(sent_at, id)` ordering, atomic mark-read.
- MCP and CLI: removed `from`, added fields, self-default, JSON shapes,
  per-recipient errors, operator `peek`/`tail` read-only invariant, human
  render snapshots.
- Authz and audit: allow and deny rows persist, uid-coarse actor documented.

## Out of scope and deferred (named, do not relitigate)

- Named, durable, membership-bearing rooms, and the extraction of an
  `internal/channels` context. v2 trigger.
- IRC-style channel primitive and any socket wire between co-located processes.
- Blackboard or shared-state coordination, modeled as its own Session-owned
  primitive if ever needed, never a mail mode.
- NATS or any broker, the throughput escape hatch past a fleet size not yet
  established.
- A2A protocol, cross-host, gRPC, DID, full A2A wire envelope; impersonation and
  per-agent identity isolation (all v2).

## Resolved direction (warroom-ratified)

Both were open in earlier drafts and are now ratified by the MoE warroom, with
the delivery and breaker refinements folded into §7.

### Nudge transport: no dedicated wire in v1

In v1 lilod is one composed daemon, so mail persistence, the message-append
event, the notify trigger, and the runtime that controls agents share a process. "Mail persisted for X,
wake X" is an in-process event with no boundary to cross. The four candidates
land in different roles rather than competing:

- In-process pub/sub (a tokio broadcast or watch channel) is the internal
  trigger, and is the same channel §8 reuses for `tail`. Use this.
- Unix-socket notify is the operator-observation hop, a separate `mail tail`
  process following over the socket (`lilo_sys::ipc`). It cannot wake a busy
  agent, which is not listening on the socket.
- SQLite notification does not exist cross-process: no `LISTEN`/`NOTIFY`, and
  `update_hook` is per-connection. The in-process writer already knows when it
  writes. Skip in v1.
- Filesystem watch is the only candidate that reaches a turn-based agent without
  tmux, the agent watching an inbox or signal file. A future option, not needed
  while the runtime owns a working injection path. If adopted it becomes a new
  `lilo_sys` seam wrapping `notify`, keeping OS selection in the one home
  `lilo-sys` exists to be, rather than ad-hoc mail-layer code.

The final daemon-to-agent hop stays Runtime-owned behind the `DeliveryPort`.
Today it is tmux pane injection in `internal/runtime/daemon/src/tmux.rs`
(`TmuxGateway::nudge`), which stays in the runtime. The OS seams delivery builds
on are already centralized in the published `lilo-sys` crate:
`lilo_sys::process::pid_alive` and `lilo_sys::process_exit::watch_process_exit`
for liveness, `lilo_sys::signal` for an interrupt-style wake, and
`lilo_sys::ipc` for the operator-tail socket. Presence for `Wait`/`Steer` is
runtime turn-state layered on that liveness, which is coarser than turn-state
alone. The mechanism can change
without the mail layer knowing; the policy is a port concern, not a transport.

Recommendation: no dedicated nudge wire in v1. In-process event for the trigger,
the existing unix socket for operator tail, `DeliveryPort` for the final hop.
Revisit a real wire or filesystem-watch inboxes only if lilod decomposes into
multiple processes or tmux is dropped, the same threshold the deferred broker
question waits on.

### Store shape: two new tables, drop `session_mail`

The new model is a normalization split: one mail row becomes an append-only
message log plus per-recipient delivery rows. "Evolve in place" is not
available, since a single table cannot become two by adding columns. Pre-release
status carries no data-migration obligation, and the two-table split is what
keeps observation read-only, since the operator tails `messages` while an agent
drains its `message_deliveries` and peek and tail never touch a cursor.

- `messages`: `message_id` (UUIDv7 PK), `sender_ref` (session/operator/system),
  `context_id`, `intent`, `idempotency_key` (nullable, unique per `sender_ref`),
  `content`, `sent_at`.
- `message_deliveries`: (`message_id`, `recipient_session_id`) PK, `status`
  (`unread`/`read`), `read_at`. Mailbox state only: no wake, attempt, or
  dead-letter columns.
- Drop `session_mail`.

Ratified. Retention and cascade are ruled (§7): `message_deliveries` cascade on
recipient-session deletion; `messages` persist as the transcript and are GC'd
only by explicit `context_id` purge or owning-sender deletion with zero
surviving deliveries. The `namespaces.rs` cleanup splits accordingly and never
deletes the message log on recipient deletion.
