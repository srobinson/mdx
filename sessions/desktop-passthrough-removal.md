---
title: Desktop Passthrough Removal
type: sessions
tags: [backend, transport-matters, desktop, cli, passthrough]
summary: Removed desktop provider flags and raw passthrough while preserving standalone claude and codex passthrough.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Slice B desktop cleanup on `feat/desktop-remove-passthrough`, PR #141. `transport-matters desktop` is now a thin desktop shell launcher with only backend launch options. It no longer accepts provider selection, provider specific flags, debug or print command controls, home directory overrides, route selection, or raw child passthrough after `--`.

Key decisions:

- Kept `_split_passthrough` for standalone `transport-matters claude` and `transport-matters codex`.
- Kept the internal desktop backend launch helper and hidden `_desktop-backend` command behavior.
- Removed dead desktop option validation helpers and the now unused `AgentOption` and `RouteOption` aliases.
- Stopped `/v1/runs` pane launches from inheriting `Settings.default_client_passthrough`.

## API Contract

No public `/v1/runs` request fields changed. `CreateRunRequest` remains the pane launch contract with explicit fields such as `cli`, `cwd`, `runtimeTemplate`, `continueFromSessionId`, and `idempotencyKey`.

CLI contract now enforced by Typer:

```text
transport-matters desktop [--work-dir PATH] [--web-port INT] [--storage-dir PATH]
```

Removed from public desktop:

- `--agent`, `--route`
- `--upstream`, `--claude-bin`, `--no-claude`, `--no-system-prompt`
- `--codex-bin`, `--no-codex`, `--force-http-fallback`
- `--agent-home-dir`, `--debug`, `--print-command`
- arguments after `--`

## Database Changes

No database schema or migration changes.

## Security Considerations

The change removes raw native child arguments from the desktop launch path. Captured panes now default to empty passthrough even if stale `TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH` exists in backend settings. The standalone `claude` and `codex` commands still own explicit passthrough as terminal command contracts.

## Performance Notes

No expected runtime performance impact. The change deletes CLI option handling and validation code and narrows pane spawn request construction.

Verification completed:

- `cd api && just check`
- `cd api && just test`
- `cd desktop && pnpm install --frozen-lockfile && pnpm test`
- `cd www && pnpm install --frozen-lockfile && pnpm test`
- `cd api && uv run transport-matters desktop --agent codex` exits 2 with `No such option`
- `cd api && uv run transport-matters desktop -- --model sonnet` exits 2 with unexpected extra arguments

## Open Items

- The live GUI smoke from the broader spec was not run in this terminal session. Automated API, desktop, and web tests passed.
- The parked CMD+K palette, template picker, and runtime template list endpoint remain out of scope.
