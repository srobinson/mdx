---
title: API v1 Route Helpers Consolidation
type: sessions
tags: [backend, api, dry, refactor]
summary: Consolidated duplicated API v1 response, not found, and cursor helpers into one shared module.
status: active
source: backend-engineer
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

## Summary

Implemented branch `refactor/api-v1-route-helpers` and commit `a0e1b10`.

Consolidated the duplicated API v1 helper definitions from `run_routes.py`, `session_routes.py`, and `space_routes.py` into `api/src/transport_matters/api/v1/responses.py`. The shared module now owns:

- `response_payload`
- `raise_not_found`
- `encode_cursor`
- `decode_cursor`

The initial scout found 11 local definitions across 3 modules: 3 response payload helpers, 2 not found helpers, 3 cursor encoders, and 3 cursor decoders. Cursor helpers had endpoint variation, so the shared cursor helpers parameterize filtered cursors and padding behavior instead of flattening the variants.

## API Contract

No public API contract changed. Endpoint request shapes, response envelopes, cursor strings, and machine readable error codes remain the same.

Affected route families:

- `GET /v1/runs`
- `GET /v1/sessions`
- `GET /v1/spaces`
- Run, session, space, worktree, and canvas mutation response serialization that already used the local helpers

## Database Changes

None.

## Security Considerations

Invalid cursors still return the existing `invalid_cursor` machine error through the shared `raise_api_error` path. Not found responses now share the same 404 helper while preserving the existing codes and messages.

No new inputs, permissions, secrets, or persistence surfaces were introduced.

## Performance Notes

The change is a pure route helper refactor. Cursor encode and decode still use JSON plus URL safe base64. Response serialization still delegates to Pydantic `model_dump`.

File sizes after refactor:

- `responses.py`: 67 lines
- `run_routes.py`: 639 lines
- `session_routes.py`: 522 lines
- `space_routes.py`: 462 lines

Verification completed:

- Duplicate definition grep returned zero local definitions for `_response_payload`, `_not_found`, `_encode_cursor`, and `_decode_cursor`
- Focused API route tests: 47 passed
- `just check`: passed
- `just test`: 1749 API tests plus desktop and web tests passed through the root recipe

## Open Items

None.
