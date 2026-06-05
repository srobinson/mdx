# Scout — HTTP/wire session store: placement, producer seam, reader path

Scout 1 of 2 (integration). Repo `2b8ed01`, clean tree, 2026-07-10. Companion to
`~/.mdx/projects/tm-agent-state-scout-wire.md` (capture-plane map, not re-derived
here) and to scout 2 (owns table columns + dedup). Citations are file + symbol.

**Headline:** the wire store belongs in the existing Postgres session DB as new
forward-only alembic tables. The producer is a second `ExchangeSink` observer
composed at the one registration site in `addon_runtime.py`
(`_start_session_capture`), writing through a new
`SessionWriter.submit_wire_exchange` that mirrors the shipped
`submit_run_lifecycle_event` pattern. Readers follow the run-lifecycle pattern
exactly: NOTIFY-as-trigger on `tm_events` → `@tm/activity` listener → Postgres
reader in the gateway. The frozen change is the same single composition line the
agent-state scout already named — nothing more. A durable store upgrades that
scout's NOTIFY-as-data compromise back to the house NOTIFY-as-trigger
convention and removes its restart-loses-`asked` caveat.

## Reuse Map

### 1. Tier-1 today — what the wire store must point at, not re-own

- `DiskStorageBackend.persist_exchange` (`storage/disk.py`) writes, per exchange
  (`_write_exchange_files`): `request.raw`, `request.ir.json` (full
  `InternalRequest`), curated request raw+ir, `request_audit`, `response.raw`,
  `response.ir.json` (full `InternalResponse`), redacted `transport.json`, and
  Codex `events.jsonl` + `turn.json`; plus `entry.json` and an atomic rewrite of
  the run's `index.jsonl` (the durable ordered exchange list).
- Correlation keys live on `IndexEntry` (`storage/base.py`): `id` (the exchange
  id), `run_id`, `ts`, `provider`, `model`, `mutated_manually`, and the subagent
  track fields (`track_id`, `parent_track_id`, `track_role`, `spawn_anchor`).
  Note two absences that matter for scout 2: **no `session_id`** (it rides
  `request_ir.metadata.session_id`) and **no per-run `seq`** (ordering today is
  `ts` + `index.jsonl` order).
- Derived stats already reduced at capture: `ReqStats` (system/tools/messages
  part + char counts) and `ResStats` (`stop_reason`, the four token-usage
  fields, `text_chars`, `tool_calls`) — both on `storage/base.py`.

### 2. Producer seam — `ExchangeSink`, with three integration facts the prior scout did not need

- `ExchangeSink` (`storage/exchange_sink.py`): single-slot callable
  `(IndexEntry, ExchangeArtifacts) -> None`, fired by `emit_to_index` at four
  sites — `exchange_recorder.py` `persist_http_exchange` and
  `_finalize_http_provisional_exchange`, `codex/exchange.py` (two finalize
  paths). Contract: best-effort, failures swallowed (tier-1 stays
  authoritative), implementations must be non-blocking — the occupying sink
  (`_make_exchange_cursor_sink`, `addon_runtime.py`) schedules onto the loop
  via `run_coroutine_threadsafe`; a store writer must do the same.
- **Double-fire:** a streaming exchange emits twice under one exchange id
  (provisional persist, then finalize). Store writes must be UPSERT-by-exchange-id,
  never bare INSERT.
- **Deletion asymmetry:** `emit_exchange_deleted` (`exchange_recorder.py`,
  called from the Codex repair path in `codex/exchange.py`) reaches only the SSE
  `broadcast`; the sink never learns about deletions. A sink-fed store either
  gains a deleted signal (a second frozen touch) or explicitly tolerates orphan
  rows — flagged as a decision below.
- **The infrastructure is already in scope at the registration site.**
  `_start_session_capture` (`addon_runtime.py`) constructs
  `SessionWriter(create_async_pool(), loop=loop)`, holds the loop and
  `binding_for_run_id`, and then calls
  `set_exchange_sink(_make_exchange_cursor_sink(...))`. The new observer
  composes at that line with the writer, loop, and run binding all in hand — no
  new pool, no new lifecycle.

### 3. Write-path precedent — `run_lifecycle_event` is the template

Shipped end to end and worth copying verbatim in shape:

- Migration `0007_run_lifecycle_event` builds its DDL from constants in
  `session/run_lifecycle_contracts.py` (CHECK-constraint vocab shared with
  code); TS mirrors the table/column/payload names in
  `@tm/activity` `server/pgContracts.ts`.
- `SessionWriter.submit_run_lifecycle_event` (`session/writer.py`): loop-pinned,
  best-effort with `RunLifecycleEmissionFailureCounter`, insert + typed
  `pg_notify` on `tm_events` in one transaction.
- The api plane already emits through it: `_emit_detached_run_lifecycle_event`
  (`addon_runtime.py`) — proof that capture-runtime code writing a
  non-transcript Postgres row via `SessionWriter` is an accepted, DAG-clean
  pattern (`addon_runtime` is the composition root; `storage` still never
  imports `session`).

A `submit_wire_exchange` sibling (upsert semantics instead of
insert-once) is the whole write path.

### 4. Read path — gateway-side, store-as-data, NOTIFY-as-trigger

- `createActivityGatewayDeps` (`@tm/activity` `gatewayDeps.ts`): one `pg.Pool`
  on the same `databaseUrl`, `PostgresActivityReader`
  (`adapters/postgresRecords.ts`, `readRecordsForRunAfter`),
  `TmEventsActivityListener` (`adapters/tmEvents.ts`, `parseTmEventsPayload`
  dispatching on payload `type`) → `ActivityIngestion.handlers()` →
  `ReconcileLoop` reads the store as truth. A wire table plugs in as: new
  payload type in `pgContracts.ts` + `parseTmEventsPayload`, new reader method
  (or sibling reader), new ingestion handler.
- Browser consumption goes through `@tm/contract` subpath DTOs only
  (`packages/AGENTS.md`); browser packages never import `@tm/activity`.
  `needs-you-gated` is already RESERVED in `@tm/contract`
  `activity/wire.ts` (`activityStatuses`, `needsYouForStatus`) — no enum change
  when the gate slice lands.
- The Python origin proxies activity/lifecycle routes to the gateway
  (`api/v1/run_proxy.py` `RunRouteProxy`). New wire read surfaces should mount
  on the gateway's context router, not grow a parallel Python reader.
- Correlation vocabulary for the later diff: `session/exchange_correlation.py`
  (`EXCHANGE_ID_CONTAINMENT_PROBES`, `exchange_id_containment_sql`) already
  finds exchange ids embedded in transcript event payloads; used today by
  `session/timeline_resources.py` and `session/resource_content.py`. Reuse it;
  do not re-derive.

### 5. The retired substrate — what it was, what to keep, what to avoid

`de46f86` "retire sqlite index substrate" (#37) deleted ~5,000 LOC: a SQLite
tier-2 rebuildable projection (`index/{db,schema,models,ingest,queries,rebuild,
maintenance,writer,blocks}.py`), the raw-fetch API (`api/v1/index_routes.py`),
and its drop-and-rebuild `schema_meta` version gate.

- **Learn (the old `wire_exchange` table got a lot right):** `exchange_id` TEXT
  PK; `run_id` NOT NULL + indexed; `session_id` nullable with
  `ON DELETE SET NULL` (wire rows must survive unknown/rotated sessions);
  nullable `seq`; derived stats columns; `mutated_manually`; and a `raw_dir`
  **pointer to tier-1 instead of raw bytes in the store**.
- **Learn (diff shape):** the diff substrate was content-addressed blocks
  (blake2b-256 `block` table) shared between `exchange_block` and `turn_block`
  position join tables — diff was a join over shared block hashes. That is the
  proven shape *when the diff consumer materializes*.
- **Avoid:** drop-and-rebuild version gating (the Postgres store is
  forward-only alembic, `session/migrate.py`); a second storage engine; block
  normalization before a diff consumer exists; raw bytes or a raw route in the
  store (`PROJECT.md`: "Future raw fetch needs an explicit wire store API").

### 6. Per-consumer requirements

- **needs_you{asked} durable (Slice 2):** wire rows carrying run_id, ts,
  ordinal, toolCallId, tool-block names at response completion. With a store
  row, the reconcile loop recovers `asked` after a gateway restart — resolving
  the prior scout's decision (c) durability caveat, and its decision (b)
  transport becomes plain NOTIFY-as-trigger.
- **needs_you{gated} (gate slice):** the producer is the breakpoint pause path,
  not the exchange sink: `pause_session.py` already builds run-keyed
  `paused` / `paused_tokens` broadcast payloads (`_paused_event_payload`,
  `fire_pause_count`) around `breakpoint.pause/release/drop`. Durable gated
  means gate open/close writes at those sites — separate producer touch,
  separate blessing, same store + notify + reader machinery.
- **wire-vs-transcript diff (later):** needs request/response IR queryable per
  exchange plus the exchange_id↔event correlation above. Full IR jsonb columns
  (the `event` table already stores `raw`+`ir` jsonb) serve this without the
  block substrate; blocks are a later optimization with a proven shape.
- **Bonus:** durable usage/vitals (ResStats token fields are SSE-only and
  process-resident today) and future wire-content search ride the same rows.

## Quality Map

1. `ExchangeSink` is single-slot and occupied; composing observer #2 is the
   moment to make it multi-subscriber (also flagged by the prior scout) rather
   than nesting ad-hoc wrappers.
2. `addon_runtime.py` is at 646 LOC against the 700 hard limit. The observer
   must be a new module with one-line wiring; any larger addition triggers
   refactor-first.
3. `session/writer.py` has two hand-rolled notify payload builders
   (`_notify_payload`, `_run_lifecycle_notify_payload`); a third wire variant
   must extract the shared helper, not copy the pattern.
4. The provisional→finalize double-fire is real but undocumented at the sink
   contract level (`exchange_sink.py` docstring); document it when the second
   subscriber lands.
5. `emit_exchange_deleted` bypasses the sink (SSE-only) — the one place the
   "sink sees every tier-1 mutation" assumption breaks.
6. `session/exchange_correlation.py` looks orphaned in dependency tooling but
   is live (imported by `timeline_resources.py`, `resource_content.py`) — easy
   to miss and re-derive; it is the one correlation vocabulary.
7. `exchange_recorder.py` `persist_http_exchange` vs
   `_finalize_http_provisional_exchange` remain near-duplicates (prior scout
   flag). The sink approach keeps the recorder untouched; resist any design
   that adds a third emission block there.

## Plan

**Store placement:** same Postgres DB as the session store; new forward-only
alembic migration(s) (`api/migrations/versions/0008+`); table vocabulary in a
`run_lifecycle_contracts.py`-style constants module under `session/`, mirrored
in `@tm/activity` `pgContracts.ts`. Rows carry parsed/derived data plus a
tier-1 pointer; raw bytes stay on disk.

**Producer seam:** a new api-plane module (e.g. `wire_store_observer.py`)
implementing the `ExchangeSink` shape, scheduling
`SessionWriter.submit_wire_exchange` (new method mirroring
`submit_run_lifecycle_event`: loop-pinned, best-effort, failure-counted,
UPSERT + typed `pg_notify` on `tm_events`). Composed at
`_start_session_capture`'s `set_exchange_sink(...)` line, where the writer,
loop, and run binding already exist.

**Reader path:** gateway-side through the existing activity machinery — new
payload type in `pgContracts.ts` + `parseTmEventsPayload`, reader on the shared
`pg.Pool`, ingestion handler feeding the run actor; browser DTOs via
`@tm/contract`; Python origin proxies via `RunRouteProxy` if needed.

**Frozen vs product split:** frozen touch = **one composition line in
`addon_runtime.py` `_start_session_capture` (the `set_exchange_sink`
registration; compose or make multi-subscriber) — the identical line the
agent-state scout requested, so both slices share one blessing.** Everything
else is store/product plane: the observer module (new), `SessionWriter` method
(session store, active surface), dao statements, migration, TS
contract/listener/reader. The gate slice later needs `pause_session.py`
emission touches (separate blessing when scoped).

**Decisions for Stuart:**

- **(a) Bless the frozen composition line** at `addon_runtime.py`
  `_start_session_capture` — one edit, shared by wire-store and the
  agent-state Slice-1.5 observer.
- **(b) Store granularity:** full wire-exchange rows (one upserted row per
  exchange; serves asked + gated + diff + vitals + search from one table
  family) vs a narrow asked-only wire-records table. Recommend full exchange
  rows without raw bytes; scout 2 shapes the columns.
- **(c) Deletion semantics:** extend the recorder so the sink also sees
  `emit_exchange_deleted` (a second, tiny frozen edit in
  `exchange_recorder.py`) vs tolerate orphan rows reconciled against
  `index.jsonl`. Flagged for scout 2 to weigh; the frozen-edit version is
  cleaner if (a) is being blessed anyway.
- **(d) Raw bytes stay out of Postgres** (tier-1 pointer per the retired
  `raw_dir` precedent; raw fetch remains an explicit future API). Recommend
  yes.

**Handoff to scout 2 (columns + dedup):** run_id first-class and NOT NULL
(agreed); natural PK is the exchange id (`IndexEntry.id`) with UPSERT for the
provisional→finalize double-fire; there is no per-run seq at capture — order by
`ts` or mint one at write; `session_id` comes from
`request_ir.metadata.session_id` and must stay nullable; Codex later turns are
incremental request payloads, so a row is per-turn wire reality, not a
cumulative conversation; deletion arrives only via `emit_exchange_deleted`
(decision c); subagent track fields (`track_id`, `parent_track_id`,
`track_role`) are on `IndexEntry` and should be first-class columns —
activity's per-run status scoping already fights the primary-vs-subagent
distinction on the transcript side.
