---
title: Strict module-privacy lint — review + cwd-anchor hardening
type: sessions
tags: [backend, review, enforcement-lint, module-privacy, transport-matters]
summary: Audited the strict-private-import refactor; rename was clean/complete, hardened the boundary lint against a cwd-relative silent false-pass.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

Reviewed branch `refactor/strict-private-import-rule` (codex worker's single commit `1921b83`) against `~/.mdx/projects/transport-matters-strict-private-import-spec.md`. The rename of 51 cross-module-imported private symbols (drop leading underscore at definition, update every reference) is **behavior-preserving and complete**. Found and fixed one enforcement-test weakness. Landed one new commit on top (did not rewrite `1921b83`).

## Audit result (6 review dimensions)

- **Correctness** — pure renames; no logic/signature/control-flow edits; no production exception chaining touched (only `except SyntaxError` exists, inside the new test's own scanner).
- **Completeness** — authoritative scanner reports 0 violations from repo root; `grep` for the 51 old underscored names across `src`+`tests` returns zero hits, covering `monkeypatch`/`patch`/`getattr` STRING targets and `__all__`/facade re-exports the AST scanner cannot see.
- **Enforcement test** — RED/GREEN verified by planting `from transport_matters.exchange_stats import _parse_response_ir` in a non-test file; readable offender list on failure. Test-file classification (`test_*`, `*_support.py`, `*fixtures*`, `conftest.py`) and first-party restriction correct.
- **Naming** — `DEFAULT_ATTEMPTS`, `PTY_JOIN_TIMEOUT` stayed UPPER_CASE; no builtin/stdlib shadowing.
- **Conventions** — no `from __future__` added; builtins-only hints; import DAG topology unchanged (renames add no edges).
- **DRY** — `persistable_curated_ir` defined once (`exchange_recorder_artifacts.py:37`), live re-export via `exchange_recorder.py:21` consumed by `exchange_derivation.py` (not a dead shim).

## Change landed

`67ea198 test(api): anchor private-import lint to file path, not cwd`

The scanner used cwd-relative roots `[Path("src/transport_matters"), Path("tests")]`, so it silently false-passed (scanned nothing, ~0.01s) when pytest ran from any cwd but `api/`. Anchored roots to `Path(__file__)`:

```python
_PKG_ROOT = Path(__file__).resolve().parent  # api/src/transport_matters
_API_ROOT = _PKG_ROOT.parents[1]             # api
_SCAN_ROOTS = [_PKG_ROOT, _API_ROOT / "tests"]
...
assert root.is_dir(), f"private-import scan root missing: {root}"
```

Offenders reported via `path.relative_to(_API_ROOT)` so messages stay `src/transport_matters/...`. Now cwd-independent and fails loudly if a scan root ever moves. Re-verified planted-violation RED from both `api/` and repo root.

## Verification

- `cd api && just ci` → **978 passed** (ruff format + ruff check + mypy + pytest), green before and after the change.
- Planted-violation RED check confirmed from both cwds; reverted; working tree clean.

## Security considerations

This lint is the flagship module-privacy boundary other littleorgans Python modules will copy. A guardian lint that can pass having scanned zero files manufactures false confidence — the cwd-anchor fix closes that silent-failure mode.

## Open items

- None blocking. Orchestrator (`transport-matters:general:1:3.1`) owns push/PR; I did not push or open a PR per instruction.
