---
title: Runtime policy implementation guide for agent-runtimes issue 2
type: research
tags: [agent-runtimes, transport-matters, control-plane, mcp, schema]
summary: Grounded implementation guidance for publishing per-runtime requested grants and Transport Matters MCP capabilities through capabilities.json schema 4.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-02
updated: 2026-09-02
---

## Executive summary

Issue 2 now has an implementation guide grounded in the live generator. The guide traces the current manifest to `RuntimePlan` to `capabilities.json` path, separates Transport Matters policy from existing vendor capability and MCP server configuration, and identifies the exact source, test, manifest, generated, and documentation files involved.

The GitHub body was updated without changing its title, label, parent, blocking relationship, scope, constraints, or acceptance criteria. A live `gh issue view` comparison confirmed that metadata stayed unchanged and that the final guide contains no source line anchors.

## Project metadata

- Language: Python 3.11 or newer because the generator imports `tomllib`.
- Build and verification: direct Python entry point and pytest.
- Generator entry point: `bin/generate.py`.
- Compiler package: `bin/agent_runtime_compiler/`.
- Owned runtime manifests: 10.
- Published contract: `runtimes/*/capabilities.json`, currently schema 3.
- FMM status: no `.fmm.db` exists in the repository. Analysis used read only file listing, Python AST outlines, and targeted source reads after the required FMM probe failed.

## Architecture

`bin/generate.py:168-190` defines `apply`, which reads the manifest, loads baselines and machine MCP catalogs, calls `compiler.plan`, then calls `writers.materialize`.

`bin/agent_runtime_compiler/compiler.py:71-197` defines `plan`. It validates manifest sections, resolves skills and harnesses, compiles redactions, resolves MCP servers, derives the generated contract, and returns a frozen `RuntimePlan`.

`bin/agent_runtime_compiler/manifest.py:85-136` defines `agent_identity`. It validates manifest schema 3 and owns the existing `[launch]` table through `fixed_name`. The runtime policy should extend this single launch validation path.

`bin/agent_runtime_compiler/capabilities.py:216-242` defines `derive_capabilities`. It assembles the complete `capabilities.json` payload and currently hardcodes schema 3.

`bin/agent_runtime_compiler/writers.py:42-61` defines `materialize`, and `bin/agent_runtime_compiler/writers.py:115-128` defines `_materialize_capabilities`. The writer already replaces the generated JSON from the plan, so the new policy does not require a second output path.

## Key patterns

- The generator separates pure desired state in `RuntimePlan` from filesystem writes in `writers.materialize`.
- `vendor_constraint` digests the manifest bytes, so policy edits change `generated_from` without extra digest code.
- `capabilities.toml` and `required_capabilities` describe vendor requirements from required skills. They must remain separate from the new Transport Matters tool policy.
- `[mcp]` selects machine discovered MCP server definitions. Transport Matters seeds its control plane at launch, so the new policy belongs to launch intent instead.
- All generated lists need canonical order independent of TOML author order.

## Detailed findings

The guide recommends schema 4 for both `runtime.toml` and `capabilities.json`. The manifest parser derives `none` and an empty capability list when the policy is absent. The nine ordinary runtimes use that minimum policy. `tm/orchestrator` requests `director` with the complete orchestration capability set.

The current producer and consumer issues do not name the generated JSON fields or capability identifier strings. The guide makes that contract choice the first implementation step and grounds the vocabulary in three domains already documented by Transport Matters issue 596 and `skills/tm-orchestrate/SKILL.md`: core run control, Space, Canvas, and Worktree management, and browser control.

The guide names 34 files and 14 existing symbols. A new focused `tests/test_runtime_policy.py` keeps policy tests out of `tests/test_generate.py`, which is already 627 lines.

## Verification

The live issue was fetched after editing and compared with the submitted body.

- Body: exact match.
- Title: unchanged.
- Label: `enhancement`, unchanged.
- Parent: Transport Matters issue 593, unchanged.
- Blocking relationship: Transport Matters issue 594, unchanged.
- Source line anchors: none.
- Completion reply: delivered on topic `mcp-issues-guide-wave1`.

Implementation verification remains:

```bash
python3 bin/generate.py --all
python3 bin/generate.py --audit
python3 -m pytest tests -q
```

## Relevance to Helioy

The contract lets Transport Matters calculate effective authority from three independent inputs: the runtime request, the Canvas consent ceiling, and the launching principal. Keeping the runtime artifact limited to requested policy preserves that ownership boundary and allows later tool discovery filtering without moving authorization into the generator.

## Open questions

- Lock the exact generated JSON field names before implementation.
- Lock the exact strings and order for the three capability domains.
- Confirm whether schema 4 rejects every elevated grant with an empty capability list, as the guide recommends.

## Artifact

- GitHub issue: https://github.com/littleorgans/.agent-runtimes/issues/2
