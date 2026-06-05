# CLI PR-1 adversarial review

Reviewer: backend-engineer/claude (CLI reviewer)
PR: #38 `feat/cli-launch-options` @ `c7d5287`
Scope: `launch_options.py` extraction + `--work-dir` migration (NOT the desktop command; that is PR-2)
Spec: `cli-spec.md` (Minimal refactor: New module + Work dir migration)
Date: 2026-06-06

## Verdict

**0 blockers, 0 majors. 1 minor, 2 nits, all non-blocking. PR is mergeable.**

The DRY extraction is correct and complete, behavior is preserved field-for-field,
the `--work-dir` migration is total (source, help, tests), and the full CI gate is
green (format + lint + mypy + 1143 tests). The single minor is a lost rationale
comment, not a behavior change.

## Hard-check results (vs cli-spec.md)

### 1. DRY single source — PASS

- `cli/launch_options.py` is the sole definition site for every option alias.
- `__init__.py` deletes ALL inline `typer.Option`/`typer.Argument` declarations from
  both `claude` and `codex` and replaces them with alias references
  (`api/src/transport_matters/cli/__init__.py:220-228` claude, `:278-285` codex).
- Zero inline option redefinition remains. `git diff` shows the inline blocks removed,
  not duplicated.
- Grep confirms no other call site still declares these flags inline.

### 2. Behavior preserved — PASS

Field-by-field comparison of each removed inline option against its new alias
(`launch_options.py`): flags, short aliases, `envvar`, `callback`, and path-validation
kwargs all match the originals exactly.

| Option | envvar | callback | path kwargs | Match |
| --- | --- | --- | --- | --- |
| `--proxy-port`/`-p` | `PROXY_PORT` | `validate_port_option` | n/a | yes |
| `--web-port`/`-w` | `WEB_PORT` | `validate_port_option` | n/a | yes |
| `--storage-dir`/`-d` | none (by design) | none | `file_okay=False,dir_okay=True,resolve_path=True` | yes |
| `--home-dir` | none | none | `file_okay=False,dir_okay=True,resolve_path=False` | yes |
| `--upstream`/`-u` | `UPSTREAM_URL` | none | n/a | yes |
| `--claude-bin` | none | none | `exists=True,file_okay=True,dir_okay=False,resolve_path=True` | yes |
| `--codex-bin` | none | none | `exists=True,file_okay=True,dir_okay=False,resolve_path=True` | yes |
| `--no-claude`/`--no-system-prompt`/`--no-codex`/`--force-http-fallback`/`--debug`/`--print-command` | bool | n/a | n/a | yes |

- `validate_port_option` genuinely lives in `cli/net.py:16-35`; the original `__init__.py`
  also imported it from `.net`, so the import source is unchanged (the spec sketch said
  `cli.ports`, but `.net` is the real home and the correct one).
- Only help strings were reworded (cosmetic). See nits.

### 3. `--work-dir` migration complete — PASS

- Positional `[DIRECTORY]` removed from both commands; replaced by `work_dir: WorkDirOption`.
- Internal contract unchanged: `run_start(directory=work_dir, ...)` and
  `run_codex(directory=work_dir, ...)` (`__init__.py:234, 292`), so `prepare_launch`
  is untouched.
- `help.py` now lists `--work-dir PATH` AND `--home-dir PATH` in the Options block for
  both `claude` and `codex` (`help.py` diff). `--home-dir` was previously omitted from
  custom help; that omission is now fixed, as the spec required.
- Pass-through simplified: `_split_passthrough(ctx)` drops the
  `directory.name.startswith("-")` branch (`__init__.py:110-117`). With no positional,
  a non-option first token can no longer be swallowed as `[DIRECTORY]`; it flows to the
  child. Help examples updated accordingly (`claude -- "what is 2+2"` no longer needs a
  leading `.`).

### 4. Tests assert the new surface — PASS

Updates assert the new contract; they are not coverage deletions.

- `test_start.py`: `test_start_accepts_directory_argument` renamed to
  `test_start_accepts_work_dir_option`, invokes `--work-dir`.
- `test_help.py`: now asserts `--work-dir` AND `--home-dir` appear in both claude and
  codex help (`test_help.py:64-65, 82-83`).
- `test_start_validation.py::test_start_rejects_missing_directory`: asserts a missing
  `--work-dir` is still rejected by click with exit 2 (validation parity preserved:
  neither the old positional nor `WorkDirOption` sets `exists=True`, so semantics match).
- `test_start_passthrough.py`, `test_start_workspace.py`, `test_start_storage.py`,
  `test_start_children.py`, `test_start_mint.py`, `test_codex.py`, `test_home_seed.py`:
  all `["claude"/"codex", str(dir)]` migrated to `["...", "--work-dir", str(dir)]`.
- Grep for leftover positional-style invocations (`"claude"|"codex", str(...)` without
  `--work-dir`) returns empty across `api/`. No test silently routes a path into
  pass-through.

### 5. LOC / import discipline — PASS

- `launch_options.py` is 156 LOC (spec cap 300, repo cap 700).
- Imports: stdlib (`pathlib`, `typing`), `typer`, `transport_matters.env_keys` (public),
  and `.net.validate_port_option` (public). No private imports; no cross-layer violation;
  no import cycle (`net.py` imports only `socket`, `time`, `typer`).
- `__init__.py` shrinks substantially (claude/codex bodies now ~15 lines each, well
  under the ~150 fn cap).
- `# noqa: TC001` on the alias import is correct and required: the aliases are used as
  runtime `Annotated` defaults, so they must NOT move into a `TYPE_CHECKING` block.

## Findings

### Minor 1 — lost load-bearing rationale on the `--storage-dir` no-envvar decision

`api/src/transport_matters/cli/launch_options.py:57-70` (`StorageDirOption`)

The original inline `storage_dir` option in both `claude` and `codex` carried a comment
explaining WHY `--storage-dir` deliberately has no `envvar`: a launch must not inherit a
parent session's `TRANSPORT_MATTERS_STORAGE_DIR` as its `--storage-dir`, or nested runs
would co-reside in the parent's store; the addon (pydantic settings) and `paths` still
read the env var directly. The extracted `StorageDirOption` preserves the behavior (no
`envvar`) but drops the comment.

Risk: a future maintainer editing the shared alias could add `envvar=env_keys.STORAGE_DIR`
"for consistency" with the port options and silently break nested-run storage isolation.
The comment is the guardrail.

Recommendation: port the original comment onto `StorageDirOption`. Non-blocking.

### Nit 1 — codex proxy-port help loses the "explicit-proxy" distinction

`launch_options.py:35-45` (`ProxyPortOption`)

Old claude help said "reverse-proxy listener", old codex help said "explicit-proxy
listener". The shared alias says "Proxy listener port." This is an inherent consequence
of sharing one alias and is acceptable: the proxy-mode difference is still documented in
the custom `help.py` blocks, and Typer's per-option help is suppressed by `PlainCommand`
anyway. No action required.

### Nit 2 — `--force-http-fallback` and a few help strings trimmed

`launch_options.py:147-156`

The shared `ForceHttpFallbackOption` drops the trailing sentence "Used to capture the
HTTP wire format without changing Codex CLI config." present in the old inline help. The
custom `help.py` codex block still documents the flag. Cosmetic. No action required.

## Notes (scrutinized, correct)

- `# ruff: noqa: UP040` + explicit `TypeAlias` (not PEP 695 `type X =`): correct and
  necessary. A `type` statement creates a lazy `TypeAliasType` that Typer's runtime
  `Annotated` introspection cannot unwrap to find the `typer.Option` metadata; the
  classic `TypeAlias` form keeps the metadata eager and resolvable.
- `AgentOption`/`AgentName` are defined here but unused in PR-1 (they are for PR-2's
  `desktop --agent`). Shipping them now is acceptable forward-declaration for the single
  source module; `ruff check` does not flag them (public module-level export).

## Verification performed

- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`
  → green. Full gate, not just pytest:
  - `ruff format --check src/` → 286 files already formatted
  - `ruff check src/` → All checks passed!
  - `mypy src/` → no errors
  - `pytest` → **1143 passed in 10.41s** (matches the builder's count)
- `git diff main...c7d5287` field-by-field on `__init__.py`, `help.py`, `launch_options.py`,
  and all 11 changed test files.
- `fmm_lookup_export validate_port_option` → `cli/net.py:16-35` (confirmed import source).
- Grep for leftover positional invocations across `api/` → none.
