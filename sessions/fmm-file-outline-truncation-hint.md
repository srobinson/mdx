---
title: FMM file outline truncation hint
type: sessions
tags: [backend, fmm, mcp, tool-contracts, truncation]
summary: Added a real fmm_file_outline truncate escape hatch and gated truncation hints by tool support.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented and pushed commit `8fc1eea` on branch `nancy/ALP-2707` to fix the `fmm_file_outline` truncation hint defect. The MCP response cap previously emitted a shared hint that told callers to use `truncate: false` even when the active tool did not accept that parameter. The fix adds an MCP-only `truncate` parameter for `fmm_file_outline` and gates the shared hint by actual tool support.

Phase A and Phase B reviewer signoff were received. Phase B signoff used the exact phrase: `I sign off on the truncation-hint fix as currently filed`.

## API Contract

Changed MCP tool contract:

```typescript
interface FmmFileOutlineRequest {
  file: string;
  include_private?: boolean;
  truncate?: boolean; // default true. false bypasses the 10KB MCP response cap.
}
```

Supported truncation bypass tools now share one gate:

- `fmm_file_outline`
- `fmm_read_symbol`
- `fmm_glossary`

Capped supported tools emit:

```text
[Truncated — showing {shown}/{total} lines. Use truncate: false to get the full response.]
```

Capped unsupported tools emit no phantom parameter hint:

```text
[Truncated — showing {shown}/{total} lines.]
```

No REST or GraphQL endpoints changed.

## Database Changes

No database schema, migration, or index format changes were made.

## Security Considerations

No authentication or authorization surfaces changed. The change tightens tool contract correctness by preventing clients from receiving invalid parameter guidance. The default 10KB response cap remains in place for all MCP tools. Full outline responses require explicit `truncate: false` opt in on a tool that supports it.

## Performance Notes

No cap size or truncation algorithm changes were made. Default behavior remains capped to prevent oversized MCP responses. `fmm_file_outline` can now return a full outline only when the caller explicitly opts in.

Verification completed before push:

- `just check`
- `just test`: 1219 tests passed, 3 skipped
- `fmm validate`: 407 files indexed and up to date
- `git diff --check`
- `git push`: `d627dcf..8fc1eea  nancy/ALP-2707 -> nancy/ALP-2707`

## Open Items

No open implementation items for this slice. If future tools need full response bypasses, add the parameter deliberately and include them in the shared support gate so behavior and hint text cannot drift.
