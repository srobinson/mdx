# Spec — wire session store (HTTP store): schema, write path, durable needs_you{asked}

Build spec binding the two scouts:
`~/.mdx/projects/tm-http-store-scout-integration.md` (integration spine, scout 1)
and `~/.mdx/projects/tm-http-store-scout-schema.md` (schema + dedup, scout 2).
Repo baseline `2b8ed01`. All decisions below are locked by Stuart; no re-scoping.

**What ships:** wire HTTP payloads become a queryable Postgres store beside the
session store — content-addressed, ~96% deduped, raw bytes stay tier-1 — written
by a second `ExchangeSink` observer and read gateway-side through the existing
activity machinery. First consumer: **durable needs_you{asked}** that survives a
gateway restart. Exactly two frozen-plane touches, both blessed.

## 1. Boundaries (read first)

- **Frozen touch #1 (blessed):** `storage/exchange_sink.py` becomes
  multi-subscriber (no nested wrappers) and gains a deleted event; the
  registration site `addon_runtime.py` `_start_session_capture` composes the
  new observer beside `_make_exchange_cursor_sink`.
- **Frozen touch #2 (blessed):** `exchange_recorder.py` `emit_exchange_deleted`
  also notifies the sink registry, so store deletes run lockstep with tier-1.
- **Nothing else in the capture plane changes.** No edits to `addon.py`,
  `addon_handlers.py`, the recorders' persist paths, IR, or adapters.
- Import DAG: `storage` never imports `session`. The store writer lives beside
  `SessionWriter` in `session/`; the observer is a NEW top-level api-plane
  module (composition level, like `addon_runtime`); `addon_runtime.py` is at
  646/700 LOC so it gains only wiring lines.
- Never touch `docs/ARCHITECTURE.md`.

## 2. Schema — migration `0008`, six tables (verbatim from scout 2)

Forward-only alembic on the session-store chain (`session/migrate.py`). Table
and column vocabulary lives in a new `session/wire_contracts.py` (the
`run_lifecycle_contracts.py` pattern: constants drive the DDL CHECKs and are
mirrored TS-side in `@tm/activity` `server/pgContracts.ts`).

```sql
-- one row per unique normalized IR component (the dedup heart)
CREATE TABLE wire_blob (
    hash        text PRIMARY KEY,      -- sha256(canonical_json(normalized body))
    kind        text NOT NULL CHECK (kind IN ('system_part','tool_def','message')),
    body        jsonb NOT NULL,        -- normalized IR component, cache/wire stamps stripped
    size_bytes  integer NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ordered whole-list identity for system[] and tools[]
CREATE TABLE wire_component_set (
    set_hash    text PRIMARY KEY,      -- sha256 over ordered member hashes
    kind        text NOT NULL CHECK (kind IN ('system','tools')),
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wire_component_set_member (
    set_hash    text NOT NULL REFERENCES wire_component_set(set_hash),
    position    integer NOT NULL,
    blob_hash   text NOT NULL REFERENCES wire_blob(hash),
    position_meta jsonb,               -- stripped system-part cache_hint / tool-def stamps
    PRIMARY KEY (set_hash, position)
);

-- one row per proxy exchange (turn); everything here is small + verbatim
CREATE TABLE wire_exchange (
    exchange_id     text PRIMARY KEY,  -- tier-1 exchange id (run-dir entry name)
    run_id          text NOT NULL,
    session_id      text,              -- joins "session"; nullable: wire can precede transcript
    provider        text NOT NULL,     -- 'anthropic' | 'codex'
    harness         text,
    ts              timestamptz NOT NULL,
    model           text NOT NULL,
    turn_index      integer,           -- codex continuity index; NULL for claude in v1
    -- subagent track fields, first-class (locked addition to scout 2's sketch;
    -- values come straight off IndexEntry):
    track_id        text,
    parent_track_id text,
    track_role      text CHECK (track_role IN ('parent','subagent')),
    system_set_hash text REFERENCES wire_component_set(set_hash),
    tools_set_hash  text REFERENCES wire_component_set(set_hash),
    sampling        jsonb NOT NULL,
    request_metadata jsonb,            -- IR RequestMetadata verbatim
    request_extras  jsonb,             -- provider_extras minus input_item_raw + input_item_raw_stamped
    stream          boolean NOT NULL DEFAULT false,
    mutated_manually boolean NOT NULL DEFAULT false,
    request_raw_bytes integer,         -- wire size, for savings accounting
    -- response signal, verbatim, never deduped:
    response_id     text,
    stop_reason     text,
    input_tokens    integer,
    output_tokens   integer,
    cache_read_input_tokens     integer,
    cache_creation_input_tokens integer,
    response_error  jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX wire_exchange_run_ix ON wire_exchange (run_id, ts);
CREATE INDEX wire_exchange_session_ix ON wire_exchange (session_id, ts);

-- ordered request-message manifest: the replayed history as references
CREATE TABLE wire_request_message (
    exchange_id  text NOT NULL REFERENCES wire_exchange(exchange_id) ON DELETE CASCADE,
    variant      text NOT NULL DEFAULT 'wire' CHECK (variant IN ('wire','curated')),
    position     integer NOT NULL,
    message_hash text NOT NULL REFERENCES wire_blob(hash),
    position_meta jsonb,               -- stripped cache_control / wire-index stamps
    PRIMARY KEY (exchange_id, variant, position)
);

-- response content blocks, verbatim (drives needs_you{asked} and the diff)
CREATE TABLE wire_response_block (
    exchange_id  text NOT NULL REFERENCES wire_exchange(exchange_id) ON DELETE CASCADE,
    position     integer NOT NULL,
    block_type   text NOT NULL,        -- text | thinking | tool_use | unknown
    tool_use_id  text,
    tool_name    text,                 -- 'AskUserQuestion' / 'request_user_input'
    body         jsonb NOT NULL,       -- full IR block verbatim
    PRIMARY KEY (exchange_id, position)
);
CREATE INDEX wire_response_tool_ix
    ON wire_response_block (tool_name) WHERE block_type = 'tool_use';
```

Locked storage rules: raw bytes never enter Postgres (tier-1 stays the
byte-fidelity source; `exchange_id` is the pointer into the run dir);
BOTH `input_item_raw` AND `input_item_raw_stamped` are stripped from
`request_extras` (measured on the real fallback capture: ~96–98 KB/turn —
the whole request duplicated into provider_extras; missing either strip
stores the request twice and wrecks the dedup yield); curated requests are
`variant='curated'` manifest rows only when `mutated_manually`. Codex
fallback (`/responses`) request bodies are CONFIRMED cumulative on real
data (dev-helioy-docs capture), so the message-manifest dedup applies to
the fallback exactly as to Claude; `turn_index` is populated from
`x-codex-turn-metadata` continuity.

## 3. Normalization contract (the load-bearing clause)

Hashing uses `canonical_json` from `canonicalization.py` (layer-1,
stdlib-only) over the **normalized** component body — sha256, one new module
`session/wire_normalization.py` (imports `ir` + `canonicalization` only,
both allowed for `session/`):

1. Strip `cache_hint` (SystemPart) and `cache_control` inside message-block
   `provider_data` BEFORE hashing; persist the stripped stamps on the
   reference row so exact wire reconstruction survives — message stamps on
   `wire_request_message.position_meta`, system-part `cache_hint` (and any
   future tool-def stamps) on `wire_component_set_member.position_meta`,
   symmetric with the message path; both are restored on reconstruction.
   This also keeps dedup position-independent if a hint ever moves between
   parts. One caveat the builder must handle deliberately: component sets
   are shared across exchanges by hash, so member `position_meta` is
   written once per set (first writer wins). Measured system parts are
   hint-stable turn-over-turn so this is theoretical today; if a fixture
   ever shows hint variance across exchanges sharing a set, the writer must
   detect the mismatch and fall back to distinct sets (fold the meta into
   the set hash) rather than silently reconstructing the wrong hints.
   Measured: without stripping, message dedup is ~0% (the moving
   cache breakpoint changes one byte-range per turn); with it, the replayed
   prefix dedups 100% — and 2 of 3 real system parts carry `cache_hint`, so
   the system round-trip depends on this clause too.
2. Strip the Codex wire-index stamp (`preserved_raw.stamp_wire_index`) the
   same way, into `position_meta`.
3. Drop `input_item_raw` AND `input_item_raw_stamped` from provider
   extras entirely before hashing/storing (not stashed in meta — they
   duplicate the whole request, ~96–98 KB/turn measured, and are
   reconstructible from tier-1 raw). Either one leaking through defeats
   the dedup.
4. Granularity: whole normalized `Message` per blob, plus tool-def-level and
   system-part-level. Block-level only if data later shows recurring giant
   tool_results inside otherwise-changed messages.
5. `system[]` and `tools[]` hash as ordered member-hash lists into one
   `wire_component_set` row each; the unchanged-turn common case is two
   string comparisons on the exchange row.

Reconstruction (the inverse) lives in the same module and is round-trip
tested: manifest joins + re-applied `position_meta` must reproduce the exact
IR that was persisted.

## 4. Producer + write path

**Sink seam (frozen touch #1).** `storage/exchange_sink.py` keeps the
`ExchangeSink = Callable[[IndexEntry, ExchangeArtifacts], None]` shape but
holds a registry of N subscribers; `emit_to_index` iterates all, isolating
failures per subscriber (tier-1 stays authoritative; a broken subscriber
never breaks the wire path or its peers). It gains a deleted-event
counterpart (`(exchange_id, run_id)`) with the same registry semantics.
`_start_session_capture` registers the existing cursor sink and the new
observer side by side — no wrapper nesting. The sink contract docstring must
state the REAL firing contract, confirmed against
`exchange_recorder.persist_http_provisional_exchange` (which never calls
`emit_to_index`) and the codex finalize seam in `codex/exchange.py`
("exactly once … no double emit"): `emit_to_index` fires exactly once per
exchange, at finalize/complete persist — there is no provisional-time fire —
and `emit_deleted` may reference a provisional exchange the sink never saw
(repaired away before finalize). (An earlier revision of this spec claimed a
provisional→finalize double-fire; PR-1's shipped docstring inherited that
false claim and is corrected per the PR-1 review.)

**Observer (new api-plane module `wire_store_observer.py`).** Implements the
`ExchangeSink` shape. Non-blocking: called on the proxy thread, it schedules
onto the writer loop via `run_coroutine_threadsafe` (the
`_make_exchange_cursor_sink` idiom). Normalization/hashing runs inside the
scheduled task, off the proxy hot path (push to an executor only if
profiling shows loop stalls). It has everything in scope at the
registration site: the `SessionWriter`, the loop, `binding_for_run_id`
(workspace fields for the notify payload).

**Writer (`session/writer.py`).** New `SessionWriter.submit_wire_exchange`,
mirroring `submit_run_lifecycle_event`: loop-pinned, best-effort,
failure-counted, one transaction:

1. `INSERT INTO wire_blob … ON CONFLICT (hash) DO NOTHING` for every new
   component (the `UPSERT_ARTIFACT_SQL` idiom from `dao_statements.py`,
   generalized — reuse the shape, do not invent a new one). Same for
   `wire_component_set` / members.
2. `wire_exchange` write-by-`exchange_id`, one complete write at finalize:
   the sink fires exactly once per exchange with request AND response sides
   present (see the firing contract above), so the transaction inserts the
   full exchange row plus its `wire_response_block` rows in one shot. There
   is no provisional-insert then finalize-update lifecycle
   (`persist_http_provisional_exchange` never reaches the sink). Keep the
   write idempotent under replay: `ON CONFLICT (exchange_id) DO UPDATE` plus
   delete+reinsert of the exchange's manifest/block rows within the
   transaction, so a re-fired finalize converges to identical state. This
   simplifies the writer: no partial-row state, no request-only rows, no
   response-columns-arrive-later dance. `submit_wire_exchange_deleted` stays
   as specified and may target an exchange never written (provisional
   repaired away before finalize) — the DELETE is a harmless no-op then.
3. `pg_notify` on `tm_events` with a typed payload
   (`{type: "wire_exchange", run_id, exchange_id, workspace_slug,
   workspace_hash, owner}`) — NOTIFY-as-trigger; the store is the data.

Sibling `submit_wire_exchange_deleted(exchange_id, run_id)`: delete the
exchange row (CASCADE clears manifests/blocks), notify with a deleted-flavor
payload so the reader re-reconciles the run. Blobs are not touched (GC owns
them).

**DRY (locked):** extract the shared typed-notify-payload helper in
`session/writer.py` first — `_notify_payload` and
`_run_lifecycle_notify_payload` become two callers of it; the wire payloads
are the third and fourth. Do not add a third hand-rolled copy.

**Deletion source (frozen touch #2):** `emit_exchange_deleted`
(`exchange_recorder.py`, reached from the Codex repair path in
`codex/exchange.py`) calls the sink registry's deleted event in addition to
the existing SSE broadcast. Store rows stay orphan-free by construction.

## 5. Read path + first consumer: durable needs_you{asked}

Gateway-side only; the Python origin keeps proxying (`api/v1/run_proxy.py`).
Browser sees `@tm/contract` DTOs only — never `@tm/activity`.

1. **Contract:** `pgContracts.ts` gains `WIRE_EXCHANGE_PAYLOAD_TYPE` (+ the
   deleted flavor) and the wire table/column name constants mirroring
   `session/wire_contracts.py`. `ports.ts` adds the payload interfaces to
   `TmEventsPayload`; `parseTmEventsPayload` (`adapters/tmEvents.ts`) gains
   the new cases.
2. **Reader:** new methods on the shared `pg.Pool` reader surface
   (`adapters/postgresRecords.ts` family): for a run, read wire ask-signal
   rows after a cursor — `wire_exchange` join `wire_response_block WHERE
   block_type='tool_use' AND tool_name IN ('AskUserQuestion',
   'request_user_input')`, ordered by `(ts, exchange_id)`, scoped to the
   primary track (`track_role = 'parent'`) so subagent asks do not flip the
   run tier.
3. **Ingestion:** `ActivityIngestion.handlers()` gains the wire payload
   handler; NOTIFY triggers a store read (same reconcile-reads-store
   discipline as `ReconcileLoop` — never NOTIFY-as-data). This lands the
   reserved wire-stream design from `tm-agent-state-scout-wire.md`
   unchanged: `RunActivityEventStream` gains `"wire"` with its own cursor in
   `initialSeqCursors()`; wire events never enter the record stream and
   never touch the Postgres record watermark; event identity is
   `(exchange_id, position)` under the wire cursor, so replays are idempotent.
4. **Projection:** the wire ask event folds to `question-asked` →
   `needs-you-asked`; `needsYouForStatus` (`@tm/contract` `activity/wire.ts`)
   is reused unchanged — no enum change (`needs-you-asked` exists;
   `needs-you-gated` stays reserved for the gate slice, which is NOT this
   spec).
5. **Durability rule (what "survives restart" means):** on actor
   materialization (gateway boot or first event for a run), the wire
   reconcile reads the run's LATEST wire exchange; if its response blocks
   carry an ask tool and no later exchange exists for the primary track, the
   run projects `needs-you-asked`. The transcript plane structurally cannot
   supply this while the question is pending (Claude defers journaling the
   row until answered — cm-verified); the store now can.
6. **Coexistence:** when the user answers, the next wire exchange arrives
   (clearing the rule in 5) and the transcript's late `question-asked` +
   `tool_result` replay as the existing harmless self-transition —
   independent cursors, no double-fire, no shadowing (per the agent-state
   scout's dedupe analysis, unchanged).

## 6. Correlation

- `run_id` NOT NULL end to end (`ProxyRunBinding.require_run_id` upstream).
- `session_id`: the wire write stores the SAME read-back session id the
  transcript path keys the `session` table on, so wire↔session joins for
  both providers. Resolve the native id from
  `request_ir.metadata.session_id` (the Codex request parser populates it
  via `codex_session_id_from_provider_metadata`; Claude carries it
  natively), then apply the transcript path's synthesis rule:
  `index.sessions.synth_session_id(run_id, provider, native_session_id)`
  for read-back providers (Codex), the native id unchanged for Claude —
  exactly what `addon_runtime._wire_session_id` already does for the cursor
  sink's `SessionBinding`. Do NOT store the native id verbatim: the session
  table keys Codex on the synthesized uuid5, so a verbatim native id never
  joins (PR-2 review finding F-1; an earlier revision of this section
  specified the verbatim read and was wrong). DRY: promote
  `_wire_session_id` to a public helper — natural home beside
  `synth_session_id` in `index/sessions.py` — and have the wire observer
  and the cursor sink share that one path instead of mirroring the rule.
  Stays nullable with a soft join (no enforced FK) — wire can precede the
  transcript session row. Rows written under the old rule are mechanically
  backfillable: each carries `run_id`, `provider`, and the native
  `session_id`, so a single UPDATE recomputes the synthesized id in place.
- Track fields come off `IndexEntry` verbatim.
- Later wire-vs-transcript diff reuses `session/exchange_correlation.py`
  (`EXCHANGE_ID_CONTAINMENT_PROBES` — already live in
  `timeline_resources.py` / `resource_content.py`) to anchor transcript
  events to `exchange_id`; the wire side becomes a hash anti-join per turn.
  Out of scope here; the store makes it possible.

## 7. GC

Unreferenced `wire_blob` (and empty `wire_component_set`) rows are swept by
a maintenance command on the existing `db` CLI command group (the
`session/migrate.py` docstring names the group): left-join delete of blobs
referenced by neither `wire_component_set_member` nor
`wire_request_message`, then sets with no members. No refcounting. Not
scheduled; run manually or by future maintenance tooling.

## 8. PR slicing (3 slices, each leaves main green)

**PR-1 — frozen seam.** `storage/exchange_sink.py` multi-subscriber +
deleted event; `emit_exchange_deleted` reaches the registry;
`_start_session_capture` registration updated (cursor sink re-registered
through the new API). No store, no schema. Behavior identical with one
subscriber. This is the whole blessed frozen surface, isolated for focused
review (contract-change review weight applies here, not to the store code).
*Acceptance:* registry fan-out with per-subscriber failure isolation; the
deleted event observed by a test subscriber (red before the recorder touch);
existing sink tests pass unchanged.

**PR-2 — write path (store populated, nothing reads it).** Migration 0008 +
`session/wire_contracts.py` + `session/wire_normalization.py` +
`SessionWriter.submit_wire_exchange`/`…_deleted` (with the notify-helper
extraction first) + `wire_store_observer.py` + composition line + GC
command. Ships dark: tables fill during capture, no product surface changes.
*Acceptance (red-first):*
- normalization: moving `cache_control` between turns → identical message
  hashes, stamps land in `wire_request_message.position_meta`; system parts
  carrying `cache_hint` → identical part hashes, hints land in
  `wire_component_set_member.position_meta`; reconstruction round-trips the
  exact IR for messages AND `system[]`/`tools[]` — asserted on BOTH real
  captured fixtures: the Codex one (incl. `stamp_wire_index`) and a real
  Claude fixture (see the dedup-yield bullet; synthetic Claude-shaped unit
  cases prove the mechanism but do not satisfy this bullet);
- write idempotency: one finalize fire → one complete `wire_exchange` row
  with response blocks present; a replayed finalize fire for the same
  `exchange_id` converges to identical state (no-op or clean rewrite);
  `submit_wire_exchange_deleted` for an `exchange_id` never written is a
  harmless no-op (provisional repaired away before finalize);
- deletion lockstep: `emit_exchange_deleted` → exchange row + manifests +
  blocks gone, blobs intact; GC then removes only unreferenced blobs;
- dedup yield: replay consecutive real tier-1 request IRs against the real
  Codex HTTP-fallback fixture at `api/tests/fixtures/codex_http_fallback/`
  (staged at `~/.mdx/projects/tm-codex-http-fallback-fixture/`) → newly
  inserted bytes for turn N+1 ≤ 4% of its `request_raw_bytes` (>96%
  reduction asserted; ~98% measured on the dev-helioy-docs capture). The
  same bound MUST also be asserted against a real captured Claude fixture
  (~96% measured): consecutive-turn `request.ir.json`/`response.ir.json`
  from a real `transport-matters claude` run, same layout as the Codex one,
  at a sibling `api/tests/fixtures/` directory (suggested:
  `claude_capture/`), carrying real `cache_control`-stamped blocks and
  `cache_hint`-bearing system parts. This Claude fixture is a PR-2
  acceptance requirement, not optional (PR-2 review finding F-3).
  Denominator discipline: `request_raw_bytes` means the true wire request
  size (`len(request_raw)`, what the observer stores) — NOT the fixture
  IR file size, which for Codex is ~2× the wire bytes (pretty-printing plus
  the `input_item_raw` duplicate) and inflates the headline reduction
  (PR-2 review finding F-4); record the wire byte size in the fixture
  README and feed the assertion from it. The assertion must fail if
  `input_item_raw`/`input_item_raw_stamped` leak through;
- writer failure isolation: store outage → capture and tier-1 unaffected,
  failure counter increments.

**PR-3 — read path + durable asked.** `pgContracts.ts` + `ports.ts` payload
types + `parseTmEventsPayload` cases + reader methods + ingestion handler +
`"wire"` stream/cursor in the domain + projection wiring.
*Acceptance (red-first):*
- payload parse cases (well-formed, malformed ignored);
- live path: wire exchange row with an ask block + NOTIFY → run projects
  `needs-you-asked` with `needs_you {kind:"asked"}`;
- **survives restart:** seed the store with an ask-terminal exchange, build
  a FRESH ingestion (new actor, no prior in-memory state) → reconcile alone
  projects `needs-you-asked` (this is the test that fails before the slice);
- answered flow: a later exchange for the run clears asked; transcript's
  late `question-asked`/`tool_result` replay causes no regression;
- isolation: wire events never advance the record-stream watermark; subagent
  (`track_role='subagent'`) asks do not flip the primary run tier.
- Observable end-state discipline applies (feedback lesson): assert the
  projected status/`needs_you` payload consumers read, not intermediate
  mappings.

**Gates, every slice, verbatim:** `cd api && just ci`; repo root
`just check`; `just test` (full suite — persistence + contract change; no
targeted-filter shortcuts). Judge background gate runs by output content,
not piped exit codes.

## 9. Open items (minor, non-blocking)

- `turn_index` semantics for Claude: NULL in v1 (Codex fills it from
  continuity). Minting a per-run ordinal for Claude is a follow-up if a
  consumer needs it; nothing in this spec reads it.
- GC command name/placement on the `db` group: builder's choice within the
  existing CLI conventions.
