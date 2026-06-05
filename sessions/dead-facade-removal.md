---
title: Dead Facade Removal
type: sessions
tags: [backend, transport-matters, dead-code, cli, index]
summary: Removed dead index package root exports and trimmed the CLI package facade to current compatibility seams.
status: active
source: backend-engineer
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

## Summary

Implemented branch `refactor/remove-dead-facades` at commit `f652505`.

The `transport_matters.index` package remains because production code still imports inner modules. The package root no longer re-exports transcript adapter, session, or tailer symbols.

The CLI package facade now keeps only the 8 current compatibility exports proven in use: `main`, `SIGNAL_EXIT`, `BindFailure`, `WorkspaceLock`, `allocate_port_pair`, `port_in_use`, `run_children`, and `workspace_root`. Test-only `run_root` and `workspace_id` imports now come from `transport_matters.workspace`.

## API Contract

No HTTP, WebSocket, CLI command, request, or response contract changed. The installed entry point still resolves `transport_matters.cli:main`.

## Database Changes

No schema, migration, data access, or index changes.

## Security Considerations

No authentication, authorization, secret handling, or network boundary changes. The cleanup reduces package-scope surface area by removing unused public import aliases.

## Performance Notes

Package import work is smaller for `transport_matters.index` and slightly smaller for `transport_matters.cli` because unused facade imports are gone. No runtime performance change was measured or expected.

## Verification

- Custom AST grep proved no remaining `transport_matters.index` package-root facade import, attribute, or string references.
- Custom AST grep proved no remaining references to removed `transport_matters.cli` facade names.
- `python -m compileall -q api/src/transport_matters/index/__init__.py api/src/transport_matters/cli/__init__.py api/src/transport_matters/cli/test_start_workspace.py` passed.
- `git diff --check` passed.
- `just check` passed, including desktop tests 46 passed, www typecheck, api ruff and mypy.
- `just test` passed, including desktop 46 passed, www 1057 passed, api 1749 passed.

## Open Items

None for this slice. Adjacent legacy surfaces such as block store, diff, and raw fetch remain follow-up candidates only when separately scoped.
