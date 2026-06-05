---
title: Mail Check CLI Surface Drop
type: sessions
tags: [backend, littleorgans, cli, mcp, mail]
summary: Removed the human `mail check` CLI while preserving the MCP and daemon count primitive.
status: active
source: backend-engineer
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

## Summary

Implemented commit `1dbe4a1` on `feat/mail-observability` to delete the human `mail check` command surface. The count primitive remains available through `SessionRpc::MailCheck`, the daemon handler, MCP `mail_check`, authz, and the hot path bench.

Key decisions:

- Kept the full `[tools.mail_check]` contract and set `render_cli_help = false` so the tool is MCP only.
- Deleted the handwritten CLI variant, args, dispatcher branch, and human output renderer.
- Removed positive CLI help coverage for `mail check` without adding deletion guard tests.
- Updated top level `lilo mail` help from `tools/schemas/cli.toml` so rendered help no longer mentions `mail check`.
- Converted the hot path bench to measure the daemon `mail_check` RPC directly rather than invoking the deleted CLI surface.

## API Contract

No public HTTP API changes.

MCP contract retained:

```typescript
interface MailCheckRequest {
  selector: string;
  namespace?: string;
}

interface MailCheckResponse {
  unread: number;
  counts: Array<Record<string, unknown>>;
}
```

CLI contract changed:

- Removed: `lilo mail check` and `sm mail check`.
- Retained: `lilo mail stop-check` and `sm mail stop-check`.
- Retained: MCP tool `mail_check`.

## Database Changes

None. Existing mail tables, unread counts, and RPC data shapes are unchanged.

## Security Considerations

- Existing `SessionRpc::MailCheck` authorization remains in the daemon authz gate.
- Removing the human CLI path reduces a redundant local entrypoint without weakening daemon side authorization.
- MCP schema generation still emits `mail_check`, so agent callers keep the explicit count primitive.

## Performance Notes

- The hot path bench now measures the daemon `mail_check` RPC directly.
- Bench compile proof: `cargo bench -p lilo-session-app --bench hot_path --no-run`.

Verification completed:

- `just check`
- `just build`
- `just test`
- `cargo test -p lilo-session-app`
- `cargo bench -p lilo-session-app --bench hot_path --no-run`
- `cargo run -p xtask -- codegen --check`
- `fmm generate && fmm validate`
- Manual help checks: `lilo mail --help`, `sm mail --help`, `lilo mail check --help`, `sm mail check --help`, and `mail stop-check` help.

## Open Items

- Phase B review signed off by engineering-code-reviewer on 2026-06-04 with no issues found.
