---
title: Capture-substrate roadtest2 — /raw 404 fix (raw_dir workspace-scoped root)
type: sessions
tags: [backend, transport-matters, capture-substrate, raw-fetch, moe, roadtest]
summary: GET /api/index/exchanges/{id}/raw 404'd on live captures because tier-2 raw_dir was rooted at the global default instead of the workspace-scoped tier-1 storage root; fixed by threading the backend root through the sink.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

Road-test 2 of the capture-substrate read API (`/api/index`). MoE pair: this pane (Claude `:3.1`) triaged + fixed; peer (Codex `:3.2`) adversarially verified; orchestrator (`:2.1`) gated. Six findings triaged; one real bug fixed.

- **#1 raw fetch — BUG (prime), FIXED @ `122d161`** on branch `fix/roadtest2-rawdir-workspace-root` (off main, no PR — orch gates on dual sign-off).
- **#2 occurrence search, #3 filtered `[]`, #4 block-mode null fields, #5 diff, #6 pivot — BY-DESIGN / CORRECT** (independently verified vs the live `index.db`, no fix).

### #1 root cause

`build_wire_job` (`api/src/transport_matters/index/ingest.py`) computed `wire_exchange.raw_dir` via `DiskStorageLayout().new_exchange_dir(entry.id, now=entry.ts)` on the **global default** root. But tier-1 artifacts persist under the **workspace-scoped** `settings.storage_dir` (`~/.transport-matters/workspaces/<slug>/<hash>/<session>/`), while the tier-2 `index.db` is **global** (`index_db_path() == default_storage_root()/index.db`). The stored **absolute** `raw_dir` therefore dangled and `GET /raw` 404'd on every live capture, though the bytes were safe on disk. Same family as #23 (a tier-2 path computed independently of the real tier-1 write).

Disk proof: index.db `raw_dir(adfe5384) = ~/.transport-matters/20260604T213553Z-adfe5384` (MISSING); real bytes at `.../workspaces/private-tmp-tm-livecap-test/ef619ce4/add90dbe-.../20260604T213553Z-adfe5384/request.raw` (99539 bytes). The dir NAME was correct; only the ROOT was wrong. `ExchangeArtifacts` carries no on-disk path, so the orch's "use artifact paths" lead was not available — threading the root is the fix.

## API contract

No contract change. `GET /api/index/exchanges/{id}/raw?part=request|response` now streams `FileResponse` bytes (was 404 for workspace-scoped captures). `RawRef` unchanged.

## Database changes

None. `wire_exchange.raw_dir` semantics unchanged (absolute tier-1 pointer); only its computed value is corrected to the real backend root.

## Code changes

- `index/ingest.py`: `build_wire_job(..., *, storage_root: Path | None = None)` → `raw_dir = DiskStorageLayout(storage_root).new_exchange_dir(entry.id, now=entry.ts)`. `make_index_sink(..., *, storage_root)` forwards it. `new_exchange_dir` is a pure path-compute; reconstructs the recorder's exact dir from `id` + `entry.ts` (verified == real on-disk dir for live `adfe5384`).
- `addon_runtime.py` `load_runtime`: captures `DiskStorageBackend.root` and passes `storage_root=` into `make_index_sink`. This is the injection point, so the `storage → index` DAG back-edge stays absent. Default `None` preserves unit callers.

## Tests / proof

- Unit (`index/test_ingest.py`): `raw_dir` honours a provided `storage_root` (asserts the **parent/root**, not just `.name` — the gap the prior test had) + default fallback.
- Integration (`tests/integration/test_raw_fetch_roundtrip.py`): drives the **real** FastAPI `/api/index/exchanges/{id}/raw` route end-to-end (tier-1 under a workspace-scoped root → fixed sink → real route → 200 + bytes).
- **Mutation:** reverting `raw_dir` to `DiskStorageLayout()` (default root) → both regressions RED with the exact road-test symptom (route 404); restored → green.
- **Real-run proof on the live `adfe5384` capture** (the one that 404'd): ingested via the fixed sink into a temp index.db, hit the real route → `part=request` 200/99539 bytes, `part=response` 200/1746 bytes, byte-identical to disk.
- CI gate green: `ruff check src/`, `ruff format --check src/`, `mypy src/` (269 files), `pytest` 1076 passed.

## Security considerations

None new. Raw bytes are streamed from tier-1 the same as before; the fix only corrects which directory the pointer resolves to (the user's own workspace storage).

## Performance notes

None. `raw_dir` is a pure path computation (no extra FS scan); the sink remains non-blocking (`writer.submit`).

## Open items

- **#4 (optional UX, deferred):** block-mode search responses emit per-edge fields as `null` (`stream/entity_id/role/...`) because that mode aggregates across occurrences. Cheap follow-up: `response_model_exclude_none` (or a mode-specific response model) so it doesn't read as broken. Left out of this fix to keep the blast radius on the prime bug.
- Workflow note for self: used `git checkout -- <file>` to revert a mutation and it wiped the uncommitted fix — use a targeted substring revert (or stash) for mutation checks, never a whole-file checkout of unstaged work.
