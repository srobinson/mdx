# PR #316 S1 reshape review — aggregate / domain / contract lens

Date: 2026-07-22
PR: [#316](https://github.com/littleorgans/transport-matters/pull/316)
Head: `855bd0a938c68123a24178d7c92953e10b720721`
Baseline: `9ac8d10d2d5304bc579980636729d466e952f404`
Reviewer lens: two-aggregate M:N model, `worktree_in_space` predicate, canvas anchoring,
reconcile boundary, contract parity. Complements gpt's identity/concurrency review
(`tm-s1-reshape-review-gpt.md`).

Verdict (net-new to gpt): **0 blockers, 1 major, 1 minor.**
Cross-review: co-sign gpt M1 / M2 / M6, deny gpt M4 (deferred scope, not an S1 defect),
concur gpt M3 / M5.

Builder trust: **low**. The two-aggregate shape is correctly realized (see Verified below),
but the slices built under the silent low-effort downgrade (detection classifier, migration
0030) shipped real correctness holes that full-effort tests and CI did not catch.

---

## Aggregate model — verified realized, not just declared

These are the load-bearing invariants from the proposal (v3 §1-5) and cm `019f8a57`. All hold
in code at this head:

- **Single membership authority.** `worktree_in_space(owner, space_id, worktree_id)` SQL
  function is the *only* membership computation, and every read plus every authorization path
  consumes it: inventory SQL (`store.py:41`, `:50`), `list_worktrees` (`:170`),
  `list_canvases` (`:298`), and service authz via `_require_worktree_in_space` →
  `store.worktree_in_space` (`service.py:436`, called at `:197/:253/:280/:311`). No read
  reimplements default-vs-named membership. This is the correct realization of proposal §1.
- **Detection never writes membership.** Zero production references to `space_worktree_link`
  (grep clean outside tests). `reconcile_detection` (`service.py:115`) upserts only path
  identities and roots; it never touches the junction. M4 stays dead.
- **Canvas appears in every Space referencing its anchor.** Canvas assembly keys on
  `worktree_in_space(..., c.anchor_worktree_id)` (`store.py:50`, `:298`), so a canvas surfaces
  in the default Space and every named Space whose link includes its anchor worktree. Matches
  proposal §3 canvas rule.
- **Reconcile atomicity.** `reconcile_detection` wraps `upsert_worktree` + `ensure_worktree_root`
  in one `self._conn.transaction()` under `pg_advisory_xact_lock` (`service.py:123-128`,
  `_lock_detection:460`); the reciprocal pair trigger is `DEFERRABLE INITIALLY DEFERRED`
  (`0030:251-264`), so worktree and root validate together at commit. Filesystem detection I/O
  is correctly kept *outside* the write lock (the post-commit `_snapshot` at `:129`).
- **Computed-default guard rails.** `validate_named_space_worktree_link` blocks linking a
  default Space, and `validate_default_space_membership` blocks a linked Space becoming default
  (`0030:141-199`). Partial-unique `UNIQUE (owner) WHERE is_default` (`0030:31`) plus
  `ensure_default_space` `ON CONFLICT (owner) WHERE is_default DO NOTHING` (`store.py:67`) give
  exactly one idempotent default.
- **Root FK / anchor topology.** `space_worktree_root_canvas_fk` binds
  `(owner, worktree_id, root_canvas_id) → canvas(owner, anchor_worktree_id, canvas_id)`
  (`0030:65-72`), forcing a root canvas to be anchored to its own worktree; `NO ACTION
  DEFERRABLE INITIALLY DEFERRED` blocks direct/lone root delete at commit. Canvas anchor FK is
  `ON DELETE CASCADE` (`0030:324-327`) for the privileged worktree-delete path.

---

## Major 1 (net-new): `reconcile_worktrees` refreshes only one repo of a multi-repo Space

Locations: `space/service.py:225` (`reconcile_worktrees`), `:233` (`_refresh_path`),
`:568` (`_refresh_path` impl), route `api/v1/space_routes.py:315`
(`POST /spaces/{space_id}/worktrees/reconcile`).

The route contract is "reconcile the worktrees of this Space." The implementation picks a
*single* representative path:

```python
refreshed = await self.resolve_cwd(_refresh_path(snapshot.worktrees), owner=..., create=True)
```

`_refresh_path` returns the first worktree whose `missing is False`, and `resolve_cwd(create=True)`
runs `reconcile_detection(detect_space(that_one_path))`, which materializes only the worktrees
sharing that path's git common directory (or that single plain dir).

The two-aggregate model exists precisely to let one Space span worktrees across multiple
repos/locations (VSCode-multiroot; the computed-all default Space is inherently multi-repo).
For such a Space this reconcile is incomplete:

- A newly created linked worktree in a *sibling* repo (repo B) is never materialized when the
  chosen path is in repo A. Proposal §8.10 requires "a newly enumerated linked Worktree remains
  absent until explicit reconcile, then gets one Worktree ID and one protected root" — the
  explicit reconcile here structurally cannot reach repo B (it has no repo-B cwd and only
  detects the one picked path).
- Secondary: if every worktree in the Space is momentarily `missing`, `_refresh_path` raises
  `worktree_not_found` ("Space has no confirmed active Worktree path"), so a whole-Space
  reconcile fails hard even though the durable Space is intact.

Reads mask the *projection* half (branch/HEAD/missing refresh, because `_snapshot`/`_detect_paths`
re-detect all stored paths), so the user-visible defect is narrowed to "new sibling-repo
worktree does not appear after reconcile" and "reconcile errors when all paths are transiently
missing." Fix: iterate detection over one live path per distinct repo group among the Space's
worktrees (dedupe by `repo_group_key`), and treat an all-missing Space as a no-op refresh rather
than an error.

## Minor 1 (net-new): duplicated single-missing-worktree `DetectedSpace` construction

Locations: `space/service.py:475-492` (inline in `_materialize_missing_worktree`) and
`:594-613` (`_missing_detection`).

Both build a `DetectedSpace` wrapping one `DetectedWorktree(missing=True, is_primary=None,
repo_group_key=None, ...)` with near-identical field lists. Extract one helper. Distinct from
gpt M6 (which is the `_canonical_path` triplication); this is a second DRY seam in the same file.

---

## Confirmations of gpt findings that touch the aggregate / contract

- **gpt M1 (classifier totality) — CONFIRMED first-hand; I would elevate toward blocker.**
  `_read_gitdir_marker` (`detection.py:165`) and `_resolve_common_dir` (`:152-160`) raise
  `UnicodeDecodeError` / `ValueError`; the boundaries at `:106` and `:136` catch only
  `(OSError, RuntimeError)`, so these escape the total `git/plain/inconclusive` contract.
  `service._detect_paths` catches only `SpaceDetectionError` (`:416`), so a raw error propagates
  and fails the *owner-wide* Space list, not just one checkout. Reproduced at this head:

  ```
  gitdir bad-encoding     RAISED UnicodeDecodeError
  empty commondir         RAISED ValueError  empty commondir marker: .../commondir
  commondir bad-encoding  RAISED UnicodeDecodeError
  ```

  This violates proposal §8.9 (classifier must cover malformed markers) with aggregate blast
  radius (one corrupt checkout poisons all Space reads). Fix: widen the classifier boundaries to
  return `INCONCLUSIVE` on any metadata read/validation failure; cover invalid encoding + empty
  commondir.

- **gpt M2 (frontend drops `showSwitcher`) — CONFIRMED (contract).** Backend emits
  `show_switcher = space_count > 1` (`space_routes.py:244`); `fetchSpaces()` returns only
  `items` (`spaceTransport.ts:59-65`) and the `SpaceSummary` TS interface has no `showSwitcher`
  field, so the "surface the default Space only when >1 Space" rule (proposal preamble) is lost
  at the transport boundary. MCP exposes no spaces-list switcher surface, so there is no REST/MCP
  parity break — this is REST-envelope-only.

- **gpt M6 (`_canonical_path` triplicated) — CONFIRMED.** Identical
  `Path(...).expanduser().resolve(strict=False)` in `store.py:505`, `service.py:575`, and
  `projection.py:88` (projection adds only None-handling). These sit on the identity-lookup,
  projection, and persisted-query seams; drift silently desyncs stored vs projected worktrees.
  Export one helper from the identity boundary.

- **gpt Minor 1 — CONFIRMED.** `SpaceSummary` and `SpaceSnapshot` (`projection.py:22-33`) are
  byte-identical dataclasses; `service.list_spaces` builds `SpaceSnapshot` then repacks field
  for field into `SpaceSummary` (`:157-173`) for no gain. `Worktree = ProjectedWorktree` alias
  (`models.py:199`) keeps the retired ambiguous name. `repo_group_key` stays plain `str`/`string`
  with no nominal `RepoGroupKey` boundary.

## Denials / reclassifications

- **gpt M4 (cross-anchor default blocks worktree delete) — DENY as an S1 code defect.** There is
  **no** worktree-delete seam anywhere in S1 (no `DELETE FROM space_worktree`, no store/service
  delete method — grep clean). The model *does* permit a user canvas anchored to B to name A as
  `default_worktree_id` (`canvas_default_worktree_fk` is anchor-agnostic, `0030:328-332`), so
  gpt's reproduction is valid, but the "privileged worktree deletion clears surviving defaults"
  behavior is proof §8.6, which cm `019f8a57` explicitly **defers** to the later Space-CRUD
  slice. Action: move acceptance proof §8.6 to that slice's spec; nothing to fix at this head.

## Concurrence (outside aggregate lens, verified counts only)

- **gpt M3 (downgrade `USING NULL::uuid` nulls durable stamps, `0030:81/:86`)** — concur; the
  durable Space/Worktree stamps are aggregate state and the downgrade should checked-cast, not
  null them.
- **gpt M5 (700-line limit)** — concur; verified `api/v1/test_capture_rpc_routes.py` = 735,
  `session/test_migrate.py` = 701. No changed *production* file crosses 700.

---

## Verification

- Local HEAD == PR HEAD == `855bd0a9`.
- Interpreter check: `requires-python >=3.14`, repo venv 3.14.5; `detection.py` `py_compile`
  clean. The unparenthesized `except OSError, subprocess.TimeoutExpired:` at `detection.py:286`
  is valid PEP 758 syntax and matches a repo-wide convention (10+ sites) — **not** a defect.
- gpt M1 reproduced directly against this head (three malformed-metadata cases above).
- `worktree_in_space` consumer trace: 6 production call sites, all reads + authz; no reimplementation.
- `space_worktree_link` production write trace: none (detection cannot mutate membership).
- Source tree unmodified during review.
