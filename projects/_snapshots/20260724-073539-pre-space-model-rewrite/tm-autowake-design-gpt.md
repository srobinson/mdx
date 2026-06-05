# B1 durable reciprocal wake design

Status: design for `controlplane-autowake` at
`e05373b6a4f5a101f1f4da95d499682e6bc8ee11`.

## Decision

Carry a full delivery UUID through the terminal input and bind that UUID when
capture persists the outbound provider request. The provisional exchange
generation is the request identity. Final wire persistence resolves the same
generation to the durable `wire_exchange.exchange_id` in one Postgres
transaction.

Every delivery and every turn has durable causal ancestry. A direct prompt or
launch prompt creates one reciprocal wake obligation for its source run. A
watch or reciprocal wake delivery creates no further reciprocal obligation.
Explicit watch delivery is suppressed when the recipient already appears in
the caused turn's ancestry. This rule applies to Activity and wire events by
their shared request generation.

No callback order, latest run state, counter, or process lifetime map decides
causality.

## Required invariants

1. A delivery UUID exists in Postgres before any PTY write.
2. The exact terminal text contains the full UUID. The existing eight
   character dispatch token remains display metadata only.
3. One delivery binds to at most one request generation. One generation may
   bind any number of deliveries found in that request.
4. One request generation resolves to at most one finalized exchange.
5. The final wire transaction can reconstruct the binding from request IR if
   provisional request observation was delayed or lost.
6. A source run receives at most one reciprocal wake for one caused
   generation, even when several of its deliveries appear in that request.
7. A watcher in a turn's transitive ancestry receives no explicit watch event
   for that turn. The direct source still receives its single stored
   reciprocal obligation.
8. Activity classification and `turn_completed` classification use the same
   generation and ancestry rows.
9. Retry uses the same outbound delivery UUID. The live runtime accepts that
   UUID once for the lifetime of the target run.
10. Time bounds affect retry and storage compaction only. They never choose
    which turn a delivery caused.

## Durable model

Add migration `api/migrations/versions/0017_control_plane_turn_causality.py`
after `0016_action_dispatch_idempotency`.

### `control_plane_delivery`

One row represents one target and one attempted terminal submission.

| Column | Meaning |
| --- | --- |
| `delivery_id uuid primary key` | Stable idempotency and marker identity |
| `dispatch_id uuid null` | Existing action identity, shared by fanout targets |
| `owner text not null` | Owner boundary |
| `workspace_id text not null` | Workspace boundary |
| `source_run_id text not null` | Run that requested or caused the delivery |
| `source_generation text null` | Exact source turn when the action arose inside a turn |
| `target_run_id text not null` | PTY target |
| `kind text not null` | `prompt`, `launch_prompt`, `watch`, or `reciprocal` |
| `mode text not null` | `nudge` or `interrupt` |
| `envelope_sha256 text not null` | Audit and marker validation without duplicating text |
| `creates_reciprocal boolean not null` | True only for direct and launch prompts |
| `executor_outcome text not null` | `prepared`, `accepted`, `unknown`, or `rejected` |
| `executor_reason text null` | Stable failure classification |
| `created_at`, `accepted_at`, `terminal_at` | Lifecycle timestamps |
| `terminal_reason text null` | `no_turn`, `target_gone`, `rejected`, or `expired_after_run` |

Checks enforce nonempty identity fields and the allowed vocabularies. Index
`(owner, workspace_id, target_run_id, terminal_at)` supports pending work.
Index `(source_run_id, created_at)` supports audit. A unique partial index on
`(dispatch_id, target_run_id)` where `dispatch_id is not null` makes action
replay converge.

### `wire_request_anchor`

This table makes the provisional generation a durable request identity.

| Column | Meaning |
| --- | --- |
| `generation text primary key` | Existing provisional exchange id |
| `owner`, `workspace_id`, `run_id` | Capture scope |
| `provider text not null` | Adapter evidence |
| `observed_at timestamptz not null` | Request persistence time |
| `exchange_id text unique null` | Final `wire_exchange` identity |
| `finalized_at timestamptz null` | Same commit as final wire row |
| `retracted_at timestamptz null` | Provisional repair or explicit deletion |

`exchange_id` references `wire_exchange(exchange_id)` with `ON DELETE SET
NULL`. Deleting wire content cannot erase the causal audit. Add
`request_generation text not null` to `wire_exchange`, backfill it from
`exchange_id`, then add a unique constraint. Current
`WireExchangeWrite.generation` already supplies the value.

### `control_plane_turn_delivery`

This is the exact many deliveries to one request relation.

| Column | Meaning |
| --- | --- |
| `delivery_id uuid primary key` | One delivery binds once |
| `generation text not null` | Request containing the full marker |
| `bound_at timestamptz not null` | Request observation time |

Foreign keys reference `control_plane_delivery` and `wire_request_anchor`.
Binding validates owner, workspace, and target run in the transaction. A
marker from another target is rejected and counted as an integrity error.

### `control_plane_turn_ancestor`

Materialize the transitive run closure for stable, cheap watch decisions.

| Column | Meaning |
| --- | --- |
| `generation text not null` | Caused request |
| `ancestor_run_id text not null` | Run already in the causal path |

The primary key is `(generation, ancestor_run_id)`. When delivery `D` binds to
generation `G`, insert `D.source_run_id` and copy every ancestor of
`D.source_generation` into `G`. Multiple bound deliveries take the set union.
This transaction is idempotent.

`ControlPlaneService.prompt` resolves `source_generation` from the source
run's current `wire_request_anchor`. The MCP skin resolves this context when
the call enters the API. Capture creates the anchor when the provider request
starts, before its response can invoke a control plane tool. A harness has at
most one provider generation able to execute tools at a time, so the open
generation or its just finalized successor is exact. The resolver fails closed
if the store exposes more than one candidate. Human REST actions carry no
source generation and become causal roots. Watch facts always carry their
explicit source generation.

### `control_plane_watch_subscription`

The present `Watcher.targets` map is process resident. Persist its current
materialized value so restart can resume the same obligation.

The primary key is `(owner, workspace_id, watcher_run_id, target)`. Store the
normalized event array and `updated_at`. `watch` upserts this row before
returning `subscribed`. `unwatch` deletes it. The action table remains the
history. Startup loads subscriptions, then starts the existing shared feeds.

### `control_plane_wake_outbox`

| Column | Meaning |
| --- | --- |
| `wake_id uuid primary key` | Outbox identity |
| `recipient_run_id text not null` | PTY target |
| `source_generation text not null` | Turn that generated the fact |
| `source_exchange_id text null` | Filled on finalization |
| `event_kind text not null` | `reciprocal`, `turn_completed`, `state_changed`, or `needs_you` |
| `event_key text not null` | Replay stable source event identity |
| `facts jsonb not null` | Immutable rendered input source |
| `delivery_id uuid unique not null` | Outbound idempotent delivery |
| `state text not null` | `pending`, `accepted`, or `terminal` |
| `attempts`, `next_attempt_at`, `accepted_at`, `terminal_reason` | Worker state |

Use unique `(recipient_run_id, event_key)`. Completion uses
`turn:{generation}:complete`, so a reciprocal obligation and an explicit
`turn_completed` subscription for the same recipient converge to one row.
Activity transitions use their durable Activity source key, so separate state
changes within one turn remain distinct and replay idempotent. Activity facts
in the source ancestry are suppressed before insertion, so a source watching
`state_changed` cannot wake early and then wake again at completion.

Claim rows with `FOR UPDATE SKIP LOCKED`. Render their immutable fact set with
the preallocated `delivery_id`, create the corresponding
`control_plane_delivery(kind='watch' or 'reciprocal')`, and call the gateway.
The outbox row reaches `accepted` only after an accepted or duplicate accepted
runtime result. Unknown outcomes remain retryable with the same delivery UUID.

## Marker and request binding

Add `api/src/transport_matters/controlplane/delivery_marker.py` as the single
owner of marker format and parsing. Use an ASCII prefix that survives terminal
input, provider adaptation, transcript storage, and bracketed paste:

```text
[tm delivery 018f3b77-8ab9-7e8d-a18c-2e7b596f22cb]
```

`controlplane/envelope.py:format_prompt_envelope` and
`format_watch_envelope` accept a `delivery_id` and place the full marker before
human text. The marker budget is reserved before truncating user text. Prompt
fanout gets one delivery UUID per target. Launch first prompt and every watch
flush follow the same path.

The parser inspects text blocks in `InternalRequest.messages` and returns full
UUIDs. Database validation supplies authenticity: the UUID must name a
prepared or accepted delivery with the same owner, workspace, and target run.
The first valid request wins through the primary key on
`control_plane_turn_delivery`. Full history replay may expose the marker on
later Claude requests; those observations become harmless conflicts. Codex
incremental requests follow the same first binding rule.

Extend `storage/exchange_sink.py` with a distinct request observed sink. Keep
the completed exchange contract unchanged. Call the request sink after Tier 1
provisional persistence in:

* `exchange_recorder.py:persist_http_provisional_exchange`
* `codex/exchange.py:persist_codex_provisional_exchange`
* the nonprovisional branches before their completed exchange emission

`wire_store_observer.py:WireStoreObserver` registers this sink and schedules
`SessionWriter.submit_wire_request_anchor`. The writer inserts the anchor,
validates markers, binds deliveries, and materializes ancestry in one
transaction. It emits one identity only `tm_events` doorbell for the run.

`SessionWriter.submit_wire_exchange` repeats the same pure marker extraction
from `WireExchangeWrite.request`. Inside its existing transaction it:

1. writes `wire_exchange` with `request_generation`;
2. upserts and finalizes `wire_request_anchor`;
3. inserts any missing delivery bindings and ancestry;
4. creates reciprocal outbox rows for completed parent turns;
5. closes live status and emits the existing wire doorbell.

This repair path handles request notification loss, API restart between
request and response, and finalization arriving before the provisional DB
write. A late provisional write sees the sealed anchor and converges.

## One cause for Activity and wire watch paths

Add a request anchor read to
`packages/activity/src/adapters/postgresRecords.ts:PostgresActivityReader` and
its port in `packages/activity/src/ports.ts`. The Activity reconcile loop reads
the current anchor after transcript records and before
`reconcileWireSnapshot`.

Extend `RunActivityContext` with:

* `turnCauseGeneration: string | null`
* `turnCauseResolved: boolean`
* `statusEventKey: string`

A transcript `turn-open` sets unresolved cause. A durable request anchor sets
the generation and resolves it without changing status. Lifecycle only states
resolve as a root. Live status already supplies generation. Final wire state
maps `wireAssertedExchangeId` back to `wire_exchange.request_generation`.
Retain the cause until the next `turn-open`.

Every state changing domain event sets `statusEventKey` from durable source
identity: lifecycle sequence, transcript session and sequence, live generation
and sequence, or final exchange id. Expose `cause_generation`,
`cause_resolved`, and `status_event_key` through:

* `projections/workspaceActivity.ts:RunActivityProjection`
* `server/activityRouter.ts:runToWire`
* the `@tm/contract/activity` wire type
* `controlplane/activity.py:GatewayActivityRun`

Include all three fields in `sameRunActivityProjection`. A transcript status may
arrive before request capture. Its unresolved delta is held. Anchor
reconciliation emits a second projection for the same status with the durable
generation, at which point the watch engine decides. A root turn has a
resolved generation with an empty ancestor set and remains visible.

Change `ControlPlaneWatchEngine._record_activity_delta` and
`_record_completed_turn` to create stable event keys and insert outbox rows
through a shared `ControlPlaneWakeDecider`. The decider loads ancestry by
generation. It suppresses an explicit watch when the watcher is an ancestor.
It creates the direct reciprocal row at finalized completion. Notification
order now affects latency only.

`needs_you` keeps its current independent visibility contract. If product
policy requires an ancestor to receive `needs_you`, insert that event despite
ancestry. Its outbound delivery still has `creates_reciprocal=false`, so it
cannot start a causal loop.

## Ping pong proof

Assume A directly prompts B with delivery `D1`.

1. `D1` binds to B generation `GB`. Ancestors of `GB` contain A.
2. Activity events from `GB` cannot produce explicit watch input to A because
   A is an ancestor.
3. Finalization of `GB` creates one reciprocal outbox row keyed by
   `(A, turn:GB:complete)`, regardless of duplicate finalization, several A to B
   deliveries, or A's explicit `turn_completed` watch.
4. That wake is delivery `D2` with `creates_reciprocal=false` and source
   generation `GB`.
5. `D2` binds to A generation `GA`. Ancestors of `GA` contain B and every
   ancestor of `GB`, including A.
6. B's reciprocal explicit watch sees B in `GA` ancestry and is suppressed.
   `D2` creates no reciprocal obligation.

The chain terminates. The same proof holds for longer causal paths because
ancestry is a transitive set union. Unrelated human turns have empty ancestry
and retain normal watch behavior.

## Acceptance and retry

Extend these contracts with `deliveryId`:

* `controlplane/activity.py:PromptDeliveryPort.deliver_input`
* `api/v1/run_proxy.py:RunRouteProxy.deliver_input`
* `runtimeRouter.ts:InputRunBody`
* `RunManager.ts:RunManager.deliverInput`
* `RunInputDelivery.ts:DeliverInputRequest`

Each live `RunManager` run owns an accepted delivery UUID set. The input queue
checks the UUID before `PtySession.tryWrite`. A repeated UUID returns
`{status: "delivered", duplicate: true}` without another PTY write. Record the
UUID immediately after accepted `tryWrite` and retain it until the run ends.
This state shares the run's process lifetime. If that process dies, its PTY and
run die with it, so the durable outbox terminates as `target_gone` after
restart. API response loss is safe because a retry reaches the same live run
and UUID.

The durable delivery row records observed executor outcomes. Capture evidence
has precedence over an `unknown` HTTP outcome. A bound request proves that the
input reached the harness even when the gateway response vanished.

## Completion integrity prerequisite

Current completion queries require `wire_exchange.response_id is not null`.
`WireStoreObserver.on_exchange` can receive raw response bytes with
`response_ir=None` after a parse failure. B1 must first add explicit raw wire
completion evidence.

Add `response_complete boolean not null default false` and
`response_parse_error text null` to `wire_exchange`, with a corresponding
`ExchangeArtifacts` and `WireExchangeWrite` field set by the recorder's actual
stream terminal path. `completed_wire_turn` queries use `response_complete`.
A partial or aborted stream remains false. A complete response with failed IR
parsing becomes a completed turn with limited response projection and still
releases its reciprocal wake.

## Failure semantics

| Failure | Durable result |
| --- | --- |
| Delivery intent insert fails | No gateway call |
| Gateway rejects before PTY write | `rejected`; no binding and no retry |
| Gateway response is lost | `unknown`; retry same UUID or accept later capture proof |
| PTY accepts, no provider request appears | Keep unbound while run lives; no reciprocal wake |
| Several deliveries precede one request | Bind every valid marker to one generation; one wake per source run |
| Marker appears in later retained history | Existing delivery binding wins; no new ancestry |
| Provisional anchor write fails | Final wire transaction reconstructs it |
| Final write repeats | Unique keys make binding, ancestry, and outbox insertion idempotent |
| Doorbell is lost or queues overflow | Catch up from anchors and outbox rows |
| API restarts | Reload subscriptions, retry outbox for reachable runs, and reconcile anchors; mark process resident runs lost with the API as `target_gone` |
| Target run ends before request | Mark accepted unbound deliveries `no_turn`; no wake |
| Outbound wake target is gone | Mark outbox and delivery `target_gone` |
| Final exchange is deleted later | Preserve causal tombstone and delivered wake audit |

## Garbage collection

There is no correctness TTL for an accepted delivery while its target run is
alive. A delayed marker must still bind to its first request.

Run lifecycle termination closes all accepted unbound deliveries for that run
as `no_turn`. Rejected intent may become terminal immediately. Outbox rows
become terminal after acceptance, definite target loss, or policy cancellation.

After the audit retention period, compact terminal rows rather than removing
their identities:

* retain delivery UUID, scope, outcome, generation, and envelope hash;
* remove rendered fact JSON and retry diagnostics;
* retain request generation, final exchange id, and ancestor closure while the
  corresponding wire exchange or any delivery tombstone remains;
* delete a closed causal component only when every run is terminal, every
  outbox row is terminal, and no retained wire or delivery row references it.

This preserves replay fences. GC never makes an old marker eligible to bind a
new request.

## File and symbol plan

### Python API and capture

* `controlplane/models.py`: table constants and durable row vocabulary.
* `controlplane/delivery_marker.py`: one formatter and parser.
* `controlplane/delivery_store.py`: prepare, outcome, bind, ancestry, and
  subscription transactions.
* `controlplane/wake_outbox.py`: claim, deliver, retry, and terminal handling.
* `controlplane/envelope.py`: full marker in prompt and watch envelopes.
* `controlplane/service.py:ControlPlaneService.prompt`: prepare per target
  before fanout and resolve source generation.
* `controlplane/launch_service.py:ControlPlaneLauncher._prepare` and
  `launch_delivery.py:deliver_first_prompt`: prepare and carry launch delivery.
* `controlplane/watch.py:ControlPlaneWatchEngine`: durable subscriptions,
  generation aware facts, shared decider, and outbox delivery.
* `controlplane/watch_models.py:WatchFact`: stable source generation, exchange,
  and event key.
* `api/v1/run_proxy.py:RunRouteProxy.deliver_input`: carry idempotency identity.
* `storage/exchange_sink.py`: request observed sink alongside completed sink.
* `exchange_recorder.py:persist_http_provisional_exchange` and
  `codex/exchange.py:persist_codex_provisional_exchange`: emit request anchor.
* `wire_store_observer.py:WireStoreObserver`: schedule request and final writes.
* `session/writer.py:SessionWriter`: make final wire, binding, ancestry, outbox,
  live close, and doorbell one transaction.
* `session/wire_store.py:WireExchangeWrite`: persist request generation and raw
  completion evidence.
* `controlplane/read_store.py`: generation, ancestry, subscription, and outbox
  replay reads.
* `addon_runtime.py:_start_session_capture`: register and drain request anchor
  observation before final wire observation.

### TypeScript runtime and Activity

* `runtime/src/service/RunInputDelivery.ts:DeliverInputRequest`: delivery UUID.
* `runtime/src/service/RunManager.ts:RunManager.deliverInput`: per run
  idempotency set.
* `runtime/src/server/runtimeRouter.ts:registerRunRoutes`: validate and return
  duplicate acceptance.
* `activity/src/ports.ts`: request anchor read model.
* `activity/src/adapters/postgresRecords.ts:PostgresActivityReader`: anchor and
  final generation reads.
* `activity/src/domain/runActivityContext.ts:RunActivityContext`: retained turn
  cause.
* `activity/src/service/activityIngestion.ts:reconcile`: apply request anchor
  before final wire resolution.
* `activity/src/projections/workspaceActivity.ts`: project and compare cause.
* `activity/src/server/activityRouter.ts:runToWire`: expose cause on SSE.
* `contract/activity`: add the two cause fields.

No listed file needs to cross the 700 line threshold. New stores and outbox
logic stay separate from `service.py`, `watch.py`, and `writer.py`.

## Verification gates

Unit tests must prove marker round trip, wrong scope rejection, first request
wins, many deliveries to one generation, transitive ancestry, unique outbox
rows, subscription restart, runtime duplicate acceptance, and terminal GC.

Postgres integration tests must prove provisional then final convergence, final
without provisional self repair, late provisional after final, duplicate
finalize, raw complete parse failure, deleted exchange tombstones, and
concurrent outbox claims.

The acceptance test must use a real managed PTY and both harness adapters:

1. submit a prompt with a delivery UUID;
2. lose the gateway HTTP response after PTY acceptance;
3. capture the provider request and verify its generation binding;
4. finalize the exact exchange;
5. restart the API between each legal boundary;
6. deliver the reciprocal wake once;
7. replay wire before Activity and Activity before wire;
8. enable reciprocal `turn_completed` and `state_changed` watches;
9. prove no further PTY input is accepted for the causal chain;
10. submit an unrelated human turn and prove its watches still fire.

Also cover two prompt deliveries before one provider request, a delivery that
never produces a request, an active turn with queued human input, and a
complete raw response whose IR parser fails.

The final review requires a pristine worktree, migration round trip, focused
Python and TypeScript suites, and one recorded end to end trace containing
delivery UUID, request generation, final exchange id, outbox key, and runtime
duplicate result.
