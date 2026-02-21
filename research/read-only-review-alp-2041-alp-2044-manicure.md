---
title: Read-only review of ALP-2041 and ALP-2044 Codex test decomposition
type: research
tags: [manicure, codex, tests, review, alp-2041, alp-2044]
summary: ALP-2041 and ALP-2044 are complete, with preserved test bodies and passing Codex pytest suite.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed commits `6e40620` and `c392ffc` in `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`. Both requested decompositions are complete: original monolith test functions were moved into focused files, helper ownership is clean, AST bodies match the pre split sources, and the Codex pytest suite passes.

## Project Metadata

- Project: manicure
- Area: `api/src/manicure/codex`
- Language: Python 3.13.0 in `api/.venv`
- Test runner: pytest 9.0.3 through `uv run --project api pytest`
- Relevant Linear issues: ALP-2041, ALP-2044
- Reviewed commits: `6e40620`, `c392ffc`

## Architecture

ALP-2041 removes `api/src/manicure/codex/test_transport_turns.py` and distributes its ten websocket turn lifecycle tests into four files:

- Completion: `test_transport_turn_completion.py:16`, `test_transport_turn_completion.py:131`, `test_transport_turn_completion.py:188`
- Close and interrupted turns: `test_transport_turn_close.py:17`, `test_transport_turn_close.py:117`
- Derivation, tool result, tool search: `test_transport_turn_derivation.py:24`, `test_transport_turn_derivation.py:111`, `test_transport_turn_derivation.py:160`
- Pause and stale request state: `test_transport_turn_pause.py:21`, `test_transport_turn_pause.py:84`

ALP-2044 removes `api/src/manicure/codex/test_repair.py`, moves shared repair builders into `test_repair_support.py:30` through `test_repair_support.py:150`, and distributes eight repair tests into four behavior files:

- Rebuild: `test_repair_rebuild.py:24`, `test_repair_rebuild.py:90`, `test_repair_rebuild.py:155`
- Migration: `test_repair_migration.py:23`
- Diagnostics: `test_repair_diagnostics.py:26`, `test_repair_diagnostics.py:75`
- Safety: `test_repair_safety.py:24`, `test_repair_safety.py:86`

## Key Patterns

- Support fixtures remain centralized. Transport turn tests keep using `manicure.codex.test_transport_support` via `pytest_plugins` and `_codex_flow`; repair tests use a single `test_repair_support.py` owner for builders and the `storage` fixture.
- Scenario names remain searchable because function names were preserved exactly.
- The split follows behavior seams rather than arbitrary file size cuts.

## Detailed Findings

### ALP-2041

Verdict: complete.

Evidence:

- Linear spec was available and required lifecycle focused files, no recreated monolith, searchable scenario names, preserved assertions, and a passing Codex pytest suite.
- fmm shows four focused transport turn files, 854 total LOC, largest file 273 LOC.
- `test_transport_turns.py` is absent from the working tree and from `git ls-files`.
- AST comparison against `6e40620^:api/src/manicure/codex/test_transport_turns.py` reported no missing, added, or changed function bodies.
- `uv run --project api pytest api/src/manicure/codex` passed, 96 tests.

Correctness concerns: none found.

Quality notes:

- Imports are local to each scenario family. Example: pause specific breakpoint and flow state dependencies only appear in `test_transport_turn_pause.py:11` through `test_transport_turn_pause.py:16`.
- No single replacement file recreates the original monolith.

### ALP-2044

Verdict: complete.

Evidence:

- Linear spec was available and required repair behavior files by artifact phase, one fixture builder owner, preserved private helper names if surgical, and a passing Codex pytest suite.
- fmm shows five repair files, 764 total LOC, with `test_repair_support.py` imported by four downstream repair behavior files.
- `test_repair.py` is absent from the working tree and from `git ls-files`.
- AST comparison against `c392ffc^:api/src/manicure/codex/test_repair.py` reported no missing, added, or changed function bodies.
- `uv run --project api pytest api/src/manicure/codex` passed, 96 tests.

Correctness concerns: none found.

Quality notes:

- Fixture builders have one owner in `test_repair_support.py:30` through `test_repair_support.py:150`.
- The support module preserved existing helper names, which keeps the diff surgical and avoids behavior churn.

## Dependencies

Critical test dependencies observed:

- `mitmproxy.websocket` and `wsproto.frame_protocol.Opcode` for websocket message fixture construction.
- `manicure.codex.transport.ensure_codex_transport_state` for transport turn state assertions.
- `manicure.codex.repair.repair_codex_derived_artifacts` and `resolve_codex_derived_artifacts` for repair behavior coverage.
- `manicure.storage.disk.DiskStorageBackend` via the shared repair `storage` fixture.

## Relevance to Helioy

This is a clean example of seam based test decomposition in Helioy: behavior files become navigation units, while support modules own reusable fixture construction. The AST preservation check is a useful review tactic for pure test moves.

## Open Questions

None for ALP-2041 or ALP-2044. No follow up fixes are required from this review.
