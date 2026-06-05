# Scout: "conversation 404"

Read-only scout on main `ade9c356`. No edits, no commits; working tree and HEAD identical before and after. No
captured runs, no Postgres queries against the owner's stores, no keychain, no `~/Library`, no channel homes. Evidence
is source reading only.

## Verdict

**Not a defect on current main. The 404 is deliberate and correct, and it has one genuinely reachable window that
reads as wrong to a user.** The backlog phrase most likely names that window, or one of four other states the surface
collapses into the same bare 404. The item's real content is a *presentation* problem, not a lookup problem.

It is **not** a consumer reaching for a retired surface. The conversation surface exists, is served, and is queried
against live Postgres; the retired index/block/diff/raw surfaces are not on this path, and the wire store is not
consulted.

## 1. Which endpoint returns it

Three hops, one origin:

| layer | symbol | behaviour |
|---|---|---|
| user surface | `api/v1/controlplane_routes.py::conversation` (`GET /v1/conversation/{run_id}`) and the MCP `conversation` verb | maps control-plane `not_found` → HTTP 404 via `_GENERAL_CONTROL_PLANE_ERROR_STATUS` |
| gateway route | `packages/activity/src/server/activityRouter.ts::registerConversationRoute` (`GET /workspaces/:workspaceId(.+)/runs/:runId/conversation`) | catches `ConversationNotFoundError` → `reply.code(404).send({ error: "not_found" })` |
| origin | `packages/activity/src/adapters/postgresConversation.ts::PostgresConversationReader.readConversation` | throws `ConversationNotFoundError` when `CONVERSATION_STREAM_SQL` returns zero rows |

Python reaches the gateway through `api/v1/controlplane_gateway_reads.py::read_conversation` +
`workspace_conversation_route_path`. Note that `read_conversation` has no 404 special case (unlike
`read_terminal_snapshot`, which maps 404 → `None`), so the 404 propagates as a `GatewayResponseError` and surfaces as
a 404 to the caller.

The sibling completed-turns route (`activityRouter.ts` line ~249, thrown by
`packages/activity/src/service/completedTurns.ts::DurableCompletedTurnReader.readCompletedTurns`) has the same 404 but
reaches it differently — see section 3.

The inspector has **no** conversation consumer (no match for `conversation` under `www/packages/inspector/src`), so
this is a control-plane/MCP surface only. Nothing in the canvas reads it either.

## 2. The precondition

`CONVERSATION_STREAM_SQL` is `FROM session LEFT JOIN transcript_event`, so the row count is governed entirely by the
**session** side. Zero rows means no `session` row satisfying **all five** predicates:

1. `session.run_id = $1`
2. `session.owner = $2`
3. `session.workspace_slug = $3`
4. `session.workspace_hash = $4`  (both parts from `packages/activity/src/ids.ts::workspaceIdParts`, splitting the
   `slug/hash` workspace id on its last `/`)
5. `primaryTranscriptSql.ts::PRIMARY_SESSION_FILTER` — the session has no parent inside the same run

Because it is a LEFT JOIN, **a run with a session but no messages returns 200 with an empty list**, not a 404. So the
precondition is never "no conversation yet"; it is always "no session row for this exact tuple". Five distinct states
produce it:

- **A: the session row does not exist yet.** `session` rows are written by `SessionWriter`
  (`session/session_statements.py` `INSERT INTO "session"`), driven from the transcript tailer and backfill paths, not
  at launch. Between run start and the first transcript ingest, a run that is live in the roster has no session row.
- **B: owner mismatch.** A run belonging to another owner.
- **C: workspace-identity mismatch.** The run's session was written under a different `slug/hash` than the read
  supplies.
- **D: channel mismatch.** Each channel owns a separate database (`transport_matters`,
  `transport_matters_preview`, `transport_matters_dev`), so a run captured on one channel and read from another finds
  no row at all. This is the brief's "written by one channel and read by another" and it remains open.
- **E: the run genuinely never existed, or its rows were removed** (`just reset` drops and recreates the channel
  database).

Predicate 5 cannot cause a false 404: every in-run parent chain has a root, so at least one session always survives
the filter.

## 3. Absence or defect

**Absence, and deliberately so.** Two tests pin the design:

- `packages/activity/src/adapters/postgresConversation.test.ts::"distinguishes an inaccessible run from an empty
  conversation"` — a session row with no events resolves to `{ items: [] }`; only the no-row case throws. The
  separation between "empty" and "absent" is the stated contract, and it holds.
- `packages/activity/src/pgConversationIntegration.test.ts::"revalidates owner and workspace on every durable read"` —
  a foreign owner and a foreign workspace each raise `ConversationNotFoundError` by design. Returning 404 rather than
  403 there is the right call: a foreign owner must not learn the run exists.

So states B, C and E are correct behaviour. State D is correct behaviour with a confusing cause. **State A is the one
that reads as a defect**: the run is real, visible in the roster, and the user is told it was not found.

The two sibling readers disagree on exactly this point, which is the sharpest evidence that A is unintended.
`DurableCompletedTurnReader.readCompletedTurns` first calls `store.runsForWorkspace(workspaceId, owner)` and throws
only when the run is genuinely absent from that owner's workspace; a known run with no data returns `[]`. The
conversation reader has no equivalent existence check and infers absence from the data query alone.

## 4. What the user sees

A bare 404. The gateway sends `{ error: "not_found" }` and **discards** the reader's message
(`run ${request.runId} was not found`), which is never serialised. Python then maps the control-plane `not_found` code
to HTTP 404 with no added reason.

So the surface cannot distinguish "never existed" from "not yours", "wrong workspace", "wrong channel", or "exists but
has not been tailed yet" — five causes, one indistinguishable response, and the two that most deserve different
handling (A and D) look identical to the one that is genuinely terminal (E). That is the substance of the backlog
item.

## 5. Whether recent work changed it

**No.** None of #341, #344, #345 or #348 touches the conversation reader, the activity router, or session identity
derivation:

- #341 — `session/testing.py` and its test only (test support).
- #344 — `session_store_preflight.py` only.
- #345 — control-plane launch identity; nothing under `packages/activity` or `session/`.
- #348 — no session, workspace or activity files.

`git log` on `postgresConversation.ts` shows its last two changes were #290 and #287; nothing since. So this behaviour
has been stable for weeks, which is consistent with a phrase carried for weeks. #344 is *adjacent* rather than causal:
it changes how a channel's configuration materialises, and channel choice is what selects the database in state D, but
it did not create or close the 404.

## The smallest thing that would resolve it

Give the conversation reader the same run-existence check the completed-turns reader already performs, so that a known
run with no session yet returns an empty conversation instead of 404, and so that a true 404 keeps its current
meaning. Everything else (states B, C, E) then keeps behaving exactly as it does now. A second, independent
improvement is to stop discarding `ConversationNotFoundError`'s message at the gateway boundary so the caller learns
which absence it hit; state D in particular is unrecoverable for a user who cannot see that they are reading the wrong
channel's database.

## What would falsify this

My conclusion is that the reproducible complaint is state A (or D), reached before the tailer has written a session
row. It would be falsified if the owner's original 404 occurred on a run whose transcript had already been ingested —
that would make it state C, a workspace-identity mismatch, which is a genuine lookup defect and needs the opposite
fix.

The single query that decides it is: for the offending `run_id`, select `owner`, `workspace_slug`, `workspace_hash`,
`parent_session_id` from `session` in the channel database the read was issued against, and compare them to the
`owner` and `workspaceId` the control-plane read sent. If a row exists with different slug/hash → state C, defect. If
no row exists but the run is in the roster → state A, timing. If the row exists and matches → my reading of the SQL is
wrong.

I did not run it: the owner's Postgres stores are out of scope for this pass. It needs one read-only query against a
throwaway or explicitly authorised store, or the owner running it himself.

## Checked and ruled out

- **Retired surfaces.** No path in the conversation read touches the retired index, block store, diff projection or
  raw fetch surface, and the wire store (populated, no read surface) is not consulted. The reframing the brief
  anticipated does not apply here.
- **The inspector.** No conversation or exchange view consumes this endpoint.
- **Tier-1 run reads.** `api/v1/run_storage.py::resolve_run_storage_or_404` also raises 404
  (`{"code": "run_not_found", "message": "Run {run_id} not found"}`) for `exchanges.py` reads when a run directory is
  absent — the reset-swept case the brief names. That one is a true absence and, unlike the conversation route, it
  carries a code and a message. It is a separate surface from "conversation" and did not look like the item.
- **Route-shape mismatch.** `:workspaceId(.+)` accepts the slug/hash pair Python sends via
  `quote(workspace_id, safe="")`; no encoding mismatch is involved.
