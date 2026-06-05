# Transport Matters — Session Store (charter)

Orchestrator-authored from a long design chat. The panel fleshes this into a
buildable spec. Settled decisions are not up for relitigation; ground them in the
actual repo, fill the open questions, and harden. Read this instead of the chat.

## North star

The product is a SESSION PLATFORM: replay, fork, share (to teams), eval, learn,
built on captured agent sessions. Local first, hosting ready, where hosting is
just deployment (same app and schema, pointed at a remote Postgres). This thread
designs the SESSION / TRANSCRIPT STORE the platform sits on.

The wire/transcript DIFF is NOT a product feature and must not be built. It was a
casual interest, never a requested tool.

## Scope

IN: the transcript/session store (Postgres), its ingest path, live append, the
fork/share/eval/learn read surfaces, and migration from the current store.

PARKED (separate concern, do NOT design here): wire-exchange storage
(`request.ir`, `response.ir`, `request.raw`, `response.raw`, codex
`transport.json` which is effectively the codex raw response). The proxy and wire
capture keep running; we are only deferring how wire exchanges are stored. Design
the schema so a wire exchange can later attach as a correlated per-turn sibling,
but do not specify it now.

## Settled decisions (build on these)

- Store = Postgres. Connection via config (a `DATABASE_URL`-style setting);
  docker, local, or cloud is just that value. Provisioning is not the app's job.
- The session store is the DURABLE, first-class asset, not a disposable
  projection. Schema evolution is forward migrations (Alembic). No
  drop-and-rebuild gate for this store.
- Transcript content is stored at event/record granularity: one CLI transcript
  record = one row, ordered by seq, append only.
- Per event store BOTH: the raw CLI record (JSONB, for fork fidelity and portable
  resume) AND the normalized IR (JSONB, for render, eval, FTS). Transcript raw is
  cheap (incremental) and fork critical, unlike wire raw.
- Artifacts captured BY VALUE (bytes copied in), keyed by content hash, so a
  shared or replayed session is self-contained and works cross machine. This is
  what makes codex images (written to `~/.codex.lilo/generated_images/...`)
  travel with the session.
- Live append: ingest commits an event, Postgres LISTEN/NOTIFY fires, the server
  pushes over SSE to pane 1. SSE for read-only chat append; WebSocket is reserved
  for the cockpit TUI, not this store.
- Reuse, do not reimplement: the existing transcript adapters (`normalize`), the
  live tailer, launch ownership (managed-mint / session-id ownership / per-run
  isolation / headless launch), and the tier-1 transcript snapshot. Swap the
  lossy-block write for a rich JSONB event write plus NOTIFY.
- Promote path: this store is first-class; the SQLite tier-2 block index, pivot,
  and diff RETIRE with the diff. Tier-1 raw capture files stay as a thin local
  forensic tier (keep) for the parked wire raw/transport and as a possible
  transcript fork source; the panel confirms the exact boundary.
- A session is a self-contained, portable unit served via an API even locally.

## The play's capabilities and what each needs

- Replay: read a session's event stream, render faithfully from the normalized IR.
- Fork: reconstruct a CLI-resumable session of events 1..N from the raw CLI
  records, then relaunch resuming via launch ownership. Needs the raw CLI record
  plus a fork pointer / lineage.
- Share: export a session as a self-contained bundle (events + by-value
  artifacts), importable elsewhere or uploadable to a hosted instance. Stable
  session ids; an `owner` column (trivial local user now, real account later).
- Eval: structured per-turn access (IR + JSONB queries). Schema must make
  "find turns where tool X was called with input Y" a query.
- Learn: Postgres `tsvector` FTS over event content for search and browse.

## Open questions for the panel

- Concrete schema: `session`, `event`, `artifact` tables; columns, types (JSONB),
  indexes (seq, FTS tsvector, JSONB GIN); the fork pointer / lineage
  (`parent_session_id` + fork-point seq?); `owner`, `status`, and the
  resumable-state pointer.
- Ingest write path: where it sits in the import DAG; how it consumes the tailer +
  adapter `normalize`; the transaction + NOTIFY seam; the idempotency/dedup key
  for events.
- Artifact storage: `bytea`-in-DB vs a content-addressed external store referenced
  by hash; the capture-by-value mechanics (read bytes at ingest from the tool
  record's path); dedup by hash.
- Fork mechanics: exactly how to reconstruct a CLI-resumable session from stored
  raw records for claude (and codex), the lineage model, and relaunch via launch
  ownership.
- Share/export: the self-contained bundle format, import, id stability, and the
  owner/identity stub.
- Migration: stand up the Postgres store + Alembic; what of tier-1/tier-2 retires
  (the SQLite block index, pivot, diff) vs stays (forensic raw); a backfill from
  existing tier-1 transcript snapshots into the new store.
- Async driver + pool (`asyncpg` or `psycopg3`); a default local DSN or dev
  `docker-compose`.
- Import-DAG placement + LOC budgets; the new package(s) (a `session/` package, or
  evolve `index/`); the privacy boundary.

## Verify, do not assume

- Does the transcript normalized IR round-trip well enough for faithful render.
- Does the stored CLI raw record suffice to reconstruct a resumable session for
  fork, for claude and for codex.

## Deliverable

`/Users/alphab/.mdx/projects/transport-matters-session-store/spec-session-store.md`
(author: backend-engineer/claude). Reviewer (backend-engineer/codex, gpt-5.5) does
one adversarial pass to `review-session-store.md` after the orchestrator signals
the draft is ready. The orchestrator integrates.

## Acceptance bar

Grounded and cited in the actual repo; DRY (reuse adapters/tailer/launch
ownership, no parallel impls); Postgres-idiomatic (JSONB, GIN, tsvector,
LISTEN/NOTIFY, Alembic); durable-store migration model (no drop-rebuild); hosting
ready (config-driven, `owner` column, portable export); wire exchanges left as a
clean future sibling, not designed; respects repo invariants (import DAG, LOC
<=700/file & fn <=~150, builtins-only typing, Pydantic v2, IR frozen, AST privacy
boundary). No em dashes.

## Comms protocol (anti-chatter)

No pane messages another. All replies go to the orchestrator only
(`transport-matters:general:1:2.1`). The bus carries one-line `done:`/`blocked:`
signals; all content lives in files. The author writes the spec; the reviewer does
ONE adversarial pass after the orchestrator signals the draft is ready. The
orchestrator integrates and is the only one who opens a round 2. Questions go in an
"Open questions for orchestrator" section in the file, with a working assumption.
