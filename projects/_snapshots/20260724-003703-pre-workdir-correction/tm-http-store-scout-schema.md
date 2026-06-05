# Scout — wire store SQL schema + dedup strategy (HTTP store, scout 2 of 2)

Schema scout for persisting Claude + Codex wire traffic without storing the
~90% per-request repetition. Citations are file + symbol, repo at `2b8ed01`
(clean tree). Measurements are from real tier-1 data
(`~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/71d0469e…/2026…`,
run of 2026-07-10).

**Headline: content-addressed component storage keyed by a normalized IR
hash, 6 tables, ~95% measured request-byte reduction.** Both harnesses
already normalize to one IR (`ir.py` `InternalRequest`/`InternalResponse`),
so the schema is IR-shaped, not per-provider. The session store already ships
the exact idiom we need (`artifact(hash PK, bytes)` +
`UPSERT … ON CONFLICT (hash) DO NOTHING`, migration
`0001_session_store_foundation.py`, `dao_statements.py`
`UPSERT_ARTIFACT_SQL`) — this proposal generalizes it, it does not invent a
new mechanism.

## 1. Claude wire schema (anthropic `/v1/messages`)

Parsed by `adapters/anthropic.py` `AnthropicAdapter.inbound_request` /
`inbound_response` (SSE fold in `_inbound_response_sse`).

Request IR: `model`, `system: list[SystemPart]`, `tools: list[ToolDef]`,
`messages: list[Message]` (full replayed history every turn),
`sampling: SamplingParams`, `metadata: RequestMetadata` (session_id parsed
out of `metadata.user_id`), `stream`, `provider_extras` (observed:
`thinking`, `context_management`, `output_config` — small).

**Measured repetition, consecutive turns 5 minutes apart (105,726-byte
request):**

| component | bytes | turn-over-turn behavior |
|---|---|---|
| `system` (3 parts) | ~9.8 KB | byte-identical |
| `tools` (21 defs) | ~50.8 KB | byte-identical |
| `messages` prefix (all prior turns) | ~47 KB and growing | identical **except** the moving `cache_control` stamp |
| new messages (the turn's delta) | ~2 KB | new |

The one prefix-instability is load-bearing: message N-1's block carries
`provider_data: {"cache_control": {"ttl":"1h","type":"ephemeral"}}` on turn
N and loses it on turn N+1 when the cache breakpoint moves. Naive
whole-message hashing gets 0% prefix reuse; stripping cache hints into
reference-level metadata before hashing gets 100%. This is the dedup
contract's critical clause.

Response IR (`InternalResponse`): `id`, `model`, `stop_reason`,
`usage` (input/output/cache_read/cache_creation), `content` blocks
(text | thinking | tool_use — `AskUserQuestion` is a plain `ToolUseBlock`),
`provider_extras`. Small (1.6–13 KB measured). Entirely signal; never dedup.

## 2. Codex wire schema (`response.create` WS + `/responses` SSE)

Parsed by `codex/request_parser.py` `parse_codex_request` and
`codex/response_parser.py` `parse_codex_response_payloads` (HTTP SSE and WS
share payload shapes — `parse_codex_response_sse` docstring).

Request: `instructions` → `SystemPart` (repeats per turn), `input[]` items
(`message`, `function_call`, `function_call_output`, `reasoning`) → IR
messages, `tools[]` (repeats), `client_metadata` (session id nested in
`x-codex-turn-metadata`, resolved by
`codex_session_id_from_provider_metadata`). **Later turns carry incremental
`input` payloads** (project CLAUDE.md wire-reality fact; turn continuity via
`codex/continuity.py` `CodexContinuityAllocator`) — so Codex is already
delta-shaped for messages, but `instructions` + `tools` still repeat and
dedup the same way. Caveat: `parse_codex_request` stashes unparseable items
verbatim as `provider_extras["input_item_raw"]` — potentially large, and
reconstructible from tier-1 raw; strip it from the Postgres copy.

Response: output items fold to the same IR — `reasoning` → ThinkingBlock,
`message` → TextBlock, tool call items (incl. `request_user_input`) →
ToolUseBlock; `token_count`/usage → `UsageStats`
(`cache_creation_input_tokens` always 0, `_parse_usage`); terminal status →
`stop_reason`; `provider_extras`: `output_item_meta`, `error`.

Because both harnesses land in one IR, **one schema serves both**; Codex
simply produces smaller manifests per exchange.

## 3. Dedup strategy — recommendation: content-addressed components

Three candidates against the measured reality:

1. **Per-turn delta (prefix pointer to previous exchange)** — REJECT.
   Assumes append-only history. Claude Code compaction rewrites history
   mid-session, breakpoint edits mutate the outbound request
   (`ExchangeArtifacts.request_curated_ir`), subagent tracks interleave, and
   retries fork. A broken pointer chain corrupts every later turn, and reads
   need recursive reconstruction.
2. **Normalized shared component tables (one table per component kind, FK
   rows)** — workable but is just content addressing with more tables and
   without the uniform GC/reuse story.
3. **Content-addressed component storage** — RECOMMENDED. Hash each IR
   component (system part, tool def, message) over
   `canonical_json` (reuse `canonicalization.py` — layer-1, stdlib-only,
   already the cross-plane canonical-JSON discipline) of its **normalized**
   body; store the body once; per-exchange ordered manifests reference by
   hash. Identical content dedups regardless of position, so compaction,
   edits, forks, and Codex's already-incremental turns all degrade
   gracefully instead of breaking. Reads are ordered joins, no recursion.
   Prior art in-store: `artifact`/`event_artifact`.

**Normalization contract (the part that makes it work):**
- Strip `cache_hint` (SystemPart) and `cache_control` inside
  message-block `provider_data` before hashing; persist the stamps on the
  *reference* row (`position_meta`) so exact wire reconstruction survives.
- Strip the Codex wire-index stamp (`preserved_raw.stamp_wire_index`)
  the same way.
- Granularity: **message-level** (whole normalized `Message`), plus
  tool-def-level and system-part-level. Measured data shows message-level
  is sufficient once cache stamps are stripped; block-level would only pay
  if giant `tool_result` payloads recur inside otherwise-changed messages —
  not observed; revisit with data.
- `tools[]` and `system[]` repeat as whole ordered lists, so hash the
  ordered member-hash list into one `component_set` row; the exchange row
  then carries two FKs and the common case (nothing changed) is two
  string comparisons.
- System parts carry `cache_hint` too (measured: 2 of 3 real parts). The
  stripped stamps live on `wire_component_set_member.position_meta`. Because
  set rows are shared across exchanges, `set_hash` must cover member hashes
  **plus** member meta, so two turns whose normalized parts match but whose
  stamps differ mint two (tiny) set rows while still sharing the blobs.
  Measured data shows system stamps are turn-stable, so in practice this
  stays one row.

## 4. Proposed DDL sketch (6 tables)

Alembic, forward-only, same migration chain as the session store
(`session/migrate.py`). Correlation columns match the existing store:
`run_id text NOT NULL` (first-class on `event`, `run_lifecycle_event`,
`ProxyRunBinding.require_run_id`), `session_id` join to `"session"`.

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
    position_meta jsonb,               -- stripped cache_hint stamps (system parts carry them too)
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
    turn_index      integer,           -- codex continuity index / claude per-run ordinal
    system_set_hash text REFERENCES wire_component_set(set_hash),
    tools_set_hash  text REFERENCES wire_component_set(set_hash),
    sampling        jsonb NOT NULL,
    request_metadata jsonb,            -- IR RequestMetadata verbatim
    request_extras  jsonb,             -- provider_extras minus input_item_raw
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

Writer idiom: `INSERT INTO wire_blob … ON CONFLICT (hash) DO NOTHING` (same
as `UPSERT_ARTIFACT_SQL`), then the manifest rows in the same transaction.

## 5. Verbatim vs deduped vs not-in-Postgres

**Verbatim, small, never lose** (the product signal):
- Every response content block, exactly as parsed — `tool_use` incl.
  `AskUserQuestion` / `request_user_input` (drives `needs_you{asked}`;
  `{gated}` comes from breakpoint state, not this store), thinking, text.
- `stop_reason`, the four usage counters (as int columns → vitals/token
  accounting queries need no jsonb digging), `response_error`.
- `sampling`, `request_metadata`, `request_extras`, `mutated_manually`.

**Aggressively deduped** (the 90%+): system parts, tool defs, replayed
message history — stored once in `wire_blob`, referenced per exchange.

**Not in Postgres at all:** raw request/response bytes. Tier-1
(`request.raw`/`response.raw` in the run dir, `DiskStorageBackend`) stays
the byte-fidelity source of truth; `wire_exchange.exchange_id` is the
pointer into it. Also excluded: `input_item_raw` (duplicate of tier-1 raw).

**Measured effect:** turn N+1 raw request = 107,491 bytes; new rows after
dedup ≈ one exchange row + 2 new message blobs (~2 KB) + response blocks
(~1.6 KB) ≈ **~4 KB stored, ~96% reduction**, converging higher as sessions
lengthen (prefix grows, delta stays constant).

## 6. Per-consumer read notes

- **Inspector full-request view:** exchange row → join two component sets +
  `wire_request_message` → `wire_blob`, re-apply `position_meta` stamps.
  Ordered joins, no recursion.
- **Vitals / activity / token accounting:** `wire_exchange` alone
  (usage columns, `stop_reason`, `model`, `run_id`) — matches what
  `ResStats` (`storage/base.py`) carries today, plus names it lacks.
- **needs_you{asked}:** partial index on `wire_response_block.tool_name` —
  the durable complement to the live `ExchangeSink` path (scout
  `tm-agent-state-scout-wire.md`).
- **Wire-vs-transcript diff (the product):** wire side is now enumerable —
  wire-only content = system-set + tools-set + message hashes with no
  transcript counterpart. Transcript rows (`event.ir`) can be hashed with
  the same normalization at read time (or a future `content_hash` column on
  `event`) to make the diff a hash anti-join per turn.
- **Savings dashboard:** `request_raw_bytes` vs sum of newly-inserted blob
  bytes per exchange.

## 7. Producer seam + correlation (handshake with scout 1)

Confirmed independently: `run_id` is first-class end to end
(`ProxyRunBinding.require_run_id`, `event.run_id NOT NULL`,
`run_lifecycle_event`); `session_id` arrives in-request for both providers
(`RequestMetadata.session_id`; Codex via
`codex_session_id_from_provider_metadata` — else NULL, so the FK must stay
nullable and un-enforced or deferrable). The natural producer is the
finalize path that already holds the full `ExchangeArtifacts`
(`request_ir`, `response_ir`, curated variants): the same
`ExchangeSink`-composition seam scout 1's wire doc names
(`addon_runtime.py`). Import-DAG constraint (api/CLAUDE.md): `storage` must
never import `session`; the writer belongs beside `SessionWriter`
(`session/writer.py`) or a sibling `wire/` package importing `ir`, injected
at `load_runtime()` like the snapshot sink.

## 8. Decisions for Stuart

1. **Dedup approach** — content-addressed components as above (recommended)
   vs per-turn delta (rejected: history rewrites break chains).
2. **Normalization contract** — strip `cache_control`/cache hints + Codex
   wire-index stamps into `position_meta` before hashing (recommended;
   measured: without it, dedup yield on messages is ~0%).
3. **Granularity** — message-level (recommended) vs block-level (only if
   recurring giant tool_results show up in data).
4. **Curated requests** — `variant='curated'` manifest rows only when
   `mutated_manually` (recommended) vs separate exchange rows.
5. **Raw bytes** — stay tier-1 only (recommended) vs bytea in Postgres.
6. **Blob GC** — unreferenced `wire_blob` rows after run/session deletion
   need a sweep (left-join delete); accept as maintenance command vs
   refcounting.
7. **Store placement** — same Postgres + same Alembic chain as the session
   store (recommended: one migrator, one pool, `session_id` join stays
   local) vs a separate database.
