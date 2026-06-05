---
title: Home Dir Flag Implementation
type: sessions
tags: [backend, cli, transport-matters, home-dir]
summary: Added managed --home-dir support for Claude and Codex launch paths with manifest recording.
status: active
source: backend-engineer
confidence: high
created: 2026-05-31
updated: 2026-05-31
---

## Summary

Implemented local commit `aa3e652` on `feat/home-dir`. The `claude` and `codex` commands now accept `--home-dir <path>`, resolve it once at the command boundary, and pass the same resolved value to managed child environment assembly and the workspace manifest. Directory creation is gated off for `--print-command`, preserving dry-run behavior.

## API Contract

CLI contract:

```text
transport-matters claude [DIRECTORY] --home-dir <path>
transport-matters codex [DIRECTORY] --home-dir <path>
```

Behavior:

- `claude --home-dir <path>` sets `CLAUDE_CONFIG_DIR=<resolved path>` on the managed Claude child.
- `codex --home-dir <path>` sets `CODEX_HOME=<resolved path>` on the managed Codex child.
- Omitted `--home-dir` leaves provider native behavior unchanged. Existing parent `CLAUDE_CONFIG_DIR` or `CODEX_HOME` still flows through unless a flag override is supplied.
- `--print-command` resolves the path for deterministic invocation building but does not create the directory.

## Database Changes

No database changes.

Manifest schema change:

```python
home_dir: str | None = None
```

The field is the final dataclass field so older manifests without `home_dir` still read as `None`. New manifests write JSON `null` when unset, not the string `"None"`.

## Security Considerations

Managed child home directory mapping is centralized in `launch_runtime.py` and fails loud with `ValueError` if a home directory is supplied for an unmapped client. Codex CA bootstrap remains independent of `CODEX_HOME`: the CA bundle is resolved before child environment assembly and `CODEX_CA_CERTIFICATE` remains an explicit absolute path in the child env.

## Performance Notes

No performance impact beyond one path resolution per CLI invocation and one directory creation for non-dry-run launches with `--home-dir`.

Verification:

```text
cd api && just check && just test
ruff check passed
mypy: Success, no issues found in 210 source files
pytest: 955 passed in 5.80s
```

## Open Items

Phase B reviewer sign-off received on bus topic `home-dir-signoff` for commit `aa3e652`. Reviewer independently read `git diff aa3e652~..aa3e652` and reran the gate from `api/`: ruff passed, mypy passed for 210 files, and pytest reported 955 passed in 6.19s. Pattern persisted in cm entry `019e7ef3-ea66-7d41-bd2d-2943dab2f723`.
