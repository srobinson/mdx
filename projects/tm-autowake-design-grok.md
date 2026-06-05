# B1 auto-wake design: durable delivery → turn causal binding

Author: grok design pane  
Base: scout `~/.mdx/projects/tm-autowake-scout.md` on `controlplane-autowake` @ `e05373b`  
Scope: durable reciprocal wake (CONTROLPLANE.md slice #22). Read-only design. No implementation.

## 1. Problem

WATCH already has two durable-aware sources:

- wire finalize → `turn_completed` via `ControlPlaneWatchEngine._consume_wire_exchange`
- Activity SSE → `state_changed` / `needs_you` via `_record_activity_delta`

A delivered control-plane input (prompt, launch first prompt, or watch nudge) can actuate a peer turn. Under reciprocal watches (A watches B and B watches A), that induced turn legally re-wakes the peer. Damping and self-exclusion do not stop the loop.

The rejected in-memory `CausalAncestryLedger` failed because it bound observation order, not causality. B1 needs an exact, replayable relation:

```
delivery_id  →  first outbound provider request that contains that delivery
             →  finalized wire_exchange.exchange_id that completed that request
```

Correctness must not depend on PTY HTTP receipt order, wire doorbell order, or Activity SSE order.

## 2. Goals and non-goals

### Goals

1. Bind a specific delivery to the specific turn it causes through a durable, replayable anchor.
2. Wake a reciprocal watcher exactly once for the independent turn that started the chain; suppress notifications of the induced turn to agents in that turn's causal ancestry.
3. Survive API restart, lost notifications, queue overflow, and reconnect via durable catch-up.
4. Handle edge cases: delivery never produces a turn; multiple deliveries before one request; ambiguous PTY acceptance; out-of-order observation.
5. Reuse existing seams; add one join relation, not a second turn oracle.

### Non-goals

- Changing the public WATCH event catalog or damping interval policy.
- Making watch subscriptions durable across API restart (still process-resident with runs).
- Using Activity projections or `state_at_write` as binding authority.
- Solving the wire parse-failure completion hole inside B1 product code (B1 depends on the already-queued wire-store integrity cleanup; see §9).

## 3. Binding mechanism

### 3.1 Core idea

**Token-proved request binding with durable delivery lifecycle.**

1. Allocate a unique `delivery_id` **before** any PTY write.
2. Embed that full identity in the terminal envelope as a search token.
3. Persist a delivery row in Postgres in status `intended` before calling the gateway.
4. When a wire exchange is written for the target run, extract user-message text from the request, find embedded delivery tokens, and **bind** each unmatched delivery whose token appears to that `exchange_id`.
5. When that exchange is a completed parent turn (`response_id IS NOT NULL` after integrity fix, non-subagent), mark the delivery `completed`.
6. Watch emission consults the same row: if the prospective watcher is in the exchange's **cause ancestry**, suppress `turn_completed` and attributable `state_changed`. `needs_you` stays visible.

The wire exchange remains the turn-completion authority. The new relation only answers "which control-plane delivery caused this exchange?"

### 3.2 Why token-in-request, not FIFO completion

| Approach | Failure mode |
| --- | --- |
| Next observed completion after PTY receipt | Race with in-flight human turn; proven unsound |
| In-memory pending counter + Activity idle | Two streams, stale `state_at_write`, infinite reciprocal loop |
| FIFO by acceptance time alone | Human typing and harness queue reorder; binds wrong request |
| **Token present in outbound request text** | Identity survives HTTP loss; exact request relation; replayable |

The capture plane already stores request message bodies content-addressed (`wire_request_message` → `wire_blob`). The delivery token is a stable substring of those bodies. Truncation is prevented by using a compact fixed marker (see §5.2) and reserving budget in envelope formatting.

### 3.3 Identity before side effects

Every PTY-bound control-plane write allocates its own `delivery_id` (UUID v4):

| Path | Seam | Scope of one delivery_id |
| --- | --- | --- |
| Prompt fan-out | `ControlPlaneService.prompt` → `_deliver_prompt_target` | One per target |
| Launch first prompt | `ControlPlaneLauncher._execute` → `deliver_first_prompt` | One per launch attempt |
| Watch flush | `ControlPlaneWatchEngine._flush_serialized` | One per watcher flush batch |

`dispatch_id` remains the fan-out / launch experiment id on `control_plane_action`. It is **not** the causal key. One dispatch can create many deliveries.

### 3.4 Lifecycle states

```
intended → accepted | rejected | unknown
accepted | unknown → bound → completed
accepted | unknown → orphaned     # no resulting request within policy
intended → abandoned              # never reached gateway (local preflight fail)
```

| Status | Meaning | Causal effect |
| --- | --- | --- |
| `intended` | Row written; PTY call not finished | Not yet eligible to suppress |
| `accepted` | Gateway/PTY reported delivered | Waiting for bind |
| `rejected` | Definite non-acceptance | Never binds; never suppresses |
| `unknown` | Ambiguous HTTP/transport | May still bind if token appears on wire |
| `bound` | Token found in request for `exchange_id` | Suppress ancestry for that exchange (state_changed during that turn; turn_completed at finalize) |
| `completed` | Bound exchange is a completed parent turn | Same suppression; terminal for wake logic |
| `orphaned` | Accepted/unknown past deadline with no bind | No suppression; honest "never produced a turn" |
| `abandoned` | Local failure before gateway call | No suppression |

Honest ambiguity: `unknown` is never rewritten to `accepted` or `rejected` by guesswork. Binding from wire content can still promote `unknown → bound` because the token on the provider request is stronger evidence than the lost HTTP receipt.

## 4. Schema / migration

Next migration after `0016_action_dispatch_idempotency` (e.g. `0017_control_plane_delivery`).

```sql
CREATE TABLE control_plane_delivery (
    delivery_id          uuid PRIMARY KEY,
    owner                text NOT NULL,
    workspace_id         text NOT NULL,
    target_run_id        text NOT NULL,
    source_kind          text NOT NULL
        CHECK (source_kind IN ('prompt', 'launch_first', 'watch')),
    source_actor_run_id  text NOT NULL,          -- prompter / launcher actor / watcher
    source_dispatch_id   uuid,                   -- prompt/launch dispatch; watch flush id
    cause_run_ids        text[] NOT NULL DEFAULT '{}',
    cause_exchange_ids   text[] NOT NULL DEFAULT '{}',
    inherited_cause_run_ids text[] NOT NULL DEFAULT '{}',
    token                text NOT NULL,          -- exact envelope marker, unique
    envelope_text        text NOT NULL,          -- bytes intended for PTY
    mode                 text,                   -- nudge | interrupt | null
    status               text NOT NULL
        CHECK (status IN (
            'intended','accepted','rejected','unknown',
            'bound','completed','orphaned','abandoned'
        )),
    pty_reason           text,                   -- gateway failure reason when present
    bound_exchange_id    text
        REFERENCES wire_exchange(exchange_id) ON DELETE SET NULL,
    intended_at          timestamptz NOT NULL DEFAULT now(),
    terminal_at          timestamptz,            -- accepted/rejected/unknown/abandoned time
    bound_at             timestamptz,
    completed_at         timestamptz,
    orphaned_at          timestamptz,
    CONSTRAINT control_plane_delivery_token_uq UNIQUE (token),
    CONSTRAINT control_plane_delivery_bound_ck CHECK (
        (status IN ('bound','completed') AND bound_exchange_id IS NOT NULL)
        OR (status NOT IN ('bound','completed'))
    )
);

CREATE INDEX control_plane_delivery_target_open_ix
    ON control_plane_delivery (target_run_id, intended_at)
    WHERE status IN ('intended','accepted','unknown');

CREATE INDEX control_plane_delivery_bound_exchange_ix
    ON control_plane_delivery (bound_exchange_id)
    WHERE bound_exchange_id IS NOT NULL;

CREATE INDEX control_plane_delivery_owner_ws_ix
    ON control_plane_delivery (owner, workspace_id, intended_at DESC);

-- partial unique: at most one open row per token already covered by token_uq
```

No mutation of `wire_exchange` schema. Optional later: denormalized `caused_by_delivery_id` on exchange is rejected for B1 to avoid dual write paths; the delivery table is the join.

`control_plane_action` stays the audit of intent/outcomes. Delivery rows are the causal substrate. Successful watch flushes that today write **no** durable success row must write a delivery row (and may continue best-effort audit).

### 4.1 Cause ancestry columns

For a watch delivery flushed to watcher W about facts F:

- `source_actor_run_id = W` (recipient of the nudge)
- `cause_run_ids` = distinct `fact.run_id` for facts in the batch
- `cause_exchange_ids` = exchange ids for `turn_completed` facts in the batch (wire path always has them; see §6.2 for Activity-only facts)
- `inherited_cause_run_ids` = union of cause ancestries of those cause exchanges (transitive)

**Effective suppression set** for an exchange E:

```
suppress_runs(E) =
  union over deliveries D bound|completed to E where D.source_kind = 'watch':
      D.cause_run_ids ∪ D.inherited_cause_run_ids
```

Prompt and launch_first deliveries record `source_actor_run_id` for attribution and eval but **do not** put the director into `suppress_runs`. Directors who prompt and watch must still observe completion of the work they requested. Reciprocal ping-pong is a watch↔watch phenomenon.

Transitive inheritance: if B's turn E1 induced watch delivery D1 to A, and A's turn E2 is bound to D1, then a later watch delivery D2 about E2 carries `inherited_cause_run_ids` including B. A's subsequent induced work continues to suppress B.

## 5. Seams (file:symbol) and changes

### 5.1 New module

`api/src/transport_matters/controlplane/delivery.py` (new)

Owns:

- `allocate_delivery(...)` → insert `intended`
- `mark_pty_outcome(delivery_id, status, reason)`
- `bind_tokens_in_exchange(run_id, exchange_id, request_text_parts)` (idempotent)
- `complete_exchange(exchange_id)` (idempotent)
- `suppress_runs_for_exchange(exchange_id) -> frozenset[str]`
- `orphan_expired(now, ttl)`

Port protocol for tests. Writer uses the session pool pattern of `ControlPlaneAuditWriter`.

### 5.2 Envelope tokens

`api/src/transport_matters/controlplane/envelope.py`

- Add `format_delivery_token(delivery_id: UUID) -> str` producing a fixed marker, e.g. `#tm-d:<32-hex>`.
- `format_prompt_envelope`: take `delivery_id` (per target) in addition to display `dispatch_id`; embed the **full** delivery token. Keep short dispatch display if useful for humans, but causal match uses only the full delivery token.
- `format_watch_envelope`: take `delivery_id`; prefix becomes e.g. `[tm watch #tm-d:<32-hex>] ...` so the token is always present even when fact text truncates.

Budget: token length is fixed (~38 UTF-16 units). Reserve it before truncating body text. Mirror budget tests already guard `MAX_CONTROL_PLANE_INPUT_UTF16_UNITS` against `RunInputDelivery.MAX_RUNTIME_INPUT_CHARS`.

### 5.3 Prompt delivery

`api/src/transport_matters/controlplane/service.py:ControlPlaneService.prompt`

- Today formats one envelope for all targets with only `dispatch_id`.
- Change: per target, `allocate_delivery(source_kind='prompt', ...)`, format envelope with that `delivery_id`, then `_deliver_prompt_target`.
- After gateway return: `mark_pty_outcome`.
- Pre-gateway local failures: `abandoned`.
- `_audit_prompt` outcomes gain `delivery_id` in `details` (no schema change to audit table; jsonb details).

### 5.4 Launch first prompt

`api/src/transport_matters/controlplane/launch_delivery.py:deliver_first_prompt`  
`api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher._execute`

- Allocate delivery before `deliver_input`.
- Persist delivery id into launch audit details / ledger frozen outcome (ledger remains process-resident for single-flight; delivery row is the durable causal record).

### 5.5 Watch flush

`api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine._flush_serialized`

Before `gateway.deliver_input`:

1. Resolve cause exchange ids for facts (see §6.2).
2. Compute `inherited_cause_run_ids` via `delivery` store.
3. `allocate_delivery(source_kind='watch', target=watcher_run_id, cause_*)`.
4. Format watch envelope with that `delivery_id`.
5. Deliver; mark pty outcome.
6. On definite connect failure: restore facts **and** mark delivery `rejected` or leave `intended`→`rejected`; do not leave a suppress-capable open delivery if bytes never went out. On ambiguous outcome: `unknown` (may still bind).

Successful watch deliveries become durable via this row even when audit remains best-effort.

### 5.6 Runtime PTY primitive

`packages/runtime/src/service/RunInputDelivery.ts:deliverInput`  
`packages/runtime/src/service/RunManager.ts:RunManager.deliverInput`  
`api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy.deliver_input`

**No required protocol change for B1.** Acceptance remains "bytes accepted by live PTY". Causal identity lives in the text and in Postgres written by Python before the call.

Optional hardening (same slice or immediate follow-up): accept optional `delivery_id` on `POST /v1/runs/{id}/input` and echo it on the result for log correlation only. Do **not** make Node write Postgres.

### 5.7 Bind at wire write

Primary hook: after a successful `write_wire_exchange` inside the same transaction as the exchange upsert, or immediately after commit in `SessionWriter.submit_wire_exchange` before NOTIFY.

Preferred: **same transaction as exchange write** so a bound delivery cannot exist without the exchange, and restart never sees an exchange without a committed binding attempt.

Seams:

- `api/src/transport_matters/session/writer.py:SessionWriter.submit_wire_exchange`
- `api/src/transport_matters/session/wire_store.py:write_wire_exchange` (extract text helpers only; keep store free of control-plane imports if possible)
- New pure helper `controlplane/delivery_bind.py:extract_delivery_tokens(text) -> frozenset[str]`
- Request text extraction from normalized request messages / blob bodies already available on `WireExchangeWrite.request`

Algorithm (idempotent):

```
tokens = extract from all user-role message texts in write.request
for each token matching open delivery for write.run_id:
    UPDATE ... SET status='bound', bound_exchange_id=write.exchange_id, bound_at=now()
    WHERE token = $1 AND status IN ('intended','accepted','unknown')
      AND target_run_id = write.run_id
if write has completed parent response:
    mark deliveries bound to this exchange_id as completed
```

Multiple tokens in one request: each binds to the same `exchange_id` (many deliveries, one turn). Deterministic and allowed.

No token match: deliveries stay open until orphan policy. **Never** bind by "next completion".

Duplicate finalize / UPSERT replay: bind updates are idempotent (`WHERE status IN open`); completed mark is idempotent.

### 5.8 Watch emission suppression

`api/src/transport_matters/controlplane/watch.py`

**`_record_completed_turn`** must receive `exchange_id` (today it drops it after read). Change signature to pass `CompletedWireTurn` through. Before `_buffer_fact`:

```
if watcher.principal.run_id in suppress_runs(turn.exchange_id):
    skip  # optional debug metric
else:
    buffer turn_completed
```

**`_record_activity_delta`** for `state_changed` (not `needs_you`):

- Resolve the **active causal exchange** for `current.run_id` if any:
  - Prefer open `bound` delivery on that run (in-flight induced turn).
  - Else, if transitioning into idle, prefer latest `completed` delivery for that run within a short commit window, or join via wire snapshot the Activity path already treats as end-of-turn oracle (`PostgresActivityReader.readWireSnapshotForRun`).
- If watcher is in `suppress_runs` for that exchange, skip `state_changed`.
- If no binding applies, emit as today (human / unbound work).

**One causal fact for both sources:** both paths call the same `suppress_runs(exchange_id)` read. Order of SSE vs wire doorbell cannot create a second wake for the suppressed peer.

Self-exclusion remains structural and separate.

### 5.9 Read store

`api/src/transport_matters/controlplane/read_store.py` and  
`api/src/transport_matters/session/controlplane_statements.py`

Add owner-scoped queries:

- open deliveries for run
- suppress_runs for exchange
- cause inheritance lookup
- completed deliveries since watermark (for restart diagnostics / tests)

### 5.10 Audit

`api/src/transport_matters/controlplane/watch_delivery.py:audit_watch_delivery`  
`api/src/transport_matters/controlplane/watch_audit.py`

Include `delivery_id` and terminal bind status in details when known. Success-path audit for watch can stay best-effort; delivery row is authoritative for causality.

## 6. Causal edge cases

### 6.1 Delivery never produces a turn

Delivery stays `accepted` or `unknown`. Orphan sweeper (API startup + periodic task in control plane lifespan, or opportunistic on watch flush) marks `orphaned` after TTL (recommend **2 hours** default, config constant). Orphaned deliveries never enter `suppress_runs`. Human turns after an orphaned nudge remain visible to reciprocal watchers.

### 6.2 Multiple deliveries before one request

Each delivery has its own token. If the harness folds several PTY submits into one outbound request and all tokens appear, all bind to that one `exchange_id`. If only a subset appears, only those bind; others remain open or orphan. No FIFO fill-in for missing tokens.

### 6.3 Out-of-order observation

| Race | Outcome |
| --- | --- |
| Wire complete before HTTP receipt returns | Delivery still `intended` or later `unknown`/`accepted`; bind already happened from wire path by token; suppress works from bound row |
| HTTP accepted before any request | Open `accepted`; no suppress yet; peer may still see unrelated turns |
| Activity idle before wire finalize | `state_changed` resolution uses bound open delivery if token already bound at request write (request usually commits with response in one finalize today); if only response-time finalize, idle may race — suppress uses bound row as soon as request side is written. **Implementation detail:** bind on request presence even when `response_id` is null; complete when response lands. |
| API restart mid-flight | Open and bound rows reload from Postgres; process-resident watchers re-subscribe; wire catch-up via `completed_wire_turns_since` re-emits only unsuppressed facts after reread |

### 6.4 Ambiguous acceptance that did actuate

Status `unknown` + later token bind → `bound`/`completed`. Loop protection holds. Audit shows honesty about the HTTP layer.

### 6.5 Ambiguous acceptance that did not actuate

Stays `unknown` → `orphaned`. No false suppress of later human turns.

### 6.6 Active human turn overlapping delivery

If a human turn is already in flight when a nudge is accepted, the nudge's token appears on a **later** request, not the in-flight one. In-flight completion is unbound to that delivery → reciprocal watcher still sees the human completion (correct). Induced turn later binds and is suppressed for cause ancestry.

### 6.7 Queued human input after watch nudge

Same as token rule: whichever request carries the delivery token is the bound turn. Human-only requests do not bind.

### 6.8 Activity facts without exchange_id

`state_changed` and `needs_you` frames do not carry exchange ids. Suppression for `state_changed` joins through the delivery table / wire snapshot (§5.8). `needs_you` never suppressed.

Watch flush cause set: for pure Activity batches with no `turn_completed`, `cause_exchange_ids` may be empty while `cause_run_ids` is populated. Inheritance then uses any currently completed delivery on those cause runs at flush time, or remains shallow (cause runs only). Shallow cause still suppresses the peer run that generated the activity, which is enough to stop A↔B ping-pong on state alone.

## 7. Ping-pong prevention (worked example)

Setup: A watches B (`turn_completed`, `state_changed`); B watches A (same).

1. Human completes B's exchange `E1`.  
   - `suppress_runs(E1)` empty.  
   - A buffers `turn_completed` for B.  
   - Flush: delivery `D1` to A, `cause_run_ids={B}`, `cause_exchange_ids={E1}`, token in envelope.

2. A's harness emits request containing `#tm-d:<D1>` → bind `D1 → E2`. Response completes → `D1.completed`.

3. Wire doorbell for `E2`:  
   - `suppress_runs(E2)` includes B.  
   - B's watcher skips `turn_completed`.  
   - Activity idle for A: B skips `state_changed`.

4. No further forced wake. Chain ends after **one** intentional wake (A learning about `E1`).

If A later does independent work without a control-plane delivery token, B receives notifications normally.

If both sides independently finish human turns, each wakes the other once per independent turn; no suppress because neither exchange is bound to a watch delivery caused by the other.

## 8. Failure and garbage-collection semantics

### 8.1 Failure matrix

| Failure | Durable record | Retry | Suppress? |
| --- | --- | --- | --- |
| Invalid envelope / empty text | no delivery or `abandoned` | caller error | no |
| Gateway connect error before accept | `rejected` (or restore watch facts + no open delivery) | watch damping retry creates **new** delivery_id | no for failed attempt |
| PTY rejected (`run_not_running`, etc.) | `rejected` | no auto retry for prompt; watch may end subscription | no |
| HTTP loss after send | `unknown` | no retry (existing contract) | only if later bound |
| Bind without response (integrity hole) | `bound` only | completeness waits on integrity fix | partial: may suppress state_changed; turn_completed absent until complete |
| Audit write failure | delivery row still commits | audit best-effort | causality unaffected |
| Duplicate wire finalize | idempotent bind/complete | n/a | stable |

### 8.2 GC policy

| Class | Retention | Action |
| --- | --- | --- |
| Terminal `rejected` / `abandoned` | 7 days | DELETE |
| `orphaned` | 7 days after orphaned_at | DELETE |
| `completed` | 30 days (eval/debug) | DELETE; ON DELETE SET NULL on exchange keeps history optional |
| Open `accepted`/`unknown`/`intended` | orphan at 2h | status → orphaned |
| Open rows for exited run | on run terminal Activity | orphan immediately |

GC is reference-light: deliveries do not keep `wire_exchange` alive (`ON DELETE SET NULL`). Wire GC (`sweep_wire_store`) remains independent.

Do **not** use TTL as loop protection. TTL only reclaims storage after identity has done its job or proven inert.

### 8.3 Restart convergence

On API boot:

1. Orphan sweep once.
2. Watch engine starts empty (subscriptions die with process; existing contract).
3. Any still-bound incomplete deliveries remain; when wire catch-up or live finalize arrives, complete + suppress correctly for any re-established watches.
4. No in-memory ledger to rebuild.

## 9. Precondition: wire-store integrity

Scout and `NOW.md` record:

1. `WireStoreObserver.on_exchange` treats parseable response IR as completion; raw-complete parse failures vanish from `completed_wire_turn`.
2. `SessionWriter.submit_wire_exchange` NOTIFY on idempotent UPSERT replay.

B1 PR plan must either:

- land wire-store integrity **before** enabling reciprocal suppress in production, or
- ship binding schema dark and gate suppression behind the integrity fix.

Without (1), an induced turn can complete on the wire, never become a completed wire turn, never mark delivery `completed`, and either fail to wake (if we only wake on complete) or fail to clear open state. Binding tokens can still attach at request write; completion coverage is the remaining hole.

## 10. Verification plan

Must exercise real runtime PTY + capture + Postgres (slice #22 integration bar):

1. **Happy reciprocal:** A watches B, B watches A; human turn on B → exactly one watch delivery to A → A's induced turn → B receives **zero** `turn_completed` / suppressed `state_changed` for that exchange; delivery row `completed` with `bound_exchange_id`.
2. **Activity-before-wire and wire-before-Activity** orderings both suppress once.
3. **Lost gateway response:** kill HTTP after PTY accept; token still binds; suppress holds; status path shows `unknown` then `bound`/`completed`.
4. **No resulting turn:** accept nudge on idle agent that never calls the provider; orphan after TTL; later human turn notifies reciprocal watcher.
5. **Multiple deliveries one request:** two tokens in one user message bind both rows to one exchange.
6. **Active turn race:** delivery during in-flight human turn does not bind to that turn.
7. **Prompt does not suppress director:** director prompts worker and watches worker; worker completion still notifies director.
8. **API restart:** bind while API down (capture path still in same process today — simulate by clearing watch memory and re-watch); durable rows converge.
9. **Unit:** token extract, suppress_runs SQL, envelope budget with full token, idempotent bind/complete.
10. **Regression:** existing watch damping, self-exclusion, connect-error fact restore, prompt audit dispatch uniqueness.

## 11. Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Revive in-memory ancestry ledger | Observation-order races; not restart-safe; already removed |
| Bind on Activity idle only | Not exact request relation; dual-stream loops |
| Extend `control_plane_action` outcomes only | Fan-out shaped; no exchange FK; written after await; successful watch lacks row |
| Runtime-only generation counter without token | Capture plane cannot prove which request consumed which accept without shared durable identity |
| Content hash of full envelope without id | Collision and truncation risk; hard to index; weaker than explicit token |
| Suppress all control-plane-sourced turns from notifying anyone | Breaks director observe-after-prompt; over-broad |

## 12. Key decisions

1. **Durable table `control_plane_delivery` is the causal join**, not process memory and not Activity.
2. **Full delivery token in envelope text is the request-side proof**; short dispatch display tokens stay non-causal.
3. **Wire exchange remains completion authority**; B1 only adds delivery→exchange binding.
4. **Suppression applies to watch-caused ancestry only**, so directors still see prompt-induced completions.
5. **Both WATCH sources share `suppress_runs(exchange_id)`**, eliminating order-dependent ping-pong.
6. **Ambiguous PTY stays `unknown` until wire evidence or orphan**, never guessed.
7. **Wire integrity cleanup is a hard precondition** for claiming complete turn coverage.

## 13. Open questions

1. Orphan TTL default (proposal: 2h open → orphan; 7d delete terminal noise; 30d keep completed for eval). Product may prefer longer eval retention.
2. Whether optional `delivery_id` on the runtime input HTTP API ships in the same PR as the table (proposal: same slice for log correlation, not required for correctness).
3. Whether watch success should also write a full `control_plane_action` row for symmetry with prompt (proposal: delivery row mandatory; action row optional follow-up).

## 14. PR Plan

### PR-1: Wire-store integrity precondition

- **Title:** fix wire completion coverage and NOTIFY replay
- **Files:** `wire_store_observer.py`, `session/writer.py`, wire store tests, `NOW.md` parking-lot exit
- **Deps:** none
- **Description:** Completed raw responses produce completed wire turns even when parse IR fails; idempotent UPSERT does not spurious-NOTIFY. Unblocks honest B1 completion.

### PR-2: Delivery schema + bind library (dark)

- **Title:** add `control_plane_delivery` and token bind helpers
- **Files:** migration `0017_...`, `controlplane/delivery.py`, `delivery_bind.py`, `envelope.py` token helpers, unit tests
- **Deps:** none (can parallelize with PR-1, but suppression not enabled)
- **Description:** Table, allocate/mark/bind/complete/orphan APIs, token format. No behavior change in watch.

### PR-3: Instrument prompt, launch, watch flush

- **Title:** allocate delivery ids on every control-plane PTY write
- **Files:** `service.py`, `launch_delivery.py`, `launch_service.py`, `watch.py`, `watch_delivery.py`, envelope call sites, integration tests with stub gateway
- **Deps:** PR-2
- **Description:** Intended→pty outcome lifecycle; full tokens in envelopes; watch success gets durable delivery rows.

### PR-4: Bind on wire write

- **Title:** bind delivery tokens inside wire exchange transaction
- **Files:** `session/writer.py`, wire write path, delivery bind SQL, tests with real request fixtures
- **Deps:** PR-2; preferably PR-1
- **Description:** Request text scan → bound/completed. Idempotent under replay.

### PR-5: Reciprocal suppress in watch engine

- **Title:** suppress watch wakes using durable cause ancestry
- **Files:** `watch.py` (`_record_completed_turn`, `_record_activity_delta`), `read_store.py`, statements, watch unit + integration tests
- **Deps:** PR-3, PR-4, PR-1
- **Description:** Enable suppress_runs for `turn_completed` and attributable `state_changed`. Document contract in `CONTROLPLANE.md` (slice #22 lands).

### PR-6: Real PTY actuation proof + GC

- **Title:** slice #22 boundary tests and delivery GC
- **Files:** integration tests (real gateway PTY), orphan sweeper in control plane lifespan, docs
- **Deps:** PR-5
- **Description:** Reciprocal, lost-response, multi-delivery, restart, orphan cases. Closes CONTROLPLANE deferred causal damping item.

## 15. Summary

B1 is a **durable delivery ledger joined to wire exchanges by an embedded full delivery token**, with watch emission consulting cause ancestry from that ledger. The PTY primitive stays dumb. The wire store stays the turn oracle. Observation order leaves the correctness path entirely.
