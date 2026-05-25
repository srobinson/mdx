---
title: Roadtest Capture Content Trim
type: sessions
tags: [backend, rust, capture, roadtest]
summary: Implemented ANSI-aware tmux capture de-padding and JSON-only ANSI stripping for capture output.
status: active
source: backend-engineer
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

## Summary

Implemented ROADTEST item 10 on branch `fix/roadtest` as commit `52d71ae`.

The capture path now strips trailing blank tmux viewport rows before applying `--scrollback-lines`, so `N` counts returned content lines rather than empty pane grid rows. `--output json` now emits plain text capture content by stripping ANSI escape sequences at the CLI JSON presentation boundary. Default text output preserves ANSI.

## API Contract

No endpoint or RPC schema changed.

Capture response semantics now are:

```typescript
interface PaneSnapshot {
  content: string;
  captured_at_ms: number;
  scrollback_lines_requested: number;
  scrollback_lines_included: number; // final returned content line count
  pane_history_lines: number; // tmux #{history_size}, unchanged
}
```

CLI presentation contract:

- `lilo capture <id>` prints raw capture content and preserves ANSI escapes.
- `lilo capture <id> --output json` serializes capture content with ANSI escapes removed.
- Trailing blank rows are removed for both default capture and explicit `--scrollback-lines N`.
- Last N selection applies after trailing blank row removal.

## Database Changes

None.

## Security Considerations

ANSI stripping is centralized in `lilo_rm_core::strip_ansi_escapes`. The daemon remains format agnostic and receives no client output format hint. The helper preserves newlines, so JSON stripping does not change line counts.

## Performance Notes

`internal/runtime/platform/src/tmux.rs::trim_explicit_scrollback` performs one `split_inclusive('\n')` collection, removes trailing blank lines in place, then slices the final last N window. No second split or duplicate ANSI implementation was introduced.

## Verification

- `cargo test -p lilo-runtime-platform --lib`: pass.
- `cargo test -p lilo-rm-core --lib`: pass.
- `cargo test -p lilo-session-app --lib cli::capture`: pass.
- `just check`: pass.
- `just build`: pass.
- `just test`: pass, 576 passed, 0 skipped.
- `fmm generate && fmm validate`: pass.
- Reviewer Phase B sign off received from `littleorgans:helioy-tools:rust-engineer:5:6.1`.
- Branch `fix/roadtest` pushed to origin at `52d71ae`.

## Open Items

None for item 10.
