---
title: Transport Matters Channels Slice 5 Docs and Live Smoke
type: sessions
tags: [backend, transport-matters, channels, docs, smoke, postgres]
summary: Documented stable and preview channels, verified live backend meta for both channels, and completed the full root gate.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Slice 5 finished the channels rollout documentation and verification pass. It added `docs/CHANNELS.md`, marked side by side dogfooding as landed in `NOW.md`, and added a concise channel note to `PROJECT.md`. The docs describe stable as the daily driver and preview as the working tree dogfood build, plus `just channel-restart preview`, isolation boundaries, channel listing, ensure DB, and code only promotion.

Commit: `fe9a96af459cf1cddea3a6b4e2b85df9e1805191` (`docs(channels): document preview workflow`).

## API Contract

No endpoint shape changed in this slice. The already implemented additive `/api/meta` fields were live smoked through FastAPI:

```typescript
interface ChannelBadgeResponse {
  text: string;
  color: "amber";
  hex: string;
}

interface MetaResponse {
  channel: "stable" | "preview";
  channel_label: string;
  channel_badge: ChannelBadgeResponse | null;
}
```

Observed live snippets:

- Preview on `127.0.0.1:8798`: `{"channel":"preview","channel_label":"Preview","channel_badge":{"color":"amber","hex":"#f59e0b","text":"PREVIEW"}}`
- Stable on `127.0.0.1:8788`: `{"channel":"stable","channel_label":"Stable","channel_badge":null}`

## Database Changes

No migration changed in this slice. The live smoke used explicit local Postgres configuration:

```bash
TRANSPORT_MATTERS_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres
```

Verification commands created or confirmed both channel databases and applied migrations:

```bash
transport-matters channel ensure-db stable
transport-matters channel ensure-db preview
```

Observed results:

- `transport_matters`: existed, migration head `0005_session_template_provenance`
- `transport_matters_preview`: created, migration head `0005_session_template_provenance`

## Security Considerations

The docs preserve the explicit Postgres server requirement. Channels only select the database name on the configured server. Promotion remains code only by inspection of `api/src/transport_matters/cli/channel_cmd.py`: `promote preview stable` calls `run_install_local(root)`, prints the stable launch command, and does not copy homes or move session data between databases.

## Performance Notes

No runtime performance path changed. The live smoke served only the FastAPI backend for each channel, without spawning Electron. Both backend ports were released after cleanup:

- `8788`: free after stable smoke
- `8798`: free after preview smoke

## Verification

- `fmm validate`: all 851 indexed files up to date.
- Live smoke:
  - Postgres reachable at `postgresql://tm:tm@localhost:55432/postgres`
  - `transport-matters channel ensure-db stable`: `database transport_matters: exists`
  - `transport-matters channel ensure-db preview`: `database transport_matters_preview: created`
  - Preview backend on `8798` returned channel `preview` with amber `PREVIEW` badge.
  - Stable backend on `8788` returned channel `stable` with `channel_badge: null`.
  - Ports `8788` and `8798` were free after cleanup.
- `just check`: exit 0.
  - desktop typecheck and tests passed: 8 files, 33 tests.
  - www format, lint, and typecheck passed. Biome reported only the existing two `!important` warnings in `src/session-canvas/components/pane-dock.css`.
  - api format, ruff, and mypy passed for 413 source files.
- `just test`: exit 0.
  - desktop: 8 files, 33 tests passed.
  - www: 140 files, 989 tests passed.
  - api: 1637 tests passed.

## Open Items

- Human road test can launch preview with `just channel-restart preview` and stable with `transport-matters desktop` or `transport-matters desktop --channel stable`.
- The slice intentionally did not run `transport-matters channel promote preview stable`, because promotion overwrites the global stable tool install.
