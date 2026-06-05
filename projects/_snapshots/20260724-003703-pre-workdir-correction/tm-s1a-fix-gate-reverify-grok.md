# S1a fix re-verify + authoritative gate (Grok)

Date: 2026-07-23  
SHA: `40c82e456c5d74dcb26e13f910c38c18acbe02d3`  
Base: `bcb36c9c` → fix `40c82e45` (9 files, +187 / −47)  
Reviewer: `multi-launch:general:1:2.4` (sole gate runner)  
Tree: pristine at start  

## Gate

| Gate | Result | Evidence |
|------|--------|----------|
| `just check` | **PASS** | desktop 102; shell format/lint/typecheck; api ruff + mypy 685 Success |
| `just test` | **PASS** | JS 1906 passed / 36 skipped; API **3447** passed / 0 failed; combined **5353** passed / **36** skipped |
| `api` `just migration-smoke` | **PASS** | 9/9 (`session/test_migrate.py`) |

## Findings addressed

| ID | Finding | Addressed | Evidence |
|----|---------|:---------:|----------|
| M1 | launchFields strip flat+nested affinity before model_copy; ingest declared fields only; forgery regression | **Y** | `affinity_launch_fields` strips `AFFINITY_FIELD_NAMES` + nested `SESSION_AFFINITY_LAUNCH_FIELD`; `register_owned_cursor` uses it; `_binding_affinity` uses `model_dump`; `test_raw_launch_affinity_forgeries_do_not_reach_session_params` |
| gpt-m1 | backfill update returns rows-affected; counters only on real change | **Y** | `update_session_affinity` → `bool` via `cursor.rowcount > 0`; backfill `if not applied: seen_unresolved; continue`; `test_backfill_counts_only_guarded_updates_that_changed_a_row` |
| grok-m2 | reject empty/blank required strings | **Y** | `validate_affinity_group` treats blank `str.strip()` as missing; parametrized `test_affinity_rejects_blank_required_strings` |
| grok-m1 | rename `*_space_identity*` → affinity-accurate | **Y** | SQL/DAO/protocol/tests all use `*_AFFINITY*` / `*_affinity*`; zero residual old session symbols |

## Residual / new issues

**None material.**

- Strip preserves legitimate non-affinity launch fields (`title`, `purpose`, `custom_meta` verified).
- Rename complete: no leftover `LIST_SESSIONS_MISSING_SPACE_IDENTITY` / `update_session_space_identity` in `api/src`.
- Intentional behavior: untrusted flat `space_id`/`worktree_id` in launch_fields no longer reach `SessionBinding` via `**launch_fields`; trusted values still come from `ProxyRunBinding.space_id`/`worktree_id` overlay.
- Launch-path stamping (S1b) still deferred; forgery test asserts null affinity group until trusted stamp lands.

## One-line (bus)

`FULL GATE PASS (check + 5353/36skip + migration-smoke 9/9) · M1 Y · gpt-m1 Y · grok-m2 Y · grok-m1 Y · residual none · path ~/.mdx/projects/tm-s1a-fix-gate-reverify-grok.md`
