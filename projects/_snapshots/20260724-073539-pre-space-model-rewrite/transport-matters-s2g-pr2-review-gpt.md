# PR #304 review: S2g PR2 inventory and startup refresh

Verdict: **issue**, 2 findings. Top severity: **medium**.

Reviewed `main..feat/s2g-inventory-refresh` at:

- Base: `76a3b8cb3c18c4fec69fd4faef46e0d970f1e633`
- Head: `73bbd5beed32c8d7cfe24d3d645e54d87351cb1f`
- PR: <https://github.com/littleorgans/transport-matters/pull/304>

## Findings

### 1. Medium: access diagnostics can be attributed to a newer connection revision

[`_connection_info`](https://github.com/littleorgans/transport-matters/blob/73bbd5beed32c8d7cfe24d3d645e54d87351cb1f/api/src/transport_matters/harnesses/inventory.py#L205-L220) reports `connection.revision` while copying the authentication and access fields from the latest row selected only by `connection_id`. The join at [`access_by_connection`](https://github.com/littleorgans/transport-matters/blob/73bbd5beed32c8d7cfe24d3d645e54d87351cb1f/api/src/transport_matters/harnesses/inventory.py#L268-L270) never compares `access.connection_revision` or `access.route_id` with the current connection.

`persist_connection` permits a later revision to change the home, route, or default status. The prior access row remains. A pure helper reproduction with a revision 2 connection and revision 1 access row produced revision 2 plus `authentication_status="authenticated"`. A home change therefore presents old credential evidence as current. A route change can present the old route's evidence under the new route until refresh replaces it. The startup refresh has the same home-change race because it probes a captured connection and the access upsert validates harness and route, but not the current parent revision.

This violates the S2g source-revision contract and can mislead the inventory, REST, and MCP diagnostics. Access evidence does not gate launch, which limits severity.

Fix by preserving the access observation's `connection_revision` in the response and invalidating or suppressing diagnostics when its revision or route does not match the current connection. The persistence boundary should also reject an observation whose `connection_revision` no longer matches its parent. Add regression coverage for a revised connection with an older access row and for a revision change during refresh.

### 2. Minor: the inventory load and 503 translation are duplicated

[`get_capabilities`](https://github.com/littleorgans/transport-matters/blob/73bbd5beed32c8d7cfe24d3d645e54d87351cb1f/api/src/transport_matters/api/v1/capabilities.py#L40-L48) duplicates the complete pool lookup, missing-pool check, inventory call, and exception translation from [`get_harnesses`](https://github.com/littleorgans/transport-matters/blob/73bbd5beed32c8d7cfe24d3d645e54d87351cb1f/api/src/transport_matters/api/v1/harnesses.py#L31-L39). This is an exact copied control-flow block in the changed lines and violates the repository's zero-tolerance DRY rule.

Factor one shared inventory-for-request helper, or have the legacy projection delegate through a shared loader before shaping its response.

## Verified behavior

- Routing is correct: `main.create_app` mounts the new router directly at `/v1`; the `/api` aggregate does not include it. The route test pins `/v1/harnesses` as 200 and `/api/harnesses` as 404.
- Inventory uses one stored observation set for installation, compatibility, resolver snapshots, legacy GET projections, and MCP. The production inventory path never calls live detection.
- `resolver.launch_options` receives the same stored objects and is the resolver's first production caller. Compatibility remains advisory. Paused pointers remain advisory, null releases enumerate no options, and grok remains pointerless and unlaunchable.
- Every synchronous detector or Postgres upsert in startup refresh is moved through `asyncio.to_thread`. Startup does not await the task. Shutdown cancels and awaits it before pool close. Failure isolation exists per connection, per harness, and at the task wrapper.
- The real persistence barrier test exercises both upserts and checks health plus `/v1/capture/prepare` while worker threads are blocked. Its structure would expose an event-loop upsert, but the database-backed case could not execute in this checkout because no test database URL is configured.
- Storeless `/api/capabilities` returning 503 is the specified posture. Startup-only stored snapshot staleness is accepted because launch continues to probe live. The wide keyword-only injection seams remain bounded and files stay below the repository size limit.
- No compatibility pointer, certification record, or rollout activation changed. `COMPATIBILITY_ROLLOUT` remains `"advisory"`.
- The MCP projection, legacy GET delegation, and explicit agent-contract additions are coherent with the new read surface.

## Checks

- `git diff --check main..feat/s2g-inventory-refresh`: pass.
- Focused refresh and storeless-route tests: 7 passed in 0.17 seconds.
- Five focused database-backed route, coherence, MCP, detector, and real-barrier cases: collection succeeded, then fixture setup errored because `TRANSPORT_MATTERS_TEST_DATABASE_URL` or equivalent database configuration is absent. No test body ran.
- GitHub Actions: all primary jobs failed before starting. The backend check annotation says recent account payments failed or the spending limit must be increased. This is infrastructure state rather than test evidence.
- Repository writes by this reviewer: zero.
