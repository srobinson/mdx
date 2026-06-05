# Space-CRUD large-context review + full gate (Grok)

Date: 2026-07-23  
Slice: Space-CRUD v1 (`~/.mdx/projects/tm-space-crud-spec-v1.md`)  
Model of record: cm `019f8a57-c947-7411-8944-be6d9ebfce0f`  
Range: `6453364a..e116ffb6` (`feat(space): add named Space CRUD`)  
Diff: 12 files, +1430 / −77  
Reviewer: `multi-launch:general:1:2.4` (read-only; large-context + authoritative local CI)  
Tree at review: idle at `e116ffb6`

## Verdict

**BLOCK merge.** Slice implementation matches §3–§9 on the happy path and domain seams, but the full suite fails two cross-cutting contract tests that `just test-affected` does not exercise. Fix those, re-run the full gate, then re-nudge.

| Severity | Count | Summary |
|----------|------:|---------|
| blocker | 2 | private import of `_space_summary`; MCP agent-contract tool set stale |
| major | 0 | — |
| minor | 1 | `service.py` at 698 LOC (2 under hard 700); split before S3 |

## Gate (authoritative, independent)

| Gate | Result | Evidence |
|------|--------|----------|
| `just check` | **PASS** | desktop 102; shell format/lint/typecheck; core+inspector+canvas typecheck; api ruff + mypy 675 files, "All checks passed!" / "Success: no issues found" |
| `just test` | **FAIL** | JS packages green (desktop 102; shell vitest **1268**; common 24; contract 8; activity 288; runtime 190; gateway 21). API: **2 failed, 3408 passed** in 196.86s |
| `just migration-smoke` | **PASS** | **9/9** passed; Alembic head remains `0030_space_crud_reset` (no new revision in diff; `alembic heads` confirms) |

Engineer claim (`just check` + `just test-affected` PASS) is consistent with local change-scoped green. Full suite is the authority and is red.

### Full-suite failures (blockers)

1. **`test_private_import_boundary`**
   - `space_mcp.py` imports `_space_summary` from `transport_matters.api.v1.space_routes`.
   - Boundary lint forbids underscored symbols across modules.
   - Root cause: §9 "reuse `_space_summary`" was implemented as a private cross-module import instead of promoting a public shared helper (or colocating the mapper).

2. **`test_mcp_tool_schemas_are_the_agent_contract`**
   - Expected tool set still lists only S1 space reads (`canvas_*`, `worktree_*`).
   - Live registry now also exposes `space_create`, `space_rename`, `space_delete`, `space_link_worktree`, `space_unlink_worktree`.
   - Fix: extend the allowlist and assert plain-object output schemas for the five new tools (same combinator-free rules as existing tools).

Both failures sit outside the Space-CRUD co-located tests. They are exactly the class of leak `test-affected` misses and this gate is meant to catch.

## Large-context review vs §3–§9 + model 019f8a57

### §3 Store — match

| Method | Present | Notes |
|--------|---------|-------|
| `create_named_space` | yes | INSERT + RETURNING, server UUID, no Python `is_default` branch |
| `rename_space` | yes | `AND NOT is_default`, returns `Space \| None` |
| `delete_space` | yes | `AND NOT is_default`, returns bool; links cascade via FK |
| `add_worktree_link` | yes | `ON CONFLICT DO NOTHING`; CheckViolation propagates |
| `remove_worktree_link` | yes | idempotent DELETE |
| `_space_from_row` | reused | |
| Repo contract guard | extended | five names in `public_operations` |

Default immutability stays in SQL predicates/triggers. No second membership write path.

### §4 Service — match (+ good race hardening)

- Five Director methods with `_require_director` extracted (also wired into `director_tree` / `reconcile_worktrees`).
- Name validation via generalized `validate_display_name` → `_display_name` → `invalid_request`.
- Default-locked disambiguation after store miss (`get_space` / `_require_space_record`) → `space_default_locked`.
- `link_worktree` maps `space_worktree_link_named_space_ck` CheckViolation; does not re-check `is_default` in Python.
- Extra (sound): transaction + `ForeignKeyViolation` → `space_not_found` / `worktree_not_found` for concurrent delete races; covered by `test_link_worktree_maps_a_concurrent_space_delete`.
- `rest_director_caller` + optional `CrudCaller.allowed_space_id`; `require_bound_space` protects space-bound reads.

### §5 Errors — match

`space_default_locked` → 409 added next to `canvas_root_locked`. REST/MCP share codes and messages (parity test present).

### §6 REST — match

| Verb | Path | Status |
|------|------|--------|
| POST | `/v1/spaces` | 201 + SpaceSummary |
| PATCH | `/v1/spaces/{id}` | 200 + SpaceSummary |
| DELETE | `/v1/spaces/{id}` | 204 |
| POST | `/v1/spaces/{id}/links` | 204 body `{ worktreeId }` |
| DELETE | `/v1/spaces/{id}/links/{wt}` | 204 |

Origin guard on all mutations. Feedback-loop test asserts `showSwitcher` after create. No new HTTP helper.

### §7 MCP — match on behavior; fail on global contract

- Five tools registered with `McpToolOutput` / `_invoke` / `space_crud_failure`.
- `director=True` builds owner-scoped unbound caller (`allowed_space_id=None`); role still from principal; service enforces Director (observer forbidden tested). Correct authz (forcing DIRECTOR on the caller would have been a hole).
- Result shapes: `SpaceResult { space }` / `SpaceAck { space_id }` per spec.
- **Blocker:** private import of `_space_summary` + agent-contract allowlist not updated.

### §8 `@tm/core` — match

Five fetchers reuse `requestApiJson` / `requestApiVoid` with camelCase bodies, `encodeURIComponent`, `detailAware: true`. Tests lock method/path/body and 409 surface.

### §9 Reuse map — match with one hygiene miss

All listed seams consumed. Disposition "never bypass membership" holds: named membership only via junction; reads still `worktree_in_space`. Detection/reconcile still does not write the junction.

Hygiene miss: reuse of `_space_summary` without promoting it public violates `test_private_import_boundary` (blocker #1).

### Model 019f8a57 coherence

- Space and Worktree remain peer aggregates; no `worktree.space_id`.
- Default stays computed-all; named Spaces are view filters via links.
- Single membership authority retained.
- No migration; durable schema objects from 0030 only.
- Placement/authz for Director mutations is owner-scoped, not space-bound (matches "placement is OWNER-scoped").

### Drift / dup / leak scan (whole path)

| Check | Result |
|-------|--------|
| Second membership predicate | none |
| Python re-check of `is_default` before store | none (SQL / trigger only) |
| New migration / schema delta | none |
| New HTTP transport helper | none |
| Parallel Space mutation service | none |
| Detection writing junction | none |
| MCP vs REST error parity | tested equal |
| Cross-module private symbol | **yes — blocker** |
| MCP tool registry vs agent-contract freeze | **stale allowlist — blocker** |

### LOC / refactor flag

| File | LOC | Note |
|------|----:|------|
| `space/service.py` | **698** | 2 under hard 700; five mutation methods + helpers landed |
| `space/store.py` | 592 | comfortable |
| `api/v1/space_routes.py` | 506 | fine |
| `api/v1/space_mcp.py` | 391 | fine |

**Minor:** preemptive split of Space-mutation service methods before S3 lands. Do not add S3 onto 698.

## Required fix list (engineer)

1. Promote `_space_summary` to a public shared mapper (or move `SpaceSummary` mapping next to the DTO) so MCP does not import a private REST symbol; satisfy `test_private_import_boundary`.
2. Update `test_mcp_tool_schemas_are_the_agent_contract` allowlist with the five new tools; keep plain-object outputSchema assertions green.
3. Re-run `just check` + `just test` + `just migration-smoke` (full, not only affected).
4. (Non-blocking) Plan `service.py` split before the next slice.

## Sign-off

Large-context: domain path coheres with the locked slice and model of record.  
Full gate: **FAIL** on two contract tests (3408 pass / 2 fail).  
Migration: head stays `0030`; smoke **9/9**.  
Do not merge until blockers are green on a re-run of the authoritative full gate.
