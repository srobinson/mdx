# PR #259 review — wire-store write path (PR-2, dark) — scout 2 / schema anchor

## Delta verify at 3071b4f (correction round) — CLEAN, one residual minor

All review conditions and fold-ins landed; verified first-hand against the tree
(pristine at 3071b4f) and the real run dirs:

1. **Claude fixture genuine (F-3, F-4 closed).** `api/tests/fixtures/claude_messages/`
   is byte-verbatim from run `71d0469e` (workspace `dev-helioy-transport-matters/ecd9b0df`):
   request/response IR sha256-match the run dir, and each `meta.json`
   `request_raw_bytes` (166,751 / 169,169 / 170,883) exactly equals the run dir's
   `request.raw` size. Real moving `cache_control` block stamp plus 3 `cache_hint`s;
   16→18→20 messages, 3 system parts, 23 real tool defs. Codex `meta.json`
   (98,067 / 101,436 / 104,018) also matches its run dir. `test_dedup_yield_on_real_turns`
   is parametrized over BOTH fixtures and asserts ≤4% of TRUE wire bytes; round-trip
   and prefix-dedup tests parametrized over both. Headline now honest.
2. **NUL fixed (F-2 closed).** `wire_normalization._component` applies
   `strip_decoded_nuls` BEFORE hashing; new unit test pins hash == stored body ==
   reconstruction for NUL-bearing content.
3. **session_id fixed (F-1 closed, matches patched §6).** `index.sessions.wire_session_id`
   promoted public (codex → `synth_session_id`, claude → native); the observer applies
   it (None-guarded) and `addon_runtime._make_exchange_cursor_sink` shares the same
   helper (`_wire_session_id` deleted — DRY as specified).
4. **Fold-ins landed (F-5..F-9 closed).** Pool: aux reserve bumped to 2 and
   `WireStoreObserver` serializes submissions (semaphore, one in-flight → exactly one
   budgeted connection), retains pending futures, and `aclose()` unregisters both
   sinks then drains before the writer closes. Write path: blob hash pre-check (one
   round-trip, only missing bodies shipped), `executemany` for members/manifest/blocks,
   writer-lifetime verified-set cache updated post-commit only. GC: four
   reverse-reference indexes added; sweep now one transaction under
   `LOCK TABLE wire_exchange IN SHARE MODE` with honest docstrings. Minors:
   `next_notify_payload` promoted to `session/testing.py` (both writer tests share it);
   `test_wire_contracts.py` pins `WIRE_TRACK_ROLES` to `track_manager.TrackRole` via
   `get_args`; `_commit_wire` scaffold shared by both submit methods. Bonus: dedicated
   captures get a `_run_binding_resolver` so their wire rows carry workspace/harness.

**Residual minor (new, from the fix itself):** `SessionWriter._verified_wire_sets` is
never invalidated. If `db wire-gc` deletes a component set (all referencing exchanges
deleted) while the API process lives, a later exchange reusing that cached `set_hash`
skips `_ensure_component_set`, the exchange upsert FK-fails, and — because the cache
never clears — every subsequent turn sharing that set fails until process restart
(failures are counted and logged, so it is visible; restart heals). One-line fix:
discard `stats.verified_set_hashes` / clear the cache in `_record_wire_failure`.
Non-blocking.

Branch `wire-store-pr2-write-path`, head `deb25b0` (one commit over main `9f2a3f6`).
Reviewed against `~/.mdx/projects/tm-http-store-spec.md` (§2 DDL, §3 normalization,
§4 producer/write, §6 correlation, §7 GC, §8 PR-2 acceptance) and the schema scout
report `~/.mdx/projects/tm-http-store-scout-schema.md`. Process: /code-review high
effort (8 finder angles, recall-biased verify) + /code-hygiene. Working tree kept
pristine throughout; PR read via `git show deb25b0:`.

## Verdict

**Conditional.** DDL, normalization contract, and the dedup model are spec-faithful
(sections 1–3), the write path is idempotent and best-effort as specified, and the
composition/GC scope matches §8 PR-2 exactly. Two conditions before merge:
(1) resolve finding F-1 — `wire_exchange.session_id` never joins the session table
for Codex (spec-inherited inconsistency, but the PR bakes wrong values into durable
rows from day one of the dark phase); (2) F-3 — the §8 acceptance list requires a
Claude fixture asserting the ≥96% bound, which is absent. Remaining findings are
craftsmanship-grade and fixable inside this PR.

## 1. Schema fidelity (brief item 1) — PASS

Migration `0008_wire_store.py` matches spec §2 table-by-table, column-by-column:

- All six tables present with exact column names, types, and nullability:
  `wire_blob(hash PK, kind CHECK, body, size_bytes, created_at)`;
  `wire_component_set(set_hash PK, kind CHECK)`;
  `wire_component_set_member(set_hash FK, position, blob_hash FK, position_meta jsonb, PK(set_hash,position))`
  — the position_meta amendment from the scout report is present;
  `wire_exchange` with `run_id NOT NULL`, `session_id` nullable (soft join, no FK — per §6),
  `harness`, track trio with CHECK, both set-hash FKs, `sampling NOT NULL`,
  `stream`/`mutated_manually` defaults, four usage columns, `response_error`;
  `wire_request_message(… variant DEFAULT 'wire' CHECK, PK(exchange_id,variant,position), ON DELETE CASCADE)`;
  `wire_response_block(… PK(exchange_id,position), ON DELETE CASCADE)`.
- Indexes: `wire_exchange_run_ix (run_id, ts)`, `wire_exchange_session_ix (session_id, ts)`,
  partial `wire_response_tool_ix ON wire_response_block(tool_name) WHERE block_type='tool_use'`. All per spec.
- CHECK values driven from `session/wire_contracts.py` constants via the new shared
  `sql_text_values` (run_lifecycle_contracts pattern, as §2 requires).
- Downgrade drops all six in FK-safe order; `test_migrate.py` covers head=0008,
  presence at head, absence after downgrade.

## 2. Normalization contract fidelity (brief item 2) — PASS

`session/wire_normalization.py` implements §3 exactly:

- `cache_hint` (SystemPart) and `cache_control` + `tm_wire_index` (provider_data,
  message-level and block-level) stripped BEFORE hashing, stashed in the returned
  `position_meta`; empty provider_data collapses to None so a stamp-only dict hashes
  identically to no dict (the moving-breakpoint case, unit-tested both ways).
- BOTH `input_item_raw` and `input_item_raw_stamped` dropped from provider extras
  entirely (`STRIPPED_REQUEST_EXTRAS_KEYS`), not stashed — per §3.3.
- Hash = sha256 over `canonical_json` of the normalized body (canonicalization.py reuse);
  set hash = sha256 over `[kind, ordered member hashes]` — §3.5.
- Reconstruction inverse in the same module, round-trip tested for messages AND
  system[]/tools[] including the real fixture request (`test_fixture_request_round_trips_exactly`).
- The codex stamp-key mirror (`tm_wire_index`, `input_item_raw_stamped`) is pinned to
  the owning `codex.preserved_raw` constants by `test_stamp_keys_match_codex_contract`
  — the DAG-safe arrangement §3 anticipated.
- §3.1's first-writer-wins caveat is handled: `_ensure_component_set` reads back stored
  members on set-hash hit, compares `(blob_hash, position_meta)` pairs, and on variance
  mints a distinct folded identity via `fold_member_meta_into_set_hash` instead of
  silently reconstructing wrong hints. Import surface is `ir` + `canonicalization` only.

## 3. Dedup genuineness (brief item 3) — GENUINE, with one honest-denominator caveat

The dedup is real, not a test artifact:

- Blobs are keyed purely by content hash in a global `wire_blob` table; component sets
  by ordered member-hash identity; manifests reference blobs by hash. Repetition
  collapses across exchanges by construction, and `test_fixture_prefix_dedups_completely`
  proves it on the real HTTP-fallback capture (turn-1 shares all 6 turn-0 message
  hashes, turn-2 all 12; system/tools set hashes identical across turns).
- `test_dedup_yield_on_real_fallback_turns` asserts stored-bytes ≤ 4% of the request
  size per replayed turn and the bound demonstrably blows up on an
  `input_item_raw`/`input_item_raw_stamped` leak (~96 KB would land in request_extras,
  which the stored-bytes measure includes).
- Caveat (minor, finding F-7): the denominator `request_raw_bytes` is fed with
  `request.ir.json` file size (202–213 KB: pretty-printed AND still containing the
  `input_item_raw` duplicate), roughly 2× the true wire size (~100 KB). The honest
  wire-relative reduction is ~96.5–97%, not the headline 98.3/98.7%. Still beats the
  spec's >96% bar and the ≤4% assertion still holds against the true wire size
  (~3.5%), so the protective function is genuine; only the headline number is inflated.

## 4. Findings (ranked, verified)

Process: 8 finder angles → dedup → per-candidate verify (CONFIRMED/PLAUSIBLE kept,
REFUTED dropped).

**F-1 · major · correctness/schema · `wire_store_observer.py:on_exchange` (session_id) · CONFIRMED**
`wire_exchange.session_id` is filled with `request_ir.metadata.session_id` — the
NATIVE Codex thread id (the codex parser populates it via
`codex_session_id_from_provider_metadata`). But the session table keys Codex
sessions on `synth_session_id(run_id, provider, native)` (`index/sessions.py`,
uuid5 over the frozen namespace; `addon_runtime._wire_session_id` applies it for
codex only). So the spec §6 clause "joins `session`" is dead for every Codex row;
only Claude works, because native == stored id there. The observer implements
§6 VERBATIM ("session_id from request_ir.metadata.session_id"), so this is a
spec-internal inconsistency, not builder negligence — but the write path is the
thing shipping, and every dark-phase Codex row carries a join-dead session_id.
`wire_exchange_session_ix` and any PR-3 session join silently return zero rows
for codex. Fix options: synthesize at write (the observer already has run_id,
provider, and native in hand — one call to `synth_session_id` mirrors the cursor
sink), or re-spec §6 to store native + synthesize at read. Backfill of rows
written before the fix is mechanical (run_id, provider, session_id all on the row).
Decision is Stuart's; the store should not ship dark for weeks writing the wrong id.

**F-2 · medium · correctness · `wire_store.py:_upsert_blobs` + `wire_normalization.py:_component` · PLAUSIBLE**
The content hash is computed over the body BEFORE storage, but storage goes
through `dao_rows.jsonb()` → `strip_decoded_nuls` (added in 5bb3072 because
provider JSON really does carry decoded NULs Postgres jsonb cannot store). A
NUL-bearing component is stored stripped under a hash of the un-stripped body:
reconstruction diverges from the persisted IR (spec §3 exact-round-trip broken)
and the same content with/without NUL mints two hashes for one stored body.
Realistic but rare. Fix at the right depth: make NUL-stripping part of
normalization (strip before hashing in `_component`), so hash, stored body, and
reconstruction agree by construction. The secondary claim (NUL in position_meta
causing per-turn folded sets) was assessed unrealistic — stamp values don't
carry NULs.

**F-3 · medium · spec drift / test coverage · `session/test_wire_writer.py` · CONFIRMED**
§8 PR-2 acceptance requires the dedup-yield bound "with a Claude fixture
asserting the same bound (~96% measured)" and round-trip coverage on "Claude and
Codex fixtures". Only the Codex HTTP-fallback fixture ships. Claude-shaped
mechanics (cache_control, cache_hint) are covered synthetically in
`test_wire_normalization.py`, which proves the mechanism but not the named
acceptance artifact: nothing exercises a real Claude request (10 system parts,
50+ tools with real schemas, replayed tool_results) end to end through the
writer, and the ~96% Claude bound is unasserted.

**F-4 · minor · measurement honesty · `test_wire_writer.py:test_dedup_yield_on_real_fallback_turns` · CONFIRMED**
The denominator `request_raw_bytes` is fed `request.ir.json` file size
(202–213 KB: pretty-printed AND still containing the ~96–98 KB `input_item_raw`
duplicate) — roughly 2× the true wire size (~100 KB). Honest wire-relative
reduction is ~96.5–97%, not the headline 98.3/98.7%. The ≤4% assertion still
holds against true wire bytes (~3.5%) and demonstrably blows up on a raw-extras
leak, so the protective function is genuine; only the headline is inflated. Fix:
feed the denominator with a stored true wire size (add it to the fixture README
or fixture metadata) or rename the variable/message to say IR bytes.

**F-5 · medium · robustness · `writer.py:submit_wire_exchange` (pool budget) · PLAUSIBLE**
The wire path draws whole-transaction connections from the same pool
(max_size=10) whose sizing budgeted 9 dispatcher shards + 1 aux reserve, with no
allowance for wire writes. One coroutine per finalized exchange under burst
contends with the dispatcher for connections; commit latency or PoolTimeout
starvation is realistic. Fix: count wire writes in the pool math (or a small
semaphore/queue-of-one in the observer, since per-exchange writes are
independent and best-effort).

**F-6 · medium · efficiency · `wire_store.py` write path · CONFIRMED**
The write path does O(history) work per turn on four axes: (a)
`normalize_request` re-dumps + `canonical_json` + sha256 over EVERY system
part/tool/message each turn (O(turns²) per session, sync on the writer loop);
(b) `_upsert_blobs`/`_insert_members`/`_insert_manifest`/`_insert_response_blocks`
await one INSERT per row — hundreds of serial round-trips per Claude-scale
exchange; (c) full blob bodies are serialized and shipped every turn only for
`ON CONFLICT DO NOTHING` to discard ~98% of them; (d) `_ensure_component_set`
re-reads and re-compares all members of both sets every turn to detect variance
the code itself calls theoretical. All four have cheap, accounting-preserving
remedies: psycopg3 `executemany(returning=True)`/pipeline mode, a hash-existence
pre-check before shipping bodies, and a session-lifetime cache of verified set
hashes. Dark-phase-tolerable; should not survive into PR-3 load.

**F-7 · minor · ops/GC · `0008_wire_store.py` + `db_cmd.py:wire_gc` · CONFIRMED (indexes) / PLAUSIBLE (concurrency)**
No index exists on `wire_exchange.system_set_hash`/`tools_set_hash`,
`wire_component_set_member.blob_hash`, or `wire_request_message.message_hash`
(Postgres never auto-indexes the referencing side), yet the three GC DELETEs
anti-join on exactly those columns — sequential scans, O(blobs × references) on
a grown store. Separately, a GC run concurrent with a live wire write can abort
on foreign_key_violation (KEY SHARE vs DELETE), contradicting the docstring
"safe to run any time" — recoverable (manual, re-runnable, writer best-effort),
but the docstring should say so or the sweep should take the reverse indexes
plus a retry. Spec §7 is silent on indexes; this goes beyond spec, flagged as
schema-anchor advice.

**F-8 · minor · DRY · `test_wire_writer.py:_next_notify_payload` · CONFIRMED**
Near-verbatim duplicate of `session/test_run_lifecycle_writer.py:_next_notify_payload`
(differs only in timeout literal and assert message). Promote to a shared
session test-support home (CLAUDE.md allows shared test-support imports;
`session/testing.py` is the candidate owner).

**F-9 · minor · consistency · `wire_contracts.py:WIRE_TRACK_ROLES` · CONFIRMED**
Hardcodes `("parent","subagent")`, mirroring `track_manager.TrackRole` with no
pin test — unlike the codex stamp-key mirror, which
`test_stamp_keys_match_codex_contract` pins to its owning constants. A
third track role added to `TrackRole` would be silently rejected by the
migration CHECK. Same remedy as the stamp keys: a one-line pin test (test code
may cross the DAG; the codex pin already establishes the pattern).

## 4b. Non-blocking observations (verified but judgment-call or by-design)

- `submit_wire_exchange`/`submit_wire_exchange_deleted`/`_commit_run_lifecycle_event`
  share a try/ensure_open/transaction/notify/failure-result scaffold three times
  (PLAUSIBLE); extraction is feasible but the shared core is thin (different
  result types, notify conditions, failure accounting). Builder's call.
- The normalize/reconstruct trios share a strip prologue in three copies
  (PLAUSIBLE); the per-kind variance (cache_hint, per-block loop) is load-bearing,
  so extraction yields little. Fine as is; the strip invariant is already
  single-sourced in `_strip_stamps` + `PROVIDER_DATA_STAMP_KEYS`.
- An exchange emitted with `response_ir=None` (codex response-parse failure)
  stores a NULL-response row — by design; the schema models it and PR-3 must
  tolerate it. REFUTED as a replay-erases-blocks bug: no constructible path
  re-fires the same exchange_id without its response.
- `_ensure_component_set`'s two-tier identity (member-hash set hash + folded
  fallback) implements spec §3.1 verbatim. Design note for Stuart: always
  folding member meta into the set hash would delete the readback + comparison
  + first-writer-wins caveat entirely, with identical dedup while stamps are
  stable (measured: they are). Worth considering at PR-3 time; not a builder error.
- `WireExchangeWrite.owner` is a constant "local" plumbed through four
  signatures into the notify payload only (no column persists it) — spec's
  payload shape requires it; harmless today, single-user product.
- The stamp-key mirror living in `wire_normalization` with a pin test is
  spec-blessed; an alternative is a layer-1 constants home shared by codex/ and
  session/, but that changes `canonicalization.py`'s stdlib-only charter or adds
  a module — not worth it now.

## 4c. Findings JSON

```json
[
  {"file": "api/src/transport_matters/wire_store_observer.py", "line": 55, "summary": "wire_exchange.session_id stores the native Codex thread id while the session table keys Codex on synth_session_id(run_id, provider, native), so the spec §6 'joins session' contract is dead for every Codex row (Claude works only because native == stored id).", "failure_scenario": "Any Codex capture: PR-3 joins/wire_exchange_session_ix lookups against session.session_id return zero rows; correlation silently broken while the store fills dark with wrong ids (backfillable, since run_id+provider+native are all on the row)."},
  {"file": "api/src/transport_matters/session/wire_store.py", "line": 166, "summary": "Blob bodies are stored via jsonb() which strips decoded NULs AFTER the content hash was computed over the un-stripped body, so hash, stored body, and reconstruction disagree for NUL-bearing content.", "failure_scenario": "A tool_result containing \\u0000 (the exact case strip_decoded_nuls was added for in 5bb3072): stored body is stripped but addressed by the unstripped hash; reconstruct_message returns different bytes than the persisted IR, breaking the spec §3 exact round-trip; NUL/no-NUL variants of identical stored content get distinct hashes."},
  {"file": "api/src/transport_matters/session/test_wire_writer.py", "line": 146, "summary": "Spec §8 PR-2 acceptance requires a Claude fixture asserting the ~96% dedup bound and Claude+Codex round-trip fixtures; only the Codex fixture ships (Claude covered synthetically).", "failure_scenario": "A Claude-specific normalization gap (real tool schemas, replayed tool_results, 10 system parts) ships unasserted; the named acceptance criterion is unmet so the PR-2 gate is not actually green against the spec."},
  {"file": "api/src/transport_matters/session/test_wire_writer.py", "line": 54, "summary": "The dedup-yield denominator is the pretty-printed request.ir.json file size (202–213 KB, still containing the ~96 KB input_item_raw duplicate), ~2× the true wire size, inflating the headline 98.3/98.7% (honest: ~96.5–97%).", "failure_scenario": "Savings accounting derived from this test overstates the reduction; against honest wire bytes the stored fraction is ~3.5%, close enough to the 4% bound that a modest regression passes the inflated test while breaching the true bound."},
  {"file": "api/src/transport_matters/session/writer.py", "line": 132, "summary": "submit_wire_exchange holds a whole-transaction connection from the same 10-connection pool sized as 9 dispatcher shards + 1 aux reserve, with no budget for wire writes.", "failure_scenario": "Burst of finalized exchanges: wire coroutines contend with dispatcher workers for connections; session-event commit latency spikes or PoolTimeout, counted as wire failures."},
  {"file": "api/src/transport_matters/session/wire_store.py", "line": 96, "summary": "The write path does O(history) work per turn: full re-hash of every component, one awaited INSERT per row (hundreds of round-trips), full blob bodies shipped for ON CONFLICT to discard, and a members readback+compare for both sets every turn.", "failure_scenario": "Claude-scale exchange (hundreds of messages) every few seconds: writer loop spends tens of ms CPU plus hundreds of serial round-trips per exchange re-processing ~98%-duplicate content; cumulative O(turns²) per session."},
  {"file": "api/migrations/versions/0008_wire_store.py", "line": 108, "summary": "No indexes on the four reverse-reference columns the GC anti-joins on (set hashes on wire_exchange, member blob_hash, manifest message_hash), and concurrent GC vs live wire write can abort on FK violation despite the 'safe to run any time' docstring.", "failure_scenario": "Grown store: db wire-gc degrades to O(blobs × references) seq scans (minutes+); run during capture it can exit 1 on foreign_key_violation or fail one best-effort wire write."},
  {"file": "api/src/transport_matters/session/test_wire_writer.py", "line": 308, "summary": "_next_notify_payload is a near-verbatim duplicate of the same-named helper in test_run_lifecycle_writer.py.", "failure_scenario": "Notify-drain fixes applied to one copy silently leave the other stale; repo has a zero-tolerance DRY rule."},
  {"file": "api/src/transport_matters/session/wire_contracts.py", "line": 36, "summary": "WIRE_TRACK_ROLES mirrors track_manager.TrackRole with no pin test, unlike the codex stamp-key mirror which is pinned.", "failure_scenario": "A third track role added to TrackRole passes type-checking everywhere but is rejected by the 0008 CHECK constraint at insert time; valid exchanges fail to store."}
]
```

## 5. Spec §8 PR-2 scope check (brief item 4)

In scope and present: migration 0008, wire_contracts, wire_normalization,
submit_wire_exchange/_deleted with the locked `_typed_notify_payload` DRY extraction
(both legacy payload builders converted — no third copy), wire_store_observer,
composition line in `_start_session_capture` (registered side by side with the cursor
sink, deleted sink registered, teardown via existing `clear_exchange_sinks` which
clears both registries), `db wire-gc` CLI, real Codex fixture at
`api/tests/fixtures/codex_http_fallback/`. No scope creep found; nothing reads the
store (ships dark).
