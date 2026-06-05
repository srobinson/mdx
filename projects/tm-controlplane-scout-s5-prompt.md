# Scout: control-plane S5 — prompt verb + deferred B1 causal-ancestry fix

Scouted read-only on main at `3dfa33e` (S4 watch merged). Tree verified pristine
(`git status --porcelain` empty) before this output. Spec: CONTROLPLANE.md
"Prompt" and "Watch" sections. All symbols verified by direct read at this SHA.

## 1. Reuse map for the prompt verb

| Capability | Owner | Verdict |
|---|---|---|
| Resultful PTY input primitive (`POST /v1/runs/{id}/input` → `RunManager.deliverInput` → `PtySession.tryWrite`) | none found | **must-build** |
| Service verb dispatch | `controlplane/service.py` `ControlPlaneService` | reuse |
| Entitlement (director gate) | none found (role carried, never checked) | must-build (trivial) |
| Grant resolution (S1) | `controlplane/grants.py` `ControlPlaneGrantStore.resolve`, `ActiveControlPlaneGrantResolver` | reuse as-is |
| Audit persistence (S2) | `controlplane/audit.py` `ControlPlaneAuditWriter.write`, `ControlPlaneAction` | reuse as-is |
| Observe-vs-action audit decision | convention, not mechanism | follow watch pattern |
| Envelope + terminal-safe text (S4) | `controlplane/envelope.py` `format_watch_envelope`, `_terminal_safe_text` | extend in place |
| `dispatch_id` | column only (`control_plane_action.dispatch_id`, audit.py) | must-build minting |
| Fan-out to N targets | none found | must-build |
| Interrupt / break bytes (Esc) | none found anywhere | must-build in gateway |
| Per-target receipt shape | none; nearest is `ControlPlaneTargetOutcome` | must-build DTO |

### Input primitive: must-build, and `nudge` is not a superset seed

Searches run: `deliverInput`, `tryWrite`, `/input` across `packages/` and
`api/src` — zero hits. What exists after S4:

- `packages/runtime/src/server/runtimeRouter.ts:158` `POST /runs/:runId/nudge`
  → `RunManager.nudge` (`packages/runtime/src/service/RunManager.ts` sym
  `nudge`) → `run.session.write(text + "\r")`, returns bool, 202/400/404.
- `validRuntimeNudge` (same file, sym `validRuntimeNudge`) **rejects every
  control character** (≤0x1f and 0x7f–0x9f) and caps at
  `MAX_RUNTIME_NUDGE_CHARS` 4096.

So nudge structurally cannot carry break bytes (Esc = 0x1b), bracketed paste
(`ESC [ 200~`), or multi-line text, and returns a bare boolean, not the typed
delivery outcome the spec names. S5 builds `deliverInput` as the general
primitive (modes: nudge | interrupt; owns break bytes, settle timing, bracketed
paste, submit; typed outcome). The S4 nudge path should become a caller of
`deliverInput` (trusted single-line mode), not a parallel implementation;
`PtySession` (`packages/runtime/src/ports.ts` sym `PtySession`) has `write`
only — `tryWrite` (liveness-checked write with typed result) is new. The
liveness/settle checks nudge does inline (`liveRun`, `state === "RUNNING"`,
`run.settle === null`) are the seed for `tryWrite`'s outcome taxonomy.

### Service verb dispatch + skins (S2/S3 pattern)

`ControlPlaneService` methods take `principal` first and translate domain
errors to `ControlPlaneError` codes; gateway errors map via
`_gateway_response_error` (service.py). Skins are logic-free:
`api/v1/controlplane_mcp.py` `_ControlPlaneTools._invoke` wraps every tool,
`api/v1/controlplane_routes.py` mirrors REST. `prompt()` slots in as one more
service method plus one tool plus one route; watch (S4) is the template for a
verb that owns an engine dependency injected at `main.py` wiring.

### Entitlement: the director gate does not exist yet

`ControlPlanePrincipal.role` (`controlplane/models.py`) is resolved and carried
end to end, but grep for role checks in service/skins finds none — all five
shipped verbs are observer-level. Prompt is the first director verb: add a
small `_require_director(principal)` in the service raising
`ControlPlaneError("forbidden", ...)`. One helper, reused by launch/manage
later.

### Audit + dispatch_id

`control_plane_action` (migration 0013) already has `text`, `mode`,
`dispatch_id`, `outcomes` — the prompt record needs zero schema change.
Builder pattern: `controlplane/watch_audit.py` (`watch_action`,
`watch_delivery_action`) constructs `ControlPlaneAction`; add a sibling
`prompt_action` builder. Observe-vs-action is decided by convention: pull
verbs never call the audit writer; action verbs construct and write a record
per call (watch registration and delivery both do). Nothing mints a
`dispatch_id` today (grep: audit.py and its migration test only); prompt mints
one UUID per fan-out call.

### Envelope

`controlplane/envelope.py` is the declared "single owner for agent-facing
control plane envelope text": UTF-16 budget (4096, mirror-tested against the
runtime constant by `test_watch_nudge_utf16_budget_matches_the_runtime_contract`),
`_terminal_safe_text` (control/format char neutralization + truncation),
prefix + overflow composition. The prompt envelope
`[tm from a1b2 «Director»]` belongs here as a sibling formatter reusing
`_terminal_safe_text` and the budget constants (rename the `WATCH_*` budget
constants to shared names or add prompt-named aliases — decision-light).
Sender-name resolution: reuse the `_resolve_names` shape in watch.py, backed
by `ControlPlaneReadPort.sessions_for_runs`.

### Fan-out + receipts

No fan-out exists (watch delivers to exactly one watcher per flush).
Per-target receipt `{run_id, delivered | failed, reason}`: build a pydantic
result model in `controlplane/observe_models.py` style; the audit
`ControlPlaneTargetOutcome {target, status, reason, details}` is the same
shape — derive the audit outcomes from the receipts so there is one
construction. Partial failure is receipt data, never an exception (spec), so
the prompt loop must catch per-target `GatewayResponseError` /
`GatewayUnavailableError` where watch's single-target flush re-raises.
Gateway HTTP plumbing to reuse: `api/v1/run_proxy.py` `deliver_watch_nudge` is
the exact template for a `deliver_input` port method (`_run_route_path`,
`_request_http`, status mapping); `WatchNudgeDeliveryPort`
(`controlplane/activity.py`) shows the port shape to extend.

### Interrupt / break bytes

No Esc/break handling exists anywhere in the repo (searched `x1b`/`u001b`
escape literals in runtime service+server, and `interrupt` repo-wide — hits
are activity-state names and process SIGINT code, not PTY break). The spec
puts break bytes + settle in the gateway primitive. Note: Esc is specified for
Claude Code; the Codex CLI break key needs verification during build (its TUI
also uses Esc, but confirm against the pinned codex version before hardcoding
a per-harness table in the gateway).

## 2. B1 causal-ancestry seam map

The reciprocal-watch-loop: A watches B, B watches A; every delivered nudge
actuates a turn, every completed turn nudges the peer — a perpetual loop. The
chain, link by link, with the contract each hop carries:

1. **Delivery origin** — `watch.py` `_flush_serialized` →
   `WatchNudgeDeliveryPort.deliver_watch_nudge(run_id, owner, text)`
   (`controlplane/activity.py`). Text-only. **Originless.**
2. **Proxy hop** — `api/v1/run_proxy.py` `deliver_watch_nudge` → gateway
   `POST /runs/{id}/nudge?owner=` body `{"text"}`. **Originless.**
3. **PTY write** — `runtimeRouter.ts` nudge route → `RunManager.nudge` →
   `PtySession.write(text + "\r")`. Raw bytes into the harness stdin; any
   structured origin dies here by nature of the medium.
4. **Target's turn recorded** — the harness submits the nudge line as user
   input; the proxy captures the outbound request; the exchange persists via
   `wire_store_observer.py` → `SessionWriter.submit_wire_exchange`
   (`session/writer.py`) → `wire_exchange` row (migration 0008). Columns
   carry identity/usage only; `request_metadata` / `request_extras` jsonb
   exist but nothing writes an origin. **Originless.**
5. **Commit signal** — `writer.py` `_wire_exchange_notify_payload`
   `{run_id, exchange_id, workspace, owner, turn_index, track_role,
   has_response}` → `session/listen.py` `WireExchangeSignal`. **Originless.**
6. **Watch consumption** — `watch.py` `_consume_wire_exchange` →
   `ControlPlaneReadPort.completed_wire_turn` → `CompletedWireTurn
   {exchange_id, run_id, turn_index, committed_at}`
   (`controlplane/read_store.py`). **Originless.**
7. **Nudge decision** — `watch.py` `_record_completed_turn` buffers
   `WatchFact {kind, run_id, status, turn_number}`
   (`controlplane/watch_models.py`) per watcher. **This is the suppression
   point**, and WatchFact is originless.

Every contract in hops 1–7 is text-only or originless; that is exactly why B1
could not land in S4. Hop 3 is the structural break: PTY input is bytes, so an
origin id can only survive it (a) embedded in the envelope text and parsed
back out of the captured request, or (b) held server-side across the hop.

### Cheapest correct shape (proposal)

**A process-resident pending-ancestry ledger inside the control-plane
service** — zero cross-boundary contract changes, no schema change:

- New small module (e.g. `controlplane/causality.py`):
  `pending: dict[target_run_id, frozenset[run_id]]` plus a marked-at
  timestamp.
- **Tag at origin**: after a successful delivery, the deliverer records
  ancestry. Watch flush (`_flush_serialized`, after `delivered=True`):
  `pending[watcher] |= union({fact.run_id} | ancestry_of(fact))`. Prompt verb:
  `pending[target] |= {actor_run_id} | pending_ancestry_of(actor)`.
- **Bind to the turn**: in `_consume_wire_exchange`, when run X's completed
  turn arrives, `ancestry = pending.pop(X)` — that turn is control-plane
  actuated with that ancestry. Keep it on a short per-run
  `last_turn_ancestry` for fact tagging.
- **Suppress**: in `_record_completed_turn`, skip watcher W when
  `W.principal.run_id ∈ ancestry`. Transitive union breaks loops of any
  length (A→B→C→A), because each delivery folds the actuating turn's ancestry
  into the target's pending set.
- **Expiry**: pop on the first completed turn after the mark; TTL fallback
  (minutes) so a stale mark cannot suppress forever after human interleaving.

Why in-memory is correct enough: subscriptions and damping are already
process-resident by spec ("they die with the API, as the runs do") — when the
ledger dies, the subscriptions that could loop die with it. If durability is
ever wanted, the landing spot is a stamped `wire_exchange.request_extras` key
or a column, written at hop 4; that is the expensive variant, not the S5 one.

Alternative considered and not recommended as primary: embed a short
`dispatch_id` in the envelope text and extract it in the exchange recorder at
hop 4. Durable and restart-proof, but it teaches the capture plane
control-plane grammar (boundary violation) and rides on text the harness may
rewrap. Worth adding the id to the envelope anyway for observability; do not
make suppression depend on parsing it back.

Over-suppression tradeoff to accept: if a human prompt and a watch nudge both
land before X's next turn, that turn carries the nudge's ancestry and one
legitimate notification may be suppressed. Fail-safe in the right direction
(one missed nudge versus an infinite loop); the watcher still catches up via
observe.

### 2.1 Adjudication: the active-turn race (builder objection)

Objection: target X mid-turn at delivery → the in-flight (non-induced) turn
completes first and consumes `pending[X]`; the induced turn completes later
untagged and escapes, so the loop is not broken; correctness allegedly needs
a durable dispatch marker.

**Can the pure A↔B loop persist under naive pop-on-next-completion? No,
for three independent reasons:**

1. **Alternation makes the target idle at delivery.** In the pure loop, the
   nudge to A is triggered by B's completion, and A's previous induced turn
   already completed (that completion is what nudged B). Nothing else drives
   A, so A is idle when the delivery lands and the tag binds to the induced
   turn correctly.
2. **Shifted binding carries identical content.** Ancestry is a set of
   run_ids, not a per-dispatch token. In an A↔B loop every delivery to B
   carries the same set (`{A} ∪ transitive`), so even when overlap shifts the
   binding by one turn, the popped tag equals the tag the induced turn should
   have carried. Suppression fires regardless.
3. **Every escape re-arms the peer.** An untagged induced turn that escapes
   produces a delivery, and that delivery writes `pending[peer]` before the
   peer's induced turn can start (PTY input lands next turn, strictly after
   delivery). At most one turn can be in flight at delivery time, so the
   shift is at most one and cannot compound; the loop damps within one hop.
   Persistence would require an external turn generator continuously keeping
   both sides mid-turn at every delivery — at which point the "loop" is
   rate-bounded by that external driver, not self-sustaining.

The race's real cost is a one-turn binding shift: one over-suppressed
notification and one escaped nudge in mixed (human-interleaved) traffic.

**In-memory hardening, no durable marker (turn start IS observable):**

- The watch engine already observes turn starts: `feed.activity` holds each
  run's live status/tier, updated per SSE delta in `_apply_activity_delta`
  (`watch.py`), derived once in the gateway activity context per
  CONTROLPLANE.md. An idle→working transition is a turn start.
- Cheapest mechanism, zero new contracts: at delivery time the engine reads
  its own `feed.activity[target].tier`. Idle at acceptance → bind the tag to
  the next completed turn (the induced one). Working or unknown at
  acceptance → span two completions: tag the in-flight turn and the next one
  (fail-safe over-suppression absorbs SSE skew). The ledger keeps a
  remaining-completions counter instead of pop-once.
- Optional hardening when S5 builds `deliverInput` anyway: the typed delivery
  receipt can report target agent-state at the PTY write instant (the
  gateway composition root injects an agent-state lookup into the runtime
  router), eliminating the SSE-lag window entirely. Not required for
  correctness of loop suppression, since the failure direction of skew is
  over-suppression, never escape-forever.

**Verdict: in-memory-fixable.** The durable wire marker remains the
durability upgrade path (wire-store integrity slice), not an S5 correctness
requirement.

## 3. Quality map (prompt + watch area)

Verified first-hand at 3dfa33e:

- **Byte-identical duplicates**: `watch.py` `_remove_ended_watcher` and
  `_remove_missing_watcher` are the same four lines under two names. Collapse
  before S5 grows the file.
- **Dead branch**: `run_proxy.py` `deliver_watch_nudge` — the
  `status_code >= 500` raise is byte-identical to the unconditional fallthrough
  raise below it. S5 will clone this method for `deliver_input`; fix it first
  so the copy is clean.
- **Audit writes under the engine-wide `_registry_lock`**: `_watch_serialized`
  performs up to four Postgres audit INSERTs while holding the lock that gates
  all activity and wire delivery (`watch.py`, registration path). A slow audit
  write stalls every workspace's watch delivery. Prompt should not copy this
  shape: decide under the lock, write audit outside it.
- **Damping re-arm hack**: `_flush_after_interval`'s finally block re-inserts
  an already-buffered fact purely to trigger `_buffer_fact`'s
  create-flush-task side effect. Extract `_schedule_flush(watcher)`; B1's
  suppression sits adjacent to this code and should not inherit the idiom.
- **Headroom**: `watch.py` is 691 lines against the 700 hard cap. S5 touches
  this file (suppression in `_record_completed_turn` / `_consume_wire_exchange`
  and the flush ledger write). The B1 ledger must be its own module and the
  duplicate/hack cleanups above should land first or alongside, or the cap is
  breached immediately.
- **Boundary risk**: retry-vs-drop delivery classification currently leaks
  through which httpx exception type escapes `_request_http`
  (`run_proxy.py`) — `ConnectError` means retry, everything else means drop.
  `deliver_input` will need the same classification; prefer making the outcome
  explicit at the port (typed result) rather than inheriting
  exception-type-as-contract.
- Two parallel `FakeReads` test fakes born in S4 (`watch_test_support.py` and
  `test_service.py`) implement the same read-port methods; S5 tests should
  consolidate on `watch_test_support.FakeReads`, not add a third.

## 4. Plan

### Decisions needed (5)

1. **B1 ledger placement**: in-memory service ledger (proposed) vs durable
   stamp on `wire_exchange`. Proposal: in-memory; durability deferred with the
   wire-store integrity cleanup already on NOW.md.
2. **Suppression scope**: `turn_completed` only (proposed for S5) vs also
   `state_changed` attributable to the actuated turn. Never suppress
   `needs_you` — a genuinely blocked run must always surface.
3. **Input-primitive consolidation**: `deliverInput` as the one write path
   with the S4 nudge route/`RunManager.nudge` refit as its trusted single-line
   mode (proposed, per DRY), vs leaving nudge parallel.
4. **Codex break byte**: verify the pinned codex CLI's interrupt key before
   encoding the per-harness break table in the gateway.
5. **Envelope id**: include a short `dispatch_id` token in delivered envelope
   text for observability (proposed: yes, cheap) — suppression never depends
   on it.

### Proposed steps (bound to the reuse map)

1. **Gateway input primitive**: `PtySession.tryWrite` outcome type in
   `ports.ts`; `RunManager.deliverInput(runId, owner, {text, mode})` owning
   break bytes (per-harness), settle, bracketed paste, submit;
   `POST /runs/:runId/input` in `runtimeRouter.ts` returning the typed
   outcome; refit nudge onto it (decision 3). Colocated vitest incl. the
   RunManagerNudge.test.ts pattern.
2. **Service prompt verb**: `_require_director`; fan-out loop with per-target
   receipts (`PromptResult`); envelope formatter in `envelope.py`;
   `dispatch_id` minting; `prompt_action` audit builder; port method
   `deliver_input` on the gateway port beside `deliver_watch_nudge`
   (template: run_proxy `deliver_watch_nudge`, minus the dead 5xx branch).
3. **Skins**: MCP tool + REST route via the existing `_invoke` /
   routes pattern; contract tests per S2/S3 shape.
4. **B1**: `controlplane/causality.py` ledger; write-on-delivery in
   `_flush_serialized` and the prompt executor; pop-and-tag in
   `_consume_wire_exchange`; suppress in `_record_completed_turn`; pre-clean
   the watch.py duplicates for headroom.
5. **Tests + gates**: unit — director gate denial, fan-out partial failure
   receipts, envelope budget, ledger transitivity (A→B→A and A→B→C→A
   suppressed; unrelated watcher unaffected; TTL expiry), nudge-refit parity.
   Integration — extend the S1 end-to-end (spawn with director grant → prompt
   peer → receipt + audit row) and a reciprocal-watch loop test proving one
   nudge each and then silence. Gates verbatim: `just check` and `just test`
   (api), `pnpm --filter @tm/runtime test` + full `pnpm --filter @tm/shell
   test` for the runtime seam (structural TS changes take the full suite).
