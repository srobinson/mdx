---
title: Recall Rank Key Slice 1 Implementation
type: sessions
tags: [backend, context-matters, recall, ranking]
summary: Implemented deterministic recall rank key with store-owned ranking mode configuration and CI-clean all-target clippy fixes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented slice 1 for recall ranking on branch `feat/recall-rank-key`, PR #79. The current pushed fix commit is `f6121d2`, following config injection commit `0c6b165` and initial rank key commit `28a0ab4`.

The change adds a pure deterministic rank prefix in `cm-core`, moves recall ranking mode ownership into `cm-store` configuration, exposes the selected mode through `ContextStore::recall_ranking_mode()`, and keeps the default legacy path behavior unchanged. `cm-capabilities` no longer reads config files or environment variables during recall.

The CI fix in `f6121d2` rewrites rank key ordering property assertions in `cm-core/tests/types_test.rs` to avoid `clippy::nonminimal_bool` while preserving semantic checks for irreflexivity, antisymmetry, and transitivity.

## API Contract

No public HTTP or MCP request shape changed.

Ranking mode is resolved internally with this config shape:

```toml
[recall]
ranking_mode = "legacy" # legacy | shadow | live
```

Environment override:

```sh
CM_RECALL_RANKING=legacy|shadow|live
```

`legacy` remains the default and preserves existing scope depth ordering. `live` serves deterministic ordering by kind tier, confidence, priority, scope depth, BM25 score, recency, and id. `shadow` is accepted for forward compatibility and currently serves legacy ordering until the shadow canary slice lands.

## Database Changes

No schema or migration changes in this slice.

`cm-store` config parsing accepts the `[recall]` table without dropping existing `data_dir`, `log_level`, or scope inference settings. The generated config template documents the option.

## Security Considerations

Ranking mode input is fail closed. Invalid config or environment values fall back to `legacy`. No entry body, title, metadata, or credential logging was added.

## Performance Notes

The default path does not change fetch limits or add canary work. Live ranking sorts the existing candidate set in memory using `RecallRankKey` as a priority prefix and preserves BM25 as the first tie breaker after that prefix. Removing config and environment reads from the recall hot path avoids per request filesystem work.

Verification completed on 2026-06-16:

```sh
cargo fmt
cargo test -p cm-core recall_rank --tests
cargo test -p cm-store config::tests
cargo test -p cm-capabilities --test recall_ranking_tests
just check && just test && just build
cargo clippy --workspace --all-targets -- -D warnings
just test
```

All listed commands passed. Commit `f6121d2` was pushed to `origin/feat/recall-rank-key`.

## Open Items

- Slice 2 must add shadow canary logging and window oversampling.
- Slice 3 must expose recall shadow data in cm-web and decide promotion based on observed diffs.
- SQL pushdown remains deferred until shadow data proves oversampling insufficient.
