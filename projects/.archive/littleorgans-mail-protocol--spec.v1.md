---
title: littleorgans mail protocol design spec
status: draft
date: 2026-05-31
---

# littleorgans mail protocol design spec

## For Stuart's evaluation

Draft in progress. Load-bearing decisions will be finalized after all design dimensions converge.

## Recommended design

### 0. Bounded context ownership

Recommendation: keep mail under Session for v1. Session owns the Mailbox aggregate and read model. Identity owns sender principal resolution, authorization, and audit decisions. Runtime owns nudge delivery. Session remains the composition root for the user verbs.

Rationale: the aggregate is the per-recipient mailbox, keyed by `session_id`. Mail items are entities inside that mailbox. The core state transition is unread to read through `read_at`. Delivery is valid only against the session keyspace and active session lifecycle. Extracting mail into a new Channels or Messaging bounded context now would either duplicate the session keyspace or create a bidirectional dependency between Session and Messaging. That lowers cohesion and increases coupling.

Nudge is not part of the Mailbox aggregate. It is an ephemeral Runtime adapter action invoked from the same operator surface. Mail and nudge share selector grammar and authorization patterns, but they do not share persistence or aggregate invariants.

A later implementation should keep the current ownership while making the collaboration explicit through ports: an Identity port for principal and authz decisions, a Runtime port for nudge delivery, and the Session store for mailbox persistence. A future Messaging context becomes justified only if the durable model stops being session-keyed, such as sender-indexed outbox, thread or conversation views, or durable notification policy independent of a session mailbox.

## Decisions & rationale

Draft in progress. Final table will be written after dimensions 0 through 7 converge.

## Migration/blast-radius

Draft in progress. Final notes will be written after dimensions 0 through 7 converge.
