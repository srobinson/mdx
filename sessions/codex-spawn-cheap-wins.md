---
title: Codex Spawn Cheap Wins
type: sessions
tags: [backend, codex, performance, captured-run]
summary: Implemented process-local Codex startup caches, process-exit CA cache cleanup, and a captured pane starting indicator.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary
Implemented the approved Codex spawn cheap wins on branch `perf/codex-spawn-cheap-wins`, PR #138. Commit `ccca143` added process-local startup caches and the captured pane starting indicator. Commit `48ad168` registered cached generated CA bundle directories for process-exit cleanup while preserving in-process reuse.

## API Contract
No public API contract changed. Existing captured run creation and terminal WebSocket routes are unchanged:

```typescript
// POST /v1/runs
// WS /v1/runs/{runId}/terminal?cols={cols}&rows={rows}
```

The UI now surfaces a generic status message inside `CapturedRunPane` until the first ordinary PTY output arrives.

## Database Changes
No database schema or migration changes.

## Security Considerations
- `codex --version` cache is keyed by resolved binary path and mtime so upgraded binaries re-resolve.
- Generated Codex CA bundle cache is process-local and invalidates on env digest, mitmproxy CA fingerprint, and system trust path fingerprint changes.
- Generated CA bundle directories are retained during the process lifetime for cache reuse, then removed at process exit or test cleanup.
- Resolver failures remove the just-created temporary bundle directory immediately.
- Explicit `CODEX_CA_CERTIFICATE` remains resolved each call and still reports missing configured files.
- No Codex MCP servers, templates, auth material, or runtime capabilities changed.

## Performance Notes
- Removed repeated `codex --version` shell-outs for unchanged Codex binaries.
- Reused generated CA bundles instead of rebuilding them for every launch.
- Held cache locks through resolution to keep concurrent launches from duplicating work for the same key.
- Added a captured terminal `Starting <CLI>` indicator that clears on first PTY output, without parsing CLI-specific terminal text.

## Verification
- `cd api && just check`: exit 0.
- `cd api && just test`: exit 0, 1533 passed.
- `just www check`: exit 0.
- `just www test`: exit 0, 894 passed.
- `just www test-e2e`: exit 0, 42 passed.

## Open Items
- The main user-visible Codex delay remains Codex CLI MCP server startup. This slice intentionally did not reduce MCP servers, change templates, or prewarm Codex.
