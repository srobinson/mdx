# S4 control-plane WATCH max review

Review target: `controlplane-s4-watch` at
`7054d439b85c92396b26ceb90e488a7af2e648fd`, compared with `main` at
`b8d83ec5fcd62fc59b9eb7415a4f2d2a649aa7c8`.

Review mode: adversarial, static, read only against the repository. No builds,
tests, type checks, generated files, commits, or branch edits were run. The
repository was pristine before this document was written, and
`git diff --check main...controlplane-s4-watch` exited cleanly.

## Verdict

Counts: **3 Blocker / 3 Major / 5 Minor / 8 Low**.

The merge blockers are an unbounded reciprocal watch loop, duplicate PTY prompt
submission after an ambiguous HTTP outcome, and a false successful PTY delivery
receipt during the terminal exit race. The three major findings are durable
replay gaps, false completion events from idempotent finalize replay, and missed
completion events when response parsing fails.

Scope labels used below:

- **S4 introduced**: the failing behavior is new on this branch.
- **S4 correction introduced**: the behavior is specifically in `7054d43`.
- **S4 surfaced**: an older storage or PTY behavior was safe for its original
  consumers, but the new WATCH path interprets it as a stronger contract and
  creates the defect.
- **Preexisting substrate**: older code contributes to the mechanism. We count
  it only when S4 turns it into a WATCH failure.

## Blockers

### B1. Reciprocal watchers form an unbounded actuation loop

- **Scope:** S4 introduced.
- **Confidence:** 100/100.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py:_target_events`,
  `ControlPlaneWatchEngine._record_completed_turn`,
  `ControlPlaneWatchEngine._flush`;
  `packages/runtime/src/service/RunManager.ts:RunManager.nudge`.
- **Failure mechanism:** `_target_events` suppresses only an event whose
  `run_id` equals the current watcher's own run. It carries no control-plane
  origin, causal delivery id, hop count, or reciprocal suppression. A nudge is
  submitted as a new prompt with a trailing carriage return, so the recipient's
  resulting response finalizes a fresh exchange. The new exchange id passes the
  replay dedupe and is eligible for every peer watcher.
- **Failing scenario:** runs A and B both watch `workspace` for
  `turn_completed`. B completes a genuine turn, which nudges A. A answers the
  injected prompt, which emits A's completion and nudges B. B answers, emits a
  new completion, and nudges A again. Damping adds delay but never terminates the
  A to B to A cycle. `state_changed` can add more triggers to the same loop.
- **Test gap:**
  `test_workspace_watch_excludes_the_watcher_own_activity_and_turns` proves only
  direct self exclusion. It never creates two mutually watching runs.
- **Impact:** unbounded agent work, provider usage, audit noise, and repeated
  control-plane actuation without further human intent.

### B2. Ambiguous POST outcomes can submit the same PTY prompt twice

- **Scope:** S4 correction introduced, using the S4 nudge and retry path.
- **Confidence:** 92/100.
- **Anchors:**
  `api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy.deliver_watch_nudge`,
  `RunRouteProxy._request_http`;
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._flush`,
  `_restore_failed_facts`;
  `packages/runtime/src/server/runtimeRouter.ts:createRuntimeRouter`.
- **Failure mechanism:** the Python client sends an unkeyed POST. `_request_http`
  maps every `httpx.RequestError`, including a response protocol failure after
  the server accepted the request, to `GatewayUnavailableError`. `_flush` then
  restores the facts and retries the identical envelope after damping. The
  gateway has no delivery id or dedupe ledger.
- **Failing scenario:** the gateway calls `RunManager.nudge`, writes
  `text + "\r"` to the PTY, then its 202 response is truncated or the connection
  disappears before Python reads it. Python observes
  `httpx.RemoteProtocolError`, restores the batch, and submits the same prompt a
  second time. The harness receives two turns from one WATCH fact.
- **Evidence in tests:**
  `test_control_plane_watch_nudge_maps_protocol_failures_to_transient_unavailable`
  explicitly classifies `RemoteProtocolError("truncated gateway response")` as
  retryable. `test_transient_delivery_failure_retains_and_retries_the_batch`
  explicitly expects two identical attempts. Neither test models server-side
  acceptance before response loss.
- **Impact:** duplicated agent prompts and duplicated downstream actions.

### B3. The resultful nudge can return 202 after the PTY rejected the bytes

- **Scope:** S4 introduced by treating a preexisting fire-and-forget PTY write
  as a resultful control-plane primitive.
- **Confidence:** 97/100.
- **Anchors:**
  `packages/runtime/src/service/RunManager.ts:RunManager.nudge`;
  `packages/runtime/src/ports.ts:PtySession.write`;
  `packages/runtime/src/adapters/NodePtyAdapter.ts:NodePtySession.write`,
  `isTerminalGoneError`;
  `packages/runtime/src/server/runtimeRouter.ts:createRuntimeRouter`;
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._flush`.
- **Failure mechanism:** `PtySession.write` returns `void`.
  `NodePtySession.write` deliberately suppresses disposed, exited, EIO, and
  EBADF outcomes. `RunManager.nudge` calls that void method and unconditionally
  returns `true`. The route converts `true` to HTTP 202, and Python treats 202 as
  delivered and leaves its already cleared facts consumed.
- **Failing scenario:** the child closes the PTY slave before node-pty emits
  `onExit`. `RunManager` still sees `RUNNING` with no settle promise. The write
  raises EIO, `NodePtySession.write` swallows it, `RunManager.nudge` returns
  `true`, and Python drops the fact although zero bytes were accepted.
- **Evidence in tests:** `NodePtyAdapter.test.ts` explicitly proves the EIO and
  EBADF pre-exit race is swallowed. `RunManagerNudge.test.ts` uses a fake whose
  writes always append, so it never composes the nudge receipt with the real
  terminal-gone behavior.
- **Contract conflict:** `CONTROLPLANE.md` requires a resultful
  `PtySession.tryWrite` style primitive and defines delivered as bytes accepted
  by a live PTY. The locked design likewise requires a typed
  `delivered | not_found | ended | write_failed` result distinct from the void
  terminal write.
- **Impact:** silent WATCH fact loss behind a false successful receipt.

## Major

### M1. The durable replay watermark can permanently skip late commits

- **Scope:** S4 introduced the cursor and catch-up query. The
  `wire_exchange.created_at DEFAULT now()` behavior is preexisting substrate.
- **Confidence:** 98/100.
- **Anchors:**
  `api/src/transport_matters/controlplane/read_store.py:ControlPlaneReadStore.wire_replay_cursor`,
  `completed_wire_turns_since`;
  `api/src/transport_matters/session/controlplane_statements.py:GET_COMPLETED_WIRE_TURNS_FOR_OWNER_SQL`;
  `api/migrations/versions/0008_wire_store.py:wire_exchange.created_at`;
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._catch_up_wire`.
- **Failure mechanism:** the baseline is `CURRENT_TIMESTAMP`, while catch-up
  filters and advances on `wire_exchange.created_at`. In PostgreSQL both
  `CURRENT_TIMESTAMP` and the column default `now()` are transaction-start
  timestamps, not commit-order values. The code assumes their order matches
  commit visibility.
- **Failing scenario:** a writer transaction starts at t0, the watcher records
  cursor t1, and the writer commits at t2 while LISTEN is disconnected or the
  subscriber queue is replaced by a catch-up marker. The committed row retains
  `created_at=t0`, so every query using `created_at >= t1` excludes it forever.
  The same ordering problem appears when an old exchange row is finalized by an
  upsert after the cursor without refreshing `created_at`.
- **Test gap:** synthetic watch tests always give replay rows timestamps later
  than the cursor. They do not create two real PostgreSQL transactions whose
  start order and commit order invert.
- **Impact:** a promised durable reconnect and overflow recovery path silently
  loses `turn_completed`.

### M2. Idempotent finalize replay creates a false `turn_completed`

- **Scope:** S4 surfaced. The store's idempotent upsert and unconditional NOTIFY
  predate WATCH; the branch newly interprets the notification as a completion
  edge.
- **Confidence:** 95/100.
- **Anchors:**
  `api/src/transport_matters/session/wire_store.py:write_wire_exchange`;
  `api/src/transport_matters/session/dao_statements.py:UPSERT_WIRE_EXCHANGE_SQL`;
  `api/src/transport_matters/session/writer.py:SessionWriter.submit_wire_exchange`;
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._consume_wire`,
  `_remember_exchange`, `_record_completed_turn`.
- **Failure mechanism:** the wire store explicitly promises idempotence under
  replay, and the conflict path can leave durable state identical. The writer
  nevertheless emits a wire NOTIFY after every successful upsert. A new watch
  feed initializes only a timestamp cursor and an empty process-local dedupe
  set. The live path never rereads the durable row to decide whether completion
  actually transitioned.
- **Failing scenario:** exchange X finalized before the watcher subscribed. A
  recovery or replay submits the identical finalized write after subscription.
  Durable state does not change, but X is absent from the new feed's
  `seen_exchanges`, so the NOTIFY becomes a new `turn_completed` fact. The same
  false event occurs after X is evicted from the bounded 2,048-id dedupe window
  or after feed recreation.
- **Evidence in tests:**
  `test_replayed_finalize_converges_to_identical_state` proves identical replay
  leaves store state unchanged. The watch duplicate test republishes an id only
  while it is resident. The eviction test never republishes the evicted id as a
  live signal.
- **Impact:** spurious nudges, which can also seed the reciprocal loop in B1.

### M3. A complete raw response that fails IR parsing never completes the turn

- **Scope:** S4 surfaced. Raw response preservation and nullable response IR are
  preexisting; the branch uses response IR presence as its completion predicate.
- **Confidence:** 99/100.
- **Anchors:**
  `api/src/transport_matters/exchange_stats.py:parse_response_ir`;
  `api/src/transport_matters/exchange_recorder_artifacts.py:extract_response`;
  `api/src/transport_matters/wire_store_observer.py:WireStoreObserver.on_exchange`;
  `api/src/transport_matters/session/writer.py:SessionWriter.submit_wire_exchange`;
  `api/src/transport_matters/session/listen.py:_parse_wire_exchange_signal`;
  `api/src/transport_matters/session/controlplane_statements.py:GET_COMPLETED_WIRE_TURNS_FOR_OWNER_SQL`.
- **Failure mechanism:** parser failure preserves the raw provider response and
  records `response_parse_failure`, but returns `response_ir=None`.
  `WireStoreObserver` forwards only `artifacts.response_ir`. The writer emits
  `has_response=false`; the live listener rejects the signal; durable catch-up
  also requires `response_id IS NOT NULL`.
- **Failing scenario:** the provider returns a complete response containing a
  new or malformed variant that the adapter cannot parse. Tier 1 contains the
  final raw bytes, and the run has crossed a genuine response boundary, yet no
  live or replayed `turn_completed` event reaches any watcher.
- **Impact:** permanent missed completions precisely on forward-compatibility
  and malformed-response cases where observability is most valuable.

## Minor

### N1. `unwatch` and event narrowing can still deliver a buffered stale fact

- **Scope:** S4 introduced.
- **Confidence:** 88/100.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._unwatch_serialized`,
  `_watch_serialized`, `_buffer_fact`, `_flush`.
- **Failure mechanism:** removing one target only edits `watcher.targets`. It
  leaves `watcher.buffer` and `flush_task` intact when another target remains.
  Replacing an event tuple also leaves buffered removed event kinds intact.
  `_flush` copies every buffered fact without rechecking current subscriptions.
- **Failing scenario:** a watcher subscribes to A for `state_changed` and B for
  `needs_you`. A changes and is buffered. During the three-second damping
  window the caller successfully unwatches A. The B registration keeps the
  watcher alive, and the later flush still sends A's state change. Narrowing A's
  event set during the same window has the same result.
- **Impact:** one stale wake-up after the API reported the subscription removed.

### N2. Shutdown can race registration into a zombie successful subscription

- **Scope:** S4 introduced.
- **Confidence:** 88/100 for the class-level race, with production prevalence
  reduced by normal ASGI graceful draining.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._watch_serialized`,
  `aclose`.
- **Failure mechanism:** registration validates the current feed, then awaits
  the audit write while holding `_registry_lock`. `aclose` does not take that
  lock or a watcher operation lock. It sets `_closed`, clears watchers, and
  stops feeds. The suspended registration can then resume after close and
  insert a watcher without rechecking `_closed` or feed identity.
- **Failing scenario:** shutdown begins while `watch_action(...subscribed...)`
  is awaiting PostgreSQL. `aclose` returns after clearing state. The audit
  completes, registration inserts a watcher, and the caller receives success
  although no feed exists and the engine is closed.
- **Impact:** a false success and a process-resident zombie registry entry on
  abnormal or direct lifecycle shutdown paths.

### N3. The catch-up query has no supporting `created_at` index

- **Scope:** S4 introduced the query against a preexisting table and index set.
- **Confidence:** high.
- **Anchors:**
  `api/src/transport_matters/session/controlplane_statements.py:GET_COMPLETED_WIRE_TURNS_FOR_OWNER_SQL`;
  `api/migrations/versions/0008_wire_store.py:wire_exchange indexes`;
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._catch_up_wire`.
- **Failure mechanism:** catch-up filters and orders by `w.created_at`, then runs
  correlated ownership checks. Existing indexes are `(run_id, ts)` and
  `(session_id, ts)`. None supports the leading cursor predicate or ordering.
- **Failing scenario:** after the wire table grows, a listener reconnect, queue
  overflow, or each 1,000-event cursor advance scans a large part of
  `wire_exchange` before applying the owner/workspace checks. Multiple active
  workspace feeds repeat the work.
- **Impact:** slow recovery and sustained database load exactly during backlog
  or reconnect conditions.

### N4. `createRuntimeRouter` crossed the hard function-size guardrail

- **Scope:** S4 introduced by adding the nudge route to a preexisting large
  router function.
- **Confidence:** 92/100.
- **Anchors:**
  `packages/runtime/src/server/runtimeRouter.ts:createRuntimeRouter`;
  repository `AGENTS.md:Refactoring threshold`.
- **Failure mechanism:** on `main`, the outer function spans 136 physical lines
  and its returned async closure spans 134. On S4 they span 153 and 151. The
  17-line nudge route is the delta that crosses the explicit approximately
  150-line function limit.
- **Failing scenario:** the next route change must reason across create, list,
  get, terminate, nudge, plain terminal, and terminal WebSocket registration in
  one closure, despite the repository rule requiring decomposition before
  further growth.
- **Impact:** direct project-convention violation and reduced route ownership
  clarity.

### N5. Registry-wide event processing waits behind audit I/O

- **Scope:** S4 introduced.
- **Confidence:** moderate to high.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._watch_serialized`,
  `_unwatch_serialized`, `_apply_activity_snapshot`, `_apply_activity_delta`.
- **Failure mechanism:** successful and several failed watch registrations await
  `_audit.write` while holding the single `_registry_lock`. Unwatch does the
  same. Activity snapshot/delta application and buffer extraction need that
  same global lock across every workspace.
- **Failing scenario:** one audit connection stalls while registering a watcher
  in workspace A. Activity events for workspace B cannot enter the registry;
  its SSE consumer stops reading and wire queues continue filling. A prolonged
  stall can force the overflow and catch-up path.
- **Impact:** unrelated workspaces share audit latency and failure pressure.

## Low

### L1. The correction test imports private helpers from a sibling test module

- **Scope:** S4 correction introduced.
- **Confidence:** high as a hygiene concern, lower as an enforced violation
  because the current private-import boundary test skips test files.
- **Anchors:**
  `api/src/transport_matters/controlplane/test_watch_corrections.py:imports`;
  `api/CLAUDE.md:Module privacy`.
- **Failure mechanism:** `test_watch_corrections.py` imports `_engine`,
  `_principal`, `_run`, and `_until` from `test_watch.py`. Project guidance
  permits private imports from the module under test and shared test-support
  modules. A sibling test file is now acting as an undeclared support module.
- **Maintenance scenario:** splitting or renaming the primary test file changes
  a second test module's private API. Moving fakes and builders to a named test
  support module would make the ownership explicit.

### L2. The new watch implementation and primary test are almost at the file cap

- **Scope:** S4 introduced.
- **Confidence:** factual measurement; this is a forward maintenance concern,
  not a present threshold breach.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py` at 695 lines;
  `api/src/transport_matters/controlplane/test_watch.py` at 676 lines;
  repository `AGENTS.md:Refactoring threshold`.
- **Failure mechanism:** both files remain below the 700-line hard limit, but
  the implementation has only five lines of headroom. The separate 85-line
  correction test already depends on private helpers from the 676-line file.
- **Maintenance scenario:** any ordinary follow-up to loop suppression, replay
  fencing, or lifecycle tests forces an immediate split before the fix can be
  added. Natural seams already exist for activity consumption, wire replay,
  registry lifecycle, delivery, and shared test support.

### L3. Every watch registration depends on both event sources

- **Scope:** S4 introduced.
- **Confidence:** high for the coupling, low severity because the configured
  service normally has both dependencies.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._ensure_feed`,
  `_watch_serialized`.
- **Failure mechanism:** every feed starts Activity and wire tasks, and every
  `watch(...)` waits for both `activity_ready` and `wire_ready`, regardless of
  the requested event set.
- **Failing scenario:** a caller requests only `needs_you` while Activity is
  healthy, but the PostgreSQL cursor read repeatedly fails. Registration times
  out as `busy_gateway` even though its sole requested source is ready. The
  converse also prevents a turn-only subscription when Activity cannot start.
- **Impact:** avoidable availability coupling and resource use.

### L4. Four-character run references can be ambiguous

- **Scope:** S4 introduced.
- **Confidence:** high for collision possibility, low practical severity.
- **Anchors:**
  `api/src/transport_matters/controlplane/envelope.py:_format_watch_fact`;
  `CONTROLPLANE.md:Push carries references, pull carries content`.
- **Failure mechanism:** the envelope emits only `fact.run_id[:4]` beside a
  title. Titles are not unique, and four hexadecimal characters provide only a
  16-bit reference space for UUID-shaped ids.
- **Failing scenario:** two workspace runs share the same first four characters
  and the same title, or titles are unavailable and similarly truncated names
  collide. A coalesced nudge cannot identify which full run id should be passed
  to `conversation`; the watcher must perform an extra roster lookup and still
  disambiguate by other fields.
- **Impact:** rare ambiguity in a surface whose principle says push carries a
  reference.

### L5. Successful delivery audit semantics remain ambiguous

- **Scope:** S4 introduced, with conflicting design language.
- **Confidence:** 40/100 as a merge defect, retained here as requested design
  evidence.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._flush`,
  `_audit_delivery`;
  `api/src/transport_matters/controlplane/watch_audit.py:watch_delivery_action`;
  `CONTROLPLANE.md:Principle 5`, `Attribution, audit, eval`.
- **Failure mechanism:** delivery failure, rejection, and missing-watcher paths
  write `watch_delivery`; the successful path falls through without a row.
- **Failing scenario:** an operator queries `control_plane_action` to distinguish
  a successfully delivered wake-up from a subscription that never fired. Both
  have only the registration action and are indistinguishable.
- **Why this is Low:** the narrow WATCH text and locked design explicitly require
  failure audit only. The successful-delivery test asserts no success row. That
  evidence makes failure-only delivery auditing look intentional, while the
  broader "every action" wording remains unclear.

### L6. Test-only and unconsumed watch surface adds maintenance weight

- **Scope:** S4 introduced.
- **Confidence:** factual usage scan, low impact.
- **Anchors:**
  `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine.is_watching`;
  `api/src/transport_matters/controlplane/activity.py:GatewayActivityRun.needs_you`.
- **Failure mechanism:** `is_watching` has no production caller and exists only
  to inspect private state in tests. The parsed `needs_you` payload is never
  consumed by the service or watch engine, which derives the event only from
  `tier` transitions.
- **Maintenance scenario:** registry representation changes must preserve a
  public-looking test accessor, while changes to the gateway's detailed
  `needs_you` payload can drift without any consumer test noticing.
- **Impact:** small dead surface and unclear intended contract depth.

### L7. The two locked design sources disagree on event topology and retry policy

- **Scope:** design drift surfaced by S4. The code follows parts of each source.
- **Confidence:** 100/100 that the documents conflict; no standalone runtime
  severity is assigned beyond Low because the detailed design explicitly chose
  the two-source path.
- **Anchors:** `CONTROLPLANE.md:Watch`; external
  `tm-controlplane-design-fable.md:Tension 3`.
- **Failure mechanism:** `CONTROLPLANE.md` says all three events arrive through
  Activity SSE. The detailed locked design says `turn_completed` arrives through
  typed `tm_events`. `CONTROLPLANE.md` now says transient delivery keeps facts
  and retries; the detailed design says failed delivery is dropped and never
  retried into a storm.
- **Maintenance scenario:** one corrective PR follows the living reference and
  moves completion into Activity, while another follows the detailed design and
  strengthens the Python LISTEN path. Similar disagreement changes whether
  delivery idempotency is required.
- **Impact:** reviewers and future slices cannot infer the authoritative
  invariant from the locked documents alone. The established Activity contract
  also says NOTIFY is routing metadata and durable state must be reread, while
  S4's live wire path treats payload fields as completion facts.

### L8. A bindingless finalized exchange is silently dropped from the live path

- **Scope:** S4 surfaced. The observer's nullable binding result is preexisting;
  the branch adds strict live-signal parsing without an immediate fallback.
- **Confidence:** moderate; normal shared-proxy finalization usually retains a
  binding.
- **Anchors:**
  `api/src/transport_matters/wire_store_observer.py:WireStoreObserver._resolve_run`,
  `on_exchange`;
  `api/src/transport_matters/session/writer.py:SessionWriter.submit_wire_exchange`;
  `api/src/transport_matters/session/listen.py:_parse_wire_exchange_signal`.
- **Failure mechanism:** when no binding is available, the observer writes
  `workspace_slug=None` and `workspace_hash=None`. The writer still emits
  NOTIFY, but `_parse_wire_exchange_signal` returns `None` unless run id,
  exchange id, both workspace parts, and owner are nonempty. Dropping the
  payload does not enqueue a catch-up marker.
- **Failing scenario:** a finalize or recovery sink runs after its proxy binding
  disappeared while a watcher is active. The durable row may be owner-resolvable
  through session or lifecycle state, but WATCH sees nothing until some later
  listener reconnect or 1,000-event cursor advance happens to run catch-up.
- **Impact:** delayed or indefinitely absent completion notification on a
  supported best-effort binding edge.

## Scope summary

No finding above is a preexisting-only defect charged to S4. B1, B2, N1, N2,
N4, N5, and all direct registry or delivery concerns are introduced by S4 or
its correction. B3, M1, M2, M3, N3, and L8 combine new WATCH assumptions with
older PTY or wire-store behavior. The older behavior remains valid for its
original fire-and-forget or reconciliation consumers; S4 creates the stronger
and currently unmet contract.

## Clean areas verified

- Terminal text neutralization is sound for this slice. Python removes Cc, Cf,
  Cs, Zl, and Zp categories, collapses whitespace, caps names, and enforces the
  same 4,096 UTF-16-unit budget checked by TypeScript.
- The envelope has one policy owner in Python. TypeScript performs only a
  defense-in-depth terminal boundary check and the dumb nudge primitive.
- REST and MCP WATCH skins remain thin delegates to the same Python service.
- Direct self events are suppressed, duplicate notifications inside the current
  dedupe window are suppressed, and damping-boundary facts are retained for the
  next flush.
- Existing terminal `write` and `resize` behavior during `TERMINATING` remains
  fire-and-forget as intended. The result problem is confined to using that
  contract for `nudge`.
- All new files are below 700 lines. L2 records the immediate headroom risk.

## Correction order

1. Add causal provenance and loop suppression before enabling reciprocal WATCH.
2. Replace the boolean nudge with a typed PTY acceptance result and an
   idempotent delivery key spanning Python and the gateway.
3. Make completion reconciliation use a durable commit-ordered identity and
   treat NOTIFY as a doorbell. Cover late commit, replay, overflow, and reconnect
   with real PostgreSQL transaction tests.
4. Separate response completion from response IR parse success.
5. Revalidate buffered facts after watch mutations and close registration under
   one lifecycle guard.
6. Extract wire replay, activity consumption, delivery, and test support before
   adding the correction, keeping `watch.py`, its tests, and
   `createRuntimeRouter` within the project guardrails.

## Additional findings beyond the first bus reply

The first reply already contained B1, B2, B3, M1, M2, M3, N1, and N4. The
additional items in this document are:

`N2, N3, N5, L1, L2, L3, L4, L5, L6, L7, L8`.
