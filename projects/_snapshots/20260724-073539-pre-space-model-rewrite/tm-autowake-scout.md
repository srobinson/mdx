# B1 auto wake scout: durable delivery to turn binding

Scouted read only on `controlplane-autowake` at `e05373b6a4f5`. The repository
was pristine before the scout. This document maps existing seams and states the
properties a durable B1 binding must satisfy. It does not propose a design.

## Finding

The current durable end of turn authority is a finalized Postgres
`wire_exchange` row. `ControlPlaneWatchEngine` already treats that row as the
`turn_completed` source and rereads it before emitting a fact. No current
record ties a control plane delivery to the exact wire exchange it actuated.

The durable B1 requirement is therefore an exact, replayable
delivery to wire exchange relation. Correctness cannot depend on the order in
which PTY acceptance, an HTTP receipt, a wire commit notification, or an
Activity delta is observed.

## Reuse Map

### Prompt delivery

1. `api/src/transport_matters/controlplane/service.py:ControlPlaneService.prompt`
   requires a director, creates one `dispatch_id`, formats a sender envelope,
   reads visible workspace runs, and fans out targets.
2. `api/src/transport_matters/controlplane/service.py:ControlPlaneService._deliver_prompt_target`
   calls `ControlPlaneGatewayPort.deliver_input`. A delivered receipt means the
   live PTY accepted the submitted bytes. An HTTP loss after send returns an
   `unknown` outcome through
   `api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy.deliver_input`.
3. `api/src/transport_matters/controlplane/service.py:ControlPlaneService._audit_prompt`
   persists a `control_plane_action` after fanout delivery attempts. The row
   carries the full `dispatch_id`, actor, targets, envelope, mode, and outcomes.
   The write occurs after the PTY call returns, so it is a durable audit fact,
   not an acceptance boundary.
4. `api/src/transport_matters/controlplane/envelope.py:format_prompt_envelope`
   places only the first eight hexadecimal characters of `dispatch_id` in the
   terminal text. That token is useful for observation but is not a unique
   causal key.

### Launch first prompt delivery

1. `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher._prepare`
   creates the same prompt envelope from the launch `dispatch_id`.
2. `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher._execute`
   creates the run, then calls
   `api/src/transport_matters/controlplane/launch_delivery.py:deliver_first_prompt`
   after gateway authoritative readiness.
3. `deliver_first_prompt` uses the same `ControlPlaneGatewayPort.deliver_input`
   nudge path as ordinary prompt and watch delivery.
4. `ControlPlaneLauncher._execute` freezes and persists the launch audit after
   the first prompt attempt. `api/src/transport_matters/controlplane/launch_ledger.py:LaunchLedger`
   provides process lifetime single flight and audit retry. It does not bind the
   first prompt to a provider turn and is not durable across process loss.

### Runtime PTY input primitive

1. `api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy.deliver_input`
   sends `POST /v1/runs/{run_id}/input` with owner, text, and mode.
2. `packages/runtime/src/server/runtimeRouter.ts:registerRunRoutes` validates the
   body and calls `RunManager.deliverInput`.
3. `packages/runtime/src/service/RunManager.ts:RunManager.deliverInput` resolves
   the owner scoped live run and delegates to
   `packages/runtime/src/service/RunInputDelivery.ts:deliverInput`.
4. `RunInputDelivery.deliverInput` serializes input operations, optionally sends
   the harness break byte, then writes bracketed paste plus carriage return to
   `PtySession.tryWrite`. This is the exact mechanical acceptance seam.
5. The request and result contain no delivery identity, provider request
   generation, exchange identity, or durable record. The primitive proves byte
   acceptance only.

### Watch subscriptions, damping, and nudge delivery

1. `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine.watch`
   registers a process resident watcher after both event sources are ready.
   `api/src/transport_matters/controlplane/watch_registry.py:Watcher` owns target
   subscriptions, the coalescing buffer, and the flush task.
2. `ControlPlaneWatchEngine._ensure_feed` starts two independent consumers for
   each owner and workspace pair:

   * `ControlPlaneWatchEngine._consume_activity` consumes Gateway Activity SSE
     for `state_changed` and `needs_you`.
   * `ControlPlaneWatchEngine._consume_wire` consumes finalized wire exchange
     doorbells for `turn_completed`.

3. `ControlPlaneWatchEngine._record_activity_delta` and
   `ControlPlaneWatchEngine._record_completed_turn` create originless
   `WatchFact` values. `ControlPlaneWatchEngine._buffer_fact` coalesces by event
   kind and run, and `_schedule_flush` applies the damping interval.
4. `ControlPlaneWatchEngine._flush_serialized` renders one
   `format_watch_envelope` and calls the same gateway `deliver_input` nudge
   primitive. A definite gateway connection failure restores facts. Ambiguous
   or rejected outcomes are dropped to avoid duplicate PTY input.
5. Successful watch deliveries have no dispatch identity and no durable success
   row. `api/src/transport_matters/controlplane/watch_delivery.py:audit_watch_delivery`
   is best effort and is invoked for failure or ambiguous classifications.

### Durable turn boundary

The wire store is the closest existing authority.

1. `api/src/transport_matters/wire_store_observer.py:WireStoreObserver.on_exchange`
   receives a finalized capture exchange and builds `WireExchangeWrite` from
   the request and parsed response.
2. `api/src/transport_matters/session/writer.py:SessionWriter.submit_wire_exchange`
   writes the exchange and its `tm_events` notification in one Postgres
   transaction.
3. `api/src/transport_matters/session/wire_store.py:write_wire_exchange` persists
   the request messages, response blocks, `run_id`, optional `turn_index`, and a
   commit watermark. The exchange row is keyed by stable `exchange_id`.
4. `api/src/transport_matters/session/controlplane_statements.py:GET_COMPLETED_WIRE_TURN_FOR_OWNER_SQL`
   treats a non subagent row with `response_id IS NOT NULL` as completed and
   enforces owner and workspace visibility.
5. `api/src/transport_matters/controlplane/read_store.py:ControlPlaneReadStore.completed_wire_turn`
   returns `CompletedWireTurn {exchange_id, run_id, turn_index, committed_at}`.
   `completed_wire_turns_since` provides durable catch up under the wire commit
   watermark.
6. `ControlPlaneWatchEngine._consume_wire_exchange` receives only a doorbell,
   rereads this durable record, deduplicates `exchange_id`, then emits
   `turn_completed`. Reconnect and queue overflow converge through durable catch
   up rather than trusting notification order.

This boundary has one known integrity precondition. `WireStoreObserver.on_exchange`
currently derives completion from a parsed response IR, while the watch queries
require `response_id IS NOT NULL`. A complete raw response that fails parsing
does not become a completed wire turn. `NOW.md`, under wire store integrity
cleanup, records that defect. B1 cannot claim complete turn coverage until its
completion authority also covers that case.

### Transcript and Activity signals

The transcript store is durable but secondary for causal binding.

1. `api/src/transport_matters/session/ingest.py:build_event` persists raw harness
   records as owner scoped session events through
   `SessionWriter._commit_batch`.
2. `packages/activity/src/adapters/transcriptRecords.ts:activityRecordsFromPgEvent`
   derives `turn-open` and `turn-end` from Claude and Codex transcript records.
   The delivered envelope can appear in a later user record, but transcript
   ingestion is asynchronous and independent from wire capture.
3. `packages/activity/src/service/activityIngestion.ts:ActivityIngestion`
   rereads durable transcript, lifecycle, live status, and wire rows. Its actor
   and projections are process resident derived state.
4. `packages/activity/src/adapters/postgresRecords.ts:PostgresActivityReader.readWireSnapshotForRun`
   explicitly calls the latest finalized parent wire exchange the end of turn
   oracle.
5. Activity SSE frames contain status, run identity, and timestamps. They carry
   no delivery identity or exact exchange relation. They are suitable wake
   signals after a binding exists, not an authority for creating one.

## Why in memory failed

The rejected implementation was reviewed at
`5b3222336666806f276ba3872e18563255c2a49a` and removed by `b8a389c`.

### Observation order replaced causality

The deleted
`api/src/transport_matters/controlplane/causality.py:CausalAncestryLedger`
stored pending ancestry by target run. Historical
`ControlPlaneService._deliver_prompt_target` and
`ControlPlaneWatchEngine._flush_serialized` called `mark_delivery` only after
the gateway HTTP await returned. Historical
`ControlPlaneWatchEngine._consume_wire_exchange` independently called
`consume_turn` when a wire commit was observed.

Those operations had no shared turn boundary. An already active turn could
complete while Python awaited the delivery receipt, before ancestry was armed.
The reverse race also existed: a completion read begun before PTY acceptance
could resume after `mark_delivery` and consume the new marker. The ledger bound
to whichever callback ran first, not to the turn containing the delivered
input.

### `state_at_write` was stale derived state

The old runtime receipt carried `state_at_write`. Gateway production wiring
sampled `WorkspaceActivityProjections.byRun`, an asynchronous cache populated
after Postgres commit, notification, reread, actor application, and projection.
The ledger used cached idle to allocate one completion and cached working or
unknown to allocate two.

Either stale direction was unsafe. Stale idle let the current human turn spend
the only slot so the induced turn escaped. Stale working left a second slot
that could suppress an unrelated later human turn. No state label could name a
specific provider request or exchange.

### Two event streams could not be reconciled by one pending counter

WATCH deliberately has two independent sources. Wire completion consumed and
cleared pending ancestry. Activity `working` to `idle` for the same turn could
arrive later. The Activity path then saw no pending ancestry and emitted a
reciprocal `state_changed` nudge. Repeating that legal ordering could sustain
the loop indefinitely.

The reverse ordering also occurred. Tests passed because fake delivery state
was injected and completions were published only after fake delivery returned.
They proved ledger arithmetic and adapter serialization while excluding the
real race between PTY acceptance, HTTP response, wire commit, and Activity SSE.

### Ambiguous acceptance and lifetime were unresolved

If the gateway accepted PTY bytes and its response was lost, both prompt and
watch could report an ambiguous outcome without causal ancestry. The induced
turn could then restart a reciprocal chain. TTL expiry and completion counters
could limit memory, but they could not repair missing identity and could also
suppress an unrelated turn.

The S6a MAX review found the same durability principle in the launch replay
ledger: bounded eviction is safe only after a durable terminal record preserves
the complete immutable intent and outcome. Applied to B1, process memory cannot
be the only home of delivery identity or its terminal binding.

## What a durable binding requires

These are correctness requirements, not a storage or API design.

1. **Stable identity before side effects.** Every prompt target, launch first
   prompt, and watch nudge delivery needs a unique identity before any PTY write.
   It must be scoped by owner, workspace, target run, and source actor or source
   turn. A shortened display token is insufficient.
2. **Acceptance boundary evidence.** Correctness must survive an HTTP response
   loss. The durable fact must be created at the executor acceptance boundary,
   or the accepted input must carry identity that the capture plane can prove
   reached a specific outbound request.
3. **Exact request relation.** A delivery must bind to the exact first outbound
   provider request that contains or results from that input. Binding to the
   next observed completion is forbidden. Multiple deliveries before one
   request and one delivery that never produces a request need explicit,
   deterministic outcomes.
4. **Exact completion relation.** Completion must reference the finalized
   exchange by `exchange_id`, with owner, workspace, run, and commit boundary.
   A missing `turn_index`, as on Claude rows, must not weaken identity.
5. **Complete raw outcome coverage.** A provider response that completed on the
   wire must remain observable even when response parsing fails. Otherwise a
   valid induced turn can remain permanently unbound.
6. **Transitive ancestry from bound turns.** A delivery caused by a bound turn
   must inherit that turn's causal ancestry. Suppression must apply only when
   the prospective watcher is in that ancestry. Human and unrelated turns must
   remain unsuppressed.
7. **One causal fact for both WATCH sources.** `turn_completed` and every
   Activity delta attributable to the same exchange must consult the same
   durable binding. Their notification order cannot change the decision.
   `needs_you` remains independently visible under the existing contract unless
   that contract is explicitly changed.
8. **Replay and restart convergence.** Lost notifications, queue overflow,
   reconnect, duplicate finalize, API restart, and gateway retry must converge
   idempotently from durable rows. TTL, callback order, and process lifetime
   maps cannot be correctness inputs.
9. **Honest ambiguity.** Definite rejection, definite acceptance, ambiguous
   acceptance, bound request, completed exchange, and no resulting request are
   distinct facts. No ambiguous PTY outcome may be silently treated as either
   accepted or rejected for loop protection.
10. **Real boundary verification.** The proof must run through a real runtime
    PTY, capture the induced request and response, persist the binding, and
    exercise both legal orders between wire notification and Activity SSE. It
    must include reciprocal `turn_completed`, reciprocal `state_changed`,
    active turn, queued human input, lost gateway response, replay, and restart
    cases.

## Candidate anchor seams

| Seam | Existing authority | What it can anchor | Current gap |
| --- | --- | --- | --- |
| `RunInputDelivery.deliverInput` and `RunManager.deliverInput` | Exact PTY acceptance | Delivery acceptance and queue order | No identity, durable write, provider request generation, or exchange link |
| `control_plane_action` through `ControlPlaneAuditWriter.write` | Durable actor, intent, dispatch, and observed outcome for prompt and launch | Delivery intent and terminal audit | Written after the gateway await; successful watch nudges lack a dispatch and durable success row; no turn relation |
| `WireStoreObserver.on_exchange` to `SessionWriter.submit_wire_exchange` to `write_wire_exchange` | Durable captured request plus finalized response under one `exchange_id` | Exact provider request and completion | No control plane delivery identity; parse failure can hide a completed raw response |
| `wire_request_message` and transcript user records | Durable input content | Corroboration that an envelope reached a request | Prompt embeds only a short token; watch embeds no delivery token; content matching alone is collision prone and can be rewritten |
| `ControlPlaneReadStore.completed_wire_turn` and `completed_wire_turns_since` | Owner and workspace scoped replayable completion read | Delivery aware watch consumption and catch up once the relation exists | Returns exchange, run, optional turn index, and commit time only |
| Activity `readWireSnapshotForRun` and Activity SSE | Derived end state and wake transport | Emitting state after durable causal classification | No delivery identity; two independent event sources make Activity unsuitable as the binding authority |

The primary durable completion anchor is the finalized wire exchange. The
runtime PTY primitive is the acceptance anchor. `control_plane_action` is the
existing durable control plane intent and outcome seam. A correct B1 slice must
join those authorities through a real delivery to request boundary. The current
code contains each endpoint of that relation and no seam that establishes the
relation itself.
