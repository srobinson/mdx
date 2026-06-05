---
title: littleorgans mail protocol — MoE warroom charter
status: charter
date: 2026-06-01
target: littleorgans-mail-protocol--spec.md
pattern: peer-consensus (Codex + Claude)
---

# littleorgans mail protocol — warroom charter

Converge the consolidated mail protocol spec through an adversarial MoE pass.
Stuart has signed off on the spec; this is hardening, not authoring. Design only,
no implementation. The companion conduct spec is parked and out of scope.

## Inputs

- Target: `~/.mdx/projects/littleorgans-mail-protocol--spec.md`.
- Diff baseline: `~/.mdx/projects/.archive/littleorgans-mail-protocol--spec.2026-06-01-pre-consolidation.md` (the warroom-signed base) and `.v2.md`.
- Code anchors: `lilo-sys` at `c6ad8df` (`crates/lilo-sys`: process, signal, ipc, creds); mail today in `internal/session/{core,daemon,store}`; tmux at `internal/runtime/daemon/src/tmux.rs`.
- Resolved-but-confirm context: `cm` decision `019e7ea4-...` (pull-back) and the parked `--as-session` note.

## Roles

- **Codex** drafts critiques and pressure-tests feasibility and implementation realism on single-host SQLite. Owns the store, delivery-worker, and migration angles.
- **Claude** is the DDD and contract adversary. Owns aggregate boundaries, ports, invariants, ubiquitous language, and the read-only observability guarantee.
- Each cross-checks the other. Both sign off, or a contest surfaces to the orchestrator (Stuart via the host) for a ruling. Do not stall on a fork.

## Scrutinize (the deltas from the signed base, not settled ground)

1. **Store shape and retention.** Two tables (`messages` + `message_deliveries`), drop `session_mail`. Is the normalization right? Resolve message-versus-delivery retention and the `namespaces.rs` cascade.
2. **Delivery safety.** At-least-once + client idempotency key + dedup + dead-letter, and the loop/budget breaker. Feasibility on single-host SQLite, and the concrete breaker ceilings (global or per-role).
3. **Receive surface.** `mail read` drops its selector and is self-drain only; `peek`/`check`/`tail` hold selectors. Confirm the footgun removal and the operator-has-no-mailbox stance.
4. **Conversation + observability.** `context_id` as a correlation tag; operator peek/tail read-only over the log, never touching cursors; reuse of the event stream and MessageView. Verify the read-only invariant is airtight.
5. **Liveness.** `Wait`/`Steer` on runtime turn-state layered over `lilo_sys::process` liveness; tmux stays in the runtime behind `DeliveryPort`. Confirm the no-dedicated-wire recommendation.
6. **Sender + provenance.** Server-derived `session`/`operator`/`system`; public `from` deleted; uid-coarse cooperative-trust honestly stated.
7. **Ubiquitous language.** A2A/FIPA fully removed; nothing reintroduces a performative or task FSM by the back door.

## Rule on these (decide, do not merely note)

- Message-versus-delivery retention and cascade.
- Breaker ceilings and whether they are global or per-role.
- Ratify or overturn: no dedicated nudge wire in v1; two new tables dropping `session_mail`.

## Out of scope (do not relitigate)

Named rooms and a Channels context, IRC primitive, blackboard, NATS/broker, A2A/cross-host, per-agent identity isolation, impersonation, `--as-session`. All deferred or parked by prior decision.

## Sign-off criteria

Internally consistent, single-host-feasible, DDD-clean, both panes signed off, every contest either resolved or surfaced to the orchestrator. Output is a converged spec plus a short decisions delta, no code.
