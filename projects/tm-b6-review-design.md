---
title: "B6 Curated API — Adversarial Design Review (API contract lens)"
type: review
status: complete
reviewer: backend-engineer (transport-matters:helioy-tools:backend-engineer:1:3.1)
topic: b6-api-review
created: 2026-06-15
tags: [transport-matters, b6, api, design-review, contract]
---

# B6 Curated API — Design Review

Lens: API contract design quality (not code feasibility; analysts own that).
Default skeptical. Source under review: `~/.mdx/projects/tm-b6-api-proposal.md`.
Context: `tm-notes-remaining-b6-api.md`, `tm-notes-remaining-resume.md`,
orchestrator's ephemeral-home note (folded, not reviewed).

**Verdict tally: 0 blocker / 4 major / 7 minor.** The three load-bearing
*architectural* calls (in-place `/v1`, `homeDir` drop, native-resume deferral,
canvas-layout cut) are sound and I positively justify each below. The findings
are gaps in the *shape* layer: the curated nouns under-serve the very product
surface (resume) that B6 exists to unblock, and the closed sets (error codes,
verbs) have holes the API is guaranteed to hit.

---

## MAJOR

### M1 — Curated `Session` omits the resume-card's last-message preview → N+1 card list
`Session` (Decision 3) is the single-get source for the resume card
(note 15: "single-get (resume-card source)"). But resume slice **S2** lists
`lastAgentMessage` as a required deterministic resume-card field
(`tm-notes-remaining-resume.md` S2). The curated `Session` has no
`lastAgentMessage` / `lastMessagePreview` field. To render a session list or
card, the client must issue a second per-item `/events`/`/timeline` fetch — an
N+1 on the primary product surface B6 is built to unblock. The proposal already
computes `turnCount`/`inheritedTurnCount` at read from events, so the
last-message is on the same read path; it just isn't in the contract.
**Recommend:** add `lastMessagePreview` (or `lastAgentMessage`) to `Session`, or
define a dedicated `SessionCard` list projection. Don't ship a card surface that
requires a fan-out fetch to paint.

### M2 — `TranscriptEvent` drops all turn grouping, yet turns are first-class on `Session` and in lineage
The curated event (`{seq, kind, role, ts, body, resourceRefs}`) drops
`nativeTurnId` **and** `parentNativeId` — every turn-grouping signal. Meanwhile
`Session.turnCount`/`inheritedTurnCount` are first-class, and the lineage badge
must render "Forked at turn N" (resume S4) while `lineage.forkedAtSeq` is an
**event seq**. Converting `forkedAtSeq` → "turn N", or aligning a "12 turns"
count to the rendered timeline, requires a seq→turn mapping the contract no
longer exposes. Turn boundaries are not trivially derivable: CLAUDE.md notes
Codex carries "incremental request payloads on later turns," so a naive
user-message split is wrong. **Recommend:** expose a curated, non-native
`turnId` (or `turnIndex`) on `TranscriptEvent`, or specify the canonical
seq→turn boundary rule in the contract. As written, the API reports turn
quantities its own event stream cannot reconstruct.

### M3 — "Closed" `ErrorEnvelope` code set omits the cases the API will actually hit
The set (`workspace_not_found … run_not_attachable`) is declared closed but has
no code for **input validation / invalid cursor**, despite cursor pagination on
*every* list plus query params (`workspaceId, purpose, visibility,
includeInternal`). A stale/garbled cursor is a guaranteed code path (clients
persist cursors and replay them). There is also no ownership-outcome code, and
reads are "owner scoped" (CLAUDE.md) — decide explicitly whether a
non-owner/foreign id returns `*_not_found` (no existence leak) or a distinct
`forbidden`. A closed set that can't name a guaranteed case forces a wrong code
or an undocumented 422/500. **Recommend:** add `invalid_request` (or
`invalid_cursor`) and rule the ownership outcome into the set. Also: codes are
snake_case while the bodies are camelCase-throughout — fine if intentional
(machine codes), but call it out so it isn't read as drift.

### M4 — `continueFromSessionId` side-effect-mints a child `Session` with no idempotency story
Decision 4 collapses note 12's standalone continuation endpoint into a launch
param on `POST /v1/runs`, which mints a child `Session`
(`purpose=continuation`, `parentSessionId`, `forkedAtSeq`) **as a side effect of
spawning a run**. One non-idempotent POST now creates *two* resources. A retry
or a double-clicked "Resume From This Session" (resume S4 affordance) yields two
continuation sessions forked off the same prior at the same seq — duplicate
lineage polluting the session list and the resume card. Single-user blunts the
blast radius but the defect is silent and the fix is a cheap contract decision
now / expensive later. **Recommend:** accept an idempotency key on
`POST /v1/runs`, or keep the mint and the spawn as separately addressable steps
so the child session de-dups. (This is the one place note 12's split endpoint
had a real justification the proposal under-weighs.)

---

## MINOR

### m1 — `DELETE /v1/runs/{id}` mislabels a lifecycle transition as deletion
The contract's own `run_stopped` error code proves a stopped run stays
addressable — acting on it returns `run_stopped`, not `run_not_found` — so
DELETE does not remove the resource; it performs a *stop* transition and returns
the still-extant Run in terminal state. DELETE-as-stop is also non-idempotent: a
second DELETE returns the `run_stopped` *error* rather than a no-op success.
**Recommend:** either `POST /v1/runs/{id}/stop` returning the Run (verb matches
behavior), or keep DELETE but document (a) that a stopped run remains GET-able
for a window and (b) idempotent-repeat semantics. Returning a full body on
DELETE is otherwise acceptable as a terminal-state tombstone.

### m2 — Run terminal WebSocket is missing from the end-state route set
The desktop's core feature is attaching to a run terminal over
`WS /runs/{id}/terminal` (CLAUDE.md; note 12 listed `WS .../terminal`), and
dropping `webPort`/`proxyPort` from `Run` is only safe *because* the terminal WS
is proxied on the API origin. Yet the "Route set (end state)" block omits it. If
it silently stays at `/api/runs/{id}/terminal` while REST moves to `/v1`, that
is exactly the "never both live" split Decision 1 forbids. **Recommend:** add
`WS /v1/runs/{id}/terminal` to the route set explicitly. (Elevate to Major if
the WS is intended to remain un-migrated.)

### m3 — Same concept, different field names across nouns
`Workspace.lastActivityAt` vs `Session.updatedAt` for the same "most-recent
activity" timestamp; `Session.status` vs `Run.state` for lifecycle. A curated
product contract should name identical concepts identically. `status`/`state`
may be defensible (different value sets), but `lastActivityAt`/`updatedAt`
should converge. **Recommend:** pick one activity-timestamp name across nouns.

### m4 — `TranscriptEvent.body` is an untyped blob — the curation stops short of the payload that matters
The curation strips provenance but leaves `body` opaque. `body` for
`kind=user` vs `tool_use` vs `tool_result` (and wire-only injected content,
which is the product's whole point) has different shapes; an untyped `body`
pushes per-kind shape knowledge back onto the client — the mechanism leak the
curation is supposed to close. **Recommend:** make `body` a `kind`-discriminated
union, or document the per-`kind` body schema in the contract.

### m5 — Per-noun PR bundles three orthogonal contract changes
Decision 1's migration unit changes path (`/api`→`/v1`), casing
(snake→camel), and field set (curation/drops) in one atomic per-noun PR. That
maximizes blast radius per PR and defeats bisection (a regression could be the
path, the casing, or a dropped field). **Recommend:** treat the path move as a
mechanical step and make the shape/curation change the reviewable unit, even if
they land in the same PR they should be separable commits.

### m6 — Desktop canvas-layout store carries un-enforceable cross-context references
The bounded-context cut (Decision 2) is correct, but the consequence is
unaddressed: the desktop layout store persists the `CanvasPaneRef` union
including `session-picker`/`session-timeline` panes (resume S6) that reference
capture-domain `sessionId`/`workspaceHash` it does not own. B6 must **not** add
an FK across the seam; the desktop store must treat these as soft references and
tolerate dangling (deleted session → placeholder pane). Also align the layout
key's workspace identifier with the curated `workspaceId` (proposal keys on
`workspaceHash`) so the two contexts share one identity vocabulary.

### m7 — List contract under-specified beyond "nextCursor on every list"
Missing: the list response envelope shape (`{items, nextCursor}`?), the
page-size param name + default + max, and a statement that the cursor encodes /
locks the active filter set (changing `purpose`/`visibility`/`workspaceId`
mid-page must not corrupt paging). **Recommend:** define one list envelope and
one page-size param reused across every list endpoint.

---

## Positively justified as correct (stress-tested, not waved through)

- **Decision 1 — converge-in-place `/v1`, delete `/api/<noun>` same PR.** Sound.
  The backcompat hazard versioned-parallelism protects against does not exist
  here: backend + www + desktop ship as one install (CLAUDE.md), so there is no
  independently-deployed client that can hold a stale contract, and runs are
  process-resident (die on the deploy restart), so there is no in-flight-client
  migration window. Parallel `/api/v2` would buy perpetual drift for zero
  consumers. (Nit: the "`/v1` is a stability signal but no `/v2` is planned"
  rationale is self-undercutting — the prefix choice is fine, the justification
  is empty; either own that `/v2` is possible or drop the versioning prose.)

- **Decision 3 — drop `homeDir` from curated `Session`.** Correct, and verified
  against code. The durable `session.home_dir` column is write-mostly
  (`session/ingest.py`, `session/backfill.py`, COALESCE upsert in
  `session/dao_statements.py`); the only consumer, www, **types it and never
  uses it** (`sessionClient.ts` type decl + a test-fixture default; zero
  behavioral reads), and no continuation/relaunch path reads the persisted
  column. It is dead weight on the wire today. The proposal's deeper argument
  also holds: the field is a *source/provenance* value (`settings.agent_home_dir`
  via `addon_runtime.py`), never the transcript-bearing home — confirmed by the
  ephemeral-home note (the real home is the per-run `descriptor_home` that is
  `rmtree`'d at teardown). Freezing a field whose meaning flips across
  provider/launch-mode (source-template / mutated-CODEX_HOME / null) into a
  product contract would encode a runtime-dependent lie. Keep it in storage for
  forensics; if ever surfaced, surface structured `template_provenance`, not a
  raw path. **Answer to Q3: yes, droppable — no behavioral reader exists.**

- **Decision 4 — TM-seeded continuation only; native CLI resume off the table.**
  Correct, and per the owner's authoritative product direction not merely
  deferred but excluded: `transport-matters desktop` accepts no passthrough CLI
  args (no `--resume`/`-c`), so all continuation is a TM-level concept —
  `continueFromSessionId` triggers TM-internal child-session minting + Postgres-
  sourced context priming. This is also architecturally forced by ephemeral
  homes: the native session JSONL is written into the per-run overlay and
  destroyed at teardown, so `claude --resume <id>` has nothing durable to resume.
  Launch-param-only (no standalone continuation endpoint) is therefore the right
  shape — there is no pre-run continuation the UX produces. (Two notes, not
  objections: (1) M4 — because the mint is unambiguously TM-internal, its
  idempotency is entirely TM's to own, which makes the missing idempotency story
  a TM contract gap, not an upstream-CLI constraint; (2) UX framing — a TM-seeded
  "continuation" is a fork with re-injected context, not a restored agent;
  lineage fields model it correctly, copy should not promise true resume.)

- **Decision 2 — canvas-layout is not a B6 noun.** Correct DDD call. Pane layout
  is desktop view-state, orthogonal to the capture domain; folding it into the
  product contract would couple capture reads to UI presentation. (Consequence
  tracked as m6.)

- **Cursor pagination over offset.** Correct hygiene win over the current
  `limit`/`offset` on `/api/sessions` (offset is unstable under concurrent
  insert). (Detail gaps tracked as m7.)
