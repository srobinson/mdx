---
title: Transport Matters Channel CLI Hygiene
type: sessions
tags: [backend, transport-matters, channels, cli, tests, ports]
summary: Split Codex channel tests and shared pinned port error emission across launch paths.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented the channel hygiene follow up on `feat/channels` in commit `a0b78be17d82c9655017b136d9cb6d60835b0672`.

Key decisions:

- Moved the Codex channel specific tests from `cli/test_codex.py` into `cli/test_codex_channel.py` without changing their assertions.
- Replaced the duplicate desktop inline port error with shared `raise_port_in_use()` in `cli/net.py`.
- Passed the already resolved `ChannelSpec` into `_resolve_backend_ports()` instead of resolving the channel a second time.

## API Contract

No HTTP API changed.

CLI behavior covered:

```text
transport-matters codex --channel preview --no-codex --print-command
transport-matters desktop --channel preview
```

Pinned proxy and web port conflicts now share this error shape across launch paths:

```text
error: <label> port <port> is already in use.
Another process is already bound to this port. Free it, or pick a different port with <--proxy-port|--web-port>.
```

## Database Changes

None.

## Security Considerations

- No new inputs or persistence paths were added.
- The shared port error preserves explicit user recovery guidance and avoids leaking process details.
- Channel resolution remains centralized in `prepare_desktop_launch()` before launch environment construction.

## Performance Notes

- `_resolve_backend_ports()` no longer re-resolves channel configuration, removing a duplicate lookup on desktop launch preparation.
- Test file split keeps `cli/test_codex.py` below the 700 line guardrail at 624 LOC.

## Verification

- `cd api && just test src/transport_matters/cli/test_codex.py src/transport_matters/cli/test_codex_channel.py src/transport_matters/cli/test_start.py src/transport_matters/cli/test_desktop.py`: 54 passed in 0.56s.
- `cd api && just check`: ruff format unchanged, ruff check passed, mypy passed for 413 source files.
- `wc -l api/src/transport_matters/cli/test_codex.py api/src/transport_matters/cli/test_codex_channel.py`: 624 and 98 LOC.
- `git diff --check`: exit 0.
- `fmm validate`: all 848 files indexed and up to date.

## Open Items

None for this hygiene slice.
