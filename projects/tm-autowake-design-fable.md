# B1 durable auto wake: token carried causal binding

Design for the durable delivery to turn causal binding, written against pristine
`controlplane-autowake` at `e05373b6a4f5`, grounded in the scout map
`~/.mdx/projects/tm-autowake-scout.md`. All cited symbols were verified in the
working tree before writing.

## Design in one paragraph

Every control plane delivery mints a durable identity row before any PTY write
and embeds its full identity as a machine marker inside the delivered envelope
text. The marker travels the same physical path as the input itself: PTY bytes,
harness user message, outbound provider request. The binding is then written by
the capture plane, inside the same Postgres transaction that persists the
finalized wire exchange, by scanning only the fresh input suffix of the request
for markers. Causality is therefore proven by content that physically traversed
the boundary, and recorded at the single durable commit point the system
already trusts as the end of turn authority. No consumer ever mutates the
binding; wake and suppression decisions are pure reads of durable rows, so
notification order, SSE order, replay, and restart cannot change any decision.

## Why this anchor

The scout's requirement 3 forbids binding to the next observed completion. The
only artifact that deterministically relates a delivery to the exact provider
request it caused is the request content, because the delivered envelope
appears as fresh trailing input in exactly one request: the first request of
the induced turn. Every later request of the session replays that text behind a
subsequent assistant message, so a fresh suffix rule makes the relation
structurally exact rather than probabilistically ordered. The rejected
`CausalAncestryLedger` failed because it correlated callbacks; this design
correlates bytes.

## Schema

One additive Alembic migration in the existing chain
(`api/src/transport_matters/session/migrate.py` machinery), no changes to
`wire_exchange`.

```
control_plane_delivery
  delivery_id        uuid primary key          -- minted before any side effect
  dispatch_id        uuid not null             -- joins control_plane_action
  owner              text not null
  workspace_id       text not null
  target_run_id      text not null
  source_kind        text not null check in ('prompt','launch','watch','wake')
  source_run_id      text                      -- director/watcher run; null for launch
  ancestry           jsonb not null default '[]'  -- run ids this delivery is causally downstream of
  envelope_text      text not null
  pty_outcome        text not null default 'pending'
                     check in ('pending','delivered','rejected','unknown')
  wake               text not null default 'none'
                     check in ('none','due_on_bind','due','delivering','delivered','ambiguous','target_gone','expired')
  bound_exchange_id  text                      -- set only inside the wire commit transaction
  bound_at           timestamptz
  created_at         timestamptz not null default now()
  expired_at         timestamptz               -- GC bookkeeping, never a correctness input

indexes:
  (target_run_id) partial WHERE bound_exchange_id IS NULL AND expired_at IS NULL   -- binding update
  (bound_exchange_id)                                                             -- wake + suppression reads
  (wake) partial WHERE wake IN ('due','delivering')                               -- wake dispatch
```

The marker token is the delivery id itself; no separate token column. Binding
state is the pair (`bound_exchange_id`, `expired_at`): unbound, bound, or
expired. PTY outcome is deliberately orthogonal to binding (requirement 9): an
`unknown` HTTP outcome still binds if the bytes arrived, because the wire is
the truth of arrival, and a `rejected` outcome is excluded from binding.

## Envelope marker

`api/src/transport_matters/controlplane/envelope.py` grows one marker seam
shared by all envelope formatters:

- Marker format: ` ⟦tm:d:<32 hex delivery_id>⟧` appended to the envelope, with
  a single module owned regex constant for extraction. Cost is ~40 of the
  4,096 UTF-16 unit budget (`MAX_CONTROL_PLANE_INPUT_UTF16_UNITS`); the
  formatter reserves marker units before truncating body text, mirroring the
  existing prefix accounting in `format_prompt_envelope`.
- `format_prompt_envelope` keeps the human 8 hex dispatch prefix and gains the
  per delivery marker. Because the marker is per target, the envelope is now
  formatted per target rather than once per dispatch;
  `ControlPlaneService.prompt` moves envelope formatting into
  `_deliver_prompt_target` with the shared base text validated once up front.
- `format_watch_envelope` gains the same marker (successful watch nudges are
  currently identityless; this closes that gap).
- New `format_wake_envelope` for the reciprocal wake text, same marker seam.

`_terminal_safe_text` preserves the marker as is; it strips only control and
format categories.

## Delivery creation seams

A new `api/src/transport_matters/controlplane/delivery_store.py:ControlPlaneDeliveryStore`
(sibling of `ControlPlaneAuditWriter`, statements in
`api/src/transport_matters/session/controlplane_statements.py`) owns the row
writes: `create`, `record_pty_outcome`, `claim_wake`, `resolve_wake`,
`sweep_expired`.

1. **Prompt.** `ControlPlaneService.prompt` inserts one delivery row per
   visible target, wake `due_on_bind`, ancestry `[principal.run_id]`, before
   the `gateway.deliver_input` fan out in `_deliver_prompt_target`. The PTY
   outcome is recorded after the call returns. `PromptReceipt` gains
   `delivery_id` so `_audit_prompt` and callers can join audit to binding.
2. **Launch first prompt.** `ControlPlaneLauncher._prepare` mints the delivery
   row; `launch_delivery.deliver_first_prompt` sends the marked envelope and
   records the outcome. This finally gives the launch ledger the durable turn
   relation the S6a review noted it lacks.
3. **Watch nudge.** `ControlPlaneWatchEngine._flush_serialized` inserts one
   delivery row (wake `none`, source_kind `watch`) before calling
   `deliver_input`, with ancestry computed from the flushed facts (below).
4. **Wake.** The wake dispatcher (below) inserts a delivery row (wake `none`,
   source_kind `wake`) whose ancestry is the bound delivery's ancestry plus the
   completed run. Wake deliveries never arm wakes; that is what makes A wakes
   B wakes A structurally impossible.

Insertion is a durable write on the request path for prompt and launch. That is
the price of requirement 1 (identity before side effects) and it reuses the
same pool the audit writer already draws from.

## The binding rule

New pure module `api/src/transport_matters/session/delivery_binding.py`
(session may import `ir`):

- `fresh_input_texts(request: InternalRequest) -> tuple[str, ...]`: the text
  blocks of the contiguous trailing run of `role == "user"` messages after the
  last assistant message. Tool result only continuations yield nothing. Codex
  incremental request payloads (later turns carry deltas) reduce to the same
  rule: the fresh suffix is the new input.
- `extract_delivery_ids(texts) -> tuple[UUID, ...]` via the envelope marker
  regex.
- `bind_deliveries(conn, write: WireExchangeWrite) -> None`: skipped when
  `write.track_role == WIRE_TRACK_ROLE_SUBAGENT` (mirrors
  `GET_COMPLETED_WIRE_TURN_FOR_OWNER_SQL`), otherwise:

```sql
UPDATE control_plane_delivery
SET bound_exchange_id = %(exchange_id)s, bound_at = now(),
    wake = CASE WHEN wake = 'due_on_bind' THEN 'due' ELSE wake END
WHERE delivery_id = ANY(%(ids)s)
  AND target_run_id = %(run_id)s
  AND pty_outcome <> 'rejected'
  AND expired_at IS NULL
  AND (bound_exchange_id IS NULL OR bound_exchange_id = %(exchange_id)s)
```

`SessionWriter.submit_wire_exchange` calls `bind_deliveries` inside its
existing `commit()` closure, after `write_wire_exchange` and before
`_notify`. The binding therefore commits atomically with the exchange row and
is covered by the same commit watermark discipline, so
`completed_wire_turns_since` catch up always observes exchange and binding
together. Replay of a re fired finalize converges by the
`bound_exchange_id = exchange` arm. `write_wire_exchange` itself is untouched;
the wire store stays free of control plane concepts.

Multiple deliveries queued into one turn: all their markers sit in the fresh
suffix, all bind to the same exchange, each armed wake fires once.
Deterministic per requirement 3.

## Wake: exactly once on caused turn completion

Wake dispatch lives where completion consumption already lives:
`ControlPlaneWatchEngine._consume_wire_exchange` and `_catch_up_wire`. After
the existing durable reread (`completed_wire_turn`) and `remember_exchange`
dedupe, the engine also calls a new
`ControlPlaneReadStore.bound_deliveries_for_exchange(principal, exchange_id)`.
For each row with `wake = 'due'`:

1. `claim_wake`: `UPDATE ... SET wake='delivering' WHERE delivery_id=%s AND
   wake='due' RETURNING delivery_id`. The one way durable transition is the
   exactly once gate; a second consumer, a replayed doorbell, or a post
   restart catch up claims nothing.
2. Deliver `format_wake_envelope` to `source_run_id` through the same
   `gateway.deliver_input` nudge primitive, registered as its own delivery row
   (source_kind `wake`).
3. `resolve_wake`: definite success `delivered`; definite gateway connection
   failure restores `due` (retry on a later doorbell or catch up); rejected or
   unknown becomes `ambiguous` and is never retried, mirroring the watch
   engine's existing drop on ambiguous rule so one wake can never become two
   PTY inputs; source run no longer live becomes `target_gone`.

Semantics stated honestly: the binding and the wake decision are exactly once;
the PTY send is at most once per claim. That is the strongest guarantee a
non transactional terminal allows, and it is the same posture the watch
delivery path already takes.

## Suppression and the ping pong invariant

Ancestry of an exchange E is the union, over deliveries bound to E, of
`delivery.ancestry ∪ {delivery.source_run_id}`. A human turn has no bound
delivery, hence empty ancestry, hence is never suppressed (requirement 6).

The invariant that terminates every loop: **every control plane injected input
carries durable ancestry, every induced turn inherits it through the binding,
and no watcher in a turn's ancestry is ever re notified of that turn.** Under
A watches B and B watches A: a nudge to B about A's turn carries ancestry
{A}; B's induced turn binds it; its completion is suppressed toward A. The
reciprocal wake to A carries ancestry {A, B}; a turn it induces is suppressed
toward B. Ancestry saturates at the participant set, so any cycle revisits a
member within one lap and dies there.

Mechanically, both WATCH sources consult the same durable rows, read only
(requirement 7), at flush time in `_flush_serialized`:

- `turn_completed`: `WatchFact` gains `origin_exchange_id`
  (`watch_models.py`), populated by `_record_completed_turn` from the
  `CompletedWireTurn` already in hand in `_consume_wire_exchange`. Suppression
  is exact: drop the fact for watcher W when W is in ancestry(origin).
- `state_changed` and `needs_you` carry no exchange identity (Activity SSE
  never will), so attribution uses Activity's own end of turn oracle: a new
  `ControlPlaneReadStore.latest_bound_completion_for_run(principal, run_id)`
  resolves the target run's latest completed non subagent exchange and its
  ancestry at flush time. Drop the fact for W when W is in that ancestry.
  `needs_you` keeps its existing contract and is consulted the same way only
  because a caused turn's needs_you toward its own causer is the same loop
  edge; unrelated watchers still see it.

The `state_changed` attribution is approximate in one bounded way: transient
deltas of a new human turn, occurring after a caused completion and before the
human turn's own completion, can be dropped toward the causer. That can only
lose an intermediate notification; it can never create a loop, and the human
turn's `turn_completed` is exact and always delivered. The converse race (a
delta consulted before its exchange binding commits) is bounded by the flush
damping interval and by Activity deriving idle from the wire snapshot after
commit; even a fact that slips through produces a nudge that itself carries
ancestry, so the invariant, not the read timing, is what guarantees
termination.

Because suppression and wake are pure functions of committed rows, both legal
orderings of wire doorbell and Activity SSE, duplicate doorbells, queue
overflow, and catch up replay all reach identical decisions. This is the
precise property the deleted ledger lacked.

## Failure, GC, and restart semantics

- **Delivery that never produces a turn.** Row stays unbound. A sweep
  (`sweep_expired`, invoked from the existing `db` maintenance surface like
  `sweep_wire_store`) sets `expired_at` after a generous TTL (24h) or once the
  target run is terminal. Expiry excludes the row from future binding, which
  also closes the residual compaction risk (a later request quoting an old
  marker inside fresh looking input). Armed wakes resolve `expired`; nothing
  fires. TTL is bookkeeping that narrows binding eligibility; no correctness
  decision reads the clock.
- **HTTP receipt lost.** `pty_outcome='unknown'`, binding still proves or
  disproves arrival. No guessing.
- **API restart.** Delivery, binding, and wake state are rows; nothing lives
  only in process memory. Runs and watchers are process resident and die with
  the API (existing product semantics), so convergence after restart means: no
  duplicate wake is possible (`claim_wake` is durable), stale `delivering`
  rows and `due` rows for dead runs resolve `target_gone` via the sweep, and
  the full causal history remains queryable. Deliveries unbound at crash bind
  correctly if their exchange finalizes after restart, since binding rides the
  wire commit, not a consumer.
- **Parse failure gap (stated dependency).** Binding scans the request side,
  so it lands even when the response IR is absent. But `wake` release and
  `turn_completed` both flow through the `response_id IS NOT NULL` completion
  reads, so a raw complete but unparseable response leaves a bound delivery
  with a `due` wake that never fires until the NOW.md wire store integrity
  slice widens the completion authority. B1 inherits that gap; it does not
  widen it, and no false wake can result. When the integrity slice lands, the
  already durable binding releases through the ordinary catch up path.

## Files touched

- `api/src/transport_matters/controlplane/envelope.py`:
  `format_prompt_envelope`, `format_watch_envelope`, new `format_wake_envelope`,
  marker constant and regex.
- `api/src/transport_matters/controlplane/service.py`:
  `ControlPlaneService.prompt`, `_deliver_prompt_target`, `_audit_prompt`.
- `api/src/transport_matters/controlplane/prompt_models.py`: `PromptReceipt`
  (+`delivery_id`).
- `api/src/transport_matters/controlplane/launch_service.py`:
  `ControlPlaneLauncher._prepare`, `_execute`;
  `launch_delivery.py:deliver_first_prompt`.
- `api/src/transport_matters/controlplane/watch.py`:
  `_consume_wire_exchange`, `_catch_up_wire` (wake dispatch),
  `_record_completed_turn` (fact origin), `_flush_serialized` (suppression,
  delivery row, ancestry).
- `api/src/transport_matters/controlplane/watch_models.py`: `WatchFact`
  (+`origin_exchange_id`).
- New `api/src/transport_matters/controlplane/delivery_store.py`.
- `api/src/transport_matters/controlplane/read_store.py`:
  `ControlPlaneWatchReadPort` and `ControlPlaneReadStore`
  (+`bound_deliveries_for_exchange`, +`latest_bound_completion_for_run`).
- `api/src/transport_matters/session/controlplane_statements.py`: delivery SQL.
- New `api/src/transport_matters/session/delivery_binding.py`:
  `fresh_input_texts`, `extract_delivery_ids`, `bind_deliveries`.
- `api/src/transport_matters/session/writer.py`:
  `SessionWriter.submit_wire_exchange` commit closure.
- One Alembic migration (existing `session/migrate.py` chain).

Import DAG stays clean: `delivery_binding` sits in `session` and imports only
`ir`; the wire store module remains control plane free; `controlplane` already
imports `session` read helpers.

## Verification plan (requirement 10)

Integration, through a real runtime PTY and the capture path, plus the
existing fake gateway for ordering control:

1. Prompt to a live run: marker appears as fresh suffix in the captured
   request; delivery binds to the first exchange; the next exchange of the
   same session, whose history replays the marker, does not rebind.
2. Duplicate finalize replay of the same exchange: binding and wake state
   converge, wake fires exactly once.
3. Mutual watch A and B seeded by one human turn: exactly one reciprocal
   notification chain, terminating within one lap, under both orders of wire
   doorbell versus Activity delta (fake gateway sequences them both ways).
4. Lost gateway receipt (`unknown`): binding still lands; wake fires once.
5. Delivery that never produces a turn: sweep expires it; no wake.
6. Two deliveries queued into one turn: both bind to one exchange; both wakes
   fire once each.
7. Restart between wire commit and wake claim: after restart, catch up either
   claims and fires once or resolves `target_gone`; never twice.
8. Codex fixture: fresh suffix extraction against a real incremental request
   capture; Claude fixture likewise.
9. Interleaved human input during a caused turn: the following human turn is
   unbound and never suppressed.

## Risks

1. **Harness request shape assumptions (biggest risk).** Exactness rests on
   the delivered envelope surfacing verbatim as trailing user input in exactly
   the first induced request, per harness. Compaction, input rewriting, or a
   harness that reorders or merges queued input could blur the fresh suffix
   rule. Mitigations: full entropy markers, unbound only binding, expiry, and
   fixture tests per harness; residual risk is a missed binding (no wake,
   honest `expired` state), never a false loop.
2. **Request path durable insert.** Prompt latency now includes one Postgres
   insert before fan out. Acceptable: the audit writer already pays this class
   of cost, and identity before side effects is non negotiable.
3. **`state_changed` attribution window.** Documented above; bounded to lost
   intermediate notifications, with `turn_completed` exact.
