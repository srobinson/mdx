---
title: littleorgans mail protocol design spec
status: draft
date: 2026-05-31
---

# littleorgans mail protocol design spec

## For Stuart's evaluation

1. Keep durable mail in Session for v1. Identity supplies authz, audit, and sender principal references. Runtime supplies nudge delivery.
2. Delete public `from`. Sender is server-derived: session when called through the MCP bridge, otherwise operator.
3. Treat message ids as machine item identifiers only. Human workflows use selector drain and `--peek`, with at most once read semantics.
4. Make mail point to point. Agent read/check targets its own mailbox only; operator calls are administrative.
5. Namespace-scope send, read, and check by default. Explicit cross namespace widening is authorization gated.
6. Use one daemon-side MailView projection with snake_case JSON and named participants across MCP, CLI JSON, and human output.
7. Add opt-in daemon-side notify on mail send. Mail persists first; nudge is best effort and reported per recipient.
8. State the v1 trust boundary plainly. Authz and audit are uid coarse; hostile-agent isolation waits for v2 effective principals.

## Recommended design

### 0. Bounded context ownership

Recommendation: keep durable mail under Session for v1. Session owns the Mailbox aggregate and recipient read model. Identity owns principal resolution, authorization, and audit. Runtime owns nudge delivery. Session remains the composition root for the user facing mail and nudge verbs.

The aggregate root identity is the recipient mailbox. It is keyed by `session_id` and bound to the session lifecycle. Mail items are entities inside that mailbox. The core state transition is unread to read through `read_at`. Recipient addressing therefore remains a Session selector concern. Delivery is valid only against the Session keyspace and active session lifecycle.

The sender is different by design. Sender is a principal valued provenance reference owned by Identity, not a Session entity. Cohesion follows the aggregate root, not every reference it stores. The sender principal and recipient session asymmetry is intentional, and it does not justify extracting a new bounded context. Operator origin mail should use a real operator principal. It should not use a nil UUID or require a synthetic sender session.

Nudge is not part of the Mailbox aggregate. It is an ephemeral Runtime adapter action invoked through the same operator surface. Mail and nudge share selector grammar and authorization patterns, but they do not share persistence or aggregate invariants.

A later implementation should keep the current ownership while making the collaboration explicit through ports: an Identity port for principal, authorization, and audit decisions; a Runtime port for nudge delivery; and the Session store for mailbox persistence. The current send path authorizes through Identity before persistence; the later implementation must verify and, if needed, add explicit audit emission as part of the authz and provenance work.

A future Messaging or Channels context becomes justified only if the durable model stops being recipient session mailbox centered. Examples include a sender indexed outbox, conversation or thread roots, or durable notification policy independent of a Session mailbox. Until then, extraction would duplicate the Session keyspace or create a dependency loop.

### 1. Sender identity model

Recommendation: delete the explicit public `from` field for v1. Sender identity is derived only by the daemon from the request context. A client cannot assert an arbitrary sender in `MailSendRequest`, the MCP `mail_send` arguments, or the CLI send path.

The daemon should resolve an effective sender composite:

- When `RequestContext.mcp_caller_session_id` is present, the caller is an agent acting as that session. The sender is that session. Human output resolves it through the same Session read model used for recipients, preferably role plus label. Machine output carries a stable sender kind and the session id.
- When `RequestContext.mcp_caller_session_id` is absent, the caller is the direct operator over the local socket. The sender is the operator. Human output renders the fixed label `operator` for v1. Machine output carries a stable sender kind and the underlying `Local(uid)` principal.

Raw `RequestContext.principal` alone is insufficient as the sender. On a one host v1 deployment the Unix peer credential principal is the same `Local(uid)` for the operator and every spawned agent. Using that value alone would remove the nil UUID but still fail the operator question, "who is this from?" The bridge caller session id is the distinguishing agent sender reference.

Deleting public `from` eliminates first class sender field spoofing: callers no longer provide a sender unrelated to their connection. There remains a narrower trust assumption. `HELIOY_SESSION_ID` is seeded by the trusted spawner, forwarded by the agent MCP bridge, then folded into `mcp_caller_session_id` by the daemon. An agent can rewrite its own environment, so agent sender attribution is sound only inside the v1 single operator, cooperative local host trust domain. Binding each agent connection cryptographically to a session is identity-matters v2 scope, alongside impersonation.

Impersonation is the only named reintroduction trigger for a public sender override. If v2 needs send-as behavior, it should return as an explicit privileged impersonation request guarded by an identity-matters impersonate right and audited as such. It should not return as a casual `from` field.

A later implementation should replace the session-shaped `sender_id: Uuid` model with a sender reference that can represent either a session sender or an operator sender. It should also remove sender session validation from mail send. Recipient validation remains Session-owned selector validation.

### 2. Message identity and verbs

Recommendation: keep each mail id as a server generated identifier for a created mail item. The id belongs in JSON output, audit records, tests, logs, and machine correlation. It should not be the only human send output, and no v1 human verb should require the operator to copy it back into another command.

`mail send` should render a human confirmation such as delivered and failed recipient counts, with recipient details when useful. JSON output should include the created item ids and per-recipient errors. This preserves machine traceability without leaking an unusable internal handle as the primary user experience.

`mail read --selector` remains the only mutating receive verb. It drains unread mail for the selected recipient mailboxes. `--peek` is the non-mutating inspection mode. `mail check` reports unread counts. Do not add `mail ack`, `mail read <id>`, or delete by id in v1. There is no current consumer for those verbs, and adding them would create protocol surface without a workflow.

The delivery semantics are at most once per read call. When read drains unread mail, the daemon commits `read_at` for the returned set. If the client crashes after the daemon commits but before display, those items leave the unread view. `--peek` is the v1 mitigation. A future include-read or history view can make recovery ergonomic without changing the receive model.

The server generated message id is not a send retry dedupe key. A retried send after an ambiguous failure creates a new item and therefore a new UUIDv7 id. The id can support read-side correlation and idempotent consumption of one created item, but it cannot collapse duplicate sends with identical content. Send retry dedupe requires a future client supplied idempotency key.

Read ordering should be deterministic by `(sent_at, id)`. UUIDv7 gives a stable monotonic tie break when timestamps collide. A later pagination design should use selector plus limit and cursor over that ordering, not an ack-by-id model.

A later implementation should make row materialization and mark-read atomic, preferably through a single transaction or `UPDATE ... RETURNING` shape. A selector or serialization error must not mark mail read when the item cannot be returned to the client.

### 3. Addressing

Recommendation: keep addressing Session-owned. `to` and inbox selectors address recipient sessions through the existing Session selector grammar. Sender is derived from the request context and is never addressed through a `from` selector.

The public selector grammar is exactly:

- `all`
- raw `<uuid>`
- `id:<uuid>`
- `role:<name>`
- `namespace:<slug>`
- `dir:<path>`
- `label:<key>=<value>`
- `label:<key> in (v1, v2)`

`Selector::And` is internal composition used for namespace scoping. No public syntax exposes it. `workspace:` remains unsupported. Do not use open ended selector language in docs or schemas.

Send, read, and check should share the same namespace default. A selector without explicit widening is scoped to the caller namespace. `all` means all matching sessions in that namespace, not all sessions on the host. Cross namespace widening requires explicit `all_namespaces` or an explicit namespace selector, and that widening is authorization gated for send and read alike. This closes the current asymmetry where CLI send is namespace scoped but MCP send resolves host wide.

Mail remains point to point. When `mcp_caller_session_id` is present, an agent read or check targets only that session mailbox. Omitted selector defaults to self. Explicit selectors such as `all`, `role:<name>`, or another session id are constrained back to self unless Identity grants a future wider mailbox read right. For v1, agents do not get that wider right. This prevents peer mailbox drains even inside the cooperative local host trust domain.

Direct operator calls are administrative. When there is no caller session, operator read and check may target any mailbox, namespace scoped by default and widenable under authorization. Operator send may target any authorized recipient set, also namespace scoped by default and widenable under authorization.

Fan-out resolves the recipient selector once to a set of sessions. Delivery attempts only active recipient sessions. Unknown targets, inactive recipients, authorization failures, and delivery failures return per-recipient errors. Inactive recipients are explicit errors, never silent drops.

This section defines the protocol target, not only current behavior. The current MCP send path resolves a raw host-wide selector while read and check are namespace scoped. A later implementation should route MCP send through the same scoped selector path used by read and check. The read confidentiality limit caused by shared `Local(uid)` authorization is owned by the authz and provenance work in dimension 6, not by namespace scoping alone.

### 4. Output and rendering contract

Recommendation: mail output should use one daemon-side read model projection, then render that projection as human text or JSON. The Mail aggregate stores durable facts. The MailView projection enriches those facts with resolved sender and recipient summaries.

Mail must join the `--output json` honoring set. `mail send`, `mail read`, `mail check`, and `mail stop-check` should all have stable JSON shapes. JSON field names use snake_case. Sum types use the existing internally tagged convention: `type` with snake_case variants. Do not introduce camelCase fields for mail.

The core mail item view should contain `id`, `content`, `sent_at`, `read_at`, `status`, `sender`, and `recipient`. The sender view is a tagged sum:

- `type: "session"`, with `session_id`, `role`, `display_label`, `labels`, and `namespace`.
- `type: "operator"`, with `principal` and `display_label: "operator"`.

The recipient view is a session summary with `session_id`, `role`, `display_label`, `labels`, and `namespace`. Errors keep the common target error shape. Count views should include `session_id`, `role`, `display_label`, `namespace`, and `unread`.

Resolution belongs in the daemon, not only in the CLI. The daemon should batch load session summaries for all unique sender session ids and recipient ids before returning mail responses. MCP JSON, CLI JSON, and CLI human output should all consume the same MailView shape. This prevents raw id MCP output, avoids CLI-only enrichment, and keeps label resolution free of N+1 query patterns.

Human `mail send` output should be a concise delivery summary, such as delivered count, failed count, and recipient display labels. It should not print bare message ids as the primary output. Human `mail read` output should use labeled records or a table with at least sent time, sender, recipient, status, and content. Human `mail check` and `mail stop-check` output should show the total unread count plus per mailbox counts. The per mailbox data already exists in `MailUnreadCount`; the CLI should stop discarding it.

Current gaps are implementation blast radius. `Command::Mail` currently rejects `--output json`. `print_mail` currently dumps raw space joined fields. CLI `mail check` returns only the aggregate unread count. The later implementation should replace these with the shared MailView projection and a single human formatting module for all mail verbs.

### 5. Mail and nudge relationship

Recommendation: keep mail and nudge decoupled at the aggregate and handler boundaries. Mail is the durable Session mailbox channel. Nudge is an ephemeral Runtime wakeup channel. They may be composed by the Session app layer, but nudge does not become part of the Mailbox aggregate.

Add an opt-in `notify: bool` to mail send, surfaced in the CLI as `--notify` with `--nudge` as an acceptable alias if product copy wants it. This flag means: persist durable mail, then attempt a runtime nudge for each recipient whose mail item persisted. It should not create a separate verb.

The composition belongs in the daemon, not in clients. The daemon should resolve recipients once, apply the send addressing rules once, persist mail once per active recipient, then nudge exactly those persisted recipients when `notify` is true. Client-side two call composition would resolve twice and can nudge a recipient whose mail failed.

Authorization is per recipient. A notify send requires MailSend authorization for persistence. When `notify` is true, the nudge attempt also requires Nudge authorization for that recipient. Failure to authorize or deliver the nudge must not roll back persisted mail.

Mail owns send success. Nudge is best effort after persistence. Per recipient results should extend the send view from dimension 4 with both mail and notify state. JSON should expose a stable result such as `mail: "ok" | "err"` and `notify: "ok" | "err" | "skipped"`, plus the created mail item when mail succeeds and the warning or error detail when notify fails. Human send output should surface notify counts when `notify` is true, for example `3 delivered, 3 notified, 1 notify_failed`.

A nudge is only a wakeup signal for an already persisted mail item. It must not be described as durable delivery. Runtime absence, tmux unavailability, or headless runtime support should produce notify warnings or per recipient notify errors, not mail send failure.

### 6. Authorization and provenance

Recommendation: keep Identity as the authorization and audit authority. Session should call Identity for each mail and nudge decision, using the existing actions on the recipient session resource: `MailSend`, `MailRead`, and `Nudge`.

Authorization is present today on the durable and ephemeral paths. Mail send, mail read, and nudge each call `authorize()` with `session_resource(recipient)`. The authorize path records an audit row for allow and deny decisions. The audit contract for the target protocol is: every send, read, and nudge decision records actor, action, recipient session resource, decision, timestamp, and outcome.

The v1 security story is intentionally uid coarse. The audited actor is `context.principal`, derived from Unix peer credentials as `Local(uid)`. On a one host deployment, the operator and every spawned agent share that uid. Identity authz and the identity audit actor therefore do not distinguish agents.

Sender provenance uses the effective sender from dimension 1. When the MCP bridge forwards `mcp_caller_session_id`, the mail sender is that session; otherwise the sender is the operator. This removes the nil sender and deletes the public spoof field, but the session id is spawner seeded and agent forwardable. A malicious agent can rewrite its own forwarded session id inside the v1 cooperative host trust domain.

Mailbox read privacy uses the addressing rule from dimension 3. Agent read and check are scoped to the caller session mailbox. This stops accidental and casual peer mailbox reads, but it keys on the same forwarded `mcp_caller_session_id` used for sender attribution. It is therefore a cooperative trust boundary, not a hard boundary against a hostile agent forging its caller session.

These three limits share one cause: v1 identity authenticates the local Unix user, not a distinct agent session. V2 identity-matters should close them together by authenticating an effective principal that binds the connection to the caller session. That enables per-agent authorization, per-agent audit attribution, robust mailbox read isolation, and privileged impersonation. Until then, do not claim agent-level security isolation from Identity authz.

Impersonation remains out of v1. If a future caller needs to send or read as another principal, it should be a named privileged impersonation capability authorized by Identity and audited as impersonation. It should not revive an ungated `from` field.

### 7. Wire and contract compatibility

Recommendation: treat the mail protocol change as a breaking v1 contract cleanup. The repository is pre release, so compatibility aliases should not be carried forward. Delete the old `from` contract and regenerate generated surfaces from the authored mail tool definition.

The wire shape changes are intentional and cohesive:

- Send requests are server-attributed. `MailSendRequest` drops public `from` and gains `notify: bool`.
- Sender is no longer session-shaped by default. Mail uses a tagged sender reference that can represent `type: "session"` or `type: "operator"`.
- Recipients remain Session-owned session references.
- Send responses expose per recipient mail and notify status.
- Read and check responses expose daemon-side MailView, SenderView, RecipientSummary, and CountView projections.
- JSON stays snake_case and uses `type` tagged sum variants.

The tool contract changes follow that same shape. `mail_send` loses `from`, gains `notify`, and uses the same namespace-scoped addressing semantics as read and check. `mail_read`, `mail_check`, and `mail_stop_check` return the shared view types instead of raw aggregate rows or discarded counts.

The CLI contract changes match the wire contract. `--from` disappears. `--notify` is the opt-in combined durable mail plus wakeup path. Human output becomes a named, timestamped render over the same MailView data that JSON and MCP receive.

Store compatibility is a migration concern, not a compatibility promise. Sender storage changes from a sender session id to a tagged sender reference. Existing nil sender rows should become operator sender rows where appropriate. Cleanup, read ordering, and mark-read atomicity are part of the single implementation blast-radius checklist below.

V1 authorization and audit compatibility is explicit. The `authorize()` signature stays unchanged and audit actor remains `context.principal`. Per-agent audit attribution requires a v2 effective-principal change and should not be pulled into this v1 contract cleanup.

The contract source of truth remains authored surfaces plus generated output. A later implementation must regenerate help, schemas, snapshots, and drift guards from the authored definitions rather than hand-editing generated files or adding parallel compatibility paths.

## Decisions & rationale

| Fork | Chosen | Rationale | Rejected |
| --- | --- | --- | --- |
| Ownership home | Keep durable mail in Session. | The aggregate root is the recipient mailbox, keyed by session id and session lifecycle. Identity and Runtime are references through ports. | New Messaging context for v1. It would duplicate Session keyspace or create a dependency loop. |
| Sender source | Derive sender server side as an effective sender. | Deletes nil sender and removes first class sender spoofing. Agent senders map to caller session; direct socket maps to operator. | Public `from`; authz-gated `from`; raw peer credential principal only. |
| Agent sender trust | Treat `mcp_caller_session_id` as cooperative v1 attribution. | The trusted spawner seeds `HELIOY_SESSION_ID`, but the agent forwards it. Honest attribution works for v1. | Claiming hostile-agent identity binding before Identity supports it. |
| Message id semantics | Keep id as a machine identifier for created items. | Supports JSON correlation, audit, tests, and one-item consumption without forcing human copy-paste. | Bare-id stdout; `mail ack`; read-by-id; delete-by-id without a caller. |
| Read semantics | Selector drain is mutating and at most once; `--peek` is non-mutating. | Matches current mailbox model and keeps the protocol small. | Ack ceremony without a consumer; claiming at least once semantics. |
| Send retry dedupe | Future client idempotency key. | Server ids are minted after creation, so retries create distinct ids. | Using server message id to dedupe ambiguous send retries. |
| Recipient addressing | Use exact Session selector grammar. | One grammar already spans id, role, namespace, dir, labels, and all. | Hand-waved selectors, `workspace:`, or a separate mail addressing grammar. |
| Namespace scoping | Send, read, and check are namespace scoped by default. | `all` should mean the caller namespace, not silent host-wide blast. | Current MCP send host-wide asymmetry. |
| Mailbox privacy | Agents read/check only their own mailbox in v1. | Point-to-point mail means agents read their mail, not peers' mail. | Agent selector widening in v1; relying on uid-coarse authz for mailbox privacy. |
| Output shape | Use daemon-side MailView and snake_case JSON. | One projection serves MCP JSON, CLI JSON, and human output while avoiding CLI-only enrichment. | Raw space-joined dumps; camelCase fields; CLI N+1 lookups. |
| Check output | Surface total plus per-mailbox counts. | Counts already exist in the wire model. | CLI output that discards `MailUnreadCount.counts`. |
| Mail and nudge | Keep channels decoupled, compose with `notify: bool`. | Mail is durable; nudge is an ephemeral wakeup. Daemon composition resolves recipients once and nudges only persisted recipients. | Client-side two-RPC compose; nudge failure rolling back mail. |
| Notify partials | Per-recipient `mail` and `notify` status. | Operators need to know both durable delivery and wakeup outcome. | A single success bit that hides notify failures. |
| Authz and audit | Use existing `MailSend`, `MailRead`, and `Nudge` decisions on recipient session resource. | Authorization already records allow and deny audit rows through `authorize()`. | Claiming audit is absent; bypassing Identity. |
| Audit fidelity | Keep v1 actor as `context.principal`; make effective actor a v2 trigger. | Current actor is uid coarse and cannot distinguish agents. | Changing `authorize()` in v1 or claiming per-agent audit fidelity. |
| Impersonation | Defer to v2 as a privileged Identity capability. | No v1 one-operator caller needs send-as-other. | Keeping a casual spoofable `from` field. |
| Compatibility | Break contracts now and delete old paths. | Pre-release status allows cleanup without aliases. | Compatibility shims, duplicate paths, or generated surface hand edits. |

## Migration/blast-radius

Core protocol and model changes:

- `MailSendRequest`: remove `from`, add `notify: bool`.
- `Mail`: replace session-shaped `sender_id` with a tagged sender reference.
- New read model types: MailView, SenderView, RecipientSummary, CountView, and per-recipient send result.
- `MailSendResponse`, `MailReadResponse`, `MailCheckResponse`, and `MailStopCheckResponse`: return stable view types with snake_case fields.
- `MailUnreadCount`: enrich or wrap with `role`, `display_label`, and `namespace`.

Store and migration changes:

- Migrate `session_mail` sender storage from sender session id to tagged sender reference.
- Migrate nil sender rows to the operator sender where appropriate.
- Update namespace and session deletion cleanup. `internal/session/store/src/sqlite/namespaces.rs` currently deletes mail with `DELETE FROM session_mail WHERE sender_id = ? OR recipient_id = ?`; sender cleanup must become type aware once operator senders exist.
- Change unread ordering to `(sent_at, id)`.
- Make mark-read and row materialization atomic in one transaction or equivalent `UPDATE ... RETURNING` flow.

Daemon changes:

- Derive effective sender from `RequestContext`.
- Scope MCP send through the same namespace path as read and check.
- Enforce agent self mailbox reads and operator administrative reads.
- Build daemon-side MailView projections with batched session summary resolution.
- Compose `notify` after mail persistence and report notify partials.
- Keep `authorize()` unchanged for v1; document uid-coarse audit actor.

CLI and generated surface changes:

- `internal/session/app/tools/mail.toml`: remove `from`, add `notify`, update output schemas for all mail tools.
- `internal/session/app/src/cli/cli_def.rs`: remove `MailSendArgs.from`, add notify flag, and remove the `--from` flag.
- `internal/session/app/src/cli/generated_help.rs`: remove `MAIL_SEND_FROM_HELP`; add notify help.
- `internal/session/app/src/cli/mail.rs`: remove `env_session_id` sender default, stop bare-id stdout, pass json output through mail commands, render counts.
- `internal/session/app/src/cli.rs`: mark mail as JSON-supported.
- Replace `print_mail` with a shared mail human formatter over MailView.
- Regenerate MCP schemas, generated help, snapshots, tool contract registry output, and drift guards from authored sources.

Tests and verification:

- Handler tests for derived sender, sender ref persistence, namespace-scoped send, self mailbox read, operator read, inactive recipient errors, and notify partials.
- Store migration tests for sender ref, nil sender migration, namespace cleanup cascade, `(sent_at, id)` ordering, and atomic mark-read.
- MCP schema and protocol tests for removed `from`, added `notify`, self default, JSON shapes, and per-recipient errors.
- CLI snapshot tests for human send/read/check output and `--output json` support.
- Authz and audit tests proving allow and deny audit rows remain, with uid-coarse actor fidelity documented.
- Run `fmm generate && fmm validate` after structural and generated surface changes.
