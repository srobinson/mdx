---
title: Typed ID Foundation Implementation
type: sessions
tags: [backend, typed-ids, rust, lilo-common]
summary: Implemented and pushed the lilo-common typed id foundation with UUIDv4 constructors, transparent serde, optional sqlx support, and prefix helpers.
status: active
source: backend-engineer
confidence: high
created: 2026-06-03
updated: 2026-06-03
---

## Summary

Implemented item 1 of the typed id and UUIDv4 sequence on branch `refactor/typed-ids-v4`.

Commit: `c108d15` (`feat(lilo-common): add typed id foundation`).

Remote: `origin/refactor/typed-ids-v4`.

Review state:

- Reviewer `littleorgans:superpowers:code-reviewer:5:3.1` signed Phase B with `S|1|c108d15`.
- Sent `P|1|refactor/typed-ids-v4|c108d15` after pushing.
- Reviewer acknowledged `P|1` and closed item 1 from the review side.

Key decisions:

- Added `crates/lilo-common/src/id.rs` and exported it from `crates/lilo-common/src/lib.rs`.
- Added `define_id!` as the single macro source for the typed id family.
- Added six newtypes: `SessionId`, `MessageId`, `EventId`, `IntentId`, `NamespaceId`, and `AuditId`.
- Kept full 36 character hyphenated `Display` and `FromStr` semantics.
- Implemented `new()` with `Uuid::new_v4()` and no `Default` implementation.
- Added `#[allow(clippy::new_without_default)]` on the generated impl block.
- Added explicit `from_uuid`, `as_uuid`, and `into_uuid` methods. No blanket `From<Uuid>` was added.
- Added adaptive prefix helper logic over the hyphenated Display form with a 7 character floor.
- Updated workspace `uuid` features to additive `serde`, `v4`, and `v7`.
- Added optional `lilo-common/sqlx` support using `#[sqlx(transparent)]` behind the feature.

## API Contract

No HTTP, GraphQL, CLI, or wire API endpoint was added in this item.

Rust surface contract:

```rust
lilo_common::define_id!(TypeName);

impl TypeName {
    pub fn new() -> Self;
    pub const fn from_uuid(uuid: uuid::Uuid) -> Self;
    pub const fn as_uuid(&self) -> uuid::Uuid;
    pub const fn into_uuid(self) -> uuid::Uuid;
    pub fn short(&self) -> String;
    pub fn short_with<F>(&self, is_unique: F) -> String
    where
        F: FnMut(&str) -> bool;
}
```

Generated type guarantees:

- `Clone`, `Copy`, `PartialEq`, `Eq`, `Hash`, `PartialOrd`, and `Ord`.
- `serde(transparent)` with JSON encoded as a bare UUID string.
- `Display` emits the full hyphenated UUID.
- `FromStr` parses a full UUID string.
- Optional `sqlx::Type` derives under the `sqlx` feature.

## Database Changes

No schema migration was added.

The optional sqlx implementation is transparent over `uuid::Uuid` and is feature gated behind `lilo-common/sqlx`. The unit test proves an in-memory SQLite insert and select roundtrip for `SessionId` under that feature.

## Security Considerations

- Type discipline prevents accidental cross use of session, message, event, intent, namespace, and audit ids.
- `Default` is intentionally absent because a random default id would make implicit generation possible through `or_default`, derive paths, or collection helpers.
- Full id display remains unchanged so storage, wire, process arguments, and audit surfaces are not silently truncated.
- Prefix output is a human convenience only. Store backed uniqueness remains deferred to the later selector item.

## Performance Notes

- `shortest_unambiguous_prefix` checks candidate prefixes from the 7 character floor through the full hyphenated id length.
- The helper is pure and allocation free. `short` and `short_with` allocate only the full Display string and returned prefix string.
- The new module is 204 lines, below the 700 line file limit.
- All functions are below the 150 line threshold.

## Verification

Commands run before sending `C|1|c108d15`:

```bash
cargo build -p lilo-common
cargo build -p lilo-common --features sqlx
cargo test -p lilo-common
cargo test -p lilo-common --features sqlx
just check
just build
just test
fmm generate && fmm validate
```

Results:

- `cargo test -p lilo-common`: 17 passed.
- `cargo test -p lilo-common --features sqlx`: 18 passed.
- `just test`: 683 passed, 0 skipped.
- `fmm validate`: all 383 files indexed and up to date.
- `git status --short --branch`: `## refactor/typed-ids-v4...origin/refactor/typed-ids-v4` with no dirty files.

Reviewer independent verification:

- Clippy `-D warnings` passed with and without `--features sqlx`.
- `cargo test -p lilo-common`: 17 passed.
- `cargo test -p lilo-common --features sqlx`: 18 passed.
- `id.rs`: 204 LOC.

## Open Items

- Item 1 is closed from the review side.
- Later items still need the session, runtime, and identity call site sweeps.
- Store backed adaptive display and prefix selection remain deferred to item 5.
- Carry forward the reviewer macro hygiene note for item 2: because `define_id!` is currently `#[macro_export]`, downstream invocations should either fully qualify macro body paths or the macro should become crate internal if the family stays closed in `lilo-common`.
