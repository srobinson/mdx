---
title: Captured run import cycle refactor
type: sessions
tags: [backend, transport-matters, imports, fmm]
summary: Broke the captured run Codex import cycle by moving the required web port seam into launch runtime and guarding the cycle with tests.
status: active
source: backend-engineer
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

## Summary

Implemented `refactor/break-captured-run-cycle` at amended commit `cfaea78`. The original cycle was:

- `captured_codex.py` imports Codex CLI invocation helpers.
- `cli/codex_cmd.py` imported `captured_run.require_web_port`.
- `captured_run.py` imports `captured_run_context.py`.
- `captured_run_context.py` imports `captured_codex.py` for Codex captured launches.

The clean cut was extracting the required embedded web port contract to `transport_matters.cli.launch_runtime.require_web_port`. `cli/codex_cmd.py` and `captured_run.py` now import that neutral launch runtime helper. `captured_run.py` keeps its internal import for local TTY launch behavior, but no longer advertises or re-exports `require_web_port` from `__all__`.

## API Contract

No public HTTP API changed.

Python launch seam contract now has one public home:

```python
def require_web_port(web_port: int | None) -> int:
    """Return the embedded web port required by standalone harness launches."""
```

The function preserves the previous failure text for missing embedded web ports.

## Database Changes

No schema, migration, or index changes.

## Security Considerations

No authentication, authorization, or secret handling changed. The refactor preserves launch environment behavior and only changes the module that owns the web port requirement.

## Performance Notes

No runtime performance impact is expected. The change removes one static import edge from `cli/codex_cmd.py` to `captured_run.py`.

## Verification

- `cd api && .venv/bin/python -m pytest src/transport_matters/test_launch_seam_imports.py -q`: 9 passed.
- `cd api && .venv/bin/python -m pytest src/transport_matters/cli/test_codex.py src/transport_matters/test_captured_run_web_separation.py src/transport_matters/test_launch_seam_imports.py -q`: 36 passed.
- `rg -n "from transport_matters\\.captured_run import|require_web_port" api/src/transport_matters api/tests`: no `require_web_port` import from `captured_run.py`.
- AST import scan with `cd api && .venv/bin/python`: no `require_web_port` import from `transport_matters.captured_run`.
- `fmm_file_outline(file="api/src/transport_matters/captured_run.py")`: `require_web_port` absent from re-exports after the amend.
- `fmm_glossary(pattern="require_web_port")`: public definition only in `api/src/transport_matters/cli/launch_runtime.py` after the amend.
- `fmm_dependency_cycles(file="api/src/transport_matters/captured_run.py", filter="source", edge_mode="runtime", explain=true)`: no cycles.
- `fmm_dependency_cycles(file="api/src/transport_matters/cli/codex_cmd.py", filter="source", edge_mode="runtime", explain=true)`: no cycles.
- `just check`: passed. The www lint step still reports pre-existing warnings but exits zero.
- `cd api && just ci`: passed with 1755 tests.
- `just test`: passed with desktop 46 tests, www 1057 tests, and api 1755 tests.

Root `just ci` is not defined in this justfile. `cd api && just ci` is the available CI recipe.

## Open Items

Global `fmm_dependency_cycles(filter="source")` still reports a pre-existing cycle between `override_state.py` and `overrides.py`. This work intentionally removed the captured-run Codex cycle only.
