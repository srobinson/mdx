# Slice 8c-ii — boot auto-replay: a stale gate rebuilds from tier-1 instead of going empty

**Goal (the last slice):** today the `schema_meta` rebuild gate DROPS tier-2 to empty when a gated
version changes and NEVER replays — so a derivation-logic bump silently nukes the index. Now that
8c-i can faithfully rebuild from tier-1, wire it in: on boot, if the gate is stale, **rebuild from
tier-1** under a lock, before the live system comes up, instead of leaving an empty index.

**Depends on:** 8c-i (`rebuild(workspaces_root, db_path)` — REUSED wholesale), 8a/8b-i/8b-ii (tier-1
complete). **Branch:** off current `main`.

## DRY mandate (tight/clean — this slice is ~glue)

REUSE, don't rebuild: `rebuild()` (8c-i) is the executor; `lock.py`'s flock is the lock; the gate
constants/`_gated_mismatch` (schema.py) are the staleness signal. New code = a small public staleness
check + the `load_runtime` wiring + the lock file. If you write a second replay/drop path, STOP.

## Build (RE-CONFIRM line numbers)

1. **`is_rebuild_needed(db_path) -> bool`** — promote/reuse the gate's staleness logic
   (`schema.py:183-190` `_gated_mismatch`: stored `schema_meta` gated keys vs the current
   constants `schema.py:18,30`). Opens a short read-only check; returns True iff a gated key changed
   (or the db is absent/!has schema_meta). Public, no side effects.
2. **`load_runtime` wiring** (`addon_runtime.py:103-132`): BEFORE starting the live `IndexWriter` +
   tailer, if `is_rebuild_needed(index_db_path())` → acquire the rebuild lock → call
   `rebuild(default_workspaces_root(), db_path=index_db_path())` (8c-i: drops + replays with the
   current schema) → release. Then start the live system, which now connects to a current-schema,
   fully-populated DB (the in-writer gate `writer.py`→`db.py:44`→`schema.py` is satisfied → no drop).
3. **`~/.transport-matters/index.rebuild.lock`** — reuse the `lock.py:61-79` flock pattern. Single-
   flight: a second concurrent boot blocks/skips so two processes never rebuild the same DB at once.
4. **Connection-quiescence** (the §10.5 requirement, met by ORDERING, not an epoch protocol): the
   rebuild runs at boot BEFORE any live connection opens, and the lock guards concurrent boots —
   `rebuild()` deletes the db files (POSIX inode-strand risk) only while nothing else holds them. NO
   online rebuild; boot/offline only.

## Invariants (must not break)

- **DRY:** `rebuild()` is the ONLY executor; this slice does not re-implement drop/replay.
- **Boot-only + single-flight:** rebuild fires only at `load_runtime`, under the lock; never online,
  never while the live writer holds a connection.
- **No data loss on a gated bump:** a stale gate must rebuild from tier-1, NEVER leave the index empty
  (that's the whole point — it's safe now because tier-1 is complete).
- **The in-writer gate stays** as a harmless safety net (a current DB satisfies it → no drop).
- **DAG / #17 / single-writer**; LOC ≤ 700/file, funcs ≤ 150.
- Do NOT bump any gated constant here — 8c-ii wires the mechanism for FUTURE bumps; it makes no
  derivation change itself.

## Acceptance (§13.2 + integration)

- `is_rebuild_needed` is True iff a gated `schema_meta` key differs (and on a missing/empty db),
  False on a current db.
- **Stale-gate boot rebuilds (the core test):** seed tier-1 + a tier-2 db whose stored `schema_meta`
  has an OLD gated value → run the `load_runtime` boot path → the index is REBUILT from tier-1 (full
  counts), NOT left empty; assert it went through `rebuild()` under the lock.
- **Single-flight:** two concurrent boots → the lock serializes; exactly one rebuild; no corruption.
- **Current-gate boot is a no-op:** a current db boots without dropping/rebuilding.
- **Integration proof:** simulate a real gated bump (e.g. temporarily raise a gated constant in the
  test, or stub the stored schema_meta) → boot → index auto-repopulates from tier-1 → revert. The
  before/after counts match the live capture (the 8c-i killer-demo property, now automatic on boot).
- `just ci` green.

## After this: the substrate is COMPLETE

8a (enumerate/delete/GC) · 8b-i (own transcript) · 8b-ii (durable owned facts + home_dir) · 8c-i
(explicit rebuild) · 8c-ii (auto rebuild on boot). Capture → correlate → DIFF → search → delete/GC →
durable tier-1 → faithful rebuild, end to end, claude + codex.
