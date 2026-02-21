---
title: ALP-2707 Cross Type Lookup Implementation
type: sessions
tags: [backend, fmm, alp-2707, read-symbol, diagnostics]
summary: Implemented composition-aware cross-type hints for read_symbol missing member errors.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented Tier 3 cross-type lookup for `read_symbol` missing member diagnostics on `nancy/ALP-2707`.

Commit `5aacd31 feat(cli): add cross-type member hints` was pushed to `origin/nancy/ALP-2707` after Phase A and Phase B reviewer sign-off.

Key decision: use existing store and manifest metadata rather than adding schema or resolver work. The existing `method_metadata` field signatures and `declaration_kind` values are sufficient for an error-path composition-aware scan.

## API Contract

No external API contract changed.

Affected CLI/MCP diagnostic text for missing members now includes an optional cross-type section between did-you-mean suggestions and member listings:

```text
Cross-type: 'spawn' is a field on ServerState (type SpawnCoordinator).
```

The section appears only when matching cross-type composition evidence exists. Suggestions are capped at two.

## Database Changes

No schema migration.

Audit findings:

- No global `(name, kind) -> owning types` index exists.
- No structured resolved field-type column exists.
- Existing `methods` table metadata includes `signature`, `visibility`, and `declaration_kind`.
- Existing manifest data exposes this through `FileEntry.method_metadata`.

## Security Considerations

No new input boundary or external data source was introduced.

The implementation uses existing parsed metadata and performs deterministic string token matching. It does not execute user supplied content or construct shell commands.

## Performance Notes

The cross-type scan runs only on missing-member error paths. It scans indexed member metadata, filters to field declarations, compares member names exactly, and performs token-level signature matching.

Noise controls:

- Composition-aware only, not generic any-type suggestions.
- Full-token type matching prevents prefix false positives such as `SpawnCoordinatorFactory` matching `SpawnCoordinator`.
- Cap of two suggestions.
- Owner fields in the queried type file sort first, followed by stable owner/member/hint tiebreakers.

Verification run:

```text
just check && just build && just test
```

Result:

```text
1258 tests run: 1258 passed, 3 skipped
```

Manual smoke confirmed:

```text
Cross-type: 'spawn' is a field on ServerState (type SpawnCoordinator).
```

Prefix-collision smoke with `SpawnCoordinatorFactory` emitted no `Cross-type:` line.

## Open Items

- `CrossTypeSuggestion.kind` is currently always `Field` because the composition scan filters to `declaration_kind == "field"`. This is acceptable as an extensibility hook and was accepted as non-blocking in Phase B review.
- A global member index or structured resolved field-type metadata may be useful later if cross-type lookup moves beyond error-path ergonomics.
