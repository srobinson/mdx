---
title: Recall FTS Precision Implementation
type: sessions
tags: [backend, fts, sqlite, recall, context-matters]
summary: Rebuilt FTS with exact unicode61 tokenization and added recall auto-prefix behavior without changing explicit search syntax.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented PR #84 on branch `feat/recall-fts-precision` at commit `375ff12`.

Key decisions:

- Rebuilt `entries_fts` with exact `unicode61` tokenization to prevent Porter stemming collisions such as `vps` matching `vp` and `ios` matching `io`.
- Preserved the existing contentless FTS table shape, rowid mapping, JSON tag extraction, sync triggers, and backfill behavior from the post-004 schema.
- Added `FtsQuery::recall_auto_prefix` and wired it into the existing `cx_recall` Prefix tier.
- Kept `cx_search` on the explicit `FtsQuery::new` constructor so user supplied FTS syntax remains unchanged.

## API Contract

No wire schema changes.

Behavioral contract:

```typescript
// cx_recall query behavior
interface RecallFtsBehavior {
  exactTier: "uses sanitized explicit query";
  prefixTier: {
    minPrefixChars: 3;
    multiTermSemantics: "AND";
    quotedPhrases: "preserved literally";
    existingStar: "preserved without double-prefixing";
    shortTerms: "one and two character terms stay exact";
  };
  splitOrTier: "unchanged fallback";
}

// cx_search query behavior
interface SearchFtsBehavior {
  explicitSyntax: "preserved"; // e.g. migrat*, quoted phrases, AND, OR, NOT
}
```

## Database Changes

Added reversible migration files:

- `crates/cm-store/migrations/007_rebuild_fts_unicode61.up.sql`
- `crates/cm-store/migrations/007_rebuild_fts_unicode61.down.sql`

The up migration performs:

1. Drop `entries_fts_insert`, `entries_fts_delete`, and `entries_fts_update`.
2. Drop `entries_fts`.
3. Recreate `entries_fts(title, body, tags, content='', tokenize='unicode61')`.
4. Recreate sync triggers with the same rowid and JSON tag extraction shape.
5. Backfill all existing entries into the rebuilt FTS index.

The down migration restores `tokenize='porter unicode61'` using the same trigger and backfill shape.

## Security Considerations

- No new external input surfaces.
- FTS query construction continues to sanitize user input before passing it to SQLite `MATCH`.
- All SQL execution paths continue to use sqlx query APIs with bound values for runtime queries.
- Migration SQL is static and does not interpolate user input.

## Performance Notes

- Query execution remains on the existing FTS5 virtual table and ancestor walk path.
- Prefix expansion is limited to sanitized terms with at least three characters to avoid broad one and two character scans.
- Multi-term recall auto-prefix keeps implicit AND semantics to avoid widening result membership.
- Full workspace validation passed:
  - `cargo clippy --workspace --all-targets -- -D warnings`
  - `just test`
  - `just build`

## Open Items

- Monitor production or real corpus recall for any useful stemming cases lost by dropping Porter.
- If future recall needs broader linguistic matching, add it as an explicit query expansion layer rather than tokenizer stemming that changes membership unexpectedly.
