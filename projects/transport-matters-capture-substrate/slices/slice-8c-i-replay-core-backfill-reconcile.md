# Slice 8c-i — the replay core: rebuild tier-2 from tier-1 (backfill + reconcile + explicit rebuild)

**Goal (the payoff):** prove tier-2 is faithfully rebuildable from tier-1 ALONE. One DRY core
`replay_run`, three thin callers (backfill / reconcile / explicit rebuild). This is the slice that
makes "drop the index, rebuild it, the DIFF survives, even for a session whose CLI file is gone" real.

**Depends on:** 8a (`iter_run_dirs`, `delete_run`, `gc_blocks`), 8b-i (transcript snapshot), 8b-ii
(`sessions.json` owned facts). **Branch:** off current `main` (`05abbf5`).

## DRY mandate (the whole point — read this twice)

8c-i is **glue**. The ONE new function is `replay_run`; everything it does is REUSE. Do NOT reimplement
parsing, binding, IR loading, or block-building. If you write a second copy of anything below, stop.

| Step | REUSE (do not reinvent) |
|---|---|
| enumerate runs | `maintenance.iter_run_dirs(workspaces_root)` → `RunDir(root, run_id)` |
| owned facts | `session_facts.read_run_session_facts(root)` → `RunSessionFacts.sessions[*]` (8b-ii) |
| reconstruct binding | `session_id = native if minted else synth_session_id(run_id, provider, native)` (`index/sessions.py`); `decode_source_descriptor(...)` → `FileTailSource` (carries `home_dir`) |
| wire replay | `read_index`→IndexEntry, `read_exchange`→ExchangeArtifacts, `bind_exchange`, `build_wire_job` (`index/ingest.py`) → `writer.submit` |
| transcript replay | `disk_layout.transcript_snapshot_path(session_id)` → `iter_complete_records` (`tailer.py:44`) → `adapter.normalize` → `build_transcript_job` → `writer.submit` |
| delete orphans | `maintenance.delete_run` + `gc_blocks` (8a) |

## Build (new `index/rebuild.py`)

1. **`replay_run(writer, run_dir)`** — THE single reusable core. Read `sessions.json`; for each owned
   session reconstruct the `SessionBinding` (table above); replay the WIRE side (read_index → per
   entry read_exchange → bind/build_wire_job → submit) and the TRANSCRIPT side (snapshot →
   iter_complete_records → normalize → build_transcript_job → submit). Reads the **snapshot**, NEVER
   the CLI file. No live env, no `RunContext`, no `locate` (the descriptor IS the source).
2. **`backfill(writer, workspaces_root, run_id=None)`** — `replay_run` over one run dir, or all via
   `iter_run_dirs`. Thin caller.
3. **`reconcile(writer, conn, workspaces_root)`** — `iter_run_dirs` vs tier-2: a tier-1 dir with no
   tier-2 rows → `replay_run`; a tier-2 `run_id` with no dir → `delete_run` + `gc_blocks`. SKIP the
   live set (`manifest.read_all` identifies running runs — never fight a live writer). Thin caller.
4. **explicit rebuild trigger** — a public entry that replays all runs into a fresh/empty tier-2 (for
   the demo + recovery), WITHOUT the boot gate/lock machinery (that's 8c-ii). Just: (drop or fresh db)
   → `backfill(writer, workspaces_root)`.

## Invariants (must not break)

- **DRY:** `replay_run` is the ONLY core; backfill/reconcile/rebuild are thin callers (≤~15 LOC each).
- **DAG:** `index/rebuild.py` imports `ir`/`canonicalization` + index siblings (ingest/tailer/adapters/
  sessions/maintenance) + storage **READ** APIs (`read_index`/`read_exchange`/`read_run_session_facts`/
  `disk_layout`) only — NO storage WRITE; mutations go through the **writer** (same single-writer path
  as live). `storage` never imports `index`.
- **Idempotent:** replay must be safe to re-run — `upsert_session`/the wire upsert dedup, and identical
  content rehashes to the SAME `block.hash` (§3.3), so a second replay adds no duplicate rows/blocks.
  Assert it.
- **#17 privacy** (public imports only); LOC ≤ 700/file, funcs ≤ 150.
- **NO `ADAPTERS_VERSION`/schema bump** (that + the boot auto-replay is 8c-ii).

## Acceptance (§13.2; real temp SQLite + seeded run dirs incl. snapshot + sessions.json)

- `replay_run` rebuilds tier-2 for one run from tier-1 alone (wire artifacts + snapshot + sessions.json)
  — no live env, no CLI file present.
- `backfill` over multiple run dirs reconstructs all; `reconcile` backfills the missing set, deletes
  orphan tier-2 runs, and SKIPS the live set.
- **Idempotence:** running `replay_run` twice yields identical row/block counts (no dups).
- **KILLER DEMO (real run — the proof this whole arc was for):** capture real claude+codex sessions →
  `rm ~/.transport-matters/index.db*` AND delete one session's CLI transcript file → explicit rebuild →
  tier-2 returns with **identical** timelines / DIFF / pivot / correlation, INCLUDING the session whose
  CLI file is gone (replayed from the 8b-i snapshot). The block hashes match → the DIFF is byte-identical.
  State the before/after evidence (e.g. row counts + a diff bucket compare).
- `just ci` green.

## Out of scope → 8c-ii

The boot REBUILD executor: wiring `replay_run` into the `schema_meta` gate's drop path (replay-on-drop),
the `~/.transport-matters/index.rebuild.lock` (reuse the `lock.py` flock pattern), connection-quiescence,
and `load_runtime` integration so a future `ADAPTERS_VERSION` bump auto-rebuilds on boot. 8c-i exposes
the explicit trigger; 8c-ii automates it. Do NOT build it here.
