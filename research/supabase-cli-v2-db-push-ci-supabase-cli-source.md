---
title: Supabase CLI v2 — db push dry-run in CI, project ref, and env vars
type: research
tags: [supabase, cli, ci, migrations, db-push]
summary: In Supabase CLI v2, db push no longer accepts --project-ref. Use --linked (after supabase link) or --db-url. SUPABASE_PROJECT_ID and SUPABASE_DB_PASSWORD are the canonical env vars; SUPABASE_ACCESS_TOKEN is read directly via os.Getenv.
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

`supabase db push --project-ref` does not exist in CLI v2. The flag was removed; the project ref is now a linking concern, not a push concern. The correct CI pattern is:

1. Set `SUPABASE_ACCESS_TOKEN` and `SUPABASE_PROJECT_ID` as environment variables.
2. Run `supabase link` (the `--project-ref` flag is optional when `SUPABASE_PROJECT_ID` is set).
3. Run `supabase db push --linked --dry-run` (or just `supabase db push --dry-run` after linking).

## Details

### Flags on `supabase db push` (v2)

| Flag | Description |
|------|-------------|
| `--linked` | Push to the linked project (requires prior `supabase link` or `SUPABASE_PROJECT_ID`) |
| `--local` | Push to the local dev database |
| `--db-url <string>` | Push directly via a connection string (bypasses linking entirely) |
| `--dry-run` | Print pending migrations without executing them |
| `--include-all` | Include migrations not in remote history |
| `--include-roles` | Include `supabase/roles.sql` |
| `--include-seed` | Include seed data |
| `-p, --password` | Database password |

`--project-ref` is absent. There is no way to pass it directly to `db push`.

### Specifying the target project

Three approaches, in order of preference for CI:

**Option A — env var (no link step needed for the connection itself, but link still resolves config):**
```bash
SUPABASE_ACCESS_TOKEN=sbp_...  \
SUPABASE_DB_PASSWORD=secret    \
SUPABASE_PROJECT_ID=abcdefgh   \
  supabase db push --linked --dry-run
```
When `SUPABASE_PROJECT_ID` is set, `supabase link --project-ref` is not required as a separate step; `LoadProjectRef` resolves from the env var first.

**Option B — explicit link step then push:**
```bash
supabase link --project-ref "$PROJECT_REF"
supabase db push --linked --dry-run
```
This writes the ref to `.supabase/project-ref` so subsequent commands find it automatically.

**Option C — db-url (skips all linking):**
```bash
supabase db push --db-url "postgresql://postgres:$DB_PASSWORD@db.$PROJECT_REF.supabase.co:5432/postgres" --dry-run
```
No auth token required. The connection string is fully self-contained.

### Environment variables (confirmed from source)

All variables use the `SUPABASE_` prefix. Viper is configured as:
```go
viper.SetEnvPrefix("SUPABASE")
viper.SetEnvKeyReplacer(strings.NewReplacer("-", "_"))
viper.AutomaticEnv()
```

| Env var | Viper key | Purpose |
|---------|-----------|---------|
| `SUPABASE_ACCESS_TOKEN` | read via `os.Getenv` directly in `internal/utils/access_token.go` | Authenticates API calls (required for `--linked`) |
| `SUPABASE_PROJECT_ID` | `PROJECT_ID` | Sets the project ref — equivalent to `--project-ref` |
| `SUPABASE_DB_PASSWORD` | `DB_PASSWORD` | Database password — skips interactive prompt |

**Important distinction:** `SUPABASE_ACCESS_TOKEN` is read with `os.Getenv("SUPABASE_ACCESS_TOKEN")` directly, not through Viper. The others go through `viper.GetString("PROJECT_ID")` and `viper.GetString("DB_PASSWORD")` after Viper's `AutomaticEnv()` strips the `SUPABASE_` prefix.

There is no `SUPABASE_PROJECT_REF` env var. The correct name is `SUPABASE_PROJECT_ID`.

### Minimal CI workflow (GitHub Actions)

```yaml
- uses: supabase/setup-cli@v1
  with:
    version: latest

- name: Dry-run migrations
  env:
    SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
    SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID }}
    SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
  run: supabase db push --linked --dry-run
```

No explicit `supabase link` step is required when `SUPABASE_PROJECT_ID` is set, because `LoadProjectRef` in `internal/utils/flags/project_ref.go` reads the env var before falling back to the `.supabase/project-ref` file.

### How `--linked` resolves the connection

When `--linked` is passed, `ParseDatabaseConfig` calls `LoadProjectRef` (which reads `SUPABASE_PROJECT_ID` or the linked file), then calls `NewDbConfigWithPassword`. That function:

1. Sets `Password` from `viper.GetString("DB_PASSWORD")` (i.e., `SUPABASE_DB_PASSWORD`).
2. Attempts a direct TCP connection to `db.<project-ref>.supabase.co:5432`.
3. If direct connection fails (IPv6 not supported on CI runners), falls back to the connection pooler.
4. If no password is provided, calls the Management API to create a temporary login role (requires `SUPABASE_ACCESS_TOKEN`).

## Sources

- Source code: `internal/utils/flags/project_ref.go` — `LoadProjectRef` function
- Source code: `internal/utils/flags/db_url.go` — `ParseDatabaseConfig`, `NewDbConfigWithPassword`
- Source code: `internal/utils/access_token.go` — `loadAccessToken`
- Source code: `cmd/root.go` — Viper prefix configuration
- Source code: `cmd/link.go` — `PreRunE` shows `viper.IsSet("PROJECT_ID")` check
- Docs: https://supabase.com/docs/reference/cli/supabase-db-push
- Docs: https://supabase.com/docs/reference/cli/supabase-link

## Open Questions

- Does `supabase db push --dry-run` (without `--linked` or `--local`) default to linked when a project ref is available? The source checks flag state first; if neither `--linked` nor `--local` is explicitly passed, `connType` stays `unknown` and no remote connection is made. **Always pass `--linked` explicitly in CI.**
- The `--yes` global flag may be needed to suppress confirmation prompts in non-dry-run pushes; `--dry-run` skips all prompts by design.
