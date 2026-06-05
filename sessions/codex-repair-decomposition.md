---
title: Codex Repair Module Decomposition
type: sessions
tags: [backend, refactor, codex, repair]
summary: Decomposed Codex derived artifact repair into cohesive modules while preserving the public facade.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary

Implemented commit `0a2a16b` on branch `refactor/decompose-oversized-api-modules`.

`api/src/transport_matters/codex/repair.py` is now a thin public facade. The implementation is split by responsibility:

- `api/src/transport_matters/codex/repair_models.py`
- `api/src/transport_matters/codex/repair_payloads.py`
- `api/src/transport_matters/codex/repair_rebuild.py`
- `api/src/transport_matters/codex/repair_resolution.py`
- `api/src/transport_matters/codex/repair_service.py`

The existing import path `transport_matters.codex.repair` still resolves every public symbol imported by the five downstream importers.

## API Contract

No API contract changes. Public symbols preserved:

```python
CodexDerivedArtifactsDiagnostic
CodexDerivedArtifactsRepairAction
CodexDerivedArtifactsRepairResult
CodexDerivedArtifactsResolution
CodexDerivedArtifactsStatus
repair_codex_derived_artifacts
resolve_codex_derived_artifacts
```

## Database Changes

None.

## Security Considerations

No authentication, authorization, input boundary, or storage permission changes. Existing validation behavior and diagnostic shapes are preserved.

## Performance Notes

No behavioral or algorithmic changes. The split reduces module size and isolates parsing, resolution, rebuild, service, and model responsibilities.

Verification passed:

```bash
cd api && just ci
```

Observed result:

- Ruff format check passed
- Ruff check passed
- Mypy passed with no issues across 238 source files
- Pytest collected 977 items and passed 977 tests

## Open Items

None for this task.
