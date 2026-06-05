---
title: Transport Matters strict private-import boundary enforcement
type: sessions
tags: [backend, transport-matters, python, lint]
summary: Renamed all non-test cross-module private imports to public names and added enforcement for module-privacy boundaries.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary
- Implemented `refactor(api): enforce module privacy boundary` on branch `refactor/strict-private-import-rule`.
- Renamed all 63 non-test private-symbol import violations (51 symbols across 16 definer modules) to public names and updated all references, including tests and monkeypatch targets.
- Added enforcement test `api/src/transport_matters/test_private_import_boundary.py` and updated docs in `api/CLAUDE.md`.
- Verified a temporary planted non-test private import causes a red boundary test before reverting.
- Final gate `cd api && just ci` passed with 978 tests.

## API Contract
- No API contract files changed. This task is internal module-shape hygiene with no transport-level interface modifications.

## Database Changes
- None.

## Security Considerations
- Enforced namespace hygiene for module privacy: no non-test module may import private (`_name`) symbols from another module.
- This is a defensive code quality control to prevent accidental use of non-public internals.
- Private imports in tests remain allowed under the project rule for test fixtures and white-box access.

## Performance Notes
- Renames are behavior-preserving and avoid runtime overhead.
- Added one AST-based boundary test with O(number of Python files) runtime and negligible runtime cost for CI.
- Full suite baseline stayed green at 978 passing tests.

## Open Items
- Continue monitoring for future modules introducing new private names that are intended to be shared.
- Consider periodic run of the privacy boundary test before wide refactors.
