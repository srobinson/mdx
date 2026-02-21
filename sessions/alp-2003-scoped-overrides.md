---
title: ALP-2003 Track Scoped Override Store
type: sessions
tags: [backend, manicure, overrides, tracks, frontend]
summary: Scoped Manicure overrides by run and track so concurrent subagents keep isolated edits.
status: active
source: backend-engineer
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Summary

Implemented ALP-2003 for Manicure. Override state is now scoped by `(run_id, track_id)` while preserving legacy/root fallback behavior for callers that do not carry track context. The request pipeline classifies inbound requests before applying overrides, persists the track assignment in flow metadata, and exchange persistence reuses that assignment when recording final artifacts.

Commits on branch `nancy/ALP-1847`:

- `aecbfb1 feat(api): scope overrides by track`
- `41106c8 test(api): simplify override test imports`
- `2cf82e8 fix(api): preserve unscoped override reset`

## API Contract

Override endpoints accept optional query parameters:

```typescript
interface OverrideScope {
  run_id?: string | null;
  track_id?: string | null;
}

// GET /api/overrides?run_id=<run>&track_id=<track>
interface OverrideListResponse {
  overrides: Override[];
  enabled: boolean;
}

// PATCH /api/overrides?run_id=<run>&track_id=<track>
interface OverrideBatchRequest {
  overrides: Override[];
}
interface OverrideMutateResponse {
  overrides: Override[];
  enabled: boolean;
  audit: OverrideAudit | null;
  curated_ir: InternalRequest | null;
}

// DELETE /api/overrides?run_id=<run>&track_id=<track>
// 204 No Content

// POST /api/overrides/toggle?run_id=<run>&track_id=<track>
interface ToggleResponse {
  enabled: boolean;
  audit: OverrideAudit | null;
  curated_ir: InternalRequest | null;
}
```

Paused flow payloads now expose track fields so the UI can address the correct override scope:

```typescript
interface PausedFlow {
  flow_id: string;
  transport: "http" | "websocket";
  run_id?: string | null;
  track_id?: string | null;
  parent_track_id?: string | null;
  track_display_name?: string | null;
  track_role?: "parent" | "subagent" | null;
}
```

## Database Changes

No database schema or migration changes. This slice updates in process state, API payloads, flow metadata, and persisted exchange index fields.

## Security Considerations

No new authentication surface was introduced. The scope query parameters only partition local override state. Override application remains bounded to validated `Override` models and existing audit paths. Existing legacy callers without scope parameters continue to operate against the legacy/root scope.

## Performance Notes

Scoped override lookup remains in memory. Request classification happens once before request mutation, then response observation reuses the stored assignment to avoid double request classification. Full verification passed:

- Backend: `uv run ruff format --check src/`, `uv run ruff check src/`, `uv run mypy src/`, `uv run pytest` with 701 tests passing.
- Frontend: `pnpm --dir www lint`, `pnpm --dir www typecheck`, `pnpm --dir www test` with 21 test files and 253 tests passing.
- `git diff --check` clean.

Engineering review follow-up in `2cf82e8` restored legacy unscoped `DELETE /api/overrides` full reset behavior, preserved null `track_role` in SSE parsing, and tightened paused event payload typing.

## Open Items

Codebase analyst review returned LGTM. Engineering review found one critical compatibility regression, fixed in `2cf82e8`. The remaining warnings are non-blocking follow-ups except the null `track_role` coercion and payload typing, which were also fixed in `2cf82e8`.
