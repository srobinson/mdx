---
title: Circular Annotation Mod Hierarchy Fix
type: sessions
tags: [backend, fmm, rust, dependency-graph]
summary: Retagged direct Rust module hierarchy overlaps in dependency graph text output as mod hierarchy instead of circular.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented `3e7b12b fix: label rust mod hierarchy in dependency graphs` on `nancy/ALP-2707` and pushed it to origin after Phase B reviewer signoff.

The dependency graph formatter now distinguishes direct Rust module hierarchy links from real cycles. When a downstream path is also upstream or local, direct Rust mod parent-child relationships render as `# mod-hierarchy`; other overlaps keep `# circular`.

## API Contract

No API contract changes.

Human text output changed for `fmm deps` and MCP dependency graph text formatting. JSON output and graph data remain unchanged.

Before:

```text
downstream:
  - crates/rtm-core/src/lib.rs  # circular
```

After:

```text
downstream:
  - crates/rtm-core/src/lib.rs  # mod-hierarchy
```

## Database Changes

No schema or migration changes.

## Security Considerations

No security-sensitive changes. The fix is formatting-only and does not alter index persistence, query permissions, or input handling.

## Performance Notes

The added path relationship check is in text formatting only. It performs simple path component operations for entries already selected for output. No database or graph traversal cost changed.

## Open Items

The heuristic is intentionally direct-only. A transitive grandchild module relationship can still show `# circular` in broader outputs. Reviewer accepted this as out of scope for the road-test defect.
