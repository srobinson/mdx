---
title: Dry fix config identity refactor
type: sessions
tags: [backend, rust, littleorgans, refactor]
summary: Shared home expansion and session ResourceSpec construction were consolidated into owning crates.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Consolidated duplicated path and identity helpers in the assigned config identity lane. `lilo-paths` now owns home path expansion. `lilo-im-core` now owns session scoped `ResourceSpec` construction. Session and runtime callers delegate to those shared APIs.

## API Contract

Shared Rust API signatures added:

| Crate | API |
| --- | --- |
| `lilo-paths` | `pub fn expand_home_path(value: &str, home: Option<&Path>) -> Option<PathBuf>` |
| `lilo-im-core` | `impl ResourceSpec { pub fn session(session_id: Uuid) -> Self }` |

No HTTP, GraphQL, or wire API shape changed.

## Database Changes

None.

## Security Considerations

Runtime and session authorization continue to build session scoped resources with the same `session_id` semantics. The shared constructor reduces drift risk in audit and authorization resource matching.

Home expansion keeps the previous safety behavior. Daemon resolution still errors when `~` or `~/...` requires HOME and HOME is unavailable. Core normalization still preserves unresolved home prefixes when no home directory is supplied.

## Performance Notes

No material runtime impact. The new helpers are allocation equivalent to the removed local implementations.

Verification run:

`cargo check -p lilo-paths -p lilo-im-core -p lilo-session-core -p lilo-session-daemon -p lilo-runtime-daemon`

Result: OK. Finished in 13.93s.

## Open Items

`fmm generate` was not run because the shared worktree directive limited edits to the assigned lane and assigned generated or shared navigation state ownership to the orchestrator.
