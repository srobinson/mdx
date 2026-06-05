---
title: Little Organs first Transport proof design synthesis
type: design
tags: [littleorgans, transport, issue-37, architecture, arena]
summary: Comparison and graft record for the GPT, Grok, and parent Transport architecture candidates.
status: active
project: littleorgans
confidence: high
related: [littleorgans-first-transport-proof]
created: 2026-08-17
updated: 2026-08-17
---

# Little Organs first Transport proof design synthesis

## Result

Claude selected the GPT candidate as the base. The cross judge scored GPT 34,
the parent candidate 29, and Grok 26. GPT had the clearest evidence model,
commitment semantics, typed command guards, acyclic two-crate graph, and honest
limits.

The final design replaces GPT's per-session listener and pre-transaction
preparation. It uses one shared listener and database-only preparation inside
Session transaction A.

## Candidates

| Candidate | Shape | Strong parts | Rejected parts |
| --- | --- | --- | --- |
| GPT | `core` and `service`; per-session listener; prepare before transaction A | deep service boundary, port contract, stale-write guards, canonical body definition, `CommitmentUnknown`, recovery proof | listener binding before transaction A creates an orphan window and forces Identity API changes; one listener per Session adds recovery work |
| Parent | `core`, `store`, and `daemon`; shared listener; prepare in transaction A | shared listener, internal correlation header, separate state axes, no Session link table | store crate has no second consumer; initial state and evidence APIs were less complete |
| Grok | `core`, `store`, and `daemon`; shared listener; prepare in transaction A | atomic capture lease, concrete launch environment, explicit product choices | depended on undocumented URL path behavior, duplicated the Session association, mixed state axes, added extra IDs and Codex scope |

## Grafts onto GPT

The final design takes these parts from the parent and Grok candidates:

1. Bind one shared loopback listener when `lilod` starts.
2. Correlate requests with a non-secret internal header through
   `ANTHROPIC_CUSTOM_HEADERS`.
3. Strip the internal header before provider forwarding and audit the change.
4. Run database-only capture preparation inside Session transaction A.
5. Keep routing phase, mutation, commitment, and terminal outcome as separate
   types.
6. Use `SessionId` directly for the joined read. Do not add a Session link table.
7. Fail closed for unsupported Docker isolation.
8. Keep the hold timeout below Claude's resolved `API_TIMEOUT_MS`.

The final design retains these GPT parts:

1. Two private crates, `lilo-transport-core` and `lilo-transport-service`.
2. A narrow Session-facing `TransportPort`.
3. `expected_revision` and original-description digest guards for edits.
4. Exact body bytes as canonical evidence, with credential headers excluded.
5. Append-only evidence and audit records.
6. `CommitmentUnknown` for the network and database crash window.
7. Claude-only scope, explicit navigation, HTML first, and Canvas on the same
   contracts.

## Rejected alternatives

### Separate store crate

The first proof has one storage consumer and one lifecycle owner. A private
`service::store` module keeps SQL behind the service without creating a stable
crate API before the schema settles. Extract the crate when a second consumer or
independent lifecycle appears.

### Per-session listeners

Per-session ports avoid a correlation header, but listener binding becomes a
pre-transaction side effect. Recovery must rebind every stored port. One shared
listener turns capture preparation into database work and supports atomic
transaction A insertion.

### URL path correlation

Claude Code documents `ANTHROPIC_BASE_URL`, but its public contract does not
promise path-prefix preservation. The design uses the documented custom-header
mechanism instead.

### Session capture-link table

Transport captures already carry the authoritative `SessionId`. Session owns
the joined read operation by calling the Transport port. A second link table
would duplicate the same relationship and require reconciliation.

### Perfect commitment knowledge

Postgres and a provider socket cannot commit atomically. Transport persists
intent before the first provider write, records confirmed byte counts after
writes, and reports `CommitmentUnknown` after an ambiguous crash. It never
retries.

## Required document lock

Implementation remains blocked until the governing repository documents state:

1. Transport preparation returns one opaque attachment plus typed launch
   environment.
2. Database-only preparation participates in Session transaction A.
3. Canonical provider bytes mean request and response body bytes, including
   ordered response chunks.
4. The first proof supports host execution and fails closed for unsupported
   isolation.
5. The fourteen product decisions in issue 37 use the locks in the companion
   design.

## Working artifacts

The temporary comparison set is under
`~/.mdx/TMP/pstack/issue37-system-design/`:

* `grounding-code.md`
* `grounding-product.md`
* `candidate-main.md`
* `candidate-gpt.md`
* `candidate-grok.md`
* `judge.md`

