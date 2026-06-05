# TM channels: Electron identity and the inner loop

Scout output (read-only pass over `ml/auth-wire`, 2026-07-28). Companion to the persistent-state scout's inventory; this doc covers run modes, Electron identity, and the developer inner loop. Citations are `file:symbol`.

## Verdict up front

The channel design is mostly right and already committed in one place (`api/src/transport_matters/channel-specs.json`). Two structural gaps cause the blurred boundaries:

1. **`stable` is an editable install of whatever tree last ran `just install-local`.** Verified on this machine: the uv tool's `_editable_impl_transport_matters.pth` points at `.claude/worktrees/multi-launch/api/src` — the daily driver is currently running the `ml/auth-wire` feature worktree's Python, live, on every edit. "Stable" is a channel of state, not a channel of code.
2. **`stable` and dev-desktop share one Electron userData root.** `stable`'s spec has `userDataDir: null`, and `just dev desktop` defaults to `channel=stable`, so the installed daily driver, the dev harness, and the packaged .app all write `~/Library/Application Support/Transport Matters`. Dev-desktop also shares stable's home (`~/.transport-matters`) and stable's Postgres database — the only isolation dev mode has today is ports.

The two-userData-roots mystery is historical, not a live bug (explained below).

## 1. The three run modes as they exist today

| | stable | preview | dev desktop |
|---|---|---|---|
| Command | `transport-matters desktop` | `just channel-restart preview` | `just dev desktop` |
| Code source | uv tool install `--editable` — **currently this worktree** (`justfile:install-local`) | working tree via `uv run --project api` (`justfile:channel-restart`) | working tree via `uv run` + Vite dev server (`scripts/local-desktop-dev-mode.sh`) |
| ChannelSpec | `stable` | `preview` | **`stable` by default** (`local-desktop-dev-mode.sh` `channel="${TRANSPORT_MATTERS_CHANNEL:-stable}"`) |
| Home / tier-1 | `~/.transport-matters` (`storage_roots.py:default_storage_root`) | `~/.transport-matters-preview` | `~/.transport-matters` — **stable's** |
| Database | `transport_matters` | `transport_matters_preview` | `transport_matters` — **stable's** (resolved for the stable channel in the dev script's `database_url` block) |
| Ports | 8787/8788/8789 | 8797/8798/8799 | 18787/18788/18789 + Vite 15173, hardcoded in the script, not in any spec |
| Electron launch | unpackaged `electron <repo>/desktop` (`desktop_viewer.py:resolve_electron_launch` walks parents of the installed package — editable, so it finds this worktree's `desktop/`) | unpackaged, same resolution from the working tree | `pnpm --filter transport-matters-desktop dev` = tsc build + `electron .`, hosted viewer on the Vite URL (`TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`) |
| Electron name / userData | `setName("Transport Matters")` in `main.ts:applyChannelIdentity`; `userDataDir: null` → default `~/Library/Application Support/Transport Matters` | `setName("Transport Matters Preview")`, explicit `~/.transport-matters-preview/electron-user-data` | same identity as stable → **same userData root as stable** |
| Gateway | backend-supervised from the workspace/wheel (`gateway_supervisor.py:plan_gateway_supervision`; `GATEWAY_SUPERVISE=1` set in `desktop_cmd.py:_build_desktop_backend_env`) | same | separate tmux pane, `node --import tsx src/main.ts`, supervision suppressed via `TRANSPORT_MATTERS_GATEWAY_URL` |
| Dock | plain Electron icon | amber icon + `PREVIEW` badge | plain Electron icon, indistinguishable from stable |

There is also the plain CLI capture path (`just start` → `transport-matters claude`), which writes to the active channel home (stable unless `TRANSPORT_MATTERS_CHANNEL` says otherwise) and is orthogonal to the desktop.

## 2. Why two Electron userData roots exist

Both are real, and the split is a clean before/after:

- **`~/Library/Application Support/transport-matters-desktop`** — created May 4, last written **Jun 20 04:10**, dormant since. Before commit `87d6d3e2` (#159, merged **2026-06-20**, which introduced `applyChannelIdentity`/`setName`), unpackaged `electron .` used the package.json name `transport-matters-desktop` for its default userData. This is the pre-channels legacy root. Safe-to-delete candidate (deferred to the state-inventory scout; nothing was deleted in this pass).
- **`~/Library/Application Support/Transport Matters`** — active today (mtime Jul 28 06:40). Every unpackaged run since #159 with the stable spec calls `setName("Transport Matters")` before `app.whenReady`, which redirects the lazily-resolved default userData. Empirically confirmed: `com.github.Electron.plist` (the unpackaged Electron binary's own bundle id) was touched Jul 28 06:39, one minute before this root — an unpackaged run wrote here today. Three writers share this one root: installed stable, `just dev desktop`, and the packaged .app (productName `Transport Matters` in `desktop/electron-builder.yml`).

The three preference plists follow the same timeline:

- `com.electron.transport-matters.plist` + helper (May 4 / Jun 7): electron-builder packaging **before** `appId` was configured — its default is `com.electron.${name}`. `appId: io.helioy.transport-matters` only landed in `electron-builder.yml` with `5534a296` (#251, 2026-07-09). Dead residue.
- `io.helioy.transport-matters.plist` (Jul 26): current packaged .app (`just dmg` smoke).
- `com.github.Electron.plist` (Jul 28): every unpackaged dev/stable run. On macOS, preference identity comes from the binary's `CFBundleIdentifier`; `app.setAppUserModelId` (`main.ts:applyChannelIdentity`) is a Windows-only API and does not change this.

## 3. Electron identity: what's right, what's the one gap

**Already right, keep as is:**
- One committed spec fans out to every boundary (`channel-specs.json` → `channel.py:ChannelSpec` and `env.ts:resolveDesktopChannelSpec` parse the same file). This is the correct shape; do not add a config layer on top.
- Preview is fully isolated: own name, appId, explicit userData under its own home, amber icon + badge. This matches Electron best practice (Beta/Dev builds of VS Code, Slack, Discord all do exactly this: distinct productName, distinct bundle id suffix, distinct userData).
- Packaged identity is right: `electron-builder.yml` sets `appId: io.helioy.transport-matters` / `productName: Transport Matters`, so the .app's Info.plist carries the real bundle id.

**The one gap: `stable.userDataDir: null` plus dev defaulting to the stable channel.** Two remedies, in preference order:

1. **Give dev its own channel entry** (recommended). Add a third spec `dev` to `channel-specs.json`: `homeDir: .transport-matters-dev`, `databaseName: transport_matters_dev`, the 18787/18788/18789 ports that `local-desktop-dev-mode.sh` already hardcodes, `appName: "Transport Matters Dev"`, `appId: io.helioy.transport-matters.dev`, explicit `userDataDir`, and its own icon/badge (a second tinted PNG next to `desktop/assets/preview-amber.png`). Then `local-desktop-dev-mode.sh` defaults `channel=dev` and reads its ports from the spec (it already parses the spec file for port lookup — the mechanism exists, it just reads the wrong entry). This deletes the ad-hoc port block rather than adding machinery, and dev stops writing stable's home, database, and renderer localStorage. Cost: one JSON entry, one icon, ~20 lines of script simplification, one `ensure-db dev`.
2. **Give stable an explicit `userDataDir`** (`~/.transport-matters/electron-user-data`, mirroring preview). Makes stable self-contained and makes a future `reset` verb spec-derivable. Trade-off: the existing default root holds live renderer state — canvas layout persists via zustand → localStorage — and switching the path orphans it (old root left behind, layouts appear wiped). If done, it needs a one-time copy of the old root, which is exactly the kind of persistence migration that has bitten before. Not urgent once (1) removes the second writer; the packaged .app and installed stable writing one shared root is then correct, since they are the same channel.

**Explicitly not recommended now (searched, none exist, keep it that way until packaged distribution is real):**
- Protocol handlers: no `setAsDefaultProtocolClient` anywhere in `desktop/src`. None needed.
- Auto-update channels: no `autoUpdater` usage; DMG-1 is unsigned and signing is a later slice per `electron-builder.yml`. Wiring update channels before signing is dead code.
- macOS dock identity for unpackaged runs will always be the Electron binary (`com.github.Electron`); only `dock.setIcon` differentiates. Accept this for dev/preview; real identity arrives with the packaged app.

## 4. The inner loop today, and ranked improvements

### Where time goes per mode

- **`just dev desktop`** (`scripts/local-desktop-dev-mode.sh`, 2x2 tmux: backend | gateway / Vite | Electron):
  - Renderer edit (`@tm/inspector`, `@tm/canvas`, `@tm/core`, shell): **Vite HMR, sub-second.** Workspace packages are source deps, so HMR covers all of them. This part of the loop is already excellent.
  - Python edit: **no reload.** `desktop_cmd.py:serve_desktop_backend` runs uvicorn without reload (the only reload in the repo is `__main__.py`, the bare API dev server). Manual: Ctrl-C the backend pane, re-run, wait for health (~5–10s), re-arm any in-app state.
  - Gateway edit: **no watch.** The pane runs `node --import tsx src/main.ts`; manual Ctrl-C + re-run.
  - Electron main edit: quit the viewer (which tears down the whole window via the `--teardown` path) and re-run `just dev desktop`; `pnpm dev` re-runs tsc first. Rare edits, but the teardown coupling makes it the most expensive restart.
- **`just channel-restart preview`**: `pnpm install` + **four sequential package builds** (inspector Vite, canvas Vite, gateway esbuild, desktop tsc) + `electron:install` + stop/ensure-db/launch. Realistically 1–3 minutes wall-clock (estimate; two full Vite production builds dominate). This is the only way to see working-tree changes under the preview identity.
- **stable**: no loop — except that the editable install means Python edits leak in silently (gap #1), which is worse than slow.

### Ranked improvements (time saved per day vs cost)

1. **Un-editable stable** — not a speed win but the highest-value boundary fix, so it leads the list. `justfile:install-local` swaps `uv tool install --editable "{{api_dir}}"` for a wheel build + install (the wheel path already exists end-to-end in `justfile:verify-wheel`); `channel promote` (`channel_cmd.py:run_install_local`) inherits the fix for free. Trade-off: install-local gets slower (wheel build); that is the point — stable stops tracking the tree. Cost: ~5 justfile lines.
2. **Backend auto-reload in the dev harness** — biggest daily time saver for API work. In dev-desktop the gateway is external (`TRANSPORT_MATTERS_GATEWAY_URL` suppresses supervision per `desktop_cmd.py:_build_desktop_backend_env`), so uvicorn reload cannot orphan a supervised gateway there. Precedent exists in `__main__.py` (`reload=True`). Wire a `--reload` flag through `_desktop-backend` that only the dev script sets. Trade-off: a reload kills in-flight captured runs (mitmdump children) — acceptable in a dev harness, and worth stating in the flag's help. Cost: small flag + one script line; saves the restart-and-rewait cycle on every Python edit.
3. **Gateway watch in the dev pane** — change the dev script's gateway command to `tsx watch src/main.ts`. The file's own comment avoids a pnpm/tsx *wrapper* for the desktop-spawned child because it swallows SIGTERM; the dev pane is tmux-owned and killed by Ctrl-C/teardown directly, so that concern does not transfer — but verify teardown still exits cleanly once before keeping it. Cost: one word.
4. **Parallelize the preview rebuild** — collapse the four sequential builds in `justfile:channel-restart` into one `pnpm --filter @tm/inspector --filter @tm/canvas --filter @tm/gateway --filter transport-matters-desktop build` (pnpm parallelizes across the topology). Roughly halves the dominant build phase of every preview restart. Cost: one line. (Same collapse applies to `install-local`, `verify-wheel`, `dmg`.)
5. **Skip, deliberately:** Electron-main watch/relaunch tooling (electronmon or similar) — main-process edits are rare and the teardown choreography makes auto-relaunch fragile; not worth the machinery. Renderer already has HMR.

## 5. The reset story

Today there is **no reset verb** (`channel_cmd.py` has `list`/`status`/`stop`/`ensure-db`/`promote` only; the only "reset" hits in `cli/` are codex-session internals). A real reset is four manual deletions across four stores (runtime record + processes, Postgres DB, channel home, Electron userData), and missing one is exactly how blurred state accumulates.

What `just reset <channel>` (backed by `transport-matters channel reset <channel>`) should mean:

1. `channel stop <channel>` (existing path).
2. Drop and recreate the channel database, then `ensure_channel_database` (existing path) so it comes back migrated.
3. Delete the channel home (`ChannelSpec.home`).
4. Delete the channel's Electron userData **only when `electron_user_data` is non-null in the spec** — the spec is the sole path authority; the verb must never glob `~/Library/Application Support`. (This is another reason gap-fix 3.1/3.2 matters: today stable's userData is not spec-owned, so a reset verb literally cannot reach it safely.)

Guardrails:

- **`stable` refuses `reset` outright.** Not a confirmation — a hard error naming what to do instead (stop + targeted manual deletion). The daily driver's history is the product; a one-word typo must not be able to erase it.
- `preview`/`dev` reset requires typing the channel id back (the `gh repo delete` pattern), plus `--yes` for scripted use.
- Every deleted path is printed before deletion, derived from `ChannelSpec`, never from the environment (`TRANSPORT_MATTERS_HOME` set → refuse, since the spec-to-path mapping no longer holds; `channel.py` already documents that override collapsing channels).

## Searches run (for the "none found" claims)

- `rg setAsDefaultProtocolClient|autoUpdater desktop/src` → none.
- `rg reload api/src` → only `__main__.py` (bare API dev server) and unrelated comments.
- `rg -l reset api/src/transport_matters/cli` → codex session internals only; no channel reset.
- uv tool editable target: `~/.local/share/uv/tools/transport-matters/.../_editable_impl_transport_matters.pth` → `.claude/worktrees/multi-launch/api/src`; installed version `0.3.0.post1.dev339+g9734986ae` = this branch's HEAD.
