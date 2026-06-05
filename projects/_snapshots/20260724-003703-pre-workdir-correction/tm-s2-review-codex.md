# S2 typed run inventory review

Range: `1c6f06456b4a54c895025a28fa0f93a915219d63..3cf2e2c01a975e5d3cfca569ea05bef1c88abeb4`

Branch and reviewed head: `feat/multi-launch` at
`3cf2e2c01a975e5d3cfca569ea05bef1c88abeb4`

Verdict: 0 blockers, 0 majors, 0 minors.

## Findings

No actionable findings.

## Contract proof

- `api/src/transport_matters/api/v1/controlplane_gateway_runs.py::_GatewayRunListPage`
  decodes `items` as `tuple[GatewayRunView, ...]` and aliases
  `nextCursor` to `next_cursor`.
- `api/src/transport_matters/api/v1/controlplane_gateway_runs.py::list_runs`
  requires a nonblank owner, emits `limit=100`, serializes present
  `SpaceId` and `WorktreeId` values as `spaceId` and `worktreeId`, preserves
  the base query on every page, follows `nextCursor`, and rejects a cursor
  that does not advance.
- The unchanged Node route
  `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes` accepts
  the same owner, cursor, limit, Space, and Worktree query fields. Its maximum
  limit is 100 and its response is `{items, nextCursor}`.
- `api/src/transport_matters/api/v1/controlplane_gateway_runs.py::_typed_run_request`
  maps GET transport failures to `GatewayUnavailableError`, HTTP rejection or
  invalid GET payloads to `GatewayResponseError`, and reserves
  `GatewayOutcomeUnknownError` for mutation transport ambiguity or invalid
  mutation success payloads.
- The extracted create body, terminate URL and 404 handling, structured
  rejection decoding, compact JSON encoding, and mutation ambiguity behavior
  match the parent implementation. The only origin lookup refactor resolves
  the same normalized `RunRouteProxy` Gateway URL.
- `api/src/transport_matters/api/v1/test_run_route_proxy.py` contains the five
  stated focused tests: exact Worktree query, exact Space query, two page
  owner and filter preservation, repeated cursor rejection, and invalid
  success response rejection. The typed `RunRouteProxy.list_runs` method is
  absent at the parent revision, so these tests exercise behavior introduced
  by this commit.
- `api/src/transport_matters/api/v1/test_run_proxy_controlplane.py` remains 678
  lines and is byte identical across the range. It retains the create and
  terminate wire contract plus terminate ambiguity proofs.
- The range changes five Python files only. It changes no TypeScript file or
  migration and introduces no `canvasId` or `canvas_id` reference.
- All touched files remain below the 700 line project limit.

## Verification boundary

The repository was pristine before review and before this verdict. No tests,
builds, type checks, linters, or other gates were run, per the shared tree
brief.
