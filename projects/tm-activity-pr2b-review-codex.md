# PR #256 review, Codex family

Head: `be8d57d24a13985ef5c383dec9d322c77699d637`

Verdict: issue, 3 major and 2 minor findings.

## Findings

### 1. Major: the desktop gateway ignores the canonical custom config home

`desktop/src/gateway/gatewayProcess.ts::resolveGatewayDatabaseUrl` always reads `channel.home/settings.toml`. The canonical Python path gives `TRANSPORT_MATTERS_HOME` precedence in `api/src/transport_matters/storage_roots.py::default_storage_root`. With database configuration only in a relocated home, Python starts against that configured store while the Electron-owned gateway sees no URL or a different default-home URL. Activity is then disabled or connected to a different store, so the strip stays empty.

Evidence:

- [desktop resolver](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/desktop/src/gateway/gatewayProcess.ts#L177-L194)
- [canonical home resolution](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/api/src/transport_matters/storage_roots.py#L18-L33)

The gateway should consume the same resolved home contract or receive the already resolved database URL from the backend launch seam.

### 2. Major: supported hostless PostgreSQL URLs bypass channel database rewriting

`desktop/src/gateway/gatewayProcess.ts::databaseUrlWithDatabaseName` requires a nonempty authority after `://`. Valid libpq forms such as `postgresql:///transport_matters` and `postgresql:///transport_matters?host=/var/run/postgresql` therefore return unchanged. Python explicitly rewrites both forms. On preview, Python connects to `transport_matters_preview` while Gateway Activity connects to `transport_matters`, violating channel isolation.

Evidence:

- [desktop URL rewrite](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/desktop/src/gateway/gatewayProcess.ts#L213-L224)
- [canonical Python rewrite](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/api/src/transport_matters/config.py#L240-L258)
- [locked hostless and socket cases](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/api/src/transport_matters/test_channel.py#L123-L140)

Direct probe at this head:

```text
postgresql:///transport_matters => postgresql:///transport_matters
postgresql:///transport_matters?host=/var/run/postgresql => postgresql:///transport_matters?host=/var/run/postgresql
```

### 3. Major: one route-level Activity stream cannot populate panes from other worktrees

`www/packages/canvas/src/workbench/SessionCanvasRoute.tsx::activityWorkspaceId` opens exactly one workspace stream from the resolved launch session or backend metadata. Canvas already supports captured runs from multiple worktrees coexisting in one Canvas, and workspace identity is derived from each resolved worktree path. A pane in any nonselected worktree never enters `runVitalsStore`, so its always-on strip remains empty.

Evidence:

- [single workspace subscription](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L39-L47)
- [coexisting per-worktree panes](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/www/packages/canvas/src/model/canvasStore.test.ts#L789-L810)
- [path-derived workspace identity](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/api/src/transport_matters/workspace.py#L58-L68)
- [snapshot replacement semantics](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/www/packages/core/src/activityStreamEvents.ts#L39-L52)

Subscription and store ownership need to cover every distinct workspace represented by captured-run panes. Multiple streams cannot feed the current global store unchanged because each snapshot replaces the whole workspace view.

### 4. Minor: elapsed values can stay stale for almost a full display unit

`www/packages/core/src/useElapsedTick.ts::schedule` waits a full minute or hour from mount instead of the remaining time to the next formatted boundary. A pane restored at age `1m59s` displays `1m` for another minute, until `2m59s`. Hourly values can lag almost an hour. This also regresses the existing Inspector pending timer, which previously refreshed every second.

Evidence: [coarse scheduler](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/www/packages/core/src/useElapsedTick.ts#L20-L31)

Schedule the first timeout for the remainder to the next second, minute, hour, or day boundary, then continue at the coarse cadence.

### 5. Minor: two added em dashes violate the governing writing rule

The session `AGENTS.md` instruction says never to use em dashes. This PR adds one as the missing-token placeholder in `RunVitalsStrip.tsx::VitalsReadout` and another in the proxy regression test comment.

Evidence:

- [missing-token placeholder](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx#L51-L55)
- [proxy test comment](https://github.com/littleorgans/transport-matters/blob/be8d57d24a13985ef5c383dec9d322c77699d637/api/src/transport_matters/api/v1/test_run_proxy.py#L258-L264)

## Confirmed behavior

- `_workspace_activity_route_path` re-encodes the ASGI-decoded workspace ID exactly once for both snapshot and stream routes. Literal percent and space characters are also preserved through correct percent encoding.
- `RunRouteProxy.forward_sse` uses an unlimited request timeout, `stream=True`, `aiter_raw()`, and closes upstream in `finally`. A gated probe received the first frame before the upstream released its second frame.
- The Activity proxy changes do not modify capture ingest, `pgContracts`, or run lifecycle code.
- The gateway database URL is passed only through the child environment. No credential logging was found.
- Canvas prefers `resolved.workspaceId`, falls back to full `meta.workspaceId`, and remains disabled when both are empty.
- The populated Playwright case asserts rendered tokens and status from an Activity snapshot.
- `useElapsedTick` has one shared implementation and both Canvas and Inspector use it.

## Verification

- Python proxy tests: 12 passed.
- Desktop gateway tests: 15 passed.
- Focused Canvas and Core tests: 52 passed across 4 files.
- Incremental SSE probe: first frame arrived before the upstream gate; upstream closed after completion.
- `git diff --check origin/main...HEAD`: clean.
- PR remained open, non-draft, and eligible at the reviewed head.
- `git status --short`: pristine before writing this external artifact.
