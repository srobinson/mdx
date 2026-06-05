---
title: Transport Matters Channel CLI and Port Plumbing Slice 2
type: sessions
tags: [backend, transport-matters, channels, cli, desktop, ports]
summary: Implemented channel aware CLI activation, deterministic channel ports, and channel environment propagation for Python and Electron launch paths.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented slice 2 of the Transport Matters channel build on branch `feat/channels`.

Commit: `977aefcfe8f4a8d5188610b57a34b86b322ec04b`

Key decisions:

- Added `--channel` as a shared launch option for `claude`, `codex`, `desktop`, and hidden `_desktop-backend`.
- Activated the requested channel before launch preparation, preflight, settings cache reads, and backend app creation.
- Changed top level CLI launch port resolution to use deterministic channel ports when flags are omitted.
- Kept prepared captured run and shared proxy preparation on allocator based ports so nested run preparation can still retry and avoid channel port collisions.
- Carried `TRANSPORT_MATTERS_CHANNEL` through launch env, desktop backend env, desktop backend command args, and Electron backend process env.

## API Contract

No HTTP API endpoints changed.

CLI contract added:

```text
transport-matters claude --channel <id>
transport-matters codex --channel <id>
transport-matters desktop --channel <id>
transport-matters _desktop-backend --channel <id>
```

`TRANSPORT_MATTERS_CHANNEL` is also accepted as the env var source for the option.

Unknown channel behavior:

```text
exit code: 2
message includes: unknown channel '<id>'
hint includes: transport-matters channel list
```

Port behavior:

- Omitted top level launch ports use `ChannelSpec.proxy_port` and `ChannelSpec.web_port`.
- Explicit `--proxy-port` or `--web-port` overrides that slot only.
- Resolved channel ports are treated as pinned for port in use and bind failure handling.

## Database Changes

No schema or migration changes in this slice.

Database selection depends on slice 1 channel config plumbing. Slice 2 ensures channel activation happens before preflight resolves settings.

## Security Considerations

- Channel activation validates against package owned channel specs before launch work proceeds.
- Unknown channels fail closed with exit code 2.
- Channel env propagation is explicit. Backend, addon, and child launch environments receive the same canonical channel id.
- No secrets were introduced or logged.

## Performance Notes

- Deterministic port resolution avoids kernel allocation for top level channel launches.
- Existing allocator paths remain available for captured run preparation and test mode paths where retry behavior is required.
- No new database queries or long running startup work were added.

## Verification

Fail first proof:

```text
cd api && just test \
  src/transport_matters/cli/test_start.py::test_start_channel_flag_activates_preview_defaults \
  src/transport_matters/cli/test_start.py::test_start_unknown_channel_exits_with_list_hint \
  src/transport_matters/cli/test_codex.py::test_codex_channel_flag_uses_preview_defaults \
  src/transport_matters/cli/test_desktop.py::test_desktop_backend_env_and_command_carry_channel \
  src/transport_matters/cli/test_desktop.py::test_desktop_channel_default_port_in_use_fails_fast
```

Observed before implementation: 5 failed.

Final gate evidence:

```text
cd api && just test src/transport_matters/cli/test_start.py src/transport_matters/cli/test_codex.py src/transport_matters/cli/test_desktop.py
# 54 passed

cd desktop && just test
# 7 files passed, 29 tests passed

cd api && just check
# ruff format unchanged, ruff check passed, mypy passed
```

Extra evidence:

```text
cd api && just test src/transport_matters/cli
# 345 passed

git diff --check
# EXIT=0
```

## Open Items

- Slice 3 will add `transport-matters channel` subcommands and database lifecycle helpers.
- Slice 4 will complete Electron identity, app naming, badge, and channel spec consumption in desktop and web surfaces.
