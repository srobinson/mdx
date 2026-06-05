---
title: LILO environment namespace Phase 5 implementation
type: sessions
tags: [backend, env-vars, logging, ci]
summary: Implemented LILO_LOG_FORMAT, the LILO env const registry, docs, and env gate wiring for Phase 5.
status: active
source: backend-engineer
confidence: high
created: 2026-06-03
updated: 2026-06-03
---

## Summary

Implemented Phase 5 closeout for `chore/lilo-env-namespace` after reviewer `S|A|p5` on rev4. The broad raw literal sweep was explicitly deferred to Item 16 by orchestrator adjudication. This phase delivers name set authority, key registry consumption sites, the logging format knob, docs, and CI gate wiring.

Commits:

- `74d43f0` `feat(logging): add LILO_LOG_FORMAT knob, drop dead LILO_LOG_JSON (Item 8)`
- `70b73d2` `feat(lilo-paths): env-var const registry consumed by check-env (Item 11)`
- `3a6a2e4` `docs(env): document the LILO_ env-var contract (Item 9)`
- `0274bf7` `build(ci): enforce the env gate in just check + moon ci (Item 10b)`

Sent `C|p5|74d43f0,70b73d2,3a6a2e4,0274bf7|just check green + gate 0` to the reviewer and `M|p5|...` to the orchestrator. Awaiting reviewer `S|B`, then send `P`.

## API Contract

No HTTP, RPC, or daemon API contract changed.

Logging environment contract changed:

```typescript
type LiloLogFormat = "auto" | "pretty" | "json" | "compact";
```

Selection order:

1. Explicit `LILO_LOG_FORMAT` wins.
2. Otherwise `--output json` selects JSON logging.
3. Otherwise `auto` selects pretty on a terminal and JSON when not attached to a terminal.

Unknown `LILO_LOG_FORMAT` values fail with an input validation diagnostic.

## Database Changes

No schema, migration, or data model changes.

## Security Considerations

- `scripts/check-env.sh --check` now builds the authoritative owned `LILO_*` set from `crates/lilo-paths/src/env.rs` specifically. This prevents stray const declarations in other files from self registering.
- The gate rejects owned looking Rust string literals whose names are not registered.
- Existing forbidden namespace raw token scanning remains intact with the same self and convention document exclusions.
- Six scoped env read or declaration sites now consume `lilo_paths::env` or `crate::env` constants: `lilo.rs`, `logging.rs`, `docker_preflight.rs`, `reconcile.rs`, `server/config.rs`, and `mail.rs`.
- `LILO_LOG_JSON` was removed from tracked authored files.

## Performance Notes

- No runtime hot path performance impact beyond one optional `LILO_LOG_FORMAT` env read during logging initialization.
- `check-env` currently scans the repository and took about one minute in local verification. It is wired into `just check` and Moon CI as requested.

## Verification

Completed verification:

- `python3 scripts/check-env.sh --check` exited 0.
- Gate bite proof: temporary `"LILO_BOGUS"` Rust literal failed the gate, then removal restored exit 0.
- `cargo test -p lilo-common logging` passed 7 of 7 logging tests.
- `git grep -n LILO_LOG_JSON` returned 0 tracked hits.
- Authored file grep excluding `.git`, `.nancy`, and `target` returned 0 `LILO_LOG_JSON` hits.
- `cargo tree -p lilo-common --depth 1` shows `lilo-common -> lilo-paths`; Cargo build and test proved no dependency cycle.
- `just check && just build && just test` exited 0. The final nextest summary reported 657 tests passed, 0 skipped.

## Open Items

- Await reviewer `S|B`, then send protocol `P`.
- Item 16 remains parked: full literal sweep that forbids all raw registered `LILO_` literals across production Rust source.
