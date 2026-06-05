---
title: Runtime Home Credential Symlinks
type: sessions
tags: [backend, runtime-home, credentials, transport-matters]
summary: Runtime overlays now symlink rotating credentials from native auth sources.
status: active
source: backend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 2 credential handling for runtime home overlays on branch `feat/runtime-home-slice2` in PR #119. Codex `auth.json` and Claude `.credentials.json` now materialize as symlinks from the native auth source when present. Missing native credentials are skipped without falling back to template or content credentials.

Key decision: rotating credentials are special overlay material, not copied local config. Content config still comes from the content source. Codex hook trust relocation keeps the content source by passing an internal hook trust source through the seeder environment while `CODEX_HOME` points at the native auth source for credential handling.

## API Contract

No public API contract changes.

## Database Changes

No database changes or migrations.

## Security Considerations

- Runtime overlays reference live native credentials by symlink, so token refresh writes through to the native file and survives overlay teardown.
- Template or content credentials are never copied into the overlay when a native auth source is provided.
- If the native credential file is absent, overlay creation skips the link without error and does not synthesize a credential.
- Teardown uses normal runtime root removal, which unlinks credential symlinks without following them into the native credential file. Tests assert the native file remains present after teardown.

## Performance Notes

No material performance impact. Credential materialization is one file existence check and symlink creation per credential candidate.

## Validation

- Fail first: focused credential tests failed before implementation because Codex copied `auth.json`, Claude `.credentials.json` linked from content, absent native credentials fell back to content, and teardown tests had no symlink to verify.
- Passing focused check: `cd api && uv run python -m pytest src/transport_matters/cli/test_home_seed_credentials.py -q`, 5 passed.
- Quality check: `cd api && just check`, passed.
- Gate: `cd api && just test`, 1396 passed.

## Open Items

None for this slice. Future template secret rejection remains owned by the later materialization policy slice.
