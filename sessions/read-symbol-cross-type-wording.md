---
title: Read Symbol Cross Type Wording
type: sessions
tags: [backend, fmm, read-symbol, diagnostics]
summary: Tightened cross type missing member diagnostics to use owner.member wording across CLI and MCP surfaces.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented the item 17 cross type wording fix for `read_symbol` missing member diagnostics. The diagnostic now renders owner qualified member hints in the form `ServerState.spawn (field of type SpawnCoordinator)` instead of the previous prose sentence. The change was committed as `060b415df5b0a6a14a0d726b6dbb2d510d570ce3` and pushed to `origin/nancy/ALP-2707` after Phase B signoff.

## API Contract

No HTTP API endpoints changed.

Observable CLI and MCP diagnostic contract:

```text
Cross-type: ServerState.spawn (field of type SpawnCoordinator).
```

Multiple suggestions keep the same semicolon separated structure with each suggestion rendered as:

```text
Owner.member (field of type RelatedType)
```

## Database Changes

None.

## Security Considerations

No authentication, authorization, input validation, or persistence behavior changed. This was a diagnostic formatting only change.

## Performance Notes

No runtime lookup behavior changed. The implementation only changed formatting of already collected cross type suggestions and renamed the local member label helper from article based wording to noun based wording.

Verification completed before push:

```text
fmm validate
just check
just test
```

Results:

```text
fmm validate: all 410 files indexed and up to date
just check: passed
just test: 1259 passed, 3 skipped, doctests ok
```

## Open Items

None for this item.
