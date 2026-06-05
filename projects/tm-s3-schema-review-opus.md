# S3-schema PR1 review — Opus (Anthropic-family MoE vote)

- **Range:** `git diff 57d1f087..1962bf82` on `ml/s3-schema` (58 files, +1934 / −4930)
- **Lens:** schema + persistence + contract correctness + S1 interplay
- **Tree:** pristine before verdict (`git status --short` empty)
- **Authority:** cm 019f918b (domain model), 019f91b3 (refinements), 019f9297 (provenance), 019f92cc (slice map)

## Verdict: APPROVE — 0 blockers / 0 majors / 2 minors. Builder-trust: HIGH.

---

## Lens 1 — Schema reshape correct ✓

`migrations/versions/0032_space_worktree_ownership.py`:
- `_drop_inventory_schema` drops `space_worktree_link`, `space`, `space_worktree`, `canvas` + the M:N routines `worktree_in_space`, `validate_named_space_worktree_link`, `validate_default_space_membership`. **is_default column, `space_default_owner_uq` partial index, and both M:N triggers/validators are gone** from the upgrade schema (they survive only inside `_create_legacy_*` downgrade helpers).
- `_create_owned_worktree`: `space_id uuid NOT NULL`; owner-safe FK `space_worktree_space_fk (owner, space_id) → space(owner, space_id) ON DELETE CASCADE`; `space_worktree_space_path_uq UNIQUE (space_id, canonical_os_path)` — **replaces** the old `space_worktree_workspace_uq (owner, slug, hash)` + `space_worktree_path_uq (owner, path)`, exactly per 019f91b3. `canonical_os_path` exposed as `path` via `_WORKTREE_COLUMNS` alias in `store_worktree_ops.py`.
- `_create_canvas`: anchor/parent/root-pair constraints preserved — `canvas_anchor_worktree_fk … ON DELETE CASCADE`, `canvas_parent_fk … ON DELETE CASCADE`, `canvas_kind_shape_ck`, `validate_space_worktree_root_pair` trigger + DEFERRABLE circular root-pair FK (`space_worktree_root_canvas_fk`).
- `Space.name` now `NOT NULL`; model `Space.name: str` (was `str | None`), `is_default` field removed — matches zero-backend-default refinement.

## Lens 2 — Persistence safety ✓ (CRITICAL, clean)

- **No FK from session/wire/turn/artifact IR into inventory.** Live CREATE-TABLE set that references space/worktree/canvas is confined to the inventory tables themselves. The S1 affinity stamp is `ALTER TABLE "session" ADD COLUMN` of **plain FK-free `uuid`/`text`** columns (`canvas_id`, `worktree_path`, …) in `0031_session_affinity_stamp.py` — not foreign keys.
- **0032 never touches the `session` table** (no ALTER/DROP against session/wire/turn/transcript). Deleting a Space cascades only `space → space_worktree → canvas`; session/wire transcript IR and the write-once affinity stamps survive as tombstones.
- S1 write-once stamp columns/behavior untouched by this PR.

## Lens 3 — Contract parity ✓

- `StoredWorktree.space_id: SpaceId` added to the base; `ProjectedWorktree` **drops its own** `space_id` (inherits — DRY dedup). `path: str` now required (matches `NOT NULL`).
- Row decode is single-authority: `store_records.worktree_from_row` decodes `space_id` once; `_WORKTREE_COLUMNS`, INSERT column list, and RETURNING all carry `space_id` in `store_worktree_ops._write_detected_worktree`. INSERT/RETURNING/params parity intact.
- `_SPACE_INVENTORY_SELECT_SQL` emits `space_id` via `to_jsonb(w)` (renames `canonical_os_path → path`), so `StoredWorktree.model_validate` receives the now-required `space_id`.
- REST/MCP client-composed bootstrap (approach A): `space_mcp.worktree_create(space_id, path)` → `service.create_workdir(caller, space_id, path)`; `spaceTransport.createWorkdir(spaceId, path)` POSTs `/v1/spaces/{id}/worktrees`. `CrudCaller` gains `allowed_worktree_id` for N:1 authz.

## Lens 4 — DRY ✓ (one authority, no forked path)

- Single `SpaceCrudService`. M:N surface **fully removed from src** (no residual `space_worktree_link` / `worktree_in_space` / `link_worktree` / `unlink_worktree` / Space-`is_default` outside migration downgrade helpers; the `is_default` grep hits are the unrelated harness-connections domain).
- `link_worktree`/`unlink_worktree` → replaced by `create_workdir` + `reconcile_detection`; `_require_worktree_in_space` → `_require_owned_worktree` (membership → ownership). `space_mutations.link/unlink` and the `session/backfill.backfill_session_spaces` cwd→space resolver deleted with no live caller.
- `session/backfill.py` net `−127` is surgical: only the M:N `SessionCwdResolver`/`update_session_affinity` block was excised; the legitimate transcript-replay core (`replay_transcript_run`, still imported by `test_ingest`/`test_subagents`) is intact — not a broken stub.
- `test_reshape_structure.py` guards hold the line: file ≤700, single type authority, service-facade boundary, fresh-import seams, one `canonical_path` runtime implementation.

## Minors

- **m1 (forward-note, `0032._create_canvas`):** `canvas_default_worktree_fk` is `ON DELETE NO ACTION DEFERRABLE`. The S3-delete slice **must null `canvas.default_worktree_id` first** for any canvas pointing at a to-be-deleted worktree, or the delete raises an FK violation. Already anticipated by the slice map ("default_worktree_id null-first"); flagging so the schema decision made *here* is not lost when delete lands.
- **m2 (low confidence, out of core lens):** CMDK progressive disclosure (create-only until >1 Space) was not evidenced by a test in the frontend files I read (`useSpaces.test.tsx`, `commandModel.testSupport.ts`); may live elsewhere. Recommend a quick confirm that a test asserts the disclosure gate.

## Builder-trust verdict (codex build): HIGH

- **Craftsmanship:** owner-safe composite FKs, DEFERRABLE handling of the circular root-pair FK, `space_id` deduped to the base model, surgical M:N removal with zero parallel path.
- **Test rigor:** solid — schema-shape/structure guards + fresh-import tests; the large test-LOC drop reflects deleting the M:N test surface, not thinning coverage; correctly defers the IR-survives-delete test to S3-delete.
- **Spec + reuse fidelity:** faithful to the confirmed N:1 model and refinements (no backend default, `UNIQUE(space_id, canonical_os_path)`, zero-spaces OK, delete deferred); reuses `WorktreeProvenance`, `canonical_path`.
- **Shortcuts:** none detected. No dangling delete across routes/mcp/contracts/transport; no dead stub; no lingering dropped-column reference.
