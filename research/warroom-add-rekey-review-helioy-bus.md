---
title: Durable warroom_add rekey review for helioy-bus
type: research
tags: [helioy-bus, warroom, tmux, rekey, code-review]
summary: Final review cleared the durable warroom_add rekey path after registry, PID, and inbox migration fixes.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Executive Summary

`helioy-bus` is a Python MCP based inter agent bus with a tmux backed warroom service. This review focused on the durable `warroom_add` flow that splits a pane without launching, refreshes existing members by stable `pane_id`, rekeys identity state, migrates inboxes, then launches the new pane.

The final pass found no blocker. The duplicate role registry collision, stale active state, and invisible inbox risks are now covered by implementation and regression tests.

## Project Metadata

- Language: Python 3.12 or newer, from `pyproject.toml`.
- Runtime surface: MCP servers `helioy-bus` and `helioy-warroom`.
- Build system: Hatchling, managed with `uv`.
- Core dependencies: `mcp-hmr`, `mcp[cli]>=1.0.0`.
- Verification stack: Ruff, mypy, shellcheck, pytest via `just check`.
- Persistence: SQLite registry at `~/.helioy/bus/registry.db`.
- Orchestration: tmux panes and windows via `server/_tmux.py`.

## Architecture

The relevant flow crosses three layers:

1. `server/warroom_server.py` exposes MCP tools and delegates to service functions.
2. `server/services/warroom.py` owns warroom lifecycle, member rows, registry reconciliation, PID mapping rewrites, and inbox migration.
3. `server/_tmux.py` is the tmux boundary for pane creation, target lookup, pane titles, layout, and runtime launch.

The current `warroom_add` flow in `server/services/warroom.py:750-771` calls `gateway.spawn_pane(..., launch=False)`, refreshes existing member targets, resolves the new pane target, then calls `gateway.launch_pane(...)`.

## Key Patterns

- Stable tmux `pane_id` is the durable identity anchor. Mutable `session:window.pane` targets are refreshed from it.
- Runtime registration uses canonical agent ids shaped as `{repo}:{desired_role}:{tmux_target}`.
- PID mapping files under `~/.helioy/bus/pids` are part of runtime self identification and must follow id rekeys.
- Inboxes under `~/.helioy/bus/inbox/{agent_id}` must also follow id rekeys so pending mail remains visible.
- Duplicate roles are valid warroom state, so rekey logic cannot assume `desired_role` uniqueness.

## Detailed Findings

### Fixed: duplicate same role members corrupted registry rekey

The first review found that per row rekeying could collapse duplicate same role members into one `agents` row when pane targets shifted together. The updated implementation stages matched registry rows through temporary primary keys, then applies final ids by stable SQLite `rowid`. See `server/services/warroom.py:290-322`.

Regression coverage includes `tests/test_warroom_members.py:485-603`, which verifies two same role members shift together while preserving two registry rows with correct PID and session ownership.

### Fixed: active state without a registry row

The first review found that a persisted `agent_instance_id` could keep a member active even when no live `agents` row existed. The updated implementation sets `next_agent_id` only when a registry row was actually found and rekeyed. See `server/services/warroom.py:327-328`.

Regression coverage includes `tests/test_warroom_members.py:685-734`, which verifies a stale member becomes pending with `agent_instance_id` cleared when no registry row exists.

### Fixed: inbox directories did not migrate on agent id rekey

The second review found that pending inbox files could remain under the old agent id after PID mapping changed to the new agent id. The updated implementation adds `_migrate_inbox_mapping_batch()` and `_merge_directory()` to stage old inboxes, then merge unread and archived mail into final new id inboxes without overwriting destination files. See `server/services/warroom.py:180-231` and the call at `server/services/warroom.py:348`.

Regression coverage includes `tests/test_warroom_members.py:606-682`, which verifies unread files, archived files, and pre existing destination inbox files survive migration.

Manual validation also covered a duplicate role chain where member A's new inbox id equals member B's old inbox id. With both old inboxes containing unread and archived files, staging preserved mail correctly for both final ids.

## Verification

Ran targeted regressions locally:

```bash
uv run pytest tests/test_warroom_members.py::test_warroom_add_migrates_inboxes_when_member_ids_change tests/test_warroom_members.py::test_warroom_add_rekeys_duplicate_role_members_without_losing_registry_rows tests/test_warroom_members.py::test_warroom_add_marks_rekeyed_member_pending_without_registry_row -q
```

Result: `3 passed in 0.29s`.

## Residual Risk

Filesystem effects for PID and inbox migration now happen after refresh SQL updates, but still before the outer `warroom_add` transaction commits and before new member insertion finishes. A later unexpected SQLite failure could leave filesystem identity state ahead of rolled back database state. Probability appears low.

An optional extra test could cover the duplicate role inbox chain that was manually validated.

## Dependencies

- tmux provides stable `pane_id` and mutable target lookup.
- SQLite stores warrooms, members, and registered agents.
- Runtime adapters build launch commands for Claude and Codex.
- Shell hooks maintain PID to agent id mappings for runtime self identification.
- Filesystem inbox directories store unread and archived bus messages by `agent_id`.

## Relevance to Helioy

Warroom messaging depends on stable, correct `agent_id` values. The current durable rekey path now preserves registry rows, PID mappings, and pending mail across tmux pane reflows caused by `warroom_add`.

## Open Questions

- Should target refresh move into a shared reconciliation service so `warroom_status` can repair external tmux pane index changes too?
- Should `warroom_add` persist `desired_repo` when called with a `cwd` override, so future canonical ids match the runtime launch cwd?
- Should failed launch after split clean up the empty pane, or is preserving it intentional for debugging?
- Should rekey also migrate `nudge_log` rows keyed by old agent id, or is throttle reset acceptable?
