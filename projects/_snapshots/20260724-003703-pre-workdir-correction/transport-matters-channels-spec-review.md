---
title: Transport Matters channels spec — architect review
type: review
tags: [transport-matters, channels, review, adversarial, desktop, postgres]
summary: Adversarial pass over the channels implementation spec, verified against main. 2 Major, 4 Minor; seam accuracy otherwise strong.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# Channels spec — architect review (read-only, verified against `main`)

Reviewed: `~/.mdx/projects/transport-matters-channels-spec.md`
Baseline: clean working tree on `main`. Locked design in the proposal (2-rung shape,
naming, one `--channel` knob) treated as final and not re-opened.

**Verdict: conditional sign-off.** Substantive issues found. 2 Major, 4 Minor.
The locked design is sound; the issues are in the spec's *mechanisms* (packaging,
a cross-feature contract change, two DRY/ordering nits), all fixable without
touching the locked scheme.

Verification method: fmm symbol lookups + `git`-clean `main` grep. Every cited
seam below was confirmed present on `main` unless flagged.

---

## Major

### M1 — Single-source file at repo root breaks the Python wheel/sdist packaging mechanism (item 2)

The spec places `channel-specs.json` at the **repo root** and asks for "a hatch
`force-include` that places `channel-specs.json` at `transport_matters/channel-specs.json`
in the wheel," with `channel.py` reading the packaged resource and an editable
fallback to the repo root.

The Python build root is **`api/`** (`api/pyproject.toml` → `[project.scripts]`
`transport-matters = "transport_matters.cli:main"`). A repo-root file is `../channel-specs.json`
relative to that root, and the existing packaging is rooted strictly inside `api/`:

- `[tool.hatch.build.targets.wheel].artifacts` and `force-include` resolve relative
  to `api/`; the current `force-include` is `"migrations" = "migrations"` (in-root).
  A parent-of-root source (`../channel-specs.json`) is not a supported/clean
  force-include.
- `[tool.hatch.build.targets.sdist].only-include = ["src/transport_matters", "migrations",
  "alembic.ini", "tests", "README.md", "LICENSE"]` — a repo-root file is in none of
  these and outside `api/`, so it is **absent from the sdist**. Any non-editable build
  (`python -m build`, CI wheel) ships without it; `channel.py`'s `importlib.resources`
  read then fails and the "editable fallback to repo root" does not exist in an
  installed package.
- The established precedent is the opposite: `settings.example.toml` lives **inside**
  the package at `src/transport_matters/settings.example.toml` and is packaged via
  `artifacts`.

Editable-only installs (`install-local` → `uv tool install --editable api/`, and
`promote` reusing that path) mask this at runtime via the repo-root fallback, but the
spec's stated force-include is unsound and a real source build breaks.

**Fix (location was not locked by the proposal — only the 2-rung shape + naming were):**
keep ONE committed source but place it under `api/src/transport_matters/channel-specs.json`,
packaged exactly like `settings.example.toml` via `artifacts`. Have
`desktop/scripts/copy-channel-specs.mjs` read `../api/src/transport_matters/channel-specs.json`
(the desktop build is rooted at `desktop/`). This preserves DRY (single source, both
languages read it), removes the force-include + sdist gap, and matches the existing
data-file convention.

### M2 — `config.resolve_database_url` change erases the no-config signal the no-DB/store-picker track depends on (item 6)

The spec adds a third fallback to `config.resolve_database_url`:
`TRANSPORT_MATTERS_DATABASE_URL` → `[database].url` → `resolve_channel_spec(settings.channel).database_url`.
This is load-bearing for the feature (out-of-box `stable` → `transport_matters`), but it
makes `resolve_database_url` **always return a URL**, removing the
`MissingDatabaseConfigError` raise that exists today (`config.py:resolve_database_url`).

`NOW.md` "No-DB startup + store picker" (researched) and Next-up #1 (onboarding) both
build on detecting "no store configured" and both extend the **same surface this spec
also extends**:

- `api/v1/meta.py:MetaResponse`/`get_meta` — channels adds `channel`/`channel_label`/
  `channel_badge`; no-DB adds `db_status`. Same symbol, same www consumer
  (`www/src/api.ts:Meta`/`fetchMeta`). Additive, but must be coordinated so they extend
  the response shape together rather than racing it.
- The store-picker's trigger: with the channel fallback, the user with no env/TOML no
  longer gets `MissingDatabaseConfigError`; they get a channel URL pointing at a
  presumed-local server. The picker must therefore key off **connectivity**
  (`check_session_store` / the two guards `launch_runtime.preflight_session_store_or_exit`
  and `run_manager.RunManager._ensure_session_store_available`), not the removed error.
  `session_store_setup_help()` guidance also shifts from "no DB configured" to
  "can't connect to `transport_matters_<channel>`".

**Fix:** call this out in the spec as a shared-surface coordination point — extend
`MetaResponse` additively (reserve room for `db_status`), and note that the no-config
error path is being replaced by a connectivity-based signal so the picker work keys off
`check_session_store` rather than `MissingDatabaseConfigError`. Not a blocker for the
channels build (no-DB is uncommitted), but it is exactly the item-6 collision and should
be recorded.

---

## Minor

### m3 — Port formula is re-encoded in two languages, against the proposal's explicit rule (item 2 DRY)

`channel-specs.json` stores `baseProxyPort`/`baseWebPort` + per-channel `offset`. The
derivation `port = base + 10*offset` is then computed **twice**: Python
`channel.resolve_channel_spec` (producing `ChannelSpec.proxy_port`/`web_port`) and TS
`env.ts:resolveDesktopChannelSpec` (same shape). The locked proposal says verbatim
"Never re-encode the port math in two languages." The JSON single-sources the *data* but
not the *formula*.

**Fix:** store the resolved `proxyPort`/`webPort` per channel directly in
`channel-specs.json` (drop `baseProxyPort`/`baseWebPort`/`offset`, or keep them as
comments). Then both languages only *read*; neither computes. Color/badge is already
correctly single-sourced (`badge.hex`), so only the port math needs this.

### m4 — `storage/disk_layout.py:_DEFAULT_ROOT` is an eager snapshot omitted from the asserted storage cascade (item 1)

The spec asserts the `default_storage_root` change "cascades to `workspace.workspace_root`,
`workspace.run_root`, the per-run tier 1 tree, settings scaffold, and the shared proxy
runtime directory" and relies on everything being lazy. One place is **not** lazy:
`storage/disk_layout.py` binds `_DEFAULT_ROOT = default_storage_root()` at **module import**,
used as the fallback `.root` in `DiskStorageLayout.__init__`. `disk_layout` is imported
during desktop startup (via `cli/desktop_cmd` → `transport_matters.main` → storage stack),
i.e. **before** `activate_channel` runs as the command's first statement — so `_DEFAULT_ROOT`
freezes to the `stable` home regardless of `--channel`.

Currently **dormant**, not a live bug: the two module-level singletons that construct
without a root (`codex/exchange.py:_STORAGE_LAYOUT`, `exchange_recorder.py:_STORAGE_LAYOUT`)
call only the stateless, root-independent helper `exchange_index_path_for`; every real
write path constructs `DiskStorageLayout(root)` with an explicit channel-derived root
(`storage/disk.py`, `storage/session_facts.py`, `storage/transcript_snapshot.py`,
`session/backfill.py`). But it is a latent cross-wire: any future default-constructed
layout that touches a `.root`-dependent path (`index_path`, `new_exchange_dir`,
`transcript_snapshot_path`, …) on the channel path would silently write `preview` into the
`stable` home.

**Fix:** make `_DEFAULT_ROOT` lazy (a function/property re-reading `default_storage_root()`),
or add an explicit note + guard that no channel-path construction relies on the default
root. Cheap to harden now; expensive to debug later.

### m5 — `serve_desktop_backend` ordering description omits the in-between preflight (item 1)

The spec says `serve_desktop_backend` "already applies `plan.env`, then clears
`get_settings`, then calls `create_app`; preserve that order." On `main` the real order is
`_apply_desktop_backend_env(plan.env)` → **`preflight_session_store_or_exit()`** →
`get_settings.cache_clear()` → `create_app()`. The omitted preflight itself calls
`get_settings.cache_clear()` then `check_session_store()`, i.e. it *resolves the DB* before
the spec's named cache-clear. This is benign only because `_build_desktop_backend_env` is
required (correctly, per the spec) to carry `TRANSPORT_MATTERS_CHANNEL`, so the channel env
is applied before preflight resolves the URL. The spec's "preserve that order" should name
the preflight step explicitly so the invariant "channel env applied before preflight
resolves DB" is stated, not implied.

(Positive: the broader ordering claim checks out. No module-level `get_settings()` runs in
the CLI import graph — the only one, `__main__.py:settings = get_settings()`, is the
`python -m` dev server, not the `cli:main` entry point — and `activate_channel`'s defensive
`cache_clear` neutralizes any import-time cache. `disk_layout` in m4 is the sole "not lazy"
exception.)

### m6 — Slice/packaging completeness + two gate nits (item 5)

- The `api/pyproject.toml` packaging edit (artifacts/force-include/sdist for the channel
  spec file) is **not in any slice's explicit file list** (slice 1 lists
  `channel-specs.json, channel.py, env_keys.py, config.py, storage_roots.py,
  settings.example.toml, tests`). `channel.py`'s packaged-resource read can't work without
  it — add `api/pyproject.toml` to slice 1.
- Slice 3 gate cites `just channel-restart preview --dry-run` "if the recipe grows a dry run
  flag" — that flag does not exist; either drop the gate line or commit to adding `--dry-run`.
- `migration-smoke` lives only in `api ci` (`api/justfile`), not in root `just check`/`just
  test`. The DB-lifecycle slice (3) touches `session/migrate.py` and the migration-advisory
  lock (`session/migrate.py:_MIGRATION_ADVISORY_LOCK_KEY`) but its gate is `api just test` +
  common final gate, neither of which runs `migration-smoke`. Add `cd api && just ci` (or
  `just migration-smoke`) to slice 3.

---

## Positively verified (no issue)

- **Seam accuracy (item 4):** all cited symbols exist on `main` —
  `storage_roots.default_storage_root`, `config.resolve_database_url`/`get_settings`
  (`@lru_cache`)/`Settings`, `launch_runtime.resolve_launch_ports`/`preflight_session_store_or_exit`,
  `desktop_cmd._resolve_backend_ports`/`_build_desktop_backend_env`/`_build_desktop_backend_command`/
  `prepare_desktop_launch`/`serve_desktop_backend`/`spawn_detached_electron`,
  `cli/__init__.py` commands `claude`/`codex`/`desktop`/hidden `desktop_backend`
  (`hidden=True`, name `DESKTOP_BACKEND_COMMAND`), `run_manager.RunManager._ensure_session_store_available`,
  `session/migrate.apply_migrations`, `launch_environment.build_launch_env`,
  `shared_proxy/manager.SharedProxyManager.create` + `_control_socket_path`,
  `db_cmd.db_app`/`_resolve_or_exit`, `api/v1/meta.py:MetaResponse`/`get_meta`/`get_run_meta`,
  `desktop/src/main.ts:registerDesktopLifecycleFromEnv`/`resolveBackendStartupOptions`,
  `desktop/src/backendProcess.ts:buildBackendLaunch`, `desktop/src/window.ts:createWindowOptions`/`APP_NAME`,
  `desktop/src/env.ts:ENV` (has `PROXY_PORT`/`WEB_PORT`; `CHANNEL` to be added),
  `www/src/api.ts:Meta`/`fetchMeta`, `www/src/rootShell.tsx`, `www/src/components/WindowDragRegion.tsx`.
- **`spawn_detached_electron` channel propagation:** builds env from `{**os.environ, …}`, so
  `TRANSPORT_MATTERS_CHANNEL` set by `activate_channel` in the parent flows to hosted viewers
  without an explicit add — consistent with the spec.
- **Pill placement correction is right:** moving the pill out of `WindowDragRegion` (the
  `aria-hidden` drag map mounted before `#root`) into a new `ChannelBadge.tsx` in
  `rootShell.tsx` is correct; anything visible inside `WindowDragRegion` sits under the app.
- **Gate recipes (item 5) are real and quoted accurately:** root `just check`/`test` fan out
  to `desktop`/`www`/`api`; `desktop check: typecheck test` + `package-smoke`; `www check:
  format lint typecheck`; `api check: format lint typecheck` + `ci` (`…migration-smoke…
  pytest`); `api test *args` accepts file args. Gate test files exist
  (`test_start.py`/`test_codex.py`/`test_desktop.py`/`test_launch_preflight.py`/`test_meta.py`/
  `test_config.py`/`test_env_keys.py`); `test_channel.py`/`test_channel_cmd.py` are net-new.
- **Slice ordering** otherwise satisfies dependencies (1 foundation → 2 CLI/ports → 3 DB →
  4 desktop/badge → 5 smoke/promote).
- **Traceability rule satisfied:** the spec uses file+symbol throughout; no `file:line`
  anchors found.
