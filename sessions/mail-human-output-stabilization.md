---
title: Mail Human Output Stabilization
type: sessions
tags: [backend, littleorgans, mail, cli, short-ids]
summary: Stabilized human mail output with short recipient ids, single follow headers, and clarified send status semantics.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary

Implemented `mailbugs-signoff` item 3 in commit `07f84e0` on `fix/mail-observability-bugs`.

Key decisions:

- Human mail surfaces render `RECIPIENT-ID` with adaptive short session ids.
- JSON and generated machine output keep full ids.
- `mail tail --follow` freezes the `ShortSessionIdSet` once at stream start and freezes table widths from the first non-empty batch.
- Recipients absent from the frozen set render via `id.short()`, avoiding full UUID overflow in later follow batches.
- `mail send` and `mail read` treat short-id load failure as display-only and fall back to full ids after state changes.
- Output tests moved to `internal/session/app/src/cli/output/tests.rs` to keep `output.rs` under the 700-line cap.

## API Contract

No wire API shape changed.

Human CLI contract changed:

```text
mail send summary columns:
RECIPIENT-ID ROLE CONTEXT INTENT NOTIFY MAIL [ERROR]
```

`ERROR` appears only when any result contains an error.

Human mail `RECIPIENT-ID` policy:

- `mail send`: short id when short-id load succeeds, full id fallback when it fails.
- `mail read`: short id when short-id load succeeds, full id fallback when it fails.
- `mail tail`: short id for human output, full id for JSON.
- `mail tail --follow`: one header for the stream, fixed widths from the first non-empty batch, stable short-id set for the stream.

Generated help now clarifies:

- `MAIL` means inbox acceptance.
- `NOTIFY` means wake delivery status: `ok`, `err`, or `skipped`.

## Database Changes

None.

## Security Considerations

- No authorization changes.
- No new persistence paths.
- JSON and machine-readable ids remain full ids, preserving exact identifiers for integrations.
- Send/read avoid hiding already-applied state changes behind display-only short-id load errors.

## Performance Notes

- `mail tail --follow` loads short ids once before streaming, avoiding repeated list RPCs per batch.
- Follow table widths are computed once from the first non-empty batch.
- `ShortSessionIdSet` non-member fallback uses bounded `id.short()` to avoid wide full UUID rows.

## Verification

- `cargo test -p lilo-session-app`: passed.
- `just check && just build && just test`: passed, `707/707` nextest cases.
- `fmm generate && fmm validate`: passed, 387 indexed files up to date.
- Line caps verified: `output.rs` 565 LOC, `output/tests.rs` 184 LOC, `mail.rs` 371 LOC.
- Rendered help verified with `target/debug/lilo mail send --help`, showing `summary MAIL` and `summary NOTIFY` semantics.

## Open Items

None for item 3 implementation. Awaiting reviewer Phase B audit on `07f84e0~..07f84e0`.
