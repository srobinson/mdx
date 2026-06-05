---
title: Home Seed Decomposition
type: sessions
tags: [backend, cli, refactor, home-seed, transport-matters]
summary: Split managed client home seeding into cohesive CLI modules while keeping the public facade stable.
status: active
source: backend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented a behavior preserving decomposition of `api/src/transport_matters/cli/home_seed.py` on branch `refactor/home-seed-decomposition`, commit `931531a`, PR#120.

Key decisions:

1. `home_seed.py` is now a thin public facade with reexports only.
2. Shared constants live in `home_constants.py` so lower modules import down from one leaf.
3. Restrictive JSON and secret file writes live in `home_io.py`.
4. Claude behavior lives in `claude_home.py`.
5. Codex TOML trust and session root behavior lives in `codex_home.py`.
6. Overlay materialization and daemon locality checks live in `home_overlay.py`.
7. Seeder dispatch and public overlay preparation orchestration live in `home_seeders.py`.

## API Contract

No HTTP API changes.

Existing Python import contract preserved through `transport_matters.cli.home_seed`:

```python
RuntimeHomeOverlay
apply_claude_proxy_env_settings
claude_projects_root
codex_sessions_root
prepare_runtime_home_overlay
resolve_source_home_dir
seed_home_dir
```

Internal tests now import private or owning module symbols directly where needed.

## Database Changes

None.

## Security Considerations

The refactor preserved restrictive file handling for managed home secrets:

1. JSON and secret writes still use mode `0o600`.
2. Runtime home directories still use mode `0o700`.
3. Claude daemon and dispatch state still stay local to runtime overlays.
4. Native credential files are still linked from the auth source instead of copied from the content template.
5. Codex hook trust state still relocates copied source home table keys to the overlay home.

## Performance Notes

No runtime performance change intended. The split reduces module size and improves import boundary clarity. `home_seed.py` moved from 685 LOC to 18 LOC. All new modules are under the 700 LOC project limit.

## Verification

Observed verification:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/cli/test_home_seed.py src/transport_matters/cli/test_home_seed_credentials.py src/transport_matters/test_private_import_boundary.py
# 33 passed

cd api && just check
# ruff format, ruff check, mypy all passed, EXIT=0

cd api && just test
# 1397 passed, EXIT=0
```

The new `test_home_seed_modules_import_in_fresh_subprocess` proves the decomposed modules import cleanly in a fresh Python process.

## Open Items

None for this refactor.
