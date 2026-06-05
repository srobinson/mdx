---
title: littleorgans agent communication protocol spec — anti-ping-pong conduct and skill
status: parked
parked_until: littleorgans-mail-protocol--spec.md lands; depends on its intent field, context_id, breaker, and automated receipts
date: 2026-06-01
companion: littleorgans-mail-protocol--spec.md
deliverable: an MCP resource (canonical contract) plus an agent-facing skill
---

# littleorgans agent communication protocol spec

The conduct agents follow when using lilo mail, written to prevent mail
ping-pong and runaway agent-to-agent loops. The mail protocol spec owns the
mechanics (the wire model, the `intent` field, automated receipts, the circuit
breaker). This spec owns the behavioral contract and how it reaches agents.

## Purpose and the defense-in-depth split

A circuit breaker catches a loop after it starts. It does not stop agents from
starting one. Prevention and enforcement are separate layers, and the design
uses three that reinforce each other:

1. **Model.** The `intent` field and `context_id` on every message make the
   rules checkable. Defined in the mail protocol spec.
2. **Conduct.** The behavioral contract agents follow. This spec. Delivered as
   an MCP resource plus a skill.
3. **Breaker.** The loop and budget backstop, keyed on conversation depth and
   per-sender rate. Defined in the mail protocol spec, §7.

The contract is partly machine-checkable, so it is more than honor-system. The
daemon enforces the cheap, decidable rules; the skill carries the judgment that
cannot be enforced; the breaker covers whatever slips both.

## Intent vocabulary

The spine of loop prevention is that most messages must not be replyable. Every
message carries one intent. The vocabulary is closed and minimal. It is a
pragmatic loop-control tag set, deliberately not a FIPA performative ontology;
the mail protocol spec drops that lineage on purpose.

- **`request`** asks the recipient to do or answer something. The only intent
  that licenses a reply.
- **`inform`** shares state. No reply expected or permitted.
- **`result`** is the answer to a `request`. Terminal. It closes the request.
  No reply.
- **`receipt`** is the daemon's automated read-receipt, system-sender. Terminal.
  Agents never author it and never reply to it.

The rule that kills most ping-pong: only `request` may be replied to. `result`,
`inform`, and `receipt` are terminal.

## Conduct rules

- **Reply only to a `request`.** A `result`, `inform`, or `receipt` ends a leg
  of the conversation. Do not respond to it.
- **Reply to the sender, never to the recipient set.** A `request` fanned out
  to `role:reviewer` produces independent replies to the sender, never a
  reply-all amplification across the fan-out set.
- **Do not acknowledge by message.** `read_at` already proves delivery, and the
  daemon emits the read-receipt automatically. Confirming receipt by sending
  mail is the canonical ping-pong seed. Acknowledge by action.
- **One request, one closure.** A `request` is closed by exactly one `result`,
  or one terminal `inform` if nothing is owed. Do not send a second result.
- **Respect the conversation budget.** Every exchange shares a `context_id`.
  Track turn depth and stop at the cap. The breaker is the backstop for when an
  agent does not.
- **Drop duplicates silently.** A message already seen, by id or idempotency
  key, is dropped. Never reprocess, never re-reply.
- **Nudge once, then wait.** While awaiting a reply, wake the recipient at most
  once. Do not re-send the request and do not poll-spam.
- **Guard self and echo.** Never address yourself. Ignore your own message when
  it arrives through a fan-out set.
- **Stop and escalate.** On a budget trip, a suspected loop, or an exchange you
  cannot parse, stop and surface to the operator. Do not try to recover by
  sending more mail.

## Enforcement split

What the daemon enforces, because it is cheap and decidable:

- Reject a reply whose target message has a terminal intent (`result`,
  `inform`, `receipt`).
- Reject a reply addressed to the fan-out set rather than the original sender.
- Drop a duplicate by id or idempotency key.

What stays conduct, because it needs judgment the daemon cannot make:

- When a conversation is genuinely done versus needs one more turn.
- When to escalate to the operator.
- Whether a received `request` warrants action or a polite terminal `inform`.
- Conversation hygiene within the budget.

What the breaker enforces, as the final backstop:

- Conversation depth and per-sender rate ceilings, independent of agent
  compliance.

## Delivery: MCP resource plus skill

The contract must not live in a prompt suffix. The field's cautionary case is a
multi-agent product that encoded its protocol ("send `ACK:` on receive") as a
string appended to every agent's task prompt; it was fragile and load-bearing
in the wrong place. lilo does the opposite.

- **Canonical contract: an MCP resource.** The mail MCP tools advertise a
  resource that states the intents, the reply rules, and the enforced subset.
  Every agent that can call `mail_send` can read the contract. It travels with
  the tool, not the prompt, and versions with the tool.
- **Agent-facing operationalization: a skill.** A skill teaches an agent how to
  apply the contract in practice: how to choose an intent, how to close a
  conversation, when to escalate. The skill references the MCP resource as the
  source of truth rather than restating it, so the two cannot drift.

Both render from one authored source so the enforced rules, the resource text,
and the skill stay consistent.

## Relationship to the breaker

Prevention and enforcement are complementary. The conduct rules aim to make a
loop never start. The breaker bounds the damage if one does. The breaker keys on
the same `context_id` the conduct rules use for the budget, so a conversation
that conduct fails to self-limit is the same conversation the breaker trips. A
trip is also a signal that the conduct or its budget needs tuning.

## Decisions and rationale

| Fork | Chosen | Rationale | Rejected |
| --- | --- | --- | --- |
| Loop strategy | Prevention plus enforcement, three layers. | A breaker alone is reactive; conduct alone is honor-system. | Breaker only; conduct only. |
| Vocabulary | Minimal closed intent set, four values. | Most messages must be non-replyable; a small set is enough. | FIPA performatives; an open string set. |
| Reply target | Reply to sender, never to the fan-out set. | Reply-all over a multicast is the storm vector. | Reply to the recipient set. |
| Acknowledgement | Automated `system` read-receipt; no agent acks. | Takes acknowledgement out of the agent loop entirely. | Agent-authored ack messages. |
| Delivery | MCP resource canonical, skill operationalizes. | The contract travels with the tool and versions with it. | A prompt-suffix protocol. |
| Enforcement | Daemon enforces decidable rules only. | Cheap rules are machine-checkable; judgment is not. | Enforcing judgment; enforcing nothing. |

## Open questions

- The concrete conversation-depth and per-sender-rate ceilings for the breaker,
  and whether they are global or per-role.
- Whether the skill ships as a lilo-managed skill injected at spawn, or as a
  documented skill agents load themselves. This depends on the separate
  MCP-auto-injection gap noted in the mail protocol research.
- Whether `inform` needs a sub-distinction between fire-and-forget broadcast and
  a directed status update, or whether one `inform` covers both for v1.
