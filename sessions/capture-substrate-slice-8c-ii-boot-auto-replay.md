---
title: Capture Substrate Slice 8c-ii — Boot Auto-Replay
type: sessions
tags: [backend, transport-matters, capture-substrate, slice-8c-ii, index, rebuild, schema-gate, concurrency, moe]
summary: On boot, a stale schema gate now rebuilds tier-2 from tier-1 under a lock instead of dropping the index to empty; the final slice of the capture substrate.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

The last slice of the capture substrate. Before this, the in-writer schema gate (`apply_schema`)
DROPPED tier-2 to empty whenever a gated derivation constant changed (`schema_version`,
`identity_canonical`, `session_ns`, `adapters_version`) and never replayed — so a derivation-logic
bump silently nuked the index. Now that 8c-i made tier-2 faithfully rebuildable from tier-1, this
slice wires `rebuild()` into boot: if the gate is stale, rebuild from tier-1 under a lock BEFORE the
live system opens any connection, instead of leaving an empty index.

All glue — `rebuild()` (8c-i) stays the single drop/replay executor. Branch
`feat/capture-slice-8c-ii-boot-auto-replay` @ `ba0e482` (off main `2219d50`). MoE dual sign-off
(claude 3.1 author, codex 3.2 reviewer). `just ci` green: 1219 passed, ruff + mypy clean. PR + Stuart
road-test pending.

Key decisions:
- **Always-lock, single check under the lock.** The first design used a lock-free cheap pre-check
  before acquiring the lock. Codex caught the race: `rebuild()` seeds current `schema_meta` at writer
  start (`IndexWriter.start()` → `apply_schema`) BEFORE `backfill()` finishes, so a concurrent boot's
  lock-free pre-check could read "current" mid-rebuild and skip the lock entirely, starting its live
  system against a half-populated index. Fix: acquire `exclusive_file_lock` unconditionally, then
  check `is_rebuild_needed` once under it. The lock is held across the WHOLE rebuild (drop → backfill
  → stop), so no boot observes the mid-rebuild window lock-free.
- **`query_only` read, not `mode=ro`.** `is_rebuild_needed` reads via `db.connect(read_only=True)`
  (query_only=ON), the codebase's chosen WAL-safe read path. `mode=ro` URIs trip read-only-WAL lock
  pitfalls on an unclean `-wal` at boot (documented in `db.py`).
- **`is_rebuild_needed` never returns True on a read error** — it raises. A transiently-busy/locked
  CURRENT db must never be falsely dropped (that would inode-strand a running writer). Only genuinely
  absent / unschema'd / gated-mismatched dbs return True.

## API Contract (internal Python surface)

```python
# transport_matters/index/schema.py
def is_rebuild_needed(db_path: Path) -> bool
# True iff tier-2 must be rebuilt from tier-1: db absent, no schema_meta, or a gated key differs.
# No side effects (exists()-guard + query_only read). Promotes the shared _gated_mismatch logic
# (now _stored_gated_meta + _gated_values_differ).

# transport_matters/index/db.py
def index_rebuild_lock_path() -> Path           # default_storage_root()/index.rebuild.lock

# transport_matters/lock.py
@contextmanager
def exclusive_file_lock(path: Path) -> Iterator[None]
# BLOCKING exclusive flock (serializes concurrent holders; vs WorkspaceLock which fails fast).

# transport_matters/index/rebuild.py
def rebuild_if_stale(
    workspaces_root: Path | None = None, *, db_path: Path | None = None, lock_path: Path | None = None
) -> bool
# Boot orchestration: acquire the lock UNCONDITIONALLY → check is_rebuild_needed under it →
# rebuild() if stale. Returns True iff a rebuild ran. rebuild() is the only drop/replay path.
```

`load_runtime` (`addon_runtime.py`) calls `rebuild_if_stale()` as the first statement in the tier-2
`try`, before constructing the live `IndexWriter` (best-effort per §7.1). All three new public symbols
are re-exported from `transport_matters.index`.

## Database Changes

None. The tier-2 schema is unchanged and NO gated constant was bumped (this slice wires the mechanism
for FUTURE bumps). The in-writer gate stays as a harmless safety net — after a boot rebuild the db is
current, so `apply_schema` finds no mismatch and does not drop.

## Security / Correctness Considerations

- **Single-flight by lock, held across the whole rebuild.** `rebuild()` deletes the db files (POSIX
  inode-strand risk), so it must run while nothing else holds them. Boot-vs-boot is serialized: the
  loser blocks until the in-flight rebuild fully completes, then checks current and skips.
- **No data loss on a gated bump.** A stale gate REBUILDS from tier-1 (now complete after 8a/8b),
  never leaves the index empty.
- **Known limitation (R1, accepted out-of-scope per §10.5):** the lock guards boot-vs-boot only, not
  boot-vs-an-already-running instance's live writer on the GLOBAL `index.db`. Cross-instance quiescence
  would need an epoch protocol, deliberately out of scope ("quiescence by ORDERING, not an epoch
  protocol"). Mitigation: tier-2 is a rebuildable projection, so a stranded writer self-heals on its
  next boot. Recorded in the `rebuild_if_stale` docstring.

## Performance Notes

- Every boot now acquires the rebuild flock once and does one read-only `is_rebuild_needed` probe
  (one connect + one `schema_meta` SELECT). flock + a single read is sub-millisecond; uncontended
  boots acquire instantly. Multiple instances booting simultaneously serialize briefly on the lock.
- No new query patterns in the hot path; the probe runs once at boot, never online.

## Tests

- `index/test_schema.py::TestRebuildNeeded` — `is_rebuild_needed` cases (missing/empty/current/changed
  gated key/missing gated key/non-gated change), incl. asserting no db file is created.
- `test_lock.py` — `exclusive_file_lock` creates parent, releases on exit/exception, and BLOCKS (not
  fails) until the holder releases (threads, same-process cross-fd flock contention).
- `index/test_boot_replay.py::TestBootAutoReplay` — stale→rebuild-from-tier1-not-empty (sentinel
  proves DROP not merge), current→no-op, missing→rebuild, single-flight exactly-one-rebuild
  (deterministic: boot A held mid-rebuild under the lock while boot B blocks).
- `test_addon_runtime.py::test_load_runtime_rebuilds_index_before_opening_writer` — pins the ordering
  (rebuild_if_stale before IndexWriter) via monkeypatch spies; the IndexWriter stub raises a
  BaseException so load_runtime aborts before the uvicorn serve binds a port.
- `index/test_replay_support.py` — shared tier-1 run seeders extracted from `test_rebuild.py` (DRY;
  keeps both replay suites ≤700 LOC).

## Open Items

- PR open + `just ci` gate (orchestrator 2.1) on dual sign-off.
- Stuart road-test: bump a gated constant → restart → confirm the index auto-repopulates from tier-1
  with before/after counts matching live, then revert.
- R1 cross-instance quiescence remains a documented limitation; revisit only if multi-instance gated
  bumps become a real operational concern (would need an epoch/marker protocol).
