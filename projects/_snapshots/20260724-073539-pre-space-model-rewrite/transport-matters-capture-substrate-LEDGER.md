# LEDGER — Transport Matters Capture & Retrieval Substrate spec

- Spec:  `~/.mdx/projects/transport-matters-capture-substrate-spec.md`
- Brief: `~/.mdx/projects/transport-matters-capture-substrate-BRIEF.md`
- Orchestrator: `transport-matters:general:1:2.1`

## Current phase

**COMPLETE + EVALUATED. Ready to build.** All four phases signed off by both panes
(Claude author + Codex reviewer). Spec §1-15 filled, no placeholders.

Stuart evaluated 2026-06-04. Two post-signoff edits applied (git e3e67d1 base):
- §7.3 wart RESOLVED: the "tier-1 side" paragraph no longer instructs manifest
  recording; it now states "required tier-1 change: none" and defers to §11.1. The
  §11.1 supersession note is retained as the historical record.
- `adapters_version` added to the schema_meta rebuild gate (§3.2 seed + boot prose,
  §10.5 trigger, §11.4 trigger). Single global counter over all §5 transcript
  adapters; bump on ANY normalize change → silent whole-DB drop+rebuild (cheap, no
  embedding cost). Closes the silent-stale-parse gap (borrowed from MemPalace
  `normalize_version`; see `~/.mdx/research/mempalace-mempalace.md`).

Build decomposed into per-slice briefs (canonical spec stays whole — cross-refs are
load-bearing): `~/.mdx/projects/transport-matters-capture-substrate/` (README index +
slice-N briefs generated just-in-time). Approach: MoE peer-consensus per slice (Claude
author + Codex reviewer, dual sign-off), orchestrator gate-verify + PR.

## Build log

- **Slice 1 — core store + writer: MERGED @ #18 `44e89c0`** (2026-06-04). MoE dual sign-off
  @ a05a18a; just ci green 1023. Panel caught a §3.2 missing-gated-key gate bug (adapters_version
  exposed it) → fixed + regression. Scope note: slice 6 (gemini+opencode) PARKED.
- **Slice 2 — wire ingest + sink: MERGED @ #19 `ea13e09`** (2026-06-04). MoE dual sign-off
  @ b200cc3; just ci green 1037. Panel caught a seq-backfill bug (correlation upsert set
  session_id but left seq NULL → broke §8.3 ordering) → fixed `seq = COALESCE(existing,
  computed)` + regression. Decisions accepted: (A) no proxy --session-id mint yet → minted
  providers use anthropic's metadata.session_id directly (fwd-compat w/ slice-4 mint),
  read-back synth; (B) sink hooked only at the :264 finalized-HTTP seam, codex/provisional
  deferred to slices 5/7.
- **Slice 3 — read/query API: MERGED @ #20 `c008ae5`** (2026-06-04). MoE dual sign-off
  @ 45b2dc9; just ci green 1056. Panel caught a loop-blocking bug (async def handlers running
  sync SQLite + Path.exists on the event loop) → fixed to sync def (FastAPI threadpool) +
  dropped ASYNC240 ignore. Decisions accepted: query_only read-only conn, MATERIALIZED
  block-mode CTE, wire-only pivot/diff.
- **Slice 4 ★ MILESTONE — SPLIT 4a/4b** (2026-06-04, both panes + orchestrator agreed) on
  `feat/capture-slice-4-claude-transcript-tailer`. HARD GATE **PASSED** firsthand: 9 real
  paired sessions, wire metadata.session_id == claude transcript sessionId == filename stem
  (parsed from metadata.user_id, anthropic.py:516-521) → correlation on native session_id
  holds, minting stays deferred.
  - **4a (data + DIFF): MERGED @ #21 `317b756`** (2026-06-04). MoE dual sign-off @ ac121ee —
    FIRST clean first-pass (no blocker). Single canonical SessionBinding (slice-1/2 staged
    copies reconciled; slice-2 anthropic flipped to native_session_id + minted=False);
    build_transcript_job; the wire↔transcript DIFF (shared/wire_only/transcript_only + pivot)
    verified with one shared block across streams; golden fixture. just ci 1064.
  - **4b (liveness): MERGED @ #22 `7c65c50`** (2026-06-04). MoE dual sign-off @ 7e6b462 —
    clean, no blocker. tailer.py (single iter_complete_records seam shared w/ §11 backfill,
    partial-line safe) + transcript_turn post-commit threadsafe event + addon_runtime wiring
    (tailer-before-writer drain order). just ci 1072.

**SLICE 4 COMPLETE** — full claude path live end-to-end.

- **Code-quality audit (subagent): CLEAN.** SessionBinding single-def confirmed; 3 low findings
  folded into slice 5 (dead table-mirror models, bind()/RunContext port-ahead, test-factory dup).
- **ROAD-TEST found + FIXED a live-capture bug (#23 `1516f95`).** Real claude session captured
  ZERO rows: tier-2 sink (emit_to_index) was only hooked on the NON-provisional seam (:268), but
  claude STREAMS → provisional finalize path never reached it. 80 unit tests missed it; Stuart's
  one "Hello" caught it. Fix: emit at _finalize_http_provisional_exchange:422-426 + WARNING
  observability + provisional-flow regression. MoE dual sign-off @ 5158870, just ci 1073. Real
  e2e re-confirmed working (index.db 0 → wire=14/transcript=29/session=4/block=72, live SSE, DIFF
  returns). cm lesson stored. See `cx` lesson "Live-capture wrote ZERO rows…".

- **ROAD-TEST PASS 2 found + FIXED a second bug (#24 `1dd43fa`).** /api/index/exchanges/{id}/raw
  404'd: build_wire_job computed raw_dir on the GLOBAL default root, but tier-1 is WORKSPACE-scoped
  → dangling absolute pointer (bytes safe on disk). Fix: thread DiskStorageBackend.root through
  make_index_sink→build_wire_job; added a REAL-route integration test (test_raw_fetch_roundtrip.py).
  MoE dual sign-off @ 122d161, just ci 1076. Triage: of 6 road-test findings only #1 was a bug;
  #2-#6 by-design/correct, and #5 CONFIRMED cross-stream dedup works (the thesis). Deferred cheap
  follow-up: block-mode response_model_exclude_none UX. See cx lesson "/raw 404…".

- **Slice 5 (codex): MERGED @ #25 `33e087a`** (2026-06-05). MoE dual sign-off @ 55754e2; just ci
  1103. Live-proven on Stuart's real codex run. Read-back adapter; codex wire seam → emit_to_index
  at DURABLE seams only (provisional NOT — abandoned provisional is deleted → #24-class orphan).
  CONVERGENCE root cause: codex session id is NESTED in client_metadata["x-codex-turn-metadata"],
  not top-level → _parse_metadata now resolves via codex_session_id_from_provider_metadata. Forcing
  the live run surfaced a SERIALIZER LEAK (populating metadata.session_id made the serializer inject
  a top-level id into mutated frames the client never sent) — fixed + transparency test. model_hint
  hook threads codex turn_context.model. Audit: bind()/RunContext live, deleted dead BlockRow,
  _binding→conftest.
  - **Orchestrator independent verify** caught a false-alarm (6 NULL codex wire rows): 5 were STALE
    pre-fix rows (index.db not reset between runs), 1 was a request_kind=memory request that correctly
    carries no session_id → uncorrelated. Fix confirmed correct.
  - **FAST-FOLLOW (slice 7):** tighten the §15-risk-2 doc comment in codex.py — the uncorrelated codex
    frames are request_kind=memory + window-handshake (no session_id), possibly SEVERAL per session,
    NOT "only the frame-1 phantom". Prevents the same false-alarm recurring.

- **Slice 5b (codex managed-mint / tail-race fix): MERGED @ #26 `abe1895`** (2026-06-05). MoE
  dual sign-off @ 558234a (fresh `moe-codexmint` panel; the read-back-era `moe-tailrace` panel
  was nuked + re-spun on the locked design). just ci green 1124. ROOT CAUSE (road-test #3):
  codex transcript tail RACE — one-shot `locate()` glob ran on the first wire frame, but codex
  wrote the rollout ~1s later → glob missed, dead-root fallback, no retry → permanent miss
  (`transcript_turn=0`). FIX (Stuart-driven design): own the launch. Launcher mints
  `native_session_id=uuid4()`, pre-seeds the minimal `session_meta` rollout at the exact owned
  path, launches `codex resume <native>`; `source_descriptor`+`cli` stamped on the session row;
  tailer byte-tails the descriptor from 0. DELETED `locate` glob + dead-root fallback +
  `_poll_cursor` missing-path early-return + window-id phantom handling — "external observed
  codex" is unreachable (the proxy only sees what TM launched, so TM owns the uuid+path).
  Reviewer caught a session-row-before-cursor ordering gap (round 1): wire job now submits before
  `on_binding`; empty-row also impossible by construction (both streams upsert, COALESCE'd
  enrichment cols). REAL PROOF: 2 managed `codex resume <uuid>` instances, same cwd → each
  resumed into TM's seeded file (no fork), 5 converged turns/session, zero cross-binding. Lesson:
  read-back discovery was compensating for not owning the path; owning the launch removes the race
  class entirely.

- **Slice 5c (claude managed-mint + DRY launch-profile port): MERGED @ #27 `4869caa`** (2026-06-05).
  MoE: author @ c9b7400, reviewer-caught passthrough-guard blocker fixed @ f53657e
  (orchestrator-applied — author pane was off the bus; one-liner, Stuart-verified), reviewer clean
  sign-off on f53657e. just ci green 1149. Stuart road-tested: "everything working perfectly."
  CONTEXT: realizes the original Phase A design Stuart identified — claude OWNS its session id via
  `claude --session-id <uuid>` (proven to CREATE, no seed), so correlation is true by construction
  instead of native-adopt's "if wire==transcript==filename equality fails → STOP" invariant. The
  deferral post-mortem: slices 2/4a mischaracterized mint as deferred "proxy --session-id" work and
  shipped native-adopt as a stopgap that calcified; native-adopt RETAINED here as the external-adoption
  fallback (un-owned sessions → locate, minted=False). DESIGN: new `cli/launch_profile.py` LaunchProfile
  ABC (launch-side twin of TranscriptAdapter) — prepare/client_argv/user_supplied_session; one shared
  `prepare_managed_session`; claude+codex converge; a future mint-capable CLI = one profile (fake-profile
  test proves zero launch-flow edits). minted/session_id derivation stays in ingest.bind_exchange (DAG
  forbids index→cli): claude minted=True (id direct), codex unchanged (synth, minted=False). env vars
  generalized CODEX_*→OWNED_* (provider-neutral). REAL-RUN caught a SLUG bug units missed: claude slug =
  re.sub([^a-zA-Z0-9],"-",cwd), NOT replace("/","-") — the naive form tailed a path claude never wrote
  (transcript_turn=0). Lesson: minting was always the right design; it got filed as expensive deferred
  proxy work when `claude --session-id` is a one-flag realization — verify "we can't yet" claims against
  the actual CLI surface.

- **Slice 7 — DECISION: `session_correlated` DEFERRED** (2026-06-05, MoE dual sign-off, panel
  moe-slice7 author 3.1 + reviewer 3.2). Not a build. `transcript_turn` + the cross-thread bridge
  already shipped in 4b; opencode Pull-poll parks with slice 6. The only open feature was the
  `session_correlated` SSE event (§9.4: fire when a NULL `wire_exchange.session_id` is backfilled).
  Both panes INDEPENDENTLY confirmed (and both independently caught an error in the orchestrator's
  brief — `_WIRE_UPSERT` is last-writer-wins `session_id = excluded.session_id`, NOT a COALESCE
  backfill; only `seq` is COALESCE-guarded, ingest.py:320/334): managed-mint (5b/5c) owns the session
  id at launch, so there is NO producer of a NULL→non-NULL transition. `bind_exchange` nulls a row
  only when the request has no `metadata.session_id` (codex non-conversational/memory frames), and
  those have no session → stay NULL permanently; `emit_to_index` fires once per exchange_id at the
  durable seam (never provisional/rewrite). The event would fire on a transition that never occurs →
  DEFER (YAGNI; §8.4 pivot/diff filter on session_id so phantom NULL rows are inert — defer breaks
  nothing). REVIVE only when external-adoption or a read-back provider (opencode) creates a
  same-exchange_id NULL→non-NULL transition AND a UI consumer needs the refresh. PREREQUISITE for the
  revival build: COALESCE-protect `wire_exchange.session_id` (or guard the re-emit) — else a later
  NULL re-emit would clobber a known session_id (de-correlation on last-writer-wins). Recorded in spec
  §9.4 + README slice 7. SHIPPED regardless: the codex §15-risk-2 doc-comment fix (adapters/codex.py
  — corrected the "frame-1 phantom" characterization: codex non-conversational/memory frames + tier-1-only
  handshake-failure frames, recurring, not a single phantom). Lesson: the panel's adversarial pass
  CONFIRMED a defer (not every slice is a build) and corrected the orchestrator's own mechanism claim
  — peer-consensus earns its keep on "should we build this at all" questions, not just on diffs.

- **Slice 8a — durable enumerator + tier-2 delete + block GC: MERGED @ #29 `5d53a88`** (2026-06-05).
  MoE dual sign-off @ 0046cf0; just ci green 1159. New `index/maintenance.py` (122 LOC, SQL-only, zero
  launch state): `iter_run_dirs` (durable glob `*/*/*/index.jsonl`, NEVER manifest.read_all — manifests
  are live-only/unlink-on-exit); `delete_run`/`delete_exchange` (tier-2 entities-first, edges cascade
  via FK); `gc_blocks` (mark-sweep — block referenced by NEITHER exchange_block NOR turn_block; the
  §3.3 cross-stream dedup block survives until BOTH refs gone; FTS evict via block_ad trigger;
  idempotent). DECISIONS cleared: (A) tier-2-only delete — does NOT unlink tier-1 raw (tier-1 =
  source-of-truth + rebuild substrate; tier-1 delete stays storage-owned via the exchange_deleted
  broadcast); (B) single-writer = maintenance-as-`IndexJob(apply=…)` on the writer thread's savepoint
  (or db.transaction offline), NO 2nd write conn, NO writer.py change; (C) GC-scheduling wiring +
  reconcile/rebuild/backfill deferred to 8b. Reviewer caught an atomicity OVERCLAIM in the module doc
  (separately-enqueued delete + GC jobs are independently savepointed, not atomic) → reworded:
  atomic ONLY when one apply/db.transaction wraps both. Orchestrator real-data proof: `iter_run_dirs`
  enumerated 3 real run dirs under ~/.transport-matters/workspaces (the one FS-layout-touching fn,
  5c-slug-class risk — confirmed correct). No app surface to road-test (delete/GC wiring is 8b).

- **Slice 8b-i — own the transcript (tier-1 snapshot): MERGED @ #30 `ee0272b`** (2026-06-05). MoE dual
  sign-off @ 5defc92; just ci green 1175. WHY: tier-1 held ONLY the wire; the transcript lived only in
  the CLI's own file (~/.claude/projects, ~/.codex/sessions), which the CLI/user can GC → a tier-2
  rebuild then lost the whole transcript half (DIFF collapses to wire-only). This was a latent shortcut
  against the "tier-2 rebuildable from tier-1" thesis (surfaced by Stuart probing rebuild + the codex
  source_descriptor gap + "what if claude GCs the jsonl"). FIX: the tailer tees a BYTE-FAITHFUL copy of
  every consumed transcript record into a new per-session tier-1 slot `<run_dir>/transcripts/<session_id>.jsonl`
  BEFORE normalize (keeps the non-conversational records normalize drops). New `storage/transcript_snapshot.py`
  `make_transcript_snapshot_writer` — INJECTED callback (NO storage import in index/tailer.py — the DAG
  seam), tailer-thread append (off §7.1 hot path), structural idempotence (snapshot is a prefix copy →
  appends only the un-owned tail). Live read path UNCHANGED (still tails the CLI file, tees a copy; the
  snapshot is the read source only on the 8c rebuild path). Reviewer caught BLOCKER 1: `stat_signature`
  advanced BEFORE snapshot/ingest (stat guard short-circuited retries on a snapshot failure) + the writer
  gap branch returned SUCCESS (tier-2 could advance past a snapshot hole) → fixed: signature advances
  LAST; a gap raises `TranscriptSnapshotGapError`. LIVE ROAD-TEST (Stuart, real claude+codex under
  `--home-dir ~/.claude.lilo`): both `<run_dir>/transcripts/<session_id>.jsonl` present + non-empty;
  claude minted=1 / codex minted=0; descriptors + wire/transcript correlation clean. Sequencing: 8b-ii
  bumps ADAPTERS_VERSION AFTER this lands so the drop+rebuild has the snapshot to rebuild from.

- **Slice 8b-ii — home_dir first-class on descriptor + durable owned-launch sessions.json: MERGED @
  #31 `05abbf5`** (2026-06-05). MoE dual sign-off @ d6afc79 — round 1, NO blockers (clean first-pass);
  just ci green 1195 (+20). 4 coupled pieces: (1) `home_dir` optional field on `FileTailSource`
  (round-trips through the one codec; old descriptors decode `home_dir=None`); (2) claude `locate`
  honors `home_dir` — added to `SessionBinding`+`RunContext`, `bind()` propagates it like `cwd` (NOT a
  model_copy carry), `register_session_cursor` threads `binding.home_dir→RunContext`; (3) env channel
  `env_keys.HOME_DIR`→`build_launch_env`→`Settings`→`build_run_facts`, `bind_exchange` stamps
  `binding.home_dir` on EVERY binding (not gated on is_owned — external-adoption needs it); (4) durable
  per-run `<run_dir>/sessions.json` (new `storage/session_facts.py` `OwnedSessionFacts`/`RunSessionFacts`,
  atomic tmp+replace, upsert by native id; written by the LAUNCHER cli→storage, NO index→storage edge;
  `mints_session_id` launch-twin for minted). NON-DESTRUCTIVE: no ADAPTERS_VERSION/schema bump (schema.py
  not in the diff → the gate literally can't trip; `home_dir` is an in-memory carrier, never a
  session-row column) — the bump + drop+rebuild is deferred to 8c's executor. LIVE ROAD-TEST (Stuart,
  real claude+codex under `--home-dir`): one sessions.json per run carrying cli/minted/native +
  `descriptor.home_dir` matching the managed home (claude `.claude.lilo` minted=true; codex `.codex.lilo`
  minted=false). **Tier-1 now owns BOTH the transcript bytes (8b-i) AND the owned launch state (8b-ii)
  → a faithful rebuild is now POSSIBLE.** LAST slice = 8c (backfill/rebuild/reconcile executor).

- **Slice 8c-i — the replay core (rebuild tier-2 from tier-1): MERGED @ #32 `2219d50`** (2026-06-05).
  THE PAYOFF. MoE dual sign-off @ 6ef6e4d; just ci green 1204. New `index/rebuild.py`: ONE DRY core
  `replay_run(writer, run_dir)` + thin callers `backfill`/`reconcile`/`rebuild`. 100% reuse
  (`iter_run_dirs`, `read_run_session_facts`→binding [native if minted else synth +
  decode_source_descriptor], `read_index`/`read_exchange`/`bind_exchange`/`build_wire_job` wire,
  `transcript_snapshot_path`→`iter_complete_records`→`normalize`→`build_transcript_job` transcript-from-
  SNAPSHOT-not-CLI, `delete_run`/`gc_blocks` orphans). DRY refactor: `ingest_records` extracted into
  tailer.py, shared verbatim by `_poll_cursor` + replay. Deliberate SYNC tier-1 read (NOT the async
  DiskStorageBackend — it strands a ThreadPoolExecutor per dir + self-heals mid-read). Reviewer caught
  reconcile skipping UNDER-counted (partially-indexed) runs → fixed (`_is_undercounted` OR'd into the
  replay predicate + regression). NO ADAPTERS_VERSION bump (explicit trigger; boot-auto = 8c-ii).
  **ORCHESTRATOR RAN THE KILLER DEMO ON REAL DATA** (non-destructive, rebuilt into a temp db): rebuild
  from tier-1 ALONE == live index.db EXACTLY (sessions=2 / wire=5 / turns=8 / blocks=71 / edges 85+12),
  ALL 71 block HASHES identical (DIFF byte-identical), AND with a CLI transcript file HIDDEN the rebuild
  still produced all 8 turns (replayed from the 8b-i snapshot, not the CLI file). **THE THESIS IS
  PROVEN: tier-2 is faithfully rebuildable from tier-1, and a session survives rebuild after its CLI
  transcript is deleted.** LAST slice = 8c-ii (boot auto-replay: gate-drop wiring + rebuild.lock +
  connection-quiescence in load_runtime).

- **Slice 8c-ii — boot auto-replay (THE LAST SLICE): MERGED @ #33 `408b36e`** (2026-06-05). MoE dual
  sign-off @ ba0e482; just ci green 1219. The schema_meta gate dropped tier-2 to empty on a gated
  version change + never replayed; now a stale gate REBUILDS from tier-1 on boot instead of emptying.
  Glue over rebuild() (8c-i) + lock.py: `schema.is_rebuild_needed` (promotes _gated_mismatch; read-only
  query_only probe; raises on transient read err, never false-True), `lock.exclusive_file_lock` (blocking
  flock), `rebuild.rebuild_if_stale` (the ONLY drop/replay path — acquires the lock UNCONDITIONALLY +
  holds it across the whole drop→backfill→stop, checks staleness once under it), wired first in
  load_runtime before IndexWriter. Reviewer caught a LATE-CURRENT RACE (the original cheap pre-lock
  early-return let a concurrent boot see the mid-rebuild current schema + skip the lock → start against a
  half-rebuilt db) → fixed by unconditional lock-hold across the rebuild + the single-flight test now
  holds A mid-rebuild while B blocks. test_rebuild.py split 766→428 (shared seeders → _support module).
  R1 cross-instance-strand ACCEPTED out-of-scope (§10.5 ordering, not epoch; docstring note); R2
  load_runtime ordering test REQUIRED + added (asserts rebuild_if_stale before IndexWriter). ORCHESTRATOR
  REAL-DATA DEMO: a current db → rebuild_if_stale no-op (ran=False); a forged-stale db → ran=True,
  rebuilt from tier-1 to full counts (wire 5, turns 8) + adapters_version reseeded to current, NOT empty.

## 🏁 CAPTURE SUBSTRATE COMPLETE (2026-06-05)

All 8 slices shipped (6 = gemini/opencode parked, outside the claude+codex scope; 7 = session_correlated
DEFERRED by decision). Pipeline end to end, claude + codex: **capture → correlate → wire↔transcript DIFF
→ FTS search → timeline/pivot → delete/GC → durable tier-1 (wire raw + transcript snapshot + sessions.json)
→ faithful rebuild (explicit + boot-auto).** Tier-2 is a true rebuildable projection of tier-1; a session
survives rebuild even after its CLI transcript is deleted (proven on real data). PRs #18-#33.

## Phase status

- Phase A - Foundations (1, 2, 3, 12): APPROVED
- Phase B - Adapters (4, 5): APPROVED
- Phase C - Engine + data paths (6, 7, 8): APPROVED (both panes signed off 2026-05-31; 5 Bs across 3 rounds, session_id sourcing swept to binding.session_id)
- Phase D - Lifecycle + verification (9, 10, 11, 13, 14, 15): APPROVED (both panes signed off 2026-05-31; 3 Bs/3 rounds: durable iter_run_dirs() enumeration since manifests unlink on exit, rebuild requires connection-quiescence not just BEGIN-pause, §7.3/§11.1 supersession)

## Locked decisions (carry across phases)

- Hybrid two-tier. Tier-1 = per-run dir source of truth (raw bytes). Tier-2 = shared
  `~/.transport-matters/index.db` (WAL), rebuildable derived projection.
- Global content-addressed `block` (blake2b). FTS5 lexical first; vector deferred.
- Per-provider adapter port; MINT claude/gemini, proxy codex, api/export opencode;
  minted/synth session uuid = universal correlation key.
- Both streams first-class, never collapsed. No backcompat; LOC 700/file, 150/func.

### Phase A resolved (load-bearing)

- Block identity = SEMANTIC dedup (`identity_canonical` strips provider_data; cache_hint
  for system). Lossless reconstruction is tier-1's job. `block.n_chars` removed; nullable
  `n_tokens` back-fillable via COALESCE; immutability narrowed to identity+search cols.
- `session_id` PK = idempotency key: minted uuid (claude/gemini) or
  `uuid5(SESSION_NS, "{run_id}|{provider}|{native_session_id}")` for codex; partial
  unique index `WHERE native_session_id IS NOT NULL`.

### Phase B resolved (load-bearing)

- §4 port = ABC + dataclasses (`SessionBinding`, `TranscriptSource` file-tail/pull-api,
  `NormalizedTurn`, `normalize()`, `TurnContext.pending_calls` to bridge cross-record
  pairing). Block model reuses `ir.ContentBlock`.
- §5 adapters: claude (jsonl uuid/parentUuid, mint); codex (rollout+session_index,
  read-back, uuid5); gemini FORMAT-SPLIT (A live-session intra-record toolCalls[];
  B cross-record functionCall/Response via pending_calls; chats/*.jsonl vs Content[]);
  opencode (export info-wrapper/model/header-strip + opencode.db, one canonical reshape).

### Phase C resolved (load-bearing)

- §6 indexer = in-proxy writer thread (daemon rejected), fed by a DAG-safe injected
  post-persist sink (no recorder->index cycle); WAL+busy_timeout single-writer;
  `IndexJob` embeds `SessionBinding`; per-job `SAVEPOINT`/`ROLLBACK TO` batch isolation.
- Shared `index/sessions.py` (`SESSION_NS`/`synth_session_id`/`upsert_session`) so wire
  + transcript converge on one `session_id`. `binding.session_id` is the SINGLE
  authoritative source everywhere; `artifacts.request_ir.metadata` is INPUT-only to
  `bind_exchange`.
- §7 tier-1-first (authoritative), best-effort batched tier-2 off the hot path.
- §8 two-phase FTS; timeline reconstruction; wire<->transcript pivot/diff (join on stored
  session_id + block-hash); raw fetch via raw_path; query surface = `index/queries.py`
  + new `/api/index` router. Layering: index core imports ir+canonicalization only;
  storage coupled only at the ingest/writer boundary.

## Approved sections

- Phase A: §1, §2, §3 (+§3.8 exec verification), §12. Both signed off.
- Phase B: §4 port, §5 adapters. Both signed off.
- Phase C: §6 indexer, §7 write path, §8 read/query. Both signed off.
- Spec is 1561 lines. §9, 10, 11, 13, 14, 15 remain (Phase D).

## Open escalations

(none)
