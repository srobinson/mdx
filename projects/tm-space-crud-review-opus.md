# Space-CRUD review — opus (aggregate / domain / contract lens)

Reviewer: opus architect, multilaunch warroom.
Target: `git diff 6453364a..e116ffb6` (`feat(space): add named Space CRUD`), 12 files +1430/-77.
Spec: `~/.mdx/projects/tm-space-crud-spec-v1.md` §3-§9. Model: cm `019f8a57`.
Gate reported by orchestrator: `just check` + `just test-affected` PASS (766 JS / 62 API).
Method: read every production + test hunk against the locked contract. Read-only, tree idle.

## Verdict

**Blockers: 0 · Majors: 0 · Minors: 1 · Builder-trust: TRUST.**

This is a faithful, well-crafted implementation of the locked spec. Every hard invariant holds. The
one minor is a layering smell that will compound at S3, worth fixing before then.

## Hard invariants — all PASS

1. **Single membership authority.** No second membership path is introduced. `link_worktree` /
   `unlink_worktree` write only `space_worktree_link` via `store.add_worktree_link` /
   `remove_worktree_link`; every read/authz still routes through the shipped `worktree_in_space()`
   (store reads unchanged). Verified in `store.py` and `service.py`. ✓
2. **M:N + owner-scoped Director authz.** All five service mutations gate on `_require_director` and
   resolve the target through `_require_space_record` (owner-scoped `get_space`), **never** the
   space-bound `_require_allowed_space`. A Director bound to Space A can create/delete/link Space B.
   REST uses the new `rest_director_caller()` (`allowed_space_id=None`); MCP builds the same
   owner-scoped caller via the `director=True` branch in `SpaceMcpAdapter._invoke`. Proven by
   `test_space_mcp_mutations_use_an_owner_scoped_director_caller` (asserts `allowed_space_id is None`)
   and `test_rest_director_caller_is_owner_scoped`. ✓
3. **Default immutability is SQL-only.** No Python `is_default` re-check anywhere.
   `rename_space`/`delete_space` carry `AND NOT is_default` in the SQL predicate; `add_worktree_link`
   lets the shipped `space_worktree_link_named_space_check` trigger fire and the service catches the
   `CheckViolation` (constraint match) → `space_default_locked` (409). One new error code only.
   `_raise_crud_error.status_by_code` gained `"space_default_locked": 409`. ✓
4. **DRY.** `_require_director` extracted and the duplicated inline checks in `reconcile_worktrees`
   and `director_tree` were replaced (no sixth copy). `validate_canvas_name` generalized to
   `validate_display_name(value, *, max_len=120)`, consumed by both Canvas and Space. `_canvas_id`/
   `_worktree_id` collapsed into one generic `_crud_id`. **No new migration** (Alembic head stays
   `0030`). **No new HTTP helper** (transport reuses `requestApiJson`/`requestApiVoid` with
   `RequestInit`). ✓
5. **Contract fidelity.** REST §6 (POST 201, PATCH 200, DELETE 204, POST /links 204, DELETE
   /links/{wt} 204, all origin-guarded), MCP §7 (`space_create`/`rename`/`delete`/`link_worktree`/
   `unlink_worktree`, `SpaceResult`/`SpaceAck`), and `@tm/core` §8 (five fetchers, camelCase bodies,
   `encodeURIComponent`) all match the spec exactly. ✓

## Minor 1 — cross-adapter import of a private symbol (layering / DRY)

`api/v1/space_mcp.py` now does `from transport_matters.api.v1.space_routes import SpaceSummary,
_space_summary`. This couples the two sibling adapters (MCP → REST) and reaches past an
encapsulation boundary by importing a `_`-prefixed private helper. `SpaceSummary` and `_space_summary`
are shared presentation concerns, not REST-owned. They belong in a neutral leaf (e.g. a
`space/presentation.py` or on `space/models.py`) so both adapters import from a common location.

- Severity: minor. It works and is tested; the smell is structural.
- Why fix before S3: S3 extends **both** REST and MCP on the same DTOs, so the coupling and the
  private-symbol reach will deepen. Relocating the shared summary now is a two-line move that keeps
  the adapters siblings rather than a dependency chain. (Same principle as a shared cross-layer leaf
  belonging at a neutral home, not inside its heaviest consumer.)

## Forward-looking gate (not a defect in this diff)

`space/service.py` is now **698 LOC — 2 under the hard 700 limit.** This diff is clean. But S3
(canvas create/update) lands on this same file and will cross the limit. Per the refactor-first rule,
S3 must **begin** by extracting the five Space-mutation service methods (~70 LOC) into a focused
module **before** adding canvas mutations. Recommend the orchestrator make that split an explicit
S3 pre-step. No action required on this slice.

## Builder-trust assessment: TRUST

Stuart is gauging whether to delegate larger scope to this codex engineer. On this slice:

- **Craftsmanship (high).** Wrapped `add_worktree_link` in `self._conn.transaction()` so a
  `CheckViolation` aborts a savepoint rather than poisoning the outer transaction — the engineer
  understood the psycopg poison-transaction failure mode without being told. Generic `_crud_id`
  parser and the clean `require_bound_space` extraction (justified public method: MCP adapters call
  it) show they propagated the `allowed_space_id → optional` blast radius correctly to every prior
  consumer (`get_canvas`, `get_worktree`, `resolve_launch_worktree`, `resolve_workspace_caller`), not
  just the new code.
- **Test rigor (high, genuinely red-first + observable end-state).** The §10 cases assert what the
  user observes, not intermediate mappings:
  - The raw-SQL `test_default_membership_...` was rewritten to app-path writes and asserts computed-all
    survival after unlink (named empty, default still contains, `worktree_in_space(default)` true).
  - `test_delete_named_space_cascades_only_membership_links` asserts the exact post-state
    (`links=0, worktrees=1, canvases=1, default_spaces=1`) — the core cascade invariant.
  - `test_space_crud_routes_close_the_write_to_read_feedback_loop` drives the full lifecycle through
    the real HTTP client and reads back through the list/worktrees endpoints (write→read loop, not an
    internal assertion).
  - `test_link_worktree_maps_a_concurrent_space_delete` is a real concurrency test: it pauses the
    insert mid-flight, deletes the Space on another connection, and proves the FK-violation catch
    path actually maps to `space_not_found` under a race. This goes beyond the spec and closes the
    exact class of "CI-green-but-wrong" hole the reshape suffered.
  - Origin-guard, error-status parity, and MCP↔REST error-contract parity are all covered.
- **Spec + reuse fidelity (high).** Built on shipped seams only; no invented authz path, no duplicated
  default check, no new migration or HTTP helper. Naming matches existing conventions.
- **Shortcuts: none found.** The FK-violation handling is belt-and-suspenders over the existence
  pre-checks, and the concurrency test proves it is reachable rather than dead defensive code.

Net: this engineer can be trusted with a larger, well-specified slice. Keep the spec tight (this one
was) and the trust holds.

## Gate note

The build passed `just check` + `just test-affected`. Recommend grok's authoritative local-CI
(`just check` + `just test` + `just migration-smoke`) confirm no schema delta before merge, since the
slice claims zero migration — `migration-smoke` is the direct proof of that claim.
