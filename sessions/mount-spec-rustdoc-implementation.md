---
title: MountSpec Rustdoc Implementation
type: sessions
tags: [backend, rust, docs, runtime-matters, mount]
summary: Documented the public MountSpec parsing contract and added a compiling doctest.
status: active
source: backend-engineer
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Summary

Implemented the mount documentation batch item on `refactor/expose-mount-parser` and committed it as `0221e09` with title `docs(rtm-core): document --mount syntax for MountSpec consumers`.

Key decisions:

- Kept parser behavior unchanged.
- Documented `HOST:CONTAINER[:ro|:rw]` on the `FromStr for MountSpec` implementation as the canonical grammar location.
- Cross referenced the parser docs from `MountSpec` and `expand_mount_source` instead of duplicating the full grammar.
- Added a platform safe doctest using `/host/config:/container/config:rw`.
- Removed two redundant rustdoc link targets in `crates/rtm-core/src/lib.rs` so the required `cargo doc` smoke run is warning free.

## API Contract

No HTTP API changes.

Public Rust contract documented:

- `MountSpec`
- `MountSpec.source`
- `MountSpec.target`
- `MountSpec.read_only`
- `MountSpecParseError` and all variants
- `impl FromStr for MountSpec`
- `expand_mount_source`

The documented parser contract is:

```text
HOST:CONTAINER[:ro|:rw]
```

Behavior covered in rustdoc:

- Omitted mode defaults to read only.
- `ro` maps to `read_only = true`.
- `rw` maps to `read_only = false`.
- `~` and `~/sub` expansion applies only to the host source.
- `~foo` keeps the existing fallback behavior for compatibility.
- Container targets remain literal and are never tilde expanded.
- Four or more colon separated fields are rejected as `UnknownMode`.
- Host isolation checks are owned by CLI consumers, not the core parser.

## Database Changes

None.

## Security Considerations

The documentation explicitly preserves the security boundary: `rtm-core` parses the shared mount shape, while CLI consumers remain responsible for host isolation rejection before spawn submission.

## Performance Notes

No runtime behavior changed. The diff is documentation only plus one doctest.

Verification run:

```text
cargo test -p lilo-rm-core
cargo doc -p lilo-rm-core --no-deps
fmm generate && fmm validate
```

All checks passed. `spawn.rs` is 466 LOC, below the 700 LOC project limit.

## Open Items

- Sent `C|3|0221e09|...` to `runtime-matters:general:3:2.1` on topic `i3-mount-docs`.
- Branch is ahead one commit and waiting for `S|B` before push.
