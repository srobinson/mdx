# Slice 4 — claude transcript + tailer (the DIFF) ★ MILESTONE

**Goal:** add the transcript stream and make the wire↔transcript **DIFF** real (§1.1). Land
the §4 adapter port, the claude adapter, the file tailer, `build_transcript_job`, and the
`transcript_turn` live event — so claude transcripts are indexed, live-tailed, and correlated
to the slice-2 wire rows. First end-to-end pivot/diff.

**Depends on:** slices 1-3 (store, wire ingest, query API — all merged #18/#19/#20).
**Unblocks:** slice 5 (codex reuses port + tailer), slice 7 (live-tail completion), slice 8
(backfill reuses the iterate seam).

## ✂️ SPLIT into 4a + 4b (decided 2026-06-04; HARD GATE already passed — see below)

The HARD GATE is **confirmed passed**: 9 real paired sessions, wire `metadata.session_id` ==
claude transcript `sessionId` == filename stem (parsed from `metadata.user_id`,
`anthropic.py:516-521`). Correlation on the native id holds; minting stays deferred. Given ~7
files + cross-slice reconciliation, the slice is cut along **data vs liveness**:

- **4a (the milestone — data + DIFF):** `adapters/{base,__init__,claude}.py` + `SessionBinding`
  DRY-reconcile (incl. flipping the slice-2 anthropic wire binding to `native_session_id` +
  `session_id=metadata.session_id` + `minted=False` under the canonical §4.2 model; PK value
  unchanged, small slice-2 test updates) + `build_transcript_job` (§7.3) + the correlation
  pivot/diff DIFF test (§8.4) + committed claude golden fixture.
- **4b (liveness):** `tailer.py` FileTail iterate/partial-line + the `transcript_turn`
  threadsafe live event (§9.4) + live-tail(file) test + `load_runtime` tailer wiring.

Files/invariants/acceptance below apply across both; the per-slice cut is as above.

## ⚠️ CENTRAL CORRELATION CONTRACT (read before coding — flows from slice-2 decision A)

- Slice 2 sets `wire_exchange.session_id = ` anthropic's `metadata.session_id` (NO proxy
  `--session-id` mint exists yet). For the DIFF to work, the claude **transcript** must
  produce the **same** `session_id`.
- Claude writes `~/.claude/projects/<cwd-slug>/<sessionId>.jsonl`; the in-file `sessionId`
  == the filename stem (§5.1 verified). **The linchpin: claude's transcript `sessionId` must
  also equal the `metadata.session_id` it sends on the wire.** **HARD GATE:** verify this
  against a real *paired* sample (a transcript + its wire capture). If the equality does NOT
  hold, STOP and escalate to the orchestrator — the no-mint correlation breaks and the whole
  slice needs rethinking.
- Therefore claude `bind()` correlates on claude's **NATIVE** `session_id`, NOT a
  separately-minted uuid. `--session-id` minting is a LAUNCH/DRIVER change explicitly
  **DEFERRED** (slice-2 decision A) — do **NOT** add it here. §5.1's "MINT" path is the
  target once minting lands; for now claude is located/correlated by its native session_id,
  learned from the wire `metadata.session_id` (read-back-style → §15 risk 2 one-frame
  startup lag is acceptable).

## Read first (canonical spec)

§4 (adapter port), §5.1 (claude adapter), §7.3 (transcript write path), §9.2/§9.3 (tailer +
FileTail iterate seam), §9.4 (cross-thread `transcript_turn` event), §8.4 (pivot/diff, now
exercised for real). Real sample: a `~/.claude/projects/<slug>/<uuid>.jsonl` (§5.1 cites a
290-line one) — commit a golden fixture from it.

## Files (≤700 LOC; functions ≤150)

1. `index/adapters/base.py` (~190) — §4 port: `TranscriptAdapter` ABC +
   `SessionBinding`/`TranscriptSource`(`FileTailSource`|`PullSource`)/`RunContext`/
   `TurnContext`/`NormalizedTurn`. **RECONCILE** the `SessionBinding` staged in slices 1/2
   into THIS single canonical model (DRY — update the slice-1/2 references, no duplicate
   definition). `parts: list[ir.ContentBlock]`.
2. `index/adapters/__init__.py` — registry: `cli → adapter`, `get_adapter(cli)`.
3. `index/adapters/claude.py` (~150) — §5.1 `bind` (native session_id, `minted=False` per
   the contract above), `locate` (deterministic `~/.claude/projects/<slug>/<session_id>.jsonl`
   `FileTailSource`), `normalize` (jsonl line → `NormalizedTurn`; skip `type` ∉ {user,
   assistant}; map `message.content` per the §5.1 block table; `thinking.signature` →
   `provider_data`, stripped from identity).
4. `index/tailer.py` (~260) — §9.2 `TranscriptTailer` + `TailCursor`; §9.3 FileTail iterate
   seam (stat size/mtime, seek `byte_offset`, split on `\n`, parse **complete records only**,
   advance `byte_offset` past consumed, **leave the trailing partial**). Registers the claude
   cursor (read-back: after the first wire frame reveals `session_id`), submits
   `build_transcript_job`. The record-iterate fn is the ONE path shared with §11 backfill.
5. `index/ingest.py` — `build_transcript_job(turn, binding)` (§7.3): `upsert_session` +
   `transcript_turn` + `turn_block` edges (parts → blocks; the turn's role on every edge).
6. `index/writer.py` — `transcript_turn` live event via `loop.call_soon_threadsafe` (§9.4,
   the minimal cross-thread emit the §13.2 live-tail test needs). `session_correlated` event
   + opencode poll = slice 7 (do NOT build here).
7. Wiring: tailer started in `load_runtime()` (`addon_runtime.py:28-59`); claude cursor
   registration triggered by the first wire frame's `session_id`.

## Invariants (must not break)

- **The correlation contract above** (the central one; hard-gated).
- `SessionBinding` defined **once** in `adapters/base.py`; slices 1/2 staged copies reconciled
  to it (DRY, no duplicate model).
- Transcript turns emit only the **6 CONTENT kinds** (text/tool_use/tool_result/thinking/
  image/unknown), **never** system/tool_def (§4.1.4).
- `parts` reuse `ir.ContentBlock` **verbatim** → identical content dedups to ONE block across
  wire+transcript (the pivot linchpin, §3.3).
- `turn_id` = claude native `uuid` (no synth); `parent_id` = `parentUuid`; `is_sidechain` =
  `isSidechain`; `ts` = `timestamp`; `model` = `message.model` (assistant only).
- FileTail crash-safety: advance `byte_offset` only past the last `\n`; trailing partial waits
  (§9.3, §15 risk 6).
- Cross-thread: the `transcript_turn` event ONLY via `loop.call_soon_threadsafe` (the writer
  is an OS thread; §9.4, §15 risk 1) — never a direct `broadcast.emit` from the thread.
- Tailer = one thread per process (sibling to the writer); poll (not inotify), ~250 ms file
  (§9.2).
- #17 privacy; DAG: adapters import `ir` only; tailer/ingest import `storage`+`index`; no
  `storage → index`.

## Acceptance (§13.2; real temp SQLite + golden fixtures)

- **claude golden fixture** (real jsonl) → `normalize` produces the correct `NormalizedTurn`
  (uuid/parentUuid/role/parts), and skips non-conversational records (ai-title/system/…→None).
- **correlation join (the first real DIFF):** ingest a wire exchange + a claude transcript turn
  **sharing content** under one `session_id` → `session_pivot` reports the correspondence,
  `session_diff` buckets shared / wire_only / transcript_only correctly.
- **live-tail(file):** register a `FileTailSource` on a temp jsonl, append lines → the tailer
  consumes complete records, LEAVES a trailing partial line, the writer commits, and a
  `{type:"transcript_turn"}` event arrives on `/api/stream`.
- **HARD GATE:** `jsonl.sessionId == wire metadata.session_id` confirmed on a real paired
  sample (the correlation linchpin) — state the evidence explicitly.
- `just ci` green.

## Grounding (confirm current, post #16-#20)

`ir.ContentBlock` (slice-1). Slice-2 wire session_id sourcing (`ingest.bind_exchange`,
`metadata.session_id`). `broadcast.emit` + `/api/stream` (`api/v1/stream.py` — confirm current
path). The claude sample under `~/.claude/projects/`. `addon_runtime.load_runtime()`:28-59.
The staged `SessionBinding` (slice-1/2 location — find + reconcile).

## Build order (TDD)

`base.py` port (+ reconcile staged `SessionBinding`) → `claude.normalize` (golden fixture) →
`claude.bind/locate` → `build_transcript_job` (turn → rows) → **correlation/pivot/diff test
(the DIFF)** → tailer (FileTail iterate, partial-line, register/submit) → writer
`transcript_turn` event (threadsafe) → live-tail(file) test → wiring → privacy/DAG.

> This is the largest slice. If the panel judges it should split (e.g. adapter+DIFF as 4a,
> tailer+live-event as 4b), flag it to the orchestrator rather than overrunning the LOC/clarity
> budget.
