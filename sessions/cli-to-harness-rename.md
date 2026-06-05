---
title: CLI to harness launch axis rename
type: sessions
tags: [backend, api, migrations, frontend, transport-matters]
summary: Renamed the launch axis from cli and client_name language to harness across API, storage, runtime, desktop, and web surfaces.
status: active
source: backend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

## Summary

Implemented the ubiquitous language rename for the launch axis on branch `refactor/cli-to-harness`, committed as `97115d9`.
The code now uses `harness`, `HarnessName`, `HarnessCapability`, and `harnesses` across captured run launch, capability probes, run manager, runtime templates, transcript adapters, shared proxy bindings, session models, and web canvas state. Legacy launch axis identifiers were removed rather than aliased.

Verification completed:

- `just check` passed.
- `just test` passed with 1553 API tests plus desktop and web suites.
- `just api migration-smoke` passed with 7 migration tests.
- `git diff --check` passed.
- Targeted grep found no remaining legacy launch axis identifiers such as `client_name`, `CliName`, `"cli"`, or `cli=` in API, migrations, web, desktop, or API tests.

## API Contract

Captured run create now accepts `harness`:

```typescript
interface CreateRunRequest {
  harness: "claude" | "codex";
  cwd?: string;
  oscColorReplies?: boolean;
}

interface RunView {
  runId: string;
  workspaceId: string;
  sessionId: string;
  harness: "claude" | "codex";
  state: "running" | "exited" | "failed";
  endReason?: string;
  error?: string;
}
```

Capabilities now return `harnesses`:

```typescript
type HarnessName = "claude" | "codex";

interface HarnessCapability {
  installed: boolean;
  path: string | null;
  version: string | null;
}

interface CapabilitiesResponse {
  harnesses: Record<HarnessName, HarnessCapability>;
}
```

The web client now sends `{ harness }` to `POST /v1/runs` and consumes `run.harness` in captured run state.

## Database Changes

Edited existing migrations in place because the project is pre-release and compatibility was explicitly not required.
Session store migrations now create and query `harness` columns instead of `cli` columns. The migration smoke test recreates isolated local Postgres test databases via `TestDb.create()`, applies migrations to head, verifies downgrade and upgrade paths, and passed after the rename.

## Security Considerations

No authentication or authorization behavior changed. Existing validation still constrains the launch harness to supported values, now through `HarnessName` and shared harness constants. No backward compatible `cli` alias was left behind, so callers cannot bypass the new contract through legacy field names.

## Performance Notes

No runtime query shape expansion was introduced. Session inserts, timeline reads, shared proxy registration, and transcript tailing retained the same data flow with renamed fields. The full suite passed with no observed regression in migration or API tests.

## Open Items

- Update any external design documents or human facing docs that still describe the launch axis as `cli` if they are outside this worktree.
- Road test the new `{ harness }` launch contract through the user facing desktop or web path.
