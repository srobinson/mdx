---
title: Transcript Canvas Slice 7 Resource Content Endpoint
type: sessions
tags: [backend, transport-matters, transcript-canvas, api, resources]
summary: Implemented owner scoped session resource content endpoint with required public exchange redirect routes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Summary

Implemented PR #57 on branch `feat/transcript-canvas-slice-7`.

Commits:

- `0d009c0` added `GET /api/sessions/{session_id}/resources/{resource_id}`.
- `493507a` completed the fix round for wire redirect semantics, exchange route sharing, and exchange id correlation DRY cleanup.
- `41b1593` moved exchange redirect HTTP route composition into `api/v1` to preserve the session import DAG.
- `f3ee62c` restored `ExchangeRedirectResponse.route` as a required public string while using an internal session redirect descriptor with no HTTP route.

The backend exposes `GET /api/sessions/{session_id}/resources/{resource_id}` under the existing owner scoped session API. The route verifies the session with `_require_session`, then resolves resource ids through a dedicated resolver module.

Key decisions:

- Keep the route thin in `api/src/transport_matters/api/v1/session_routes.py`.
- Put the typed Pydantic union contract in `api/src/transport_matters/session/resource_content_models.py`.
- Put resolver logic and parameterized Postgres queries in `api/src/transport_matters/session/resource_content.py`.
- Return structured wire redirects instead of duplicating exchange payloads.
- Share exchange detail route construction through `exchange_detail_route` in the `api/v1` route handler rather than hardcoding `/api/exchanges/{id}` inside the session resolver.
- Keep `api/src/transport_matters/session/resource_content.py` free of `api.v1` imports. The session resolver returns an internal exchange redirect descriptor with exchange id plus initial view, and the API handler fills the required HTTP route on the public response.
- Share exchange id correlation shapes through `api/src/transport_matters/session/exchange_correlation.py` so the timeline projector and resource resolver use the same probe definitions.
- Treat unsupported future schemes as typed missing resources rather than bare errors.

## API Contract

```text
GET /api/sessions/{session_id}/resources/{resource_id}
```

Query parameters:

```text
owner=local
range_start=<integer>
range_end=<integer>
include_debug=false
```

Response union:

```python
ResourceContentResponse = Annotated[
    TextContentResponse
    | ImageContentResponse
    | BinaryContentResponse
    | JsonContentResponse
    | ExchangeRedirectResponse
    | MissingResourceResponse,
    Field(discriminator="kind"),
]
```

Supported resource ids in this slice:

- `inline:<artifact_hash>` resolves through `event_artifact` plus `artifact`, scoped to the selected session and owner.
- `native:<session_id>:<seq>` resolves to native record JSON only when the id session matches the route session.
- `wire:<exchange_id>` resolves to a public `exchange-redirect` after confirming the exchange id is correlated in `event.ir` for the selected session. The session layer supplies an internal descriptor with `exchangeId` and `initialView`; the `api/v1` handler constructs `ExchangeRedirectResponse` with required `route: exchange_detail_route(exchange_id)`.
- `wire:<exchange_id>` with no owned session correlation returns typed missing reason `uncorrelated`.
- `raw-provider:<exchange_id>` returns typed missing `debug-unavailable` unless debug mode is requested. Debug raw byte delivery remains unimplemented.
- Future schemes such as `tool-output` return typed missing `unsupported`.

## Database Changes

No migrations were added.

The endpoint uses existing tables:

- `session` for owner scope.
- `event` for native records and wire correlation checks.
- `event_artifact` plus `artifact` for inline artifact bytes and media metadata.

All SQL added in this slice is parameterized.

## Security Considerations

- The route requires the selected session to belong to the requested owner before resolving any resource.
- `native:<session_id>:<seq>` rejects ids whose embedded session id does not match the route session.
- `inline:<artifact_hash>` only resolves artifacts linked to the selected session.
- `wire:<exchange_id>` only returns a redirect after the exchange id is found in the selected session's owned `event.ir` correlation data.
- Raw provider debug bytes are not exposed by default. The default response for `raw-provider` is typed missing `debug-unavailable`.
- Unsupported ids do not produce bare 500 responses.

## Performance Notes

- Inline lookup is a single indexed join over `event_artifact`, `artifact`, and `session` with a limit of one.
- Native lookup is a direct session plus seq lookup.
- Wire lookup uses JSONB containment checks over the existing `event.ir` field and returns only the first matching event seq.
- Text content is capped to a 64 KiB window by default and supports `range_start` plus `range_end`.
- Image and binary inline responses have explicit 1 MiB caps. Oversized inline binary or image content returns typed missing `too-large`.

## Verification

Fail first targeted tests initially failed because the endpoint did not exist. The fix round fail first pass failed on missing `exchange_detail_route` and missing shared `exchange_correlation`, which proved the added tests covered the requested changes.

Verification completed after the fix round:

```text
TRANSPORT_MATTERS_TEST_DATABASE_URL="postgresql://$(whoami)@localhost/postgres" api/.venv/bin/python -m pytest api/src/transport_matters/api/v1/test_session_resource_content.py api/src/transport_matters/session/test_timeline.py -q
```

Result after the first fix round: 46 passed.

The route layering re-fix added a fail first test that failed while `session/resource_content.py` imported `transport_matters.api.v1.exchanges`, then passed after moving route composition into `api/v1/session_routes.py`.

```text
TRANSPORT_MATTERS_TEST_DATABASE_URL="postgresql://$(whoami)@localhost/postgres" api/.venv/bin/python -m pytest api/src/transport_matters/api/v1/test_session_resource_content.py::test_session_resource_content_layer_does_not_import_api_v1 api/src/transport_matters/api/v1/test_session_resource_content.py::test_wire_resource_content_redirects_without_payload_duplication -q
```

Result after the route layering re-fix: 2 passed.

```text
cd api && just ci
```

Result after the first fix round: ruff format check passed, ruff check passed, mypy passed, and 1234 pytest tests passed.

Route layering re-fix result: ruff format check passed, ruff check passed, mypy passed, and 1235 pytest tests passed. `rg "transport_matters\\.api\\.v1|api\\.v1" api/src/transport_matters/session -n` returned no matches.

The public contract re-fix added a fail first validation test proving `ExchangeRedirectResponse.route` was optional, then restored it to required `str` and introduced `ExchangeRedirectDescriptor` as the session internal return type.

```text
TRANSPORT_MATTERS_TEST_DATABASE_URL="postgresql://$(whoami)@localhost/postgres" api/.venv/bin/python -m pytest api/src/transport_matters/api/v1/test_session_resource_content.py::test_exchange_redirect_response_requires_non_null_route api/src/transport_matters/api/v1/test_session_resource_content.py::test_session_resource_content_layer_does_not_import_api_v1 api/src/transport_matters/api/v1/test_session_resource_content.py::test_wire_resource_content_redirects_without_payload_duplication -q
```

Result after the public contract re-fix: 3 passed.

Final public contract re-fix result: ruff format check passed, ruff check passed, mypy passed, and 1236 pytest tests passed. `rg "transport_matters\\.api\\.v1|api\\.v1" api/src/transport_matters/session -n` returned no matches.

## Open Items

- File current, file captured, and tool output resource content remain future slices.
- Raw provider debug delivery remains unimplemented by design for this slice.
- The wire redirect route assumes the existing exchange detail endpoint owns payload rendering.
