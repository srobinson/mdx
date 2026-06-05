---
title: Short ID UX Implementation
type: sessions
tags: [backend, littleorgans, short-id, typed-ids, session]
summary: Implemented adaptive short session id display and prefix based session selection.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary

Implemented short id UX item 1/1 on `refactor/typed-ids-v4` in commit `783b4a6`.

Key decisions:

- Human display uses `SessionId::short_with` and the existing 7 character floor from `lilo-common`.
- Prefix selection uses `Selector::Prefix { prefix }` with a separate 4 character input floor.
- Store side validation is the authoritative boundary because selectors also cross daemon and MCP JSON paths.
- `lilo get session` and `lilo mail peek` are the only human surfaces shortened. JSON, storage, wire payloads, process args, logs, and ordinary `Display` remain full 36 character UUIDs.

Reviewer `littleorgans:helioy-tools:backend-engineer:5:2.1` signed off with `S|B`. The branch was pushed after sign off.

## API Contract

No external HTTP API changed.

Session selector contract changed in `lilo-session-core`:

```rust
pub enum Selector {
    Id { id: SessionId },
    Prefix { prefix: String },
    Label { key: String, op: LabelOp },
    Namespace { namespace: Namespace },
    Dir { path: PathBuf },
    And { selectors: Vec<Selector> },
    Role { name: String },
    All,
}
```

CLI and MCP selector grammar now documents `<uuid-or-prefix>`.

Human output contract:

- `lilo get session` renders session ids as shortest unique prefixes with a 7 character floor.
- `lilo mail peek` renders recipient session ids the same way.
- JSON output continues to emit full UUID strings.

Selection contract:

- Bare full UUID parses as `Selector::Id`.
- Bare lowercase hex or hyphen prefix parses as `Selector::Prefix` when at least 4 characters.
- Prefixes shorter than 4 characters fail fast in the parser and are also rejected in the store.
- Ambiguous prefixes return a store error listing full candidate ids.

## Database Changes

No schema migration.

Store query change:

```sql
SELECT * FROM session_sessions
WHERE id LIKE ? || '%'
ORDER BY created_at
```

The query is parameterized. Before query execution, the store rejects prefixes shorter than 4 characters and any character outside `[0-9a-f-]`, preventing `%` and `_` LIKE wildcard abuse from deserialized selector payloads.

Old UUIDv7 rows and new UUIDv4 rows coexist because prefix matching operates on the stored UUID text representation.

## Security Considerations

- Store side validation is the choke point for CLI, daemon wire, and MCP JSON selectors.
- Parser validation remains a UX fast fail only.
- Prefix query uses bind parameters and rejects LIKE metacharacters before query execution.
- Ambiguity errors list candidate full ids only after a valid prefix passes floor and charset validation.

## Performance Notes

- Display shortening uses one batched session list snapshot for a render pass, not one count query per row.
- The uniqueness predicate counts matches in memory and includes the id itself, so uniqueness means `count == 1`.
- No N plus 1 database queries were added for `lilo get session` or `lilo mail peek` display.
- Existing line caps were preserved: `output.rs` 587 LOC and `sessions.rs` 482 LOC after the change.

Verification:

- `just check` passed.
- `just build` passed.
- `just test` passed, 686 of 686 tests.
- `fmm generate && fmm validate` passed, 384 files indexed and up to date.

## Open Items

Non blocking reviewer follow up: namespace scoped selectors currently apply prefix ambiguity globally before retaining by namespace in `Selector::And`. A prefix that is unique in the active namespace but collides globally errors as ambiguous and lists candidates from other namespaces. This matches global display uniqueness today. If namespace scoped short ids are desired later, evaluate ambiguity after namespace retain and scope the display id snapshot the same way.
