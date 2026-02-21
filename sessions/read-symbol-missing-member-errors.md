---
title: read_symbol missing member diagnostics
type: sessions
tags: [backend, fmm, cli, diagnostics, alp-2707]
summary: Implemented and pushed member aware read_symbol missing member errors with suggestions, grouped members, and CLI or MCP guidance.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented `read_symbol` missing member diagnostics for `moe-local-batch` item 14 on branch `nancy/ALP-2707`.

Commit: `ec3add4 fix(cli): clarify read_symbol missing member errors`.

The commit has been pushed to `origin/nancy/ALP-2707` after Phase B signoff.

The old negative path said an unknown dotted member was not a public or private method. The new path treats the lookup as a member error, lists available fields and methods, and suggests likely matches.

## API Contract

No public API schema changed.

Human readable CLI and MCP error text changed for missing dotted members:

```text
Member '<Type.member>' not found. '<member>' is not a member of '<Type>'.
Did you mean: <up to 3 candidates>?
Fields: <up to 20 field names>
Methods: <up to 20 method names>
(<N> members total; <CLI or MCP outline guidance>.)
```

CLI guidance uses:

```text
use fmm outline <file> --include-private for full list
```

MCP guidance uses:

```text
use fmm_file_outline(file: "<file>", include_private: true) for full list
```

## Database Changes

No database schema changes.

The implementation reads existing manifest data from:

- `FileEntry.methods`
- `FileEntry.method_metadata`
- `FileEntry.nested_fns`
- `FileEntry.closure_state`
- `private_members::extract_private_members`

## Security Considerations

No authentication, authorization, network, or persistence boundary changed.

The formatter is defensive:

- It caps suggestions at 3.
- It caps each displayed member group at 20.
- It falls back to a short error when no member catalog is available.
- It avoids propagating private member extraction failures through the diagnostic path.

## Performance Notes

The diagnostic only runs on failed dotted member lookups.

The member catalog is local to one resolved class file. Suggestion ranking uses substring matching first and Levenshtein only when substring matching finds no candidates.

Verification completed:

```text
just check
just test
just build
./target/debug/fmm generate && ./target/debug/fmm validate
```

`just test` passed with 1255 tests and 3 skipped doc-tests.

Runtime road test against `SpawnCoordinator.spawn` produced the expected suggestions, fields, methods, and 14 member total.

## Open Items

None for item 14.

Reviewer signed off with:

```text
I sign off on the member-not-found error fix as currently filed.
```

Reviewer acknowledged item 14 is closed after push. Orchestrator and reviewer were notified that `ec3add4` was pushed and the worktree was clean.
