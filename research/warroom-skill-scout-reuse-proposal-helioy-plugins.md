---
title: Warroom skill scout and reuse proposal for helioy-plugins
type: research
tags: [helioy, helioy-plugins, helioy-bus, warroom, skill-design, scout, reuse-map]
summary: Proposal authored to make Scout a required reuse and quality phase in the helioy-bus warroom skill while trimming redundant prose.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

## Executive Summary

The `helioy-bus` warroom skill already encodes strong orchestration rules, but it repeats compaction and runtime prefix guidance across several sections. The proposed draft keeps phase discipline and peer review rigor while adding a first-class Scout phase that requires a reuse map, quality map, and explicit decision points before planning or implementation.

Primary artifact: `/Users/alphab/.mdx/projects/warroom-skill-groom-codex--proposal.md`.

## Project Metadata

- Project: `helioy-plugins`
- Purpose: Claude Code plugin package for Helioy tools and bus workflows.
- Indexed: `.fmm.db` exists; `fmm_list_files(group_by="subdir")` reported 8 indexed source files under `plugins/` and 890 LOC. Markdown skill docs are outside fmm symbol coverage, so the target skill was read directly.
- Main docs read: `README.md`, `plugins/helioy-bus/skills/warroom/SKILL.md`, `/Users/alphab/.agents/skills/code-review/SKILL.md`, `plugins/helioy-tools/skills/code-hygiene/SKILL.md`.
- Dependencies and surfaces from `README.md`: `helioy-tools` and `helioy-bus` plugins; MCP servers for `cm`, `fmm`, `helioy-bus`, and `helioy-warroom`; local Rust binaries and npm packages are prerequisites.

## Architecture

`helioy-plugins` packages skills, MCP servers, agents, and hooks. The relevant area is `plugins/helioy-bus/skills/`, where `mail` handles bus messaging and `warroom` orchestrates tmux agents through `helioy-bus` and `helioy-warroom` tools.

The warroom skill is an orchestration protocol rather than application code. Its architecture is mode based:

1. Peer Consensus
2. Spec Writing
3. Code Review
4. Brainstorm
5. Slice Build Loop

The proposal keeps that taxonomy but renames Mode 2 to `Scout / Plan / Spec Writing` and adds a shared `Scout Before Plan` section used by planning and implementation modes.

## Key Patterns

- Orchestrator-only replies reduce bus noise and token churn.
- Phase boundaries require recycle or verified `/compact`, because stale pane context is treated as a correctness risk.
- Bus messages are one-sentence signals; durable artifacts go to files.
- Peer review is retained for quality, especially where independent model or role diversity catches missed reuse, bad boundaries, false assumptions, and stale-state errors.
- Scout output becomes a gate, not optional prose: Reuse Map, Quality Map, and Plan.

## Detailed Findings

### Redundancy to trim

- Compaction appears in Non Negotiables, Phase And Churn Control, Slice Build Loop, Shared Practices, and Anti Patterns: `plugins/helioy-bus/skills/warroom/SKILL.md:57`, `:107-128`, `:286`, `:297-310`.
- Runtime prefix guidance is correct but too dense in one paragraph: `plugins/helioy-bus/skills/warroom/SKILL.md:58`.
- Reviewer priming is described in depth in Code Review and then referenced again in Slice Build Loop: `plugins/helioy-bus/skills/warroom/SKILL.md:232-248`, `:280`.

### Missing Scout gate

- Mode 2 starts from spec grouping and engineer dispatch without first requiring a code audit or reuse map: `plugins/helioy-bus/skills/warroom/SKILL.md:203-220`.
- The proposal adds required Scout questions: existing code and infra to reuse, similar implementations checked and rejected, duplication, bad design, dead code, deviation decisions, and verification gates.
- Scout findings must surface before implementation so the orchestrator or human can choose reuse, refactor, deletion, deliberate deviation, or scoped deferral.

### Early code-review and code-hygiene lenses

- `/code-review` provides bug, convention, history, false-positive, and evidence discipline: `/Users/alphab/.agents/skills/code-review/SKILL.md:12-32`.
- `/code-hygiene` provides measurement, fmm use, duplication, boundary, seam, and verification discipline: `plugins/helioy-tools/skills/code-hygiene/SKILL.md:31-68`, `:70-85`, `:139-161`.
- The proposal references these as lenses during Scout and review rather than duplicating their contents.

## Dependencies

Critical operational dependencies:

- `mcp__helioy_bus`: `whoami`, `send_message`, `get_messages`, `list_agents`.
- `mcp__helioy_warroom`: `warroom_discover`, `warroom_spawn`, `warroom_add`, `warroom_status`, `warroom_kill`, `warroom_remove`.
- `mcp__cm`: `cx_recall`, `cx_store`, and `cx_deposit` for durable memory.
- `mcp__fmm`: structural code navigation when a touched repo is indexed.
- `tmux`: pane capture, compaction, and send-keys priming.

## Relevance to Helioy

This change directly supports Helioy's zero-duplication and staff-engineering bar. Making Scout mandatory before planning reduces reinvention, forces existing infra discovery, and turns code hygiene into an early design input rather than a late review complaint.

## Open Questions

- Should the live `warroom/SKILL.md` be replaced with the full draft, or should the first patch land as smaller changed sections only?
- Should Scout output be required as a separate file for all non-trivial work, or can simple cases use a bus line plus evidence?
- Should warroom tooling provide a template helper for Reuse Map and Quality Map files?

## Verification

- Proposal artifact validation passed: required sections present, no non-ASCII characters, and balanced Markdown code fences.
- Bus reply delivered to `transport-matters:general:orchestrator` with message id `176c09fa-1e51-4180-bded-67c4c3e9c5f5`.
- Current `helioy-plugins` worktree is dirty with unrelated tracked and untracked files, so no pristine-tree claim was made.
