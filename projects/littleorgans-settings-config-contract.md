# littleorgans `settings.toml` Config Layer Contract

Status: draft for implementation
Date: 2026-06-06
Branch: feat/postgres-phase-1a (stacked on the Phase 1.a work)
Parent: surfaced by the Phase 1.a `DEFAULT_ADMIN_URL` unsafe-fallback review

## Purpose

Introduce an operator-configurable `settings.toml` as the primary config API,
replacing the unsafe silent `DEFAULT_ADMIN_URL` const. Config resolves through a
clear precedence chain with `LILO_*` env as the override layer. Scope is
deliberately minimal: only the database keys flow through it in this pass.

## Locked Decisions

1. Mechanism is the existing `toml` crate + serde derive (matching
   `ToolContractRegistry::from_toml_str`). Do NOT add `figment`/`config` or any
   new config framework.
2. The `Settings` loader lives in `lilo-paths` (it already owns `LILO_HOME`, path
   derivation, and the env registry).
3. Location: `$LILO_HOME/settings.toml`. A committed `settings.example.toml` at
   repo root is the template an operator copies in. The live file is under
   `~/.lilo`, outside the repo, so no `.gitignore` entry is needed.
4. Precedence, highest wins: explicit CLI flag → `LILO_*` env → `settings.toml`
   → built-in default. No CLI flag for the database URL exists or is added now;
   env-over-toml is the operative layering.
5. Minimal scope: only `[database] url` and `test_url`. Other `LILO_*` operator
   vars stay exactly as they are. No broad config migration in this pass.
6. No `.env`/`dotenvy`. `settings.toml` is the Rust config surface; the Compose
   host port stays a plain shell-overridable var (below).
7. `DEFAULT_ADMIN_URL` is deleted. Resolution fails loud when nothing is
   configured.
8. Tests stay hermetic: the fixture resolves env first (`LILO_TEST_DATABASE_URL`
   sits at the top of precedence), so the suite never depends on a real
   `settings.toml`.

## Public Surface (`lilo-paths`)

Shape, not exact names; adjust to local conventions where cleaner:

```rust
// lilo-paths/src/settings.rs
#[derive(Debug, Clone, Default, serde::Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    pub database: DatabaseSettings,
}

#[derive(Debug, Clone, Default, serde::Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct DatabaseSettings {
    pub url: Option<String>,
    pub test_url: Option<String>,
}

impl Settings {
    /// Load `$LILO_HOME/settings.toml`. A missing file is not an error: returns
    /// `Settings::default()`. A present-but-malformed file IS an error.
    pub fn load() -> Result<Self>;
    /// Explicit path for tests / non-default homes.
    pub fn load_from(path: &Path) -> Result<Self>;
}
```

Resolvers (env over toml), co-located with the existing env helpers so callers
share one path:

```rust
/// LILO_DATABASE_URL  ??  settings.database.url
pub fn resolve_database_url(settings: &Settings) -> Option<String>;

/// LILO_TEST_DATABASE_URL  ??  LILO_DATABASE_URL
///   ??  settings.database.test_url  ??  settings.database.url
pub fn resolve_test_database_url(settings: &Settings) -> Option<String>;
```

Keep the existing env-only helpers (`env::database_url()`,
`env::test_database_url()`); the resolvers layer toml beneath them. Do not
duplicate the env read.

## Consumers

- `DbConfig` (runtime open path): build from `resolve_database_url(&Settings::load()?)`.
  When it resolves to `None`, error with actionable guidance: "set
  `LILO_DATABASE_URL`, or add `[database] url` to `$LILO_HOME/settings.toml`
  (copy `settings.example.toml`)." Never connect to a guessed host.
- `lilo-db` test fixture `admin_url()`: replace the `DEFAULT_ADMIN_URL` fallback
  with `resolve_test_database_url(&Settings::load().unwrap_or_default())`; on
  `None`, the same loud error naming `LILO_TEST_DATABASE_URL`. Env still wins, so
  CI/dev that exports the var is unaffected and hermetic.

## `settings.example.toml` (repo root)

```toml
# Copy to $LILO_HOME/settings.toml and edit. LILO_* env vars override these.
[database]
# Operator Postgres connection used by the daemon.
url = "postgres://lilo:lilo@localhost:55432/lilo"
# Admin/provisioning connection for the lilo-db test fixture (creates and drops
# throwaway test databases). Defaults to `url` if unset.
test_url = "postgres://lilo:lilo@localhost:55432/lilo"
```

## Compose Port + Port Alignment (fold in here)

1. Rename the new var `LILO_DOCKER_DATABASE_PORT` → `LILO_DOCKER_PG_PORT`;
   register it in `lilo_paths::env` and add an `env-vars.md` row (bare operator
   var, Compose-only, default `55432`). Compose line:
   `"127.0.0.1:${LILO_DOCKER_PG_PORT:-55432}:5432"`.
2. Align every remaining `:5432` to `:55432`: the `compose.yaml` header comment
   and any `env-vars.md` local-default mention. (`DEFAULT_ADMIN_URL` is deleted,
   not realigned.)

## Out Of Scope

- Migrating non-database `LILO_*` vars into `settings.toml`.
- `dotenvy` / `.env` loading.
- A CLI flag for the database URL.
- Any Phase 1.b store-query migration.

## Acceptance

```bash
./scripts/check-env.sh --check          # LILO_DOCKER_PG_PORT registered; clean
fmm validate
docker compose up -d --wait postgres    # binds 55432
cargo test -p lilo-db                    # green vs postgres:17, fixture tests pass
just check                               # fmt + clippy -Dwarnings + gates
```

- `rg "DEFAULT_ADMIN_URL|LILO_DOCKER_DATABASE_PORT|localhost:5432" -g '!target'`
  returns no hits (old name and the unsafe const are gone).
- One test proves a malformed `settings.toml` errors; a missing one yields
  defaults.
- Loud-error path: with all of `LILO_DATABASE_URL`, `LILO_TEST_DATABASE_URL`, and
  any `settings.toml` absent, the fixture/`DbConfig` returns the guidance error,
  not a connection attempt.
