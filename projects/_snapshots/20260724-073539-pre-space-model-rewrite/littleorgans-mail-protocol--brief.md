---
title: littleorgans mail protocol — redesign brief (warroom seed)
status: brief
date: 2026-05-31
---

# littleorgans mail protocol — redesign brief

Seed for a MoE spec warroom. Goal: produce a design spec for how the lilo mail protocol *should* operate. Codex drafts the spec; Claude architect adversarially reviews; converge; surface real product forks to the orchestrator (Stuart decides "what/why").

## Trigger

Operator road-test of `lilo mail` surfaced UX + identity gaps:
- `lilo mail send ...` prints only the bare message id (UUIDv7). No verb consumes that id — there is no `mail ack <id>` / `mail read <id>`; read/check work by selector. The id is an internal handle leaked to stdout with nothing behind it.
- `lilo mail check --selector all` prints only `N unread` — a bare count, no per-mailbox / per-sender breakdown; you cannot tell who has mail or from whom.
- `lilo mail read --selector <sid>` dumps the raw `Mail` struct: `{id} {sender_id} {recipient_id} {status} {content}`, space-joined, no headers. Operator-origin sends show `sender_id = 0000…0` (nil UUID).

## Verified current state (file:line — do not re-investigate, verify only if changing)

- Render: `internal/session/app/src/cli/output.rs:44-55` `print_mail` prints raw fields space-joined, no headers/labels/timestamps.
- Send render: `internal/session/app/src/cli/mail.rs:37` prints `item.id` only. Check render: `mail.rs:79` prints `"{unread} unread"`.
- MCP `mail_send`: `internal/session/daemon/src/mcp_tools/mail.rs:16-40`. `from` is set ONLY from the explicit `from` argument (line 26: `optional_string(arguments,"from")`). The caller identity is available (`context: &RequestContext` carries `caller_session_id` from the bridge / `HELIOY_SESSION_ID`) and IS used on the read path (`scoped_required_selector(state, context, …)` line 49), but is NEVER used to derive `from`. So: agent send without explicit `from` → nil sender; and `from` is a free string with no `caller == from` check → SPOOFABLE.
- Mail vs nudge are decoupled by design: `internal/session/daemon/src/handler/messaging.rs:17-53` (`mail_send`, store only, no nudge) vs `:101-122` (`nudge`, ephemeral tmux). Two orthogonal channels.
- MCP surface is mature: 22 tools, all wired to daemon RPCs, generated from `tools/*.toml` with a drift guard. Mail tools: `mail_send`, `mail_read` (drains unless peek), `mail_check` (count), `mail_stop_check`, `nudge`.
- `lilo mcp` is a stdio→unix-socket bridge; the MCP engine runs in the daemon (`mcp_bridge.rs`). NOT auto-injected into spawned agents (separate known gap, out of THIS spec's scope unless the protocol depends on it).
- Mail is NOT in the `--output json` honoring set (the item-7 `JsonOutputSupport` gate did not include mail/read/check) — mail output is text-only raw dump today.

## Design dimensions the spec MUST cover

0. **Bounded-context ownership (decide this FIRST).** The established prior is that Session owns mail — "session-matters is the natural home" — and today it lives in `internal/session` (handler/messaging.rs, core proto, store). Since the API is being redesigned, RE-DERIVE this rather than inherit it: should mail+nudge (the "channels"/messaging concern) remain a Session-owned aggregate, or become its own bounded context (a Channels/Messaging context) that Session composes? Weigh cohesion vs coupling: mail's dependencies on identity (sender/authz), audit, the selector/addressing grammar (shared with sessions/labels), tmux/runtime (for nudge), and the session lifecycle. The prior is strong, so a MOVE needs strong justification; "stay in Session" is an acceptable conclusion IF justified. This is a Stuart-fork: present the ownership recommendation with the coupling analysis, do not silently re-home. Do NOT let this balloon into a v2 reorg — it is a design recommendation, the move (if any) is a later refactor Stuart approves.

1. **Sender identity model.** Default `from` to the authenticated caller (principal/session from `context`). When/whether an explicit `from` is allowed (reject? gate to a privileged "impersonate" right via identity-matters? operator-origin as a *named* principal, not nil?). Eliminate the nil sender as a human-facing value.
2. **Message identity & verbs.** What is the message id FOR? Is there an ack/read-by-id verb, or is selector-drain the only model? Should `read` drain vs `peek` vs paginate? Idempotency / at-least-once semantics?
3. **Addressing.** Selector grammar for `to` (label:, session-id, all, role:?). Self-addressing (an agent reading "its own" mailbox). Multi-recipient fan-out semantics + the per-recipient errors array.
4. **Output / rendering contract.** Human render: columns/labels, resolve session-ids → role+label, timestamps, sender as a named principal. Machine render: add mail to the `--output json` honoring set with a stable JSON shape. One shared render path (DRY).
5. **mail vs nudge relationship.** Keep decoupled (confirmed design) but spec whether `mail send` should offer an opt-in `--nudge`/`--notify` to fire both in one call, and how that composes.
6. **Authz / provenance.** Spoofing fix; how identity-matters authorizes send/read/impersonate; audit trail (mail already writes audit rows).
7. **Wire/contract compat.** This is pre-release (breaking changes OK). Note the `Mail` struct + `MailSendRequest`/`MailReadRequest` + the `tools/*.toml` MCP contract + generated schema/snapshots impact, but the spec stays a DESIGN doc — no implementation.

## Constraints

- v1 local-first (one operator, one host, one lilod). Do NOT pull in v2 scope.
- identity-matters is the IAM authority (principals, authz, audit) — the sender model should compose with it, not reinvent it.
- DDD / bounded contexts: mail is a Session-owned aggregate. Keep the read-model vs aggregate distinction clean.
- Pre-release, zero external users: breaking changes welcome where they simplify.
- 700-line file / 150-line fn caps apply to any later implementation.

## Deliverable

A design spec written to `~/.mdx/projects/littleorgans-mail-protocol--spec.md` with:
- A **Recommended design** per dimension (the converged MoE position), each with one-line rationale.
- A **Decisions & rationale** section: every genuine fork (e.g. ownership home; allow explicit `from` at all? `read` drain vs paginate? add `--nudge` to send?) RESOLVED, each with the chosen option + why + the rejected alternatives in one line. The orchestrator (not the panes, not Stuart mid-flight) has final authority on contests — surface a contest via E to the orchestrator, who rules, then continue. Do not stall on a fork.
- A **For Stuart's evaluation** summary at the top: the 5-8 load-bearing decisions in one line each, so Stuart can override any before implementation.
- A **Migration/blast-radius** note (which types/contracts/tests/generated surfaces a later implementation touches).

Run to a COMPLETE, internally-consistent, converged design with both panes signed off. Do NOT implement — spec only.
