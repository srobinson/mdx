---
title: mdm init creates config when local index dir exists
type: sessions
tags: [backend, cli, config, tests]
summary: Fixed mdm init so an existing .mdm directory without .mdm.toml still creates the local config.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented PR #43 on branch `fix/init-config-when-dir-exists` at commit `8ec80ab`.

`mdm init --local --yes` now treats an existing `.mdm/` directory without `.mdm.toml` as an incomplete local initialization and routes through `initLocal`, which writes the default config. When both `.mdm/` and `.mdm.toml` exist, it preserves the previous no-op message.

Key code changes:

- Added an explicit local config existence check in `src/cli/commands/init-cmd.ts`.
- Deferred `loadConfigFile(cwd)` until the both-exist no-op branch, so missing local config does not consult global config before repair.
- Avoided reporting `Created .mdm/` when the directory already existed.
- Added regression coverage in `src/cli/commands/init-cmd.test.ts`.

## API Contract

This was a CLI behavior fix, not an HTTP API change.

Command contract:

```text
mdm init --local --yes
```

When current directory contains `.mdm/` but no `.mdm.toml`:

```text
Created .mdm.toml

Run "mdm index" to build the index.
```

Expected filesystem effect:

```text
.mdm/       remains present
.mdm.toml   created with generateDefaultToml output
```

When current directory contains both `.mdm/` and `.mdm.toml`:

```text
Already initialized locally.
Config: <path when config parses>

Run "mdm index" to build the index.
```

Expected filesystem effect: existing `.mdm.toml` remains untouched.

## Database Changes

No database changes.

## Security Considerations

The fix does not expand filesystem scope. It only writes `.mdm.toml` in the current working directory when the caller runs local init and the local index directory already exists. Existing config overwrite protection remains intact.

## Performance Notes

The change adds one direct `fs.existsSync` check for `.mdm.toml`. It also avoids unnecessary config loading in the repair path.

Verification completed:

- Added failing regression first. It failed with the old `Already initialized locally` output and no config creation.
- `npx --yes pnpm@10.28.0 check`
- `npx --yes pnpm@10.28.0 build`
- `npx --yes pnpm@10.28.0 test`
- Manual smoke with a temp directory containing only `.mdm/`, confirming `Created .mdm.toml` output and file creation.

## Open Items

None for this fix.
