# Spec: strict module-privacy rule + enforcement lint

Branch (already created, checked out): `refactor/strict-private-import-rule`
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
Gate: `cd api && just ci` (ruff format --check, ruff check, mypy, pytest). Baseline = **977 passed**.
Python: 3.14 floor (PEP 758 `except A, B:` is valid; run tooling via `uv run --project api ...` or `cd api && uv run ...`, never the bare root interpreter).

## Goal

Establish and enforce one flagship convention: **a leading underscore marks a name private to its defining module. Non-test code must not import a private name (or private module) from another module.** Test code may (white-box unit testing + shared test-support modules). This module is the template other littleorgans Python modules will follow, so the rule must be documented AND lint-enforced.

## The rule (precise)

A file is **test/exempt-as-importer** iff its basename: starts with `test_`, OR ends with `_support.py`, OR contains `fixtures`, OR equals `conftest.py`. Everything else (including `__init__.py` and all source modules) is **non-test**.

Violation = a **non-test** file contains `from <M> import ... _name ...` (any imported alias whose name starts with a single `_`, excluding dunders) OR `from <M> import ...` where `<M>`'s leaf component starts with a single `_` (private module), where `<M>` is first-party (`module.startswith("transport_matters")` or a relative import `level>0`). Third-party private imports are out of scope.

Current non-test violations: **51 distinct symbols across 16 definer modules, 63 import sites**. Final state must be **zero**.

## Work

For every private symbol imported by non-test code, **drop the leading underscore at its definition and update every reference everywhere** (definition + intra-file uses + ALL importers, test and non-test + any `monkeypatch.setattr`/`patch`/`getattr` string targets referencing the old `_name`). The 16 definer modules and their symbols (authoritative, regenerate with the scanner below):

- `cli/banner.py`: `_print_banner`, `_print_client_banner`
- `cli/help.py`: `_PlainCommand`, `_PlainGroup`
- `cli/instances.py`: `_list_instances`
- `cli/net.py`: `_port_in_use`, `_wait_for_port_ready`
- `cli/runner.py`: `_run_children`, `_run_client_with_retry`, `_failing_ports_from_log`, `_format_retry_exhaustion`, `_handle_bind_failure`, `_run_client_children_until_outcome`
- `cli/ports.py`: `_DEFAULT_ATTEMPTS`
- `counting.py`: `_relevant_auth_headers`
- `codex/exchange.py`: `_delete_codex_provisional_exchange`, `_finalize_codex_provisional_exchange`, `_persist_codex_handshake_failure`, `_persist_codex_provisional_exchange`, `_persist_unparsed_codex_exchange`
- `codex/exchange_derivation.py`: `_advance_codex_derived_artifacts`, `_clear_codex_breakpoint_lifecycle`, `_record_codex_breakpoint_release`, `_replay_codex_derived_artifacts`, `_rewrite_codex_provisional_exchange`, `_supported_codex_derived_artifacts`, `_updated_codex_exchange_artifacts`
- `codex/repair_payloads.py`: `_coerce_datetime`, `_int_field`, `_parse_events_jsonl`, `_parse_turn_json`, `_string_field`, `_supported_versions`, `_unsupported_versions`
- `codex/repair_rebuild.py`: `_rebuild_codex_derived_artifacts`
- `codex/response_parser.py`: `_parse_sse_event_payloads`
- `exchange_recorder.py`: `_delete_http_provisional_exchange`, `_emit_exchange_deleted`, `_persist_exchange`, `_persist_http_exchange`, `_persist_http_provisional_exchange`, `_persist_track_assignment`, `_persist_unparsed_exchange`, `_persist_unparsed_http_exchange`, `_persistable_curated_ir`*
- `exchange_recorder_artifacts.py`: `_derive_codex_http`, `_extract_response`, `_persistable_curated_ir`, `_request_raw_bytes`, `_stamped_pipeline_stats`, `_tag_http_error_status`
- `exchange_recorder_unparsed.py`: `_unparsed_request_ir`
- `exchange_stats.py`: `_parse_response_ir`
- `supervisor_pty.py`: `_PTY_JOIN_TIMEOUT`, `_install_parent_cbreak`, `_pty_shuttle`

*`_persistable_curated_ir` is defined ONCE (in `exchange_recorder_artifacts.py`) and re-exported via `exchange_recorder.py`. Rename the single definition to `persistable_curated_ir`; update the re-export and all importers.

### Authoritative scanner (use to drive + verify)

```python
import ast, pathlib, os
ROOTS = [pathlib.Path("api/src/transport_matters"), pathlib.Path("api/tests")]
def is_test(rel):
    b = os.path.basename(rel)
    return b.startswith("test_") or b.endswith("_support.py") or "fixtures" in b or b == "conftest.py"
def violations():
    out = []
    for root in ROOTS:
        for p in sorted(root.rglob("*.py")):
            rel = str(p)
            if is_test(rel): continue
            try: tree = ast.parse(p.read_text(), str(p))
            except SyntaxError: continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom): continue
                mod = node.module or ""
                if not (mod.startswith("transport_matters") or node.level): continue
                leaf = mod.split(".")[-1] if mod else ""
                if leaf.startswith("_") and not leaf.startswith("__"):
                    out.append((rel, f"private module {mod}"))
                for a in node.names:
                    if a.name.startswith("_") and not a.name.startswith("__"):
                        out.append((rel, f"{a.name} from {mod or '.'*node.level}"))
    return out
```

## Deliverable: enforcement test

Create `api/src/transport_matters/test_private_import_boundary.py` containing the scanner above and a test asserting `violations() == []` with a readable failure message listing offenders. It must:
- Scan both `api/src/transport_matters` and `api/tests`.
- Be self-verifying: include a brief check (or demonstrate during dev) that a *planted* non-test private import is actually caught. Before final commit, temporarily add `from transport_matters.counting import relevant_auth_headers as _x  # noqa` style is NOT a violation; instead plant a real one (`from transport_matters.exchange_stats import _parse_response_ir` in a non-test file), run the test, confirm RED, then revert. Report that you did this.

## Deliverable: documentation

Add a `## Module privacy` section to `api/CLAUDE.md`:
- Leading underscore = private to defining module.
- Non-test code MUST NOT import a private name/module from another module; promote to a public name instead.
- Test code MAY import privates from the module under test and from shared test-support modules.
- Enforced by `test_private_import_boundary.py`; flagship convention other monorepo Python modules follow.

## Commit plan (each commit independently green via `cd api && just ci`)

Group by subsystem, lint+doc LAST so intermediate commits stay green:
1. `refactor(cli): de-underscore cross-module cli helpers` (banner/help/instances/net/runner/ports + cli/__init__ + importers)
2. `refactor(api): de-underscore counting cross-module helper`
3. `refactor(codex): de-underscore codex exchange persistence helpers` (exchange.py + importers)
4. `refactor(codex): de-underscore codex derivation helpers` (exchange_derivation.py + importers)
5. `refactor(codex): de-underscore codex repair payload/rebuild helpers` (repair_payloads + repair_rebuild + importers)
6. `refactor(codex): de-underscore codex response parser helper`
7. `refactor(api): de-underscore exchange recorder helpers` (exchange_recorder + artifacts + unparsed + stats + importers)
8. `refactor(api): de-underscore supervisor pty helpers`
9. `refactor(api): enforce module-privacy boundary + document rule` (the test + api/CLAUDE.md)

(Adjust grouping if cohesion demands, but keep every commit green and lint/doc last.)

## Hard constraints

- Behavior-preserving rename only. No logic changes, no signature changes beyond the name.
- No `from __future__ import annotations`. Builtins-only type hints. Keep the import DAG acyclic.
- Every commit: `cd api && just ci` green (must end at >= 977 passed; final commit adds the boundary test => 978).
- Use `git mv`/edits; do not leave dead re-export shims. If a facade re-exported a now-public name, keep the re-export with the new name only if it has real importers.
- After all renames, run the scanner: it MUST report zero. Then run full `just ci`.

## Reply discipline (helioy-bus)

Reply to the orchestrator with ONE line per completed commit (`done: <commit subject> — just ci NNN passed`) and a final ONE line when the whole branch is green with the planted-violation check confirmed. Do not paste diffs or logs; the orchestrator reads the branch directly.
