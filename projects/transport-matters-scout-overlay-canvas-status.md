# Overlay status visibility scout and plan

## Scope

Read only scout at exact base `b8e30eb06ad99c6f715167bab1a7aeaf63083dac` on `feat/overlay-registry-canvas-status`. The merge base equals HEAD and the repo worktree is clean.

The current slice should expose acquisition and cache status already delivered by slices 3 through 5. It must not add composition, application, `OverrideStore`, request mutation, or a per run freeze. The full specification binds frozen run state later in slice 7. Its present completion criterion still requires the current mode and reason to reach a human through `ExchangeDetail` and `ExchangeInspectPanel`.

Primary finding: the Overlay context already owns a sanitized `GET /v1/overlays/status` response, but browsers currently use the Python origin and `create_run_proxy_mount` does not forward that route. UI work alone would receive a 404.

## Current flow and precedence

```text
startup harness refresh or captured run launch
  -> POST /v1/overlays/refresh or RunManager.observeOverlayRelease
  -> OverlaySyncService.schedule / observe
  -> synchronous PASSTHROUGH cache_miss row
  -> capture cache metadata
  -> optional registry fetch and capture install or acquisition record
  -> statusByRelease replacement
  -> OverlaySyncService.statuses, sorted by exact harness and version
  -> GET /v1/overlays/status
```

Precedence is exact and current:

1. `schedule` creates `PASSTHROUGH / cache_miss` synchronously for a new exact release.
2. The capture cache is read before a remote fetch. Accepted signed bytes remain the held candidate.
3. Registry and capture results replace the process map entry for that release.
4. A held artifact can remain `VERIFIED` during an allowed outage or entitlement grace while retaining a reason such as `account_unavailable`, `artifact_missing`, `artifact_invalid`, or `registry_unavailable`.
5. `statuses()` returns the process map sorted by `overlayReleaseKey`. It has no run id or exchange id.

This status is current process acquisition and cache state. It is not frozen run state and does not prove that an exchange used or applied an overlay.

## Reuse Map

| Concern | Existing owner and readers or writers | Reuse decision |
| --- | --- | --- |
| Cross plane DTO | `packages/contract/src/overlay/wire.ts:OVERLAY_MODES`, `OVERLAY_PASSTHROUGH_REASONS`, `OverlayStatus`, `OverlayStatusResponse` | Import from `@tm/contract/overlay`. Add no mode, reason, or duplicate browser type. |
| Cross language literals | Python mirrors in `api/src/transport_matters/overlay_artifact.py`; parity is pinned by `packages/contract/src/overlay/overlay.test.ts` and `api/src/transport_matters/harnesses/test_overlay_artifact.py:TestOverlayContractParity` | Preserve both owners and their fixture parity tests. No vocabulary change is needed. |
| Status projection | `packages/overlay/src/projections/status.ts:emptyOverlayStatus`, `refreshedStatus`, `passthroughStatus`, `hasAcceptedArtifact` | Preserve. These functions own initial and refreshed DTO construction. |
| Process status writer | `packages/overlay/src/service/OverlaySyncService.ts:OverlaySyncService.schedule`, `refresh`, `resolveResult`; private `statusByRelease` map | Preserve. The browser route reads this map. It must not become another store. |
| Capture state reader and writer | `packages/overlay/src/adapters/captureOverlayCandidate.ts:CaptureOverlayCandidateAdapter`; Python `api/src/transport_matters/overlay_cache.py:OverlayAcceptedCache.metadata`, `install`, `record_acquisition` | Preserve. Capture remains the persisted cache authority. |
| Refresh triggers | `packages/runtime/src/service/RunManager.ts:RunManager.createNew`; `packages/gateway/src/main.ts:runGatewayProcess`; Python `harnesses/state_refresh.py:refresh_harness_state` through `main.py:_notify_overlay_refresh` | Preserve. Launch remains advisory and never waits for overlay I/O. |
| Status collection reader | `packages/overlay/src/service/OverlaySyncService.ts:OverlaySyncService.statuses` | Preserve sorted exact release collection and all returned items. Do not select the first item or invent provider precedence. |
| Product route | `packages/overlay/src/server/overlayRouter.ts:createOverlayRouter`, `GET /overlays/status`; mounted under `/v1` by `packages/gateway/src/app.ts:buildGateway` | Preserve DTO and router dependencies. No new Gateway route or service is needed. |
| Interim browser origin | `api/src/transport_matters/api/v1/run_proxy.py:create_run_proxy_mount`; forwarding primitive `RunRouteProxy.forward_http` | Add one read only `/overlays/status` forwarding route. Reuse the existing proxy client, error mapping, header filtering, base URL normalization, and `/v1` mount. |
| Browser transport | `www/packages/core/src/transport.ts:requestApiJson`; `www/packages/core/src/queryKeys.ts` | Add `fetchOverlayStatuses()` and one shared query key at these owners. Do not create a product specific transport. |
| Shared browser semantics | No current overlay helper exists. `@tm/core` already depends on `@tm/contract` and React Query and is consumed by both products. | Add a small `www/packages/core/src/overlayStatus.ts` owner for the shared query policy and pure status presentation. Export it through `@tm/core`. |
| Inspector owner | `www/packages/inspector/src/components/ExchangeDetail.tsx:ExchangeDetail` | Bind the shared query here and render the shared descriptor with existing Inspector chip classes. First extract its header and tab bank so the main function falls below 150 lines. |
| Canvas owner | `www/packages/canvas/src/viewers/resource/ArkExchangePanels.tsx:ExchangeInspectPanel` | Bind the same shared query here. Render with existing `.canvas-exchange__chips` and `.canvas-exchange__chip` markup. The normal and fullscreen inspect views already share this component. |
| Existing chip presentation | Inspector `.chip` and its existing header telemetry markup; Canvas `.canvas-exchange__chip`; `www/packages/host/src/ChannelBadge.tsx:ChannelBadge` | Reuse each product's local chip styles. `ChannelBadge` is fixed host chrome for release channel metadata, so its data owner and placement do not fit exchange status. Share semantic descriptor generation, never JSX or CSS across products. |
| Plane boundaries | `www/packages/shell/src/testSupport/importGraphBoundary.test.ts` and `depLint.test.ts` | Preserve zero imports in both Inspector to Canvas directions and browser prohibition on product context imports. Browser code consumes `@tm/core` and `@tm/contract`, never `@tm/overlay`. |

### Contract values and current reachability

`OVERLAY_MODES` contains `PASSTHROUGH`, `VERIFIED`, `FROZEN`, and `APPLY`.

Current live status producers emit only:

| Mode | Current source |
| --- | --- |
| `PASSTHROUGH` | Initial projection, disabled or failed acquisition, rejected or unusable cache state, and signed passthrough artifact disposition. |
| `VERIFIED` | Accepted cached artifact, including permitted held use with a non null acquisition reason. |

`FROZEN` and `APPLY` are reserved contract values with no assignment in the live status path at this base. The presenter must still render them totality safely for future slices.

All 17 reason literals must render without blank text. Nine are reachable through the current acquisition and cache status path:

| Reachable reason | Current producer |
| --- | --- |
| `disabled` | Disabled registry or signed passthrough disposition fallback. |
| `cache_miss` | New process observation and missing cache record. |
| `registry_unavailable` | Registry outage, retry exhaustion, or non client capture install failure. |
| `account_unavailable` | Registry 401 or 403 acquisition policy and retained grace state. |
| `artifact_missing` | Registry missing response and retained cache policy. |
| `artifact_expired` | Capture cache expiry without a retained acquisition reason. |
| `artifact_invalid` | Malformed cache, 406, or client side capture install rejection. |
| `signature_untrusted` | Capture validation and restart revalidation. |
| `revision_rollback` | Capture revision protection. |

Eight contract reasons have no status producer at this base: `harness_version_unknown`, `exact_release_unavailable`, `store_disabled`, `model_unmatched`, `fingerprint_unmatched`, `payload_unrecognized`, `preimage_mismatch`, and `application_failed`. Later frozen fact and request application slices own them.

Reason and mode are independent fields. A `VERIFIED` status may carry `account_unavailable`, `artifact_missing`, `artifact_invalid`, or `registry_unavailable`. The chip must always show the supplied mode and optional reason. A warning reason must never rewrite `VERIFIED` to `PASSTHROUGH`.

### Status presentation contract

The shared pure presenter should return a stable key, a visible label, an accessible title, and a semantic tone. Proposed visible form:

`Optimization · <harness> <version> · <MODE> · <reason with spaces>`

Omit the final segment when reason is null. Keep the exact mode. Include the exact release visibly because the current endpoint is process global and the exchange DTO has no harness version with which to select one row. Render every response item in server order. Empty items render no chip. Query failure renders no chip and leaves exchange content usable.

While any item has `lastRefreshAt === null`, use the shared query policy to refetch on a short interval. Stop after every item is refreshed. Do not poll an empty collection forever. This prevents a synchronous `cache_miss` observation from becoming a stale visible result.

## Overlay dependency boundary

`packages/overlay/src/gatewayDeps.ts:OverlayGatewayDeps` is the composition factory result. It owns one constructed `OverlaySyncService` and exposes `overlay` plus disk registry dependencies. `packages/overlay/src/server/overlayRouter.ts:OverlayRouterDeps` is the narrow router mount contract and exposes only `sync.observe`, `sync.schedule`, and `sync.statuses`.

The browser read requires no change to either type. Changing their shape would reflow the slice 5 fixtures below and add no capability:

- `packages/overlay/src/server/overlayRouter.test.ts`: all four router dependency fixtures.
- `packages/gateway/src/app.test.ts`: `mounts the Overlay context router under the shared v1 product prefix`.
- `packages/gateway/src/main.test.ts`: `selects the capture RPC client when TRANSPORT_MATTERS_CAPTURE_RPC_URL is set`, `passes the resolved overlay registry URL straight into the Overlay context`, and `wires OverlaySyncService observation into the default RunManager`.

Preserve these named slice 5 proofs:

- `OverlaySyncService.test.ts`: `observes each exact tuple once while explicit schedule still refreshes`.
- `RunManagerOverlayRefresh.test.ts`: exact prepared version dispatch without waiting, null normalized version without scheduling, and synchronous or asynchronous observer failure remaining advisory.
- Python state refresh and payload tests: each observed exact tuple is notified once without redetection; one harness notification failure is isolated; registry outage cannot fail startup refresh; captured preparation carries the exact gate version; payload carries exact version or null; refresh notification posts only the exact release key.

## Quality Map

| Severity | Evidence | Required treatment |
| --- | --- | --- |
| Blocker | Python is the current browser origin. `create_run_proxy_mount` forwards runs, activity, and space routes, but no overlay status route. | Add the focused GET proxy route before UI integration. Prove a request through `create_app` reaches the real Gateway response. |
| Blocker | `ExchangeDetail` is about 266 lines, above the 150 line function limit. | Extract a private header and tab bank before adding the query or chip. Keep each function below 150 lines. |
| High | The response is current process state, with no run or exchange binding. | Include exact harness and version in the visible label. Avoid `used`, `applied`, `optimized`, or frozen run claims. |
| High | `VERIFIED` can carry a failure reason. | Render mode and reason independently and test this combination explicitly. |
| High | Initial `cache_miss` has null `lastRefreshAt` while refresh continues asynchronously. | Centralize finite pending polling in `@tm/core`; stop on refreshed or empty data. |
| High | Empty collection, null normalized harness version, Gateway restart, and query failure can produce no current row. | Render no invented fallback. Keep exchange content visible. Document that blank means no current observed status, not passthrough. |
| Medium | Multiple releases can exist in the sorted map. The exchange DTO cannot select an exact release. | Render all rows with exact release identity. Do not choose the first, infer from provider, or collapse to a worst state. |
| Medium | Both product packages already have distinct presentation systems. | Share transport, query policy, and text semantics in core. Reuse local chip tokens. Preserve the cross plane import gates. |
| Medium | Future contract modes and reasons can arrive before UI changes. | Totality test every `OVERLAY_MODES` value, every `OVERLAY_PASSTHROUGH_REASONS` value, and null reason. |
| Low | `ChannelBadge` looks reusable but reads channel metadata and hides stable. | Leave it unchanged. Reusing it would couple unrelated host chrome to exchange status. |

### Size map against hard limits

| File or function | Current size | Consequence |
| --- | ---: | --- |
| `packages/contract/src/overlay/wire.ts` | 158 lines | No change required. |
| `packages/overlay/src/server/overlayRouter.ts` | 35 lines | Preserve. |
| `packages/overlay/src/server/overlayRouter.test.ts` | 127 lines | Rerun only. |
| `packages/overlay/src/gatewayDeps.ts` | 52 lines | Preserve. |
| `packages/overlay/src/service/OverlaySyncService.ts` | 185 lines; largest method about 30 | Preserve. |
| `packages/gateway/src/main.ts` | 385 lines | Preserve wiring. |
| `packages/gateway/src/main.test.ts` | 569 lines | Rerun named tests. |
| `packages/runtime/src/service/RunManager.ts` | 690 lines | Ten lines of headroom. Avoid edits. |
| `api/src/transport_matters/api/v1/run_proxy.py` | 626 lines; `create_run_proxy_mount` about 92 | One small route remains below 700 and the function remains below 150. |
| `api/src/transport_matters/api/v1/test_run_proxy.py` | 393 lines | Add one focused test here. |
| `api/src/transport_matters/overlay_cache.py` | 675 lines | Avoid edits. |
| `www/packages/core/src/transport.ts` | 530 lines | Small fetch addition remains below 700. |
| `www/packages/core/src/queryKeys.ts` | 102 lines | Add one key here. |
| `www/packages/inspector/src/components/ExchangeDetail.tsx` | 474 lines; `ExchangeDetail` about 266 | Decompose first. File remains below 700. |
| `www/packages/inspector/src/components/ExchangeDetail.test.tsx` | 730 lines | Hard limit already exceeded. Do not edit. Add a focused test file. |
| `www/packages/inspector/src/inspector.css` | 821 lines | Hard limit already exceeded. Do not edit. Reuse present classes. |
| `www/packages/canvas/src/viewers/resource/ArkExchangePanels.tsx` | 281 lines; `ExchangeInspectPanel` about 86 | Safe owner for a small status block. |
| `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx` | 328 lines | No source change required. |
| `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.test.tsx` | 279 lines | Existing coverage remains reusable, but a new focused status file gives a smaller review surface. |
| `www/packages/canvas/src/viewers/resource/exchange-viewer.css` | 500 lines | Reuse existing chip rules. |

## Plan

### 1. Write RED proofs first

Add focused tests before source changes:

1. `test_canvas_origin_reaches_overlay_status_gateway` in `test_run_proxy.py`. Start the real test Gateway, request `/v1/overlays/status` through `create_app`, and assert `200` plus the sanitized `{"items": []}` response. Current result is 404.
2. `www/packages/core/src/overlayStatus.test.tsx`. Assert the exact transport path, shared query key, pending interval behavior, server order preservation, every contract mode, every contract reason, null reason, and `VERIFIED / account_unavailable` without mode rewriting.
3. `www/packages/inspector/src/components/ExchangeDetail.overlayStatus.test.tsx`. Reuse `components/__test-utils__/exchangeDetail.ts:makeExchangeDetail` and `@tm/core/testing`. Assert exact release, mode, and reason are visible; empty and failed status reads leave the exchange usable.
4. `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.overlayStatus.test.tsx`. Reuse the existing exchange fixture and mock transport. Assert `ExchangeInspectPanel` shows the same descriptor in normal and fullscreen inspect views, and status failure does not replace exchange content.

Run the four tests and record their failures before implementation.

### 2. Open the existing browser origin seam

Add `@router.get("/overlays/status")` inside `create_run_proxy_mount`. Delegate directly to `proxy.forward_http(request)`. Use the same GET posture as list and read routes. Do not introduce a second client, DTO, timeout, or error mapper.

### 3. Add one shared browser status owner

1. Add `overlayStatusesKey` to `queryKeys.ts`.
2. Add `fetchOverlayStatuses()` to `transport.ts`, returning the contract `OverlayStatusResponse` from `/v1/overlays/status`.
3. Add `overlayStatus.ts` with `useOverlayStatuses`, a pure pending poll decision, and a pure total presenter. The hook uses `retry: false` so an advisory status failure cannot become a competing error surface.
4. Export the new owner from `@tm/core`.

No server context import belongs in browser code.

### 4. Decompose Inspector, then bind the chip

Extract `ExchangeDetailHeader` and `ExchangeDetailTabBank` from `ExchangeDetail.tsx`, preserving markup and tests. Confirm the main function falls below 150 lines. Then call the shared hook in `ExchangeDetail` and pass descriptors into the header. Render with the existing chip or telemetry classes and product local tone mapping. Add no Inspector CSS.

### 5. Bind Canvas at the named owner

Call the same hook from `ExchangeInspectPanel` and render the descriptors before the curated request note using `.canvas-exchange__chips` and `.canvas-exchange__chip`. Map semantic tones to existing `data-tone` values. Because normal and fullscreen inspect both render this component, there is one Canvas status implementation. Add no Canvas to Inspector import and no Canvas CSS.

### 6. Pull visual UAT ahead

Before broad hardening, open one exchange in Inspector and Canvas against the same seeded current status. Confirm both show identical release, mode, and reason; the chip remains readable at narrow and fullscreen sizes; `VERIFIED / account_unavailable` is not styled or worded as passthrough; and no pause, breakpoint, or application behavior appears in Canvas.

### 7. GREEN verification

Focused commands:

```bash
cd api && uv run python -m pytest -n0 src/transport_matters/api/v1/test_run_proxy.py::test_canvas_origin_reaches_overlay_status_gateway -q

pnpm --filter @tm/shell exec vitest run --project jsdom \
  ../core/src/overlayStatus.test.tsx \
  ../inspector/src/components/ExchangeDetail.overlayStatus.test.tsx \
  ../canvas/src/viewers/resource/ArkExchangeViewer.overlayStatus.test.tsx

pnpm --filter @tm/shell exec vitest run --project node \
  src/testSupport/importGraphBoundary.test.ts \
  src/testSupport/depLint.test.ts

pnpm --filter @tm/contract test -- src/overlay/overlay.test.ts
pnpm --filter @tm/overlay test -- src/server/overlayRouter.test.ts src/service/OverlaySyncService.test.ts
pnpm --filter @tm/runtime test -- src/service/RunManagerOverlayRefresh.test.ts
pnpm --filter @tm/gateway test -- src/app.test.ts src/main.test.ts
```

Slice gates after focused GREEN:

```bash
just test-affected b8e30eb0
just check
just test
just build
git diff --check
```

CI remains the merge verdict. The implementation is complete only when the repo diff contains no application or composition path, all new files remain below 700 lines, all touched functions remain below about 150 lines, both product chips are visually judged, and exact head gates pass.

## Scout verification

No repo files were changed and no runtime tests were run during this scout. Source, tests, package instructions, architecture, warroom process, both supplied warroom analyses, and the slice 7 human state specification were read at the exact base above.
