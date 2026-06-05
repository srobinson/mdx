---
title: Mail Notify Docs and Generated Surfaces
type: sessions
tags: [backend, littleorgans, mail, notify, generated-surfaces]
summary: Updated mail --notify help and regenerated app CLI and MCP schema surfaces.
status: active
source: backend-engineer
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

## Summary

Updated `lilo mail send --notify` documentation to describe shipped `wait` and `steer` behavior. The help now states that bare `--notify` uses `wait`, `wait` waits up to about 120s for no busy marker before nudging, and `steer` sends one ESC when busy and waits up to about 5s before nudging. The v1 limitation is documented: idle means no busy marker, not a guaranteed safe prompt, and approval prompts are not detected.

Local commit: `284d73a` (`docs(session): document mail notify modes`). No push.

## API Contract

No API shape changed. Existing `notify` enum values remain:

```typescript
type MailNotifyMode = "wait" | "steer";
```

Updated surfaces:

- CLI help for `lilo mail send --notify`.
- MCP `mail_send` schema description.
- MCP `mail_send` snapshot fixture.

## Database Changes

None.

## Security Considerations

No authorization, identity, persistence, or transport behavior changed. The updated documentation clarifies that persisted mail remains durable when a notify wait or steer timeout prevents an ephemeral nudge.

## Performance Notes

No runtime performance changes. Documentation now reflects existing runtime timeout bounds: about 120s for `wait`, about 5s for `steer`.

## Open Items

- Peer Phase B review was requested with `C|3|284d73a`; no review response had arrived when this record was updated.
- `wait` and `steer` still do not detect approval prompts. This is documented as a v1 limitation.

## Verification

- `cargo build -p lilo-session-app`: passed, regenerated app CLI help and MCP schema files from `internal/session/app/tools/mail.toml`.
- `just codegen`: passed, no root `crates/lilo` notify diff because `--notify` is not in `tools/schemas/cli.toml`.
- `cargo run -p lilo --bin lilo -- mail send --help`: passed, help showed the new `--notify` text.
- First `just test`: failed only on the expected `mail_send` MCP schema snapshot drift; accepted the snapshot with `cargo insta accept`.
- `just check && just build && just test`: passed after snapshot acceptance. Nextest summary: 625 tests run, 625 passed, 0 skipped.
