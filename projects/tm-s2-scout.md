# Transport Matters S2 typed run inventory scout

Scope: read only scout and implementation plan for S2 at
`1c6f06456b4a54c895025a28fa0f93a915219d63`, which matches `origin/main`.
The tracked worktree was clean when inspected. The local `main` ref was stale,
so all findings below are pinned to the verified commit.

Verdict: S2 is one backend PR. The TypeScript inventory and stop behavior
already exist. Python needs a typed, exhaustively paged adapter over that
inventory. No TypeScript production change, Canvas filter, or migration is
needed.

Top open decision: should the Python method return one Gateway page or
enumerate every page? Recommend exhaustive enumeration inside the typed adapter.
The later delete service should receive a complete tuple of run views and
should not own Gateway cursor mechanics. A one page method can silently miss
runs because the Gateway defaults to 50 items and caps a page at 100.

## Reuse Map

| Capability | Existing owner | Reuse judgment |
| --- | --- | --- |
| Managed run filter contract | `packages/runtime/src/service/runManagerTypes.ts::ManagedRunFilters` | Reuse unchanged. Exact shape: required `owner`, optional `state`, optional `spaceId`, optional `worktreeId`. S2 uses owner plus the two identity filters. |
| Process resident run inventory | `packages/runtime/src/service/RunManager.ts::RunManager.list` | Reuse unchanged. It filters private run records by owner before projecting views, then applies state, Space, and Worktree filters, and returns defensive view copies. |
| Stop one managed run | `packages/runtime/src/service/RunManager.ts::RunManager.terminate` | Reuse unchanged. Exact input is run ID, owner, and optional reason. The default reason is explicit and teardown funnels through the existing memoized settle path. |
| Runtime run projection | `packages/runtime/src/domain/runtimeRun.ts::RuntimeRunView` | Reuse as the wire authority. Exact fields are `runId`, `spaceId`, `worktreeId`, `sessionId`, `harness`, `name`, `agentId`, `agentName`, `state`, optional `endReason`, optional `error`, and `createdAt`. |
| Trusted identity placed on the view | `packages/runtime/src/service/RunManager.ts::RunManager.register` | Reuse unchanged. Capture resolved `spaceId` and `worktreeId` win over request values before the run enters the inventory. |
| HTTP list route | `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes`, `GET /v1/runs` | Reuse unchanged. It parses owner, state, Space, Worktree, cursor, and limit, then calls `RunManager.list`. The response is `{items, nextCursor}`. Default limit is 50 and maximum limit is 100. |
| Owner normalization | `packages/runtime/src/server/runtimeRouter.ts::ownerFromQuery` | Reuse, while always sending an explicit owner from Python. An omitted or empty owner becomes `local`. |
| Existing TypeScript proofs | `packages/runtime/src/service/RunManager.test.ts`, suite `RunManager reads`; `packages/runtime/src/server/runtimeRouter.test.ts`, suite `createRuntimeRouter` | Reuse. They already prove owner partitioning, Space filtering, state filtering, combined Space and Worktree forwarding, pagination, and query rejection. |
| Python run view | `api/src/transport_matters/controlplane/run_models.py::GatewayRunView` | Reuse for returned items. It already validates the fields needed by Python run management: run ID, state, name, and agent ID. S2 needs run IDs for later termination. |
| Python run management port | `api/src/transport_matters/controlplane/activity.py::RunManagementPort` | Extend with the typed list operation. This is the existing service boundary for `create_run` and `terminate_run`; a second inventory port would duplicate ownership. |
| Typed create and stop adapter | `api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy.create_run`, `RunRouteProxy.terminate_run`, `RunRouteProxy._typed_run_request` | Reuse semantics. Python can stop a known run ID today and already distinguishes unavailable, rejected, invalid, and ambiguous Gateway outcomes. |
| Typed adapter module pattern | `api/src/transport_matters/api/v1/controlplane_gateway_reads.py`, `api/src/transport_matters/api/v1/controlplane_gateway_input.py` | Reuse as the file boundary pattern. The run management transport can be extracted beside these modules so `run_proxy.py` stays below the repository limit. |
| Typed filtered Python list | None found | Add one method on `RunRouteProxy` and the existing `RunManagementPort`. Do not add another in memory registry, filter engine, run manager, or HTTP runner. |

Existing reuse anchors: 12. Planned new behavior: one typed list operation and
one private transport page envelope.

## Quality Map

### Current end to end path

```text
Python caller
  -> RunRouteProxy
  -> GET /v1/runs?owner=...&spaceId=... or worktreeId=...
  -> runtimeRouter.registerRunRoutes
  -> ownerFromQuery
  -> RunManager.list(ManagedRunFilters)
  -> RuntimeRunView[]
  -> {items, nextCursor}
```

The browser facing FastAPI route currently forwards this HTTP response as raw
bytes. The private Python control plane uses typed `RunRouteProxy` methods for
create and terminate, but there is no typed list method for a service to call.

### Owner and identity safety

- Owner is stored only on the private `ManagedRuntimeRun`. `RuntimeRunView`
  deliberately does not expose it. Python therefore cannot detect an owner leak
  by inspecting returned items.
- The typed method must require `owner` and put it on every page request. Never
  rely on `ownerFromQuery` falling back to `local`.
- A future delete service must pass `CrudCaller.owner`, or the equivalent
  authenticated principal owner. It must never derive owner from a Space or
  Worktree request field.
- Use `SpaceId` and `WorktreeId` at the Python port, rather than loose strings.
  The Gateway treats an empty `spaceId` or `worktreeId` as absent through
  `nonEmptyString`, which would broaden an intended filtered inventory to every
  run for that owner.
- `RunManager.list` applies owner partitioning before projecting a run view, then
  applies the optional Space and Worktree equality filters. This is the
  load bearing isolation order.

### Pagination and inventory semantics

- `GET /v1/runs` returns only 50 items by default and at most 100 per page.
  Fetching one page is insufficient for a delete substrate.
- Recommend `RunRouteProxy.list_runs` request `limit=100`, follow
  `nextCursor` until null, and return `tuple[GatewayRunView, ...]`.
- Require cursor progress. A repeated cursor or malformed successful response
  must raise `GatewayResponseError` rather than loop or return a partial
  inventory.
- `RunManager` retains terminal views in its process resident map. With no state
  filter, S2 can return running and terminal views. This is safe for the later
  best effort stop because `RunManager.terminate` is idempotent through the
  settled run path. S2 should not invent a second definition of live.
- New runs append to the map and settled runs are not removed, so offset paging
  does not shift existing items. A concurrent launch can appear on a later page.

### Contract and size health

- `api/src/transport_matters/api/v1/run_proxy.py` is 690 lines. Adding the list
  transport in place would cross the 700 line hard limit.
- `api/src/transport_matters/api/v1/test_run_proxy_controlplane.py` is 678 lines.
  Add the required tests in the new focused
  `api/src/transport_matters/api/v1/test_run_route_proxy.py`.
- `packages/runtime/src/service/RunManager.ts` is 665 lines and
  `packages/runtime/src/server/runtimeRouter.test.ts` is 662 lines. S2 changes
  neither.
- The clean extraction is a new
  `api/src/transport_matters/api/v1/controlplane_gateway_runs.py`, parallel to
  the existing typed reads and input adapters. Move current typed create,
  terminate, response validation, and run error decoding there, then add list.
  `RunRouteProxy` remains the public concrete port through small delegates.
- `GatewayRunView` is a deliberately narrow Python projection of the full
  TypeScript view. Expanding it is unnecessary for S2 because filters are
  inputs and later delete needs run IDs. If later code needs affinity from the
  result, extend this one type rather than create another run view.
- No dead path or obsolete Python run registry was found. FastAPI owns
  `app.state.run_proxy_mount`; the Node Gateway owns `RunManager`.

### Scope exclusions

- No `canvasId` filter. S4a owns adding Canvas identity to `RuntimeRunView` and
  `ManagedRunFilters`.
- No hard delete orchestration. S3 consumes this port.
- No migration or durable run inventory. Runs remain process resident.
- No TypeScript production change. Existing route, filter, view, and terminate
  owners remain authoritative.

## Plan

### Tests first

Add `api/src/transport_matters/api/v1/test_run_route_proxy.py` before production
changes. Keep the existing 678 line control plane proxy test unchanged.

1. `test_run_route_proxy.py::test_typed_list_returns_runs_filtered_by_worktree`
   calls the absent typed method with an owner and `WorktreeId`, returns a typed
   run tuple, and asserts the exact Gateway query contains `owner`,
   `worktreeId`, and `limit=100`. It fails first because the method does not
   exist.
2. `test_run_route_proxy.py::test_typed_list_filters_by_space` does the same for
   `SpaceId` and proves the Worktree parameter is absent.
3. `test_run_route_proxy.py::test_typed_list_preserves_owner_and_filters_on_every_page`
   serves two pages, asserts the second request preserves owner and the identity
   filter while adding the prior cursor, and proves all items are returned.
4. `test_run_route_proxy.py::test_typed_list_rejects_a_repeated_cursor` proves a
   broken Gateway cannot create an infinite loop or a partial success.
5. `test_run_route_proxy.py::test_typed_list_rejects_an_invalid_success_response`
   proves malformed items or cursor shape raise `GatewayResponseError`.

The two named filter tests are acceptance tests. The paging, progress, and
malformed response tests close the failure modes introduced by exhaustive
enumeration.

### STEP 0: preserve the file boundary

Create
`api/src/transport_matters/api/v1/controlplane_gateway_runs.py` using the
existing gateway adapter pattern.

1. Move the current typed create body construction, terminate request, generic
   typed request validation, and structured run error decoding from
   `run_proxy.py`.
2. Define one private Pydantic page envelope with `items` and aliased
   `nextCursor`. Reuse `GatewayRunView` for every item.
3. Keep the small HTTP transport protocol structural, matching
   `controlplane_gateway_reads.py::GatewayReadTransport`. Do not create a new
   HTTP client or runner.
4. Delegate `RunRouteProxy.create_run` and `RunRouteProxy.terminate_run` to the
   extracted adapter without changing their observable request bodies, errors,
   or ambiguity semantics. Existing tests guard the move.

This extraction lowers `run_proxy.py` before S2 adds behavior and keeps all
touched files below 700 lines.

### Typed inventory

1. Add `RunRouteProxy.list_runs`, requiring `owner` and accepting optional
   `SpaceId` and `WorktreeId`. Return
   `tuple[GatewayRunView, ...]`.
2. Extend `api/src/transport_matters/controlplane/activity.py::RunManagementPort`
   with the same signature. Reuse the existing port rather than create a delete
   specific interface in S2.
3. In `controlplane_gateway_runs.py`, build the query from the required owner,
   `limit=100`, and present typed IDs. Follow `nextCursor` until null while
   preserving all filters on every request.
4. Reuse the existing GET failure semantics: connection failure becomes
   `GatewayUnavailableError`; rejected or invalid responses become
   `GatewayResponseError`. Mutation ambiguity remains limited to create and
   terminate.
5. Leave `ManagedRunFilters`, `RunManager.list`, `RunManager.terminate`,
   `RuntimeRunView`, and `runtimeRouter.ts` unchanged.

### Verification

1. Run the new focused Python test file first.
2. Run existing
   `api/src/transport_matters/api/v1/test_run_proxy_controlplane.py` to prove
   create, terminate, reads, and input behavior survived the extraction.
3. Run the existing Runtime tests for `RunManager` and `runtimeRouter` as
   unchanged end to end filter and pagination guardrails.
4. Run `just check`.
5. Run `just test`, the repository full pull request gate.
6. Recheck line counts and verify the tracked tree contains only the intended
   S2 implementation and tests.

Slice count: one PR. Migration count: zero. TypeScript production changes:
zero.
