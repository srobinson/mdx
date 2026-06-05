---
title: Transport Matters Channel Core Slice 1
type: sessions
tags: [backend, transport-matters, channels, config, storage, runtime-registry]
summary: Implemented and tightened package-owned stable and preview channel core for backend config, database, storage, and runtime registry resolution.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented slice 1 of the Transport Matters channels plan on branch `feat/channels`.

Commits:

- `afd5da85954623e4065a927f7c06be2dec412f3c` — `feat(api): add channel spec core`
- `00ddf515a1bf781124beb5dff638e508ed89e8d0` — `fix(api): tighten channel isolation`

Key decisions:

- Added one package-owned JSON source at `api/src/transport_matters/channel-specs.json` with `stable` and `preview` channel definitions.
- Added `transport_matters.channel` as the Python resolver for channel id validation, frozen channel models, `activate_channel`, and ordered spec enumeration.
- Preserved `stable` as the default channel.
- Kept database configuration explicit: no env or TOML database URL still raises `MissingDatabaseConfigError`.
- Rewrote only the configured PostgreSQL URL path to the active channel database name, including hostless libpq and Unix socket URL forms.
- Made `Settings(channel=...)` the single authority for default storage root and database name when no explicit env storage override exists.
- Made disk layout default root lazy so channel env changes are observed after module import.
- Routed runtime registry tm-fleet roots through channel-aware storage root resolution.

## API Contract

No HTTP endpoints were added or changed in this slice.

Backend Python contract added:

```python
@dataclass(frozen=True, slots=True)
class ChannelBadge:
    text: str
    color: Literal["amber"]
    hex: str

@dataclass(frozen=True, slots=True)
class ChannelSpec:
    id: str
    label: str
    home: Path
    database_name: str
    proxy_port: int
    web_port: int
    electron_app_name: str
    electron_app_id: str
    electron_user_data: Path | None
    dock_icon: Literal["default", "preview-amber"]
    badge: ChannelBadge | None

def resolve_channel_id(value: str | None, env: Mapping[str, str]) -> str: ...
def resolve_channel_spec(value: str | None = None, env: Mapping[str, str] = os.environ) -> ChannelSpec: ...
def activate_channel(value: str | None) -> ChannelSpec: ...
def all_channel_specs() -> tuple[ChannelSpec, ...]: ...
```

`env_keys.CHANNEL` is now `TRANSPORT_MATTERS_CHANNEL`.

## Database Changes

No schema migration was added.

Database URL resolution keeps the existing precedence:

1. `TRANSPORT_MATTERS_DATABASE_URL`
2. `[database].url` in `settings.toml`
3. raise `MissingDatabaseConfigError`

When a URL is present, the database path is replaced with the active channel database name:

- `stable` -> `transport_matters`
- `preview` -> `transport_matters_preview`

Query string, scheme, user info, host, and port are preserved. Hostless libpq forms such as `postgresql:///transport_matters` and `postgresql:///transport_matters?host=/var/run/postgresql` are rewritten to the channel DB name without losing the triple slash form.

## Security Considerations

- Channel ids validate against `^[a-z][a-z0-9_]*$` and must exist in the package JSON.
- The database no-config guard remains intact.
- `TRANSPORT_MATTERS_HOME` remains an explicit emergency/test override for storage root relocation.
- The backend launch smoke now uses a unique test database plus subprocess channel-spec monkeypatching, instead of skipping when a real stable database exists.

## Performance Notes

- Channel JSON loading is cached with `lru_cache`.
- `DiskStorageLayout` now re-reads `default_storage_root()` only when a default layout instance is created, avoiding stale module-import-time root binding.
- Runtime registry channel-home resolution is path-only and adds no database or filesystem scanning.

## Verification

Observed commands:

- Fail-before proof: `cd api && just test src/transport_matters/test_channel.py::test_resolve_database_url_rewrites_hostless_libpq_url src/transport_matters/test_channel.py::test_resolve_database_url_rewrites_socket_query_url src/transport_matters/test_channel.py::test_settings_channel_drives_storage_and_database_without_env` -> 3 failed before the fix.
- Pass-after proof: same targeted tests plus `src/transport_matters/test_runtime_registry.py::test_runtime_template_roots_use_preview_channel_home` -> 4 passed.
- Focused gate: `cd api && just test src/transport_matters/test_channel.py src/transport_matters/test_config.py src/transport_matters/test_env_keys.py src/transport_matters/storage/test_disk_layout.py src/transport_matters/test_runtime_registry.py tests/integration/test_backend_launch_smoke.py::test_launched_backend_reads_db_from_home_not_per_run_storage` -> 68 passed.
- `cd api && just check` -> ruff format unchanged, ruff check passed, mypy passed.
- Earlier extra full API suite before the fix round: `cd api && just test` -> 1620 passed, 1 skipped locally because the stable channel database already existed on the configured test server. The follow-up launch smoke fix removed that skip path for its test.

## Open Items

- Later slices still need CLI `--channel` plumbing, channel default ports, channel DB lifecycle commands, desktop identity, and web badge wiring.
- Optional channel model refactors using pydantic validation and a single cached specs map were intentionally skipped to avoid churn in the accepted slice foundation.
